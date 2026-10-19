"""Sub-industry universes from the Yahoo equity screener (US listings, tradability filter)."""
from __future__ import annotations

import difflib
import re

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery as Q

from iat import store
from iat.config import Workspace

YAHOO_TO_GICS = {
    "Technology": "Technology",
    "Healthcare": "Health Care",
    "Financial Services": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Basic Materials": "Materials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Communication Services": "Communication Services",
}


def all_industries() -> dict[str, list[str]]:
    from yfinance.const import EQUITY_SCREENER_EQ_MAP

    return {YAHOO_TO_GICS.get(k, k): sorted(v) for k, v in EQUITY_SCREENER_EQ_MAP["industry"].items()}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[—–\-]", "-", s)).strip().lower()


def resolve(names: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    official = [i for v in all_industries().values() for i in v]
    by_norm = {_norm(i): i for i in official}
    valid, unknown = [], {}
    for n in names:
        hit = by_norm.get(_norm(n))
        if hit:
            valid.append(hit)
        else:
            unknown[n] = difflib.get_close_matches(n, official, n=3, cutoff=0.5)
    return valid, unknown


def _screen_one(industry: str, exchanges: list[str], min_cap: float) -> list[dict]:
    q = Q("and", [Q("eq", ["industry", industry]), Q("is-in", ["exchange", *exchanges]),
                  Q("gt", ["intradaymarketcap", min_cap])])
    out, offset = [], 0
    while True:
        res = yf.screen(q, offset=offset, size=250, sortField="intradaymarketcap", sortAsc=False)
        quotes = res.get("quotes", []) if isinstance(res, dict) else []
        for x in quotes:
            price = x.get("regularMarketPrice") or 0
            vol = x.get("averageDailyVolume3Month") or 0
            out.append({
                "ticker": x.get("symbol"),
                "name": x.get("longName") or x.get("shortName"),
                "yahoo_industry": industry,
                "exchange": x.get("exchange"),
                "market_cap": x.get("marketCap"),
                "price": price,
                "adv_usd_3m": price * vol,
                "currency": x.get("currency"),
                "forward_pe_quote": x.get("forwardPE"),
            })
        total = res.get("total", 0) if isinstance(res, dict) else 0
        offset += len(quotes)
        if not quotes or offset >= total:
            break
    return out


def build(ws: Workspace, key: str) -> pd.DataFrame:
    sub = ws.sub_industry(key)
    cfg = ws.settings["screening"]
    valid, unknown = resolve(sub.get("yahoo_industries", []))
    if unknown:
        hints = "; ".join(f"'{k}' -> did you mean {v}?" for k, v in unknown.items())
        raise ValueError(f"Unknown Yahoo industry names in sub-industry '{key}': {hints}. Run `iat industries`.")
    rows = []
    for ind in valid:
        rows += _screen_one(ind, cfg["exchanges"], float(cfg["min_market_cap"]))
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["ticker", "name", "yahoo_industry", "exchange", "market_cap", "price",
                                   "adv_usd_3m", "currency", "forward_pe_quote"])
    df["status"] = "included"
    df.loc[df["adv_usd_3m"] < float(cfg["min_adv_usd"]), "status"] = "excluded: low dollar volume"
    df.loc[df["currency"].fillna("USD") != "USD", "status"] = "excluded: non-USD quote"
    for t in sub.get("exclude", []) or []:
        df.loc[df["ticker"] == t, "status"] = "excluded: manual"
    for t in sub.get("include", []) or []:
        if t not in set(df["ticker"]):
            df = pd.concat([df, pd.DataFrame([{"ticker": t, "status": "included: manual"}])], ignore_index=True)
        else:
            df.loc[df["ticker"] == t, "status"] = "included: manual"
    df = df.drop_duplicates("ticker").sort_values("market_cap", ascending=False, na_position="last")
    df.insert(0, "sub_industry", key)
    df.insert(1, "built", store.today())
    ws.universes.mkdir(parents=True, exist_ok=True)
    store.write_csv(ws.universes / f"{key}.csv", df)
    return df


def load(ws: Workspace, key: str, rebuild_if_older_than_days: int | None = None) -> pd.DataFrame:
    path = ws.universes / f"{key}.csv"
    if path.exists():
        df = pd.read_csv(path)
        if rebuild_if_older_than_days is None or (
                pd.Timestamp.today() - pd.Timestamp(df["built"].iloc[0])).days <= rebuild_if_older_than_days:
            return df
    return build(ws, key)
