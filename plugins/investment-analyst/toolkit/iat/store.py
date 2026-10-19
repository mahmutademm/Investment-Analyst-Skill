"""CSV-first storage with a rebuildable SQLite cache.

Git-friendly rule: everything that GitHub Actions commits is plain CSV/JSON/Markdown, appended or
replaced in small pieces. `iat sync` rebuilds data/iat.db from those files whenever needed.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from iat.config import Workspace


def today() -> str:
    return dt.date.today().isoformat()


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _json_default(o: Any):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (pd.Timestamp, dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def clean_json(obj: Any) -> Any:
    """Replace NaN/inf with None recursively so JSON stays valid."""
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v) for v in obj]
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if (np.isnan(f) or np.isinf(f)) else f
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def write_json(path: Path, obj: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(obj), indent=2, default=_json_default, ensure_ascii=False), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, df: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return path


def append_history(ws: Workspace, name: str, df: pd.DataFrame, keys: Iterable[str]) -> Path:
    """Append rows to data/history/<name>.csv, de-duplicating on `keys` (last write wins)."""
    path = ws.out_dir("history") / f"{name}.csv"
    keys = list(keys)
    if path.exists():
        old = pd.read_csv(path)
        df = pd.concat([old, df], ignore_index=True)
    df = df.drop_duplicates(subset=keys, keep="last").sort_values(keys).reset_index(drop=True)
    return write_csv(path, df)


def write_latest_json(ws: Workspace, name: str, obj: dict) -> Path:
    obj = dict(obj)
    obj.setdefault("as_of", now())
    return write_json(ws.out_dir("latest") / f"{name}.json", obj)


def write_latest_csv(ws: Workspace, name: str, df: pd.DataFrame, as_of: str | None = None) -> Path:
    df = df.copy()
    df.insert(0, "as_of", as_of or now())
    return write_csv(ws.out_dir("latest") / f"{name}.csv", df)


def read_latest_json(ws: Workspace, name: str) -> dict | None:
    best: dict | None = None
    for folder in ws.read_candidates("latest"):
        p = folder / f"{name}.json"
        if p.exists():
            obj = read_json(p)
            if best is None or str(obj.get("as_of", "")) > str(best.get("as_of", "")):
                best = obj
    return best


def read_latest_csv(ws: Workspace, name: str) -> pd.DataFrame | None:
    best: pd.DataFrame | None = None
    best_stamp = ""
    for folder in ws.read_candidates("latest"):
        p = folder / f"{name}.csv"
        if p.exists():
            df = pd.read_csv(p)
            stamp = str(df["as_of"].iloc[0]) if "as_of" in df and len(df) else ""
            if best is None or stamp > best_stamp:
                best, best_stamp = df, stamp
    return best


def read_history(ws: Workspace, name: str) -> pd.DataFrame | None:
    frames = [pd.read_csv(f / f"{name}.csv") for f in ws.read_candidates("history") if (f / f"{name}.csv").exists()]
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def write_report(ws: Workspace, name: str, markdown: str) -> Path:
    folder = ws.out_dir("reports")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}_latest.md").write_text(markdown, encoding="utf-8")
    dated = folder / "archive" / f"{name}_{today()}.md"
    dated.parent.mkdir(parents=True, exist_ok=True)
    dated.write_text(markdown, encoding="utf-8")
    return folder / f"{name}_latest.md"


# ---- SQLite -------------------------------------------------------------------

def _table_name(*parts: str) -> str:
    raw = "_".join(p for p in parts if p)
    return re.sub(r"[^0-9a-zA-Z_]", "_", raw).strip("_").lower()


def sync_db(ws: Workspace) -> dict[str, int]:
    """Rebuild data/iat.db from every CSV in the workspace data folders. Returns {table: rows}."""
    ws.data.mkdir(parents=True, exist_ok=True)
    if ws.db_path.exists():
        ws.db_path.unlink()
    counts: dict[str, int] = {}
    con = sqlite3.connect(ws.db_path)
    try:
        for kind in ("history", "latest", "tracking", "universes"):
            for folder, prefix in ((getattr(ws, kind), kind), (ws.local / kind, f"local_{kind}")):
                if not folder.exists():
                    continue
                for csv in sorted(folder.glob("*.csv")):
                    df = pd.read_csv(csv)
                    t = _table_name(prefix, csv.stem)
                    df.to_sql(t, con, if_exists="replace", index=False)
                    counts[t] = len(df)
        # screens: data/screens/<key>/<date>.csv -> one table "screens"
        frames = []
        for base in (ws.screens, ws.local / "screens"):
            if not base.exists():
                continue
            for csv in sorted(base.glob("*/*.csv")):
                df = pd.read_csv(csv)
                df.insert(0, "screen_date", csv.stem)
                df.insert(0, "screen_key", csv.parent.name)
                frames.append(df)
        if frames:
            allscreens = pd.concat(frames, ignore_index=True)
            allscreens.to_sql("screens", con, if_exists="replace", index=False)
            counts["screens"] = len(allscreens)
        con.commit()
    finally:
        con.close()
    return counts


def query(ws: Workspace, sql: str) -> pd.DataFrame:
    if not ws.db_path.exists():
        sync_db(ws)
    con = sqlite3.connect(ws.db_path)
    try:
        return pd.read_sql_query(sql, con)
    finally:
        con.close()
