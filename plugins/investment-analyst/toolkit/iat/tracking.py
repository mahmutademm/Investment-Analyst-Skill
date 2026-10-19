"""Watchlist, decision journal and daily checks (price stops, sector RS, earnings dates, catalysts)."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from iat import rotation, store
from iat.config import SECTOR_ETFS, Workspace

WATCH_COLS = ["ticker", "status", "sector", "sub_industry", "sector_etf", "added", "entry_ref_price", "atr_at_entry",
              "price_stop", "thesis", "thesis_stop", "catalyst", "catalyst_date", "tranche_plan", "shares_held",
              "next_review", "notes"]
JOURNAL_COLS = ["date", "ticker", "action", "price", "shares", "gate_status", "expected_return", "reason", "override"]
STATUSES = ["watch", "tranche1", "tranche2", "full", "closed"]


def _path(ws: Workspace, name: str):
    ws.tracking.mkdir(parents=True, exist_ok=True)
    return ws.tracking / f"{name}.csv"


def load_watchlist(ws: Workspace) -> pd.DataFrame:
    p = _path(ws, "watchlist")
    if p.exists():
        df = pd.read_csv(p, dtype={"ticker": str})
        for c in WATCH_COLS:
            if c not in df:
                df[c] = None
        return df[WATCH_COLS]
    return pd.DataFrame(columns=WATCH_COLS)


def save_watchlist(ws: Workspace, df: pd.DataFrame) -> None:
    store.write_csv(_path(ws, "watchlist"), df[WATCH_COLS])


def upsert(ws: Workspace, ticker: str, **fields) -> pd.DataFrame:
    df = load_watchlist(ws)
    t = ticker.upper()
    fields = {k: v for k, v in fields.items() if v is not None and k in WATCH_COLS}
    if "sector" in fields and "sector_etf" not in fields:
        fields["sector_etf"] = SECTOR_ETFS.get(fields["sector"], "")
    if t in set(df["ticker"]):
        for k, v in fields.items():
            df.loc[df["ticker"] == t, k] = v
    else:
        row = {c: None for c in WATCH_COLS}
        row.update({"status": "watch", "added": store.today()})
        row.update(fields)
        row["ticker"] = t
        df = pd.DataFrame([row]) if df.empty else pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_watchlist(ws, df)
    return df


def journal(ws: Workspace, **entry) -> None:
    p = _path(ws, "journal")
    old = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=JOURNAL_COLS)
    row = {c: entry.get(c) for c in JOURNAL_COLS}
    row["date"] = row["date"] or store.now()
    store.write_csv(p, pd.concat([old, pd.DataFrame([row])], ignore_index=True)[JOURNAL_COLS])


def check(ws: Workspace) -> pd.DataFrame:
    df = load_watchlist(ws)
    active = df[df["status"].fillna("watch") != "closed"]
    if active.empty:
        return pd.DataFrame()
    tickers = active["ticker"].tolist()
    etfs = [e for e in active["sector_etf"].dropna().unique().tolist() if e]
    px = rotation.download(tickers + etfs + ["SPY"], period="1y")
    rot = store.read_latest_csv(ws, "rotation")
    rot_by = {r["ticker"]: r.to_dict() for _, r in rot.iterrows()} if rot is not None else {}
    th = ws.settings["thresholds"]
    out = []
    for _, w in active.iterrows():
        t = w["ticker"]
        c = px["Close"][t].dropna() if t in px["Close"] else pd.Series(dtype=float)
        if c.empty:
            out.append({"ticker": t, "alerts": "NO PRICE DATA"})
            continue
        price = float(c.iloc[-1])
        a = rotation.atr(px["High"][t], px["Low"][t], px["Close"][t]).dropna()
        atr = float(a.iloc[-1]) if len(a) else np.nan
        stop = pd.to_numeric(w.get("price_stop"), errors="coerce")
        alerts = []
        if stop == stop and price <= stop:
            alerts.append(f"PRICE STOP HIT ({price:.2f} <= {stop:.2f})")
        elif stop == stop and atr == atr and price - stop < atr:
            alerts.append(f"within 1 ATR of stop ({price:.2f} vs {stop:.2f})")
        etf = w.get("sector_etf")
        rs = rot_by.get(etf, {}) if etf else {}
        if rs:
            if not rs.get("rs_pillar", True) and str(w.get("status")) in ("tranche1", "tranche2", "full"):
                alerts.append(f"sector RS no longer confirms ({etf}: {rs.get('status')}, {rs.get('quadrant')})")
            if rs.get("status") == "CONFIRMED" and str(w.get("status")) == "tranche1":
                alerts.append(f"tranche 2 trigger: {etf} relative strength CONFIRMED")
        for label, key in (("catalyst", "catalyst_date"), ("review", "next_review")):
            try:
                days = (dt.date.fromisoformat(str(w.get(key))[:10]) - dt.date.today()).days
                if 0 <= days <= th["earnings_soon_days"]:
                    alerts.append(f"{label} in {days}d")
                elif days < 0 and label == "catalyst":
                    alerts.append("catalyst date passed - did it close the gap? Re-check the thesis")
            except ValueError:
                pass
        entry = pd.to_numeric(w.get("entry_ref_price"), errors="coerce")
        out.append({"ticker": t, "status": w.get("status"), "price": price,
                    "chg_since_entry_pct": (price / entry - 1) * 100 if entry == entry and entry else np.nan,
                    "price_stop": stop, "atr14": atr, "sector_etf": etf, "sector_rs": rs.get("status") if rs else "",
                    "alerts": "; ".join(alerts)})
    res = pd.DataFrame(out)
    store.write_latest_csv(ws, "watch_check", res)
    return res


def markdown(res: pd.DataFrame) -> str:
    if res is None or res.empty:
        return "## Watchlist\n\nNo active positions.\n"
    lines = ["## Watchlist", "", "| Ticker | Status | Price | vs entry | Stop | Sector RS | Alerts |", "|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        def f(x, nd=2):
            return "" if x is None or x != x else f"{x:,.{nd}f}"
        lines.append(f"| {r['ticker']} | {r.get('status', '')} | {f(r.get('price'))} | {f(r.get('chg_since_entry_pct'), 1)}% | "
                     f"{f(r.get('price_stop'))} | {r.get('sector_rs', '')} | {r.get('alerts', '')} |")
    return "\n".join(lines) + "\n"
