"""Workspace discovery, settings (human-edited) and state (machine-written decisions).

A workspace is a folder created by `iat init`. It holds:
    config/settings.yaml        preferences the user edits (portfolio size, thresholds, ...)
    config/sub_industries.yaml  sub-industry definitions used by screening and rotation
    config/state.yaml           decisions recorded by the skills (cycle call, allocation, active screens)
    config/local.yaml           machine-local secrets such as the SEC contact string (git-ignored)
    data/                       CSV history committed by GitHub Actions, SQLite cache (git-ignored)
    filings/                    downloaded SEC documents (git-ignored)
    output/                     Excel workbooks and AI notes
"""
from __future__ import annotations

import copy
import datetime as dt
import os
from pathlib import Path
from typing import Any

import yaml

POINTER_FILE = Path.home() / ".investment-analyst" / "workspace.txt"
MARKER_FILE = ".iat-workspace"

SECTOR_ETFS = {
    "Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

DEFAULTS: dict[str, Any] = {
    "portfolio": {
        "value": None,
        "target_positions": 15,
        "risk_per_position_pct": 1.0,
        "max_position_pct": 10.0,
        "max_sector_pct": 30.0,
        "horizon_months": 6,
        "short_term_tax_rate_pct": None,
    },
    "screening": {
        "min_market_cap": 2.0e9,
        "min_adv_usd": 2.0e7,
        "news_check_top_n": 5,
        "cache_days": 6,
        "exchanges": ["NMS", "NYQ", "NGM", "NCM", "ASE"],
        "sleep_seconds": 0.4,
        "max_tickers": 150,
    },
    "rotation": {
        "benchmark": "SPY",
        "sector_etfs": SECTOR_ETFS,
        "rrg_window": 14,
        "confirm_weeks": 3,
        "extra_etfs": [],
    },
    "valuation": {
        "equity_risk_premium": 0.045,
        "terminal_growth": 0.025,
        "atr_multiple": 2.5,
        "projection_years": 10,
        "default_probabilities": {"bear": 0.25, "base": 0.50, "bull": 0.25},
        "gap_closure_with_catalyst": 0.5,
        "gap_closure_without_catalyst": 0.2,
    },
    "thresholds": {
        "cfo_ni_pass": 1.0,
        "cfo_ni_fail": 0.8,
        "accruals_watch": 0.05,
        "accruals_fail": 0.10,
        "beneish_watch": -2.22,
        "beneish_fail": -1.78,
        "piotroski_pass": 7,
        "piotroski_fail": 3,
        "altman_z_safe": 2.99,
        "altman_z_distress": 1.81,
        "altman_z2_safe": 2.60,
        "altman_z2_distress": 1.10,
        "net_debt_ebitda_watch": 3.0,
        "net_debt_ebitda_fail": 4.0,
        "interest_cover_pass": 4.0,
        "interest_cover_fail": 2.0,
        "cfo_debt_pass": 0.25,
        "sbc_revenue_watch": 0.10,
        "receivables_gap_watch": 0.10,
        "dio_rise_watch": 0.15,
        "capex_da_watch": 2.0,
        "tv_share_warning": 0.70,
        "estimate_cut_pct": -0.01,
        "short_interest_watch": 0.10,
        "earnings_soon_days": 21,
        "min_analysts": 5,
        "dispersion_watch": 0.30,
    },
    "data": {"owner": "local"},
    "sec": {"user_agent": ""},
}


class WorkspaceError(RuntimeError):
    pass


def deep_merge(base: dict, override: dict | None) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def in_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def find_workspace(explicit: str | os.PathLike | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("IAT_WORKSPACE"):
        candidates.append(Path(os.environ["IAT_WORKSPACE"]))
    cwd = Path.cwd()
    candidates.extend([cwd, *cwd.parents])
    if POINTER_FILE.exists():
        candidates.append(Path(POINTER_FILE.read_text(encoding="utf-8").strip()))
    for c in candidates:
        if (c / MARKER_FILE).exists():
            return c.resolve()
    raise WorkspaceError(
        "No investment workspace found. Run `iat init <folder>` (or the investment-setup skill), "
        "or pass --workspace / set IAT_WORKSPACE."
    )


class Workspace:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.config_dir = self.root / "config"
        self.data = self.root / "data"
        self.history = self.data / "history"
        self.latest = self.data / "latest"
        self.reports = self.data / "reports"
        self.screens = self.data / "screens"
        self.tracking = self.data / "tracking"
        self.universes = self.data / "universes"
        self.local = self.data / "local"
        self.cache = self.data / "cache"
        self.db_path = self.data / "iat.db"
        self.filings = self.root / "filings"
        self.output = self.root / "output"
        self.settings = deep_merge(DEFAULTS, _read_yaml(self.config_dir / "settings.yaml"))
        self.local_cfg = _read_yaml(self.config_dir / "local.yaml")
        self.state = _read_yaml(self.config_dir / "state.yaml")
        self.sub_industries: dict[str, dict] = (_read_yaml(self.config_dir / "sub_industries.yaml") or {}).get(
            "sub_industries", {}
        )

    # ---- write policy -------------------------------------------------
    @property
    def shared_writes(self) -> bool:
        """True when this process may write the shared, git-tracked data folders.

        When GitHub Actions own the data (settings.data.owner == "actions"), local runs write to
        data/local/ instead so they never conflict with the bot's commits.
        """
        return in_ci() or str(self.settings["data"].get("owner", "local")).lower() != "actions"

    def out_dir(self, kind: str) -> Path:
        """Folder for 'history', 'latest', 'reports' or 'screens' honoring the write policy."""
        base = getattr(self, kind)
        if self.shared_writes:
            return base
        return self.local / kind

    def read_candidates(self, kind: str) -> list[Path]:
        """Folders to read from, freshest-first is decided by the caller using as_of stamps."""
        return [getattr(self, kind), self.local / kind]

    # ---- state ----------------------------------------------------------
    def save_state(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.state["updated"] = dt.datetime.now().isoformat(timespec="seconds")
        with (self.config_dir / "state.yaml").open("w", encoding="utf-8") as fh:
            yaml.safe_dump(self.state, fh, sort_keys=False, allow_unicode=True)

    def set_state(self, dotted_key: str, value: Any) -> None:
        node = self.state
        parts = dotted_key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
        self.save_state()

    # ---- secrets ----------------------------------------------------------
    def sec_user_agent(self) -> str:
        ua = (
            os.environ.get("SEC_USER_AGENT")
            or self.local_cfg.get("sec_user_agent")
            or self.settings.get("sec", {}).get("user_agent")
            or ""
        ).strip()
        if not ua or "@" not in ua:
            raise WorkspaceError(
                "SEC EDGAR requires a contact User-Agent such as 'Jane Doe jane@example.com'. "
                "Set it with `iat config sec-agent \"<name> <email>\"` (stored in config/local.yaml, git-ignored) "
                "or the SEC_USER_AGENT environment variable / GitHub secret."
            )
        return ua

    def sub_industry(self, key: str) -> dict:
        if key not in self.sub_industries:
            known = ", ".join(sorted(self.sub_industries)) or "(none defined)"
            raise WorkspaceError(f"Unknown sub-industry key '{key}'. Known keys: {known}")
        entry = dict(self.sub_industries[key])
        entry.setdefault("key", key)
        entry.setdefault("profile", "standard")
        return entry


def load(explicit: str | os.PathLike | None = None) -> Workspace:
    return Workspace(find_workspace(explicit))


def write_pointer(root: Path) -> None:
    POINTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    POINTER_FILE.write_text(str(Path(root).resolve()), encoding="utf-8")


def write_local_config(ws: Workspace, key: str, value: Any) -> None:
    ws.local_cfg[key] = value
    ws.config_dir.mkdir(parents=True, exist_ok=True)
    with (ws.config_dir / "local.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(ws.local_cfg, fh, sort_keys=False, allow_unicode=True)
