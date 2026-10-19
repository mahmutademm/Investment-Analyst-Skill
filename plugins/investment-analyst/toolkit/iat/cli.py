"""Command line entry point: `iat <command>`. Run `iat --help` or `iat <command> --help`."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import platform
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

import yaml

import iat
from iat import config, store
from iat.config import MARKER_FILE, Workspace

TEMPLATES = Path(__file__).parent / "templates" / "workspace"
PYPROJECT_VENDORED = """[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "iat-toolkit"
version = "{version}"
license = "MIT"
requires-python = ">=3.10"
dependencies = ["pandas>=2.0", "numpy>=1.24", "requests>=2.31", "yfinance>=0.2.60", "openpyxl>=3.1",
                "PyYAML>=6.0", "beautifulsoup4>=4.12", "lxml>=4.9"]

[project.scripts]
iat = "iat.cli:main"

[tool.setuptools.packages.find]
include = ["iat*"]

[tool.setuptools.package-data]
iat = ["templates/workspace/*", "templates/workspace/*/*", "templates/workspace/*/*/*"]
"""


def _ws(args) -> Workspace:
    return config.load(getattr(args, "workspace", None))


def _print(text: str) -> None:
    print(text, flush=True)


# ---------------------------------------------------------------------------
# init / doctor / status / config / state
# ---------------------------------------------------------------------------

def _license_text() -> str | None:
    """MIT notice for the vendored copy: from the installed dist-info, else the source tree."""
    from importlib import metadata
    try:
        for f in metadata.distribution("iat-toolkit").files or []:
            if f.name == "LICENSE":
                return f.read_text(encoding="utf-8")
    except metadata.PackageNotFoundError:
        pass
    src = Path(iat.__file__).parent.parent / "LICENSE"
    if src.is_file() and (src.parent / "pyproject.toml").is_file():
        return src.read_text(encoding="utf-8")
    return None


def vendor_toolkit(root: Path) -> None:
    dest = root / ".toolkit"
    if dest.exists():
        shutil.rmtree(dest)
    pkg = Path(iat.__file__).parent
    shutil.copytree(pkg, dest / "iat", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (dest / "pyproject.toml").write_text(PYPROJECT_VENDORED.format(version=iat.__version__), encoding="utf-8")
    text = _license_text()
    if text:
        (dest / "LICENSE").write_text(text, encoding="utf-8")


def copy_workflows(root: Path) -> None:
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    for f in (TEMPLATES / "github" / "workflows").glob("*.yml"):
        shutil.copy2(f, wf / f.name)


AGENTS_MARKER = "<!-- managed by iat"


def refresh_agent_files(root: Path, force: bool = False) -> list[str]:
    """AGENTS.md (read by most AI tools) is refreshed unless the user removed its managed-by line;
    CLAUDE.md only imports it, so it is created once."""
    done = []
    agents = root / "AGENTS.md"
    if force or not agents.exists() or agents.read_text(encoding="utf-8-sig").startswith(AGENTS_MARKER):
        shutil.copy2(TEMPLATES / "AGENTS.md", agents)
        done.append("AGENTS.md")
    claude = root / "CLAUDE.md"
    if force or not claude.exists():
        shutil.copy2(TEMPLATES / "CLAUDE.md", claude)
        done.append("CLAUDE.md")
    return done


def cmd_init(args) -> int:
    root = Path(args.path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("config", "data/history", "data/latest", "data/reports", "data/screens", "data/tracking",
                "data/universes", "filings", "output"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    created = []
    for src, dst in (("config/settings.yaml", "config/settings.yaml"),
                     ("config/sub_industries.yaml", "config/sub_industries.yaml"),
                     ("README.md", "README.md"), ("gitignore.txt", ".gitignore")):
        target = root / dst
        if target.exists() and not args.force:
            continue
        shutil.copy2(TEMPLATES / src, target)
        created.append(dst)
    created += refresh_agent_files(root, force=args.force)
    copy_workflows(root)
    vendor_toolkit(root)
    (root / MARKER_FILE).write_text(json.dumps({"toolkit_version": iat.__version__, "created": store.now()}),
                                    encoding="utf-8")
    for keep in ("data/tracking", "data/history", "data/latest", "data/reports", "data/screens", "data/universes"):
        gk = root / keep / ".gitkeep"
        if not any((root / keep).iterdir()):
            gk.touch()
    config.write_pointer(root)
    _print(f"Workspace ready: {root}")
    _print("Created/updated: " + ", ".join(created + [".github/workflows", ".toolkit", MARKER_FILE]))
    _print(f"Pointer saved to {config.POINTER_FILE}")
    _print("Next: iat config sec-agent \"<Your Name> <you@example.com>\"  then  iat doctor")
    return 0


def cmd_upgrade(args) -> int:
    ws = _ws(args)
    copy_workflows(ws.root)
    vendor_toolkit(ws.root)
    agent_files = refresh_agent_files(ws.root)
    (ws.root / MARKER_FILE).write_text(json.dumps({"toolkit_version": iat.__version__, "updated": store.now()}),
                                       encoding="utf-8")
    _print(f"Refreshed .toolkit, .github/workflows{''.join(', ' + f for f in agent_files)} in {ws.root} "
           f"(toolkit {iat.__version__}). Your config and data were not touched.")
    return 0


def cmd_doctor(args) -> int:
    rows: list[tuple[str, str, str]] = []

    def add(item, status, detail=""):
        rows.append((status, item, detail))

    add("Python", "OK" if sys.version_info >= (3, 10) else "FAIL", platform.python_version())
    for mod in ("pandas", "numpy", "requests", "yfinance", "openpyxl", "yaml", "bs4", "lxml"):
        try:
            m = importlib.import_module(mod)
            add(f"package {mod}", "OK", getattr(m, "__version__", ""))
        except Exception as exc:
            add(f"package {mod}", "FAIL", str(exc))
    add("iat-toolkit", "OK", iat.__version__)
    try:
        ws = _ws(args)
        add("workspace", "OK", str(ws.root))
        add("sub-industries defined", "OK" if ws.sub_industries else "WARN", str(len(ws.sub_industries)))
        pv = ws.settings["portfolio"].get("value")
        add("portfolio.value (position sizing)", "OK" if pv else "WARN", str(pv) if pv else "not set in settings.yaml")
        try:
            ua = ws.sec_user_agent()
            add("SEC contact User-Agent", "OK", "set (" + ("env" if "SEC_USER_AGENT" in __import__("os").environ else "local.yaml") + ")")
        except config.WorkspaceError:
            ua = None
            add("SEC contact User-Agent", "WARN", "not set: iat config sec-agent \"Name email\"")
        marker = json.loads((ws.root / MARKER_FILE).read_text(encoding="utf-8"))
        vend = marker.get("toolkit_version")
        add("vendored .toolkit version", "OK" if vend == iat.__version__ else "WARN",
            f"{vend} (installed {iat.__version__})" + ("" if vend == iat.__version__ else ": run iat upgrade"))
        add("data owner", "OK", ws.settings["data"].get("owner", "local"))
    except config.WorkspaceError as exc:
        ws, ua = None, None
        add("workspace", "FAIL", str(exc))
    if not args.offline:
        try:
            from iat import macro
            s = macro.fetch_series("DGS10", (dt.date.today() - dt.timedelta(days=20)).isoformat())
            add("FRED (no key)", "OK", f"DGS10 {s.iloc[-1]:.2f} on {s.index[-1].date()}")
        except Exception as exc:
            add("FRED (no key)", "FAIL", str(exc)[:120])
        try:
            import yfinance as yf
            h = yf.download("SPY", period="5d", progress=False, auto_adjust=True)
            add("Yahoo Finance (yfinance)", "OK" if len(h) else "FAIL", f"SPY rows {len(h)}")
        except Exception as exc:
            add("Yahoo Finance (yfinance)", "FAIL", str(exc)[:120])
        if ws is not None and ua:
            try:
                from iat.sec import Sec
                n = len(Sec(ws).ticker_map())
                add("SEC EDGAR", "OK", f"{n} tickers in map")
            except Exception as exc:
                add("SEC EDGAR", "FAIL", str(exc)[:160])
    git = shutil.which("git")
    add("git", "OK" if git else "WARN", git or "not found (needed for GitHub Actions sync)")
    if git and ws is not None:
        try:
            remote = subprocess.run(["git", "-C", str(ws.root), "remote", "-v"], capture_output=True, text=True, timeout=10)
            is_repo = remote.returncode == 0
            add("workspace git repo", "OK" if is_repo else "WARN", "yes" if is_repo else "not a git repo yet")
            if is_repo:
                add("git remote", "OK" if remote.stdout.strip() else "WARN",
                    remote.stdout.strip().splitlines()[0] if remote.stdout.strip() else "no remote: GitHub Actions not connected")
        except Exception:
            pass
    width = max(len(r[1]) for r in rows)
    for status, item, detail in rows:
        _print(f"[{status:4}] {item.ljust(width)}  {detail}")
    return 1 if any(r[0] == "FAIL" for r in rows) else 0


def _age(stamp: str | None) -> str:
    if not stamp:
        return "never"
    try:
        d = dt.datetime.fromisoformat(stamp[:19])
        days = (dt.datetime.now() - d).total_seconds() / 86400
        return f"{stamp[:16]} ({days:.1f} days ago)"
    except ValueError:
        return stamp


def cmd_status(args) -> int:
    ws = _ws(args)
    out = {"workspace": str(ws.root), "data_owner": ws.settings["data"].get("owner"), "state": ws.state}
    m = store.read_latest_json(ws, "macro")
    rot = store.read_latest_csv(ws, "rotation")
    out["macro"] = {"as_of": m["as_of"] if m else None,
                    "suggested_phase": m["cycle"]["suggested_phase"] if m else None}
    out["rotation"] = {"as_of": str(rot["as_of"].iloc[0]) if rot is not None else None}
    screens = {}
    for key in ws.sub_industries:
        s = store.read_latest_csv(ws, f"screen_{key}")
        if s is not None:
            screens[key] = {"as_of": str(s["as_of"].iloc[0]), "names": len(s)}
    out["screens"] = screens
    comps = {}
    cdir = ws.output / "companies"
    if cdir.exists():
        for f in sorted(cdir.iterdir()):
            if (f / "data.json").exists():
                d = store.read_json(f / "data.json")
                comps[f.name] = {"as_of": d.get("as_of"), "gate": d.get("gate_overall"),
                                 "notes": (f / "notes.json").exists(),
                                 "workbook": sorted(p.name for p in f.glob("*.xlsx"))[-1:] or None}
    out["companies"] = comps
    from iat import tracking
    wl = tracking.load_watchlist(ws)
    out["watchlist_active"] = int((wl["status"].fillna("watch") != "closed").sum()) if not wl.empty else 0
    if args.json:
        _print(json.dumps(store.clean_json(out), indent=2, default=str))
        return 0
    _print(f"Workspace: {ws.root}  (data owner: {out['data_owner']})")
    _print(f"Macro:     {_age(out['macro']['as_of'])}  suggested phase: {out['macro']['suggested_phase']}")
    _print(f"Rotation:  {_age(out['rotation']['as_of'])}")
    cyc = (ws.state.get("cycle") or {})
    _print(f"Your cycle call: {cyc.get('phase', 'not recorded')}  (recorded {cyc.get('date', '-')})")
    _print(f"Allocation: {ws.state.get('allocation', 'not recorded')}")
    _print(f"Active screens: {(ws.state.get('screening') or {}).get('active', [])}")
    for k, v in screens.items():
        _print(f"  screen {k}: {_age(v['as_of'])}, {v['names']} names")
    for k, v in comps.items():
        _print(f"  company {k}: {_age(v['as_of'])}, gate {v['gate']}, notes {'yes' if v['notes'] else 'no'}, "
               f"workbook {v['workbook']}")
    _print(f"Watchlist active: {out['watchlist_active']}")
    return 0


def cmd_config(args) -> int:
    ws = _ws(args)
    if args.action == "sec-agent":
        if not args.value or "@" not in args.value:
            _print("Give a name and email, e.g. iat config sec-agent \"Jane Doe jane@example.com\"")
            return 2
        config.write_local_config(ws, "sec_user_agent", args.value.strip())
        _print("Saved to config/local.yaml (git-ignored). For GitHub Actions add the same value as secret SEC_USER_AGENT.")
    elif args.action == "show":
        _print(yaml.safe_dump(ws.settings, sort_keys=False, allow_unicode=True))
    elif args.action == "data-owner":
        p = ws.config_dir / "settings.yaml"
        txt = p.read_text(encoding="utf-8")
        import re
        new = re.sub(r"(?m)^(\s*owner:\s*)\S+", rf"\g<1>{args.value}", txt)
        p.write_text(new, encoding="utf-8")
        _print(f"data.owner = {args.value}")
    return 0


def cmd_state(args) -> int:
    ws = _ws(args)
    if args.action == "get":
        _print(yaml.safe_dump(ws.state, sort_keys=False, allow_unicode=True) or "{}")
        return 0
    value = yaml.safe_load(args.value) if args.value is not None else None
    ws.set_state(args.key, value)
    _print(f"state.{args.key} = {value!r}")
    return 0


# ---------------------------------------------------------------------------
# data commands
# ---------------------------------------------------------------------------

def cmd_macro(args) -> int:
    from iat import macro
    ws = _ws(args)
    res = macro.run(ws)
    _print(macro.markdown(res))
    if args.excel:
        return cmd_excel(argparse.Namespace(**{**vars(args), "kind": "macro", "target": None}))
    return 0


def cmd_rotation(args) -> int:
    from iat import rotation
    ws = _ws(args)
    table = rotation.run(ws)
    _print(rotation.markdown(table))
    return 0


def cmd_daily(args) -> int:
    from iat import macro, rotation, tracking
    ws = _ws(args)
    parts, failed = [f"# Daily report {store.today()}", ""], False
    try:
        parts.append(macro.markdown(macro.run(ws)))
    except Exception as exc:
        failed = True
        parts.append(f"Macro failed: {exc}\n")
    try:
        parts.append(rotation.markdown(rotation.run(ws)))
    except Exception as exc:
        failed = True
        parts.append(f"Rotation failed: {exc}\n")
    try:
        parts.append(tracking.markdown(tracking.check(ws)))
    except Exception as exc:
        parts.append(f"Watchlist check failed: {exc}\n")
    path = store.write_report(ws, "daily", "\n".join(parts))
    _print("\n".join(parts))
    _print(f"Report: {path}")
    return 1 if failed else 0


def cmd_industries(args) -> int:
    from iat import universe
    for sector, inds in universe.all_industries().items():
        if args.sector and args.sector.lower() not in sector.lower():
            continue
        _print(f"{sector}:")
        for i in inds:
            _print(f"  - {i}")
    return 0


def cmd_universe(args) -> int:
    from iat import universe
    ws = _ws(args)
    df = universe.build(ws, args.key)
    inc = df[df["status"].str.startswith("included")]
    _print(f"{args.key}: {len(inc)} included / {len(df)} found -> {ws.universes / (args.key + '.csv')}")
    _print(df[["ticker", "name", "yahoo_industry", "market_cap", "adv_usd_3m", "status"]].head(60).to_string(index=False))
    return 0


def cmd_screen(args) -> int:
    from iat import screener
    ws = _ws(args)
    df = screener.run(ws, args.key, refresh=args.refresh, limit=args.limit)
    _print(screener.markdown(df, args.key, top=args.top))
    if args.excel:
        from iat.excel import screen as xs
        _print(f"Workbook: {xs.build(ws, args.key)}")
    return 0


def cmd_weekly(args) -> int:
    from iat import screener
    ws = _ws(args)
    active = (ws.state.get("screening") or {}).get("active") or []
    if not active:
        _print("No active sub-industries in config/state.yaml (screening.active). Nothing to screen.")
        store.write_report(ws, "weekly", f"# Weekly screens {store.today()}\n\nNo active sub-industries.\n")
        return 0
    parts, failed = [f"# Weekly screens {store.today()}", ""], 0
    for key in active:
        try:
            df = screener.run(ws, key, progress=True)
            parts.append(screener.markdown(df, key))
        except Exception as exc:
            failed += 1
            parts.append(f"## {key}\n\nFAILED: {exc}\n")
    path = store.write_report(ws, "weekly", "\n".join(parts))
    _print(f"Report: {path}")
    return 1 if failed == len(active) else 0


def cmd_company(args) -> int:
    from iat import company
    ws = _ws(args)
    peers = [p.strip() for p in args.peers.split(",")] if args.peers else None
    d = company.run(ws, args.ticker, peers=peers, sub_industry=args.sub_industry, source=args.source,
                    download_filings=not args.no_filings)
    folder = ws.output / "companies" / d["ticker"]
    _print(f"Gate: {d['gate_overall']} | source: {d['source']} | peers: {len(d['peers']) - 1}")
    for w in d["warnings"]:
        _print(f"WARNING: {w}")
    _print(f"Summary: {folder / 'summary.md'}")
    if not args.no_excel:
        from iat.excel import company as xc
        _print(f"Workbook: {xc.build(ws, d['ticker'])}")
    return 0


def cmd_filings(args) -> int:
    from iat.sec import Sec
    ws = _ws(args)
    sec = Sec(ws)
    for t in args.tickers:
        ev = sec.recent_events(t, months=args.months)
        if args.json:
            _print(json.dumps(ev, indent=2))
            continue
        _print(f"## {ev['ticker']} recent filings (last {args.months} months)")
        for p in ev["periodic"]:
            _print(f"- {p['form']} for period {p['period']} filed {p['filed']}: {p['url']}")
        for r in ev["earnings_releases"]:
            _print(f"- Earnings release (8-K 2.02) filed {r['filed']}: {r['url']}")
        for e in ev["eight_k"]:
            _print(f"- 8-K {e['filed']}: {', '.join(e['descriptions'])} {e['url']}")
        if ev["red_flags"]:
            _print("RED FLAGS: " + "; ".join(ev["red_flags"]))
        _print("")
    return 0


def cmd_excel(args) -> int:
    ws = _ws(args)
    notes_path = Path(args.notes) if getattr(args, "notes", None) else None
    if args.kind == "macro":
        from iat.excel import macro as xm
        if notes_path is None:
            cand = ws.output / "macro" / "notes.json"
            notes_path = cand if cand.exists() else None
        _print(f"Workbook: {xm.build(ws, notes_path=notes_path)}")
    elif args.kind == "screen":
        from iat.excel import screen as xs
        if notes_path is None:
            cand = ws.output / "screens" / f"{args.target}_notes.json"
            notes_path = cand if cand.exists() else None
        _print(f"Workbook: {xs.build(ws, args.target, notes_path=notes_path)}")
    elif args.kind == "company":
        from iat.excel import company as xc
        notes = store.read_json(notes_path) if notes_path else None
        _print(f"Workbook: {xc.build(ws, args.target, notes=notes)}")
    return 0


def cmd_notes_template(args) -> int:
    from iat import notes
    ws = _ws(args)
    if args.kind == "macro":
        path, tpl = ws.output / "macro" / "notes.json", notes.MACRO
    elif args.kind == "screen":
        path, tpl = ws.output / "screens" / f"{args.target}_notes.json", notes.SCREEN
    else:
        path, tpl = ws.output / "companies" / args.target.upper() / "notes.json", notes.COMPANY
    if path.exists() and not args.force:
        _print(f"Exists (not overwritten): {path}")
        return 0
    tpl = json.loads(json.dumps(tpl))
    tpl["as_of"] = store.today()
    store.write_json(path, tpl)
    _print(f"Template written: {path}")
    return 0


def cmd_watch(args) -> int:
    from iat import tracking
    ws = _ws(args)
    if args.action == "list":
        df = tracking.load_watchlist(ws)
        _print(df.to_string(index=False) if not df.empty else "Watchlist is empty.")
    elif args.action == "check":
        res = tracking.check(ws)
        _print(tracking.markdown(res))
    elif args.action in ("add", "update"):
        if not args.ticker:
            _print("ticker required")
            return 2
        tracking.upsert(ws, args.ticker, status=args.status, sector=args.sector, sub_industry=args.sub_industry,
                        entry_ref_price=args.entry, atr_at_entry=args.atr, price_stop=args.price_stop,
                        thesis=args.thesis, thesis_stop=args.thesis_stop, catalyst=args.catalyst,
                        catalyst_date=args.catalyst_date, tranche_plan=args.tranche_plan, shares_held=args.shares,
                        next_review=args.next_review, notes=args.notes)
        _print(f"Saved {args.ticker.upper()} to data/tracking/watchlist.csv")
    elif args.action == "close":
        tracking.upsert(ws, args.ticker, status="closed")
        _print(f"Closed {args.ticker.upper()}")
    return 0


def cmd_journal(args) -> int:
    from iat import tracking
    ws = _ws(args)
    tracking.journal(ws, ticker=args.ticker.upper(), action=args.action, price=args.price, shares=args.shares,
                     gate_status=args.gate, expected_return=args.expected, reason=args.reason, override=args.override)
    _print("Journal entry saved to data/tracking/journal.csv")
    return 0


def cmd_sync(args) -> int:
    ws = _ws(args)
    counts = store.sync_db(ws)
    _print(f"Rebuilt {ws.db_path}")
    for t, n in counts.items():
        _print(f"  {t}: {n} rows")
    return 0


def cmd_sql(args) -> int:
    ws = _ws(args)
    if args.rebuild:
        store.sync_db(ws)
    import pandas as pd
    with pd.option_context("display.max_rows", 200, "display.max_columns", 50, "display.width", 200):
        _print(store.query(ws, args.query).to_string(index=False))
    return 0


# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iat", description="Investment Analyst Toolkit")
    p.add_argument("--workspace", help="workspace folder (default: auto-detect)")
    p.add_argument("--version", action="version", version=f"iat-toolkit {iat.__version__}")
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("init", help="create a workspace")
    s.add_argument("path")
    s.add_argument("--force", action="store_true", help="overwrite config templates")
    s.set_defaults(func=cmd_init)
    sp.add_parser("upgrade", help="refresh .toolkit and workflows after a plugin update").set_defaults(func=cmd_upgrade)
    s = sp.add_parser("doctor", help="check environment, data sources and workspace")
    s.add_argument("--offline", action="store_true")
    s.set_defaults(func=cmd_doctor)
    s = sp.add_parser("status", help="data freshness and recorded decisions")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)
    s = sp.add_parser("config", help="sec-agent <value> | show | data-owner <local|actions>")
    s.add_argument("action", choices=["sec-agent", "show", "data-owner"])
    s.add_argument("value", nargs="?")
    s.set_defaults(func=cmd_config)
    s = sp.add_parser("state", help="get | set <dotted.key> <yaml value>")
    s.add_argument("action", choices=["get", "set"])
    s.add_argument("key", nargs="?")
    s.add_argument("value", nargs="?")
    s.set_defaults(func=cmd_state)

    s = sp.add_parser("macro", help="FRED macro snapshot + cycle rules")
    s.add_argument("--excel", action="store_true")
    s.add_argument("--notes")
    s.set_defaults(func=cmd_macro)
    sp.add_parser("rotation", help="sector/sub-industry ETF relative strength").set_defaults(func=cmd_rotation)
    sp.add_parser("daily", help="macro + rotation + watchlist check + report").set_defaults(func=cmd_daily)
    s = sp.add_parser("industries", help="list Yahoo industry names")
    s.add_argument("--sector")
    s.set_defaults(func=cmd_industries)
    s = sp.add_parser("universe", help="build the stock universe for a sub-industry")
    s.add_argument("key")
    s.set_defaults(func=cmd_universe)
    s = sp.add_parser("screen", help="screen and rank one sub-industry")
    s.add_argument("key")
    s.add_argument("--refresh", action="store_true", help="ignore the per-ticker cache")
    s.add_argument("--limit", type=int)
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--excel", action="store_true")
    s.set_defaults(func=cmd_screen)
    sp.add_parser("weekly", help="screen every active sub-industry").set_defaults(func=cmd_weekly)
    s = sp.add_parser("company", help="deep-dive data pull + workbook")
    s.add_argument("ticker")
    s.add_argument("--peers", help="comma-separated peer tickers")
    s.add_argument("--sub-industry")
    s.add_argument("--source", choices=["auto", "sec", "yahoo"], default="auto")
    s.add_argument("--no-filings", action="store_true")
    s.add_argument("--no-excel", action="store_true")
    s.set_defaults(func=cmd_company)
    s = sp.add_parser("filings", help="recent 8-Ks, earnings releases and red-flag items (needs SEC contact)")
    s.add_argument("tickers", nargs="+")
    s.add_argument("--months", type=int, default=9)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_filings)
    s = sp.add_parser("excel", help="build a workbook: macro | screen <key> | company <TICKER>")
    s.add_argument("kind", choices=["macro", "screen", "company"])
    s.add_argument("target", nargs="?")
    s.add_argument("--notes", help="path to AI notes JSON (default: the standard location)")
    s.set_defaults(func=cmd_excel)
    s = sp.add_parser("notes-template", help="write a notes.json skeleton: macro | screen <key> | company <TICKER>")
    s.add_argument("kind", choices=["macro", "screen", "company"])
    s.add_argument("target", nargs="?")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_notes_template)
    s = sp.add_parser("watch", help="watchlist: add | update | list | check | close")
    s.add_argument("action", choices=["add", "update", "list", "check", "close"])
    s.add_argument("ticker", nargs="?")
    for flag in ("--status", "--sector", "--sub-industry", "--thesis", "--thesis-stop", "--catalyst", "--catalyst-date",
                 "--tranche-plan", "--next-review", "--notes"):
        s.add_argument(flag)
    for flag in ("--entry", "--atr", "--price-stop", "--shares"):
        s.add_argument(flag, type=float)
    s.set_defaults(func=cmd_watch)
    s = sp.add_parser("journal", help="record a decision")
    s.add_argument("ticker")
    s.add_argument("--action", required=True, help="BUY tranche 1 | ADD | TRIM | SELL | PASS | WATCH")
    s.add_argument("--price", type=float)
    s.add_argument("--shares", type=float)
    s.add_argument("--gate")
    s.add_argument("--expected", type=float, help="expected 6-month return (decimal)")
    s.add_argument("--reason")
    s.add_argument("--override", help="what you overrode against the process, if anything")
    s.set_defaults(func=cmd_journal)
    sp.add_parser("sync", help="rebuild data/iat.db from CSVs").set_defaults(func=cmd_sync)
    s = sp.add_parser("sql", help="run a SQL query on data/iat.db")
    s.add_argument("query")
    s.add_argument("--rebuild", action="store_true")
    s.set_defaults(func=cmd_sql)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except config.WorkspaceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        if "--debug" in sys.argv or __import__("os").environ.get("IAT_DEBUG"):
            traceback.print_exc()
        return 1
