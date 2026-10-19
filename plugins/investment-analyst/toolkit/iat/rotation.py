"""Sector and sub-industry relative strength: ETF/SPY ratio vs 10/40-week MAs and RRG-style quadrants.

RS-Ratio / RS-Momentum here are an open approximation of the JdK Relative Rotation Graph (the
original formula is proprietary). Use the quadrant as a direction signal, not as an exact match to
StockCharts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from iat import store
from iat.config import Workspace


def download(tickers: list[str], period: str = "3y") -> dict[str, pd.DataFrame]:
    raw = yf.download(sorted(set(tickers)), period=period, interval="1d", auto_adjust=True,
                      progress=False, group_by="column", threads=True)
    if raw is None or raw.empty:
        raise RuntimeError("Yahoo returned no price data (rate limit or network). Try again later.")
    if not isinstance(raw.columns, pd.MultiIndex):  # single ticker
        t = tickers[0]
        raw.columns = pd.MultiIndex.from_product([raw.columns, [t]])
    return {f: raw[f] for f in ("Close", "High", "Low", "Volume") if f in raw.columns.get_level_values(0)}


def _streak(b: pd.Series) -> int:
    """Signed length of the current run: +n weeks True, -n weeks False."""
    b = b.dropna()
    if b.empty:
        return 0
    last = bool(b.iloc[-1])
    n = 0
    for v in reversed(b.tolist()):
        if bool(v) != last:
            break
        n += 1
    return n if last else -n


def quadrant(rsr: float, rsm: float) -> str:
    if np.isnan(rsr) or np.isnan(rsm):
        return ""
    if rsr >= 100 and rsm >= 100:
        return "Leading"
    if rsr >= 100:
        return "Weakening"
    if rsm >= 100:
        return "Improving"
    return "Lagging"


def rrg(ratio: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    rs = 100 * ratio
    rsr = 100 + (rs - rs.rolling(window).mean()) / rs.rolling(window).std()
    roc = 100 * (rsr / rsr.shift(1) - 1)
    rsm = 100 + (roc - roc.rolling(window).mean()) / roc.rolling(window).std()
    return rsr, rsm


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def universe(ws: Workspace) -> tuple[list[dict], str]:
    cfg = ws.settings["rotation"]
    bench = cfg["benchmark"]
    rows = [{"ticker": etf, "name": sector, "sector": sector, "level": "sector", "parent": bench}
            for sector, etf in cfg["sector_etfs"].items()]
    seen = {r["ticker"] for r in rows}
    sector_etf = cfg["sector_etfs"]
    for key, sub in ws.sub_industries.items():
        etf = sub.get("etf")
        if etf and etf not in seen:
            rows.append({"ticker": etf, "name": sub.get("name", key), "sector": sub.get("sector", ""),
                         "level": "sub-industry", "parent": sector_etf.get(sub.get("sector", ""), bench)})
            seen.add(etf)
    for etf in cfg.get("extra_etfs", []) or []:
        if etf not in seen:
            rows.append({"ticker": etf, "name": etf, "sector": "", "level": "extra", "parent": bench})
            seen.add(etf)
    return rows, bench


def compute(ws: Workspace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = ws.settings["rotation"]
    window, confirm = int(cfg["rrg_window"]), int(cfg["confirm_weeks"])
    rows, bench = universe(ws)
    px = download([r["ticker"] for r in rows] + [bench])
    close = px["Close"].dropna(how="all")
    weekly = close.resample("W-FRI").last()
    out, hist = [], []
    for r in rows:
        t = r["ticker"]
        if t not in weekly or weekly[t].dropna().empty:
            out.append({**r, "status": "NO DATA"})
            continue
        ratio = (weekly[t] / weekly[bench]).dropna()
        ma10, ma40 = ratio.rolling(10).mean(), ratio.rolling(40).mean()
        above10, above40 = ratio > ma10, ratio > ma40
        rsr, rsm = rrg(ratio, window)
        quads = [quadrant(a, b) for a, b in zip(rsr, rsm)]
        q_now, q_prev = (quads[-1] if quads else ""), (quads[-2] if len(quads) > 1 else "")
        q_4w = quads[-5] if len(quads) > 4 else ""
        streak10 = _streak(above10[ma10.notna()])

        def rel(weeks):
            if len(weekly[t].dropna()) <= weeks:
                return np.nan
            a = weekly[t].iloc[-1] / weekly[t].iloc[-1 - weeks] - 1
            b = weekly[bench].iloc[-1] / weekly[bench].iloc[-1 - weeks] - 1
            return (a - b) * 100

        parent = r["parent"]
        rel_parent = np.nan
        if parent != bench and parent in weekly:
            pr = (weekly[t] / weekly[parent]).dropna()
            if len(pr) > 26:
                rel_parent = (pr.iloc[-1] / pr.iloc[-27] - 1) * 100
        c = close[t].dropna()
        ma200 = c.rolling(200).mean().iloc[-1] if len(c) >= 200 else np.nan
        a14 = atr(px["High"][t], px["Low"][t], px["Close"][t]).dropna()
        a10, a40 = bool(above10.iloc[-1]), bool(above40.iloc[-1]) if ma40.notna().iloc[-1] else False
        recent_q = quads[-confirm:] if len(quads) >= confirm else []
        rrg_persistent = bool(recent_q) and all(q in ("Improving", "Leading") for q in recent_q)
        ma_ok = a10 and a40 and streak10 >= confirm            # trend confirmed on both MAs
        rrg_ok = rrg_persistent and a10 and streak10 >= confirm  # early turn: below 40w but persistent
        if ma_ok:
            status = "CONFIRMED"
        elif rrg_ok:
            status = "TURNING (RRG + 10w, below 40w)"
        elif a10:
            status = f"EARLY ({streak10}w, false-start risk)"
        elif a40:
            status = "FADING (below 10w)"
        elif q_now == "Improving":
            status = "IMPROVING (RRG only, unconfirmed)"
        else:
            status = "WEAK"
        out.append({
            **r,
            "last_close": float(c.iloc[-1]),
            "ratio": float(ratio.iloc[-1]),
            "ratio_ma10": float(ma10.iloc[-1]),
            "ratio_ma40": float(ma40.iloc[-1]) if ma40.notna().iloc[-1] else np.nan,
            "above_10w": a10,
            "above_40w": a40,
            "weeks_above_10w": streak10,
            "rs_ratio": float(rsr.iloc[-1]),
            "rs_momentum": float(rsm.iloc[-1]),
            "quadrant": q_now,
            "quadrant_last_week": q_prev,
            "quadrant_4w_ago": q_4w,
            "rel_ret_13w_pct": rel(13),
            "rel_ret_26w_pct": rel(26),
            "rel_ret_52w_pct": rel(52),
            "rel_to_parent_26w_pct": rel_parent,
            "price_vs_200d_pct": (float(c.iloc[-1]) / ma200 - 1) * 100 if ma200 == ma200 else np.nan,
            "atr14": float(a14.iloc[-1]) if len(a14) else np.nan,
            "atr14_pct": float(a14.iloc[-1] / c.iloc[-1] * 100) if len(a14) else np.nan,
            "status": status,
            "rs_pillar": bool(ma_ok or rrg_ok),
            "data_through": c.index[-1].date().isoformat(),
        })
        recent = pd.DataFrame({"week": ratio.index[-12:].date.astype(str), "ticker": t,
                               "ratio": ratio.iloc[-12:].values, "ratio_ma10": ma10.iloc[-12:].values,
                               "ratio_ma40": ma40.iloc[-12:].values, "rs_ratio": rsr.iloc[-12:].values,
                               "rs_momentum": rsm.iloc[-12:].values, "quadrant": quads[-12:]})
        hist.append(recent)
    table = pd.DataFrame(out)
    rets = weekly[[r["ticker"] for r in rows if r["ticker"] in weekly]].pct_change().iloc[-52:]
    corr = rets.corr().round(2)
    corr.insert(0, "ticker", corr.index)
    return table, pd.concat(hist, ignore_index=True) if hist else pd.DataFrame(), corr


def run(ws: Workspace) -> pd.DataFrame:
    table, hist, corr = compute(ws)
    store.write_latest_csv(ws, "rotation", table)
    store.write_latest_csv(ws, "rotation_corr", corr.reset_index(drop=True))
    if not hist.empty:
        store.append_history(ws, "rotation", hist, keys=["week", "ticker"])
    return table


def alerts(table: pd.DataFrame, confirm: int = 3) -> list[str]:
    out = []
    for _, r in table.iterrows():
        if r.get("status") == "NO DATA":
            out.append(f"{r['ticker']}: no price data")
            continue
        q, qp = r.get("quadrant", ""), r.get("quadrant_last_week", "")
        if q and qp and q != qp:
            out.append(f"{r['ticker']} ({r['name']}): RRG quadrant {qp} -> {q}")
        w = r.get("weeks_above_10w", 0)
        if w == 1:
            out.append(f"{r['ticker']} ({r['name']}): ratio crossed ABOVE its 10-week MA (needs {confirm} weeks to confirm)")
        elif w == confirm:
            out.append(f"{r['ticker']} ({r['name']}): {confirm} weeks above its 10-week MA - check CONFIRMED/TURNING status")
        elif w == -1:
            out.append(f"{r['ticker']} ({r['name']}): ratio crossed BELOW its 10-week MA")
    return out


def markdown(table: pd.DataFrame) -> str:
    lines = ["## Sector rotation (ETF / SPY)", "",
             "| ETF | Name | Status | Quadrant (prev) | Wks >10w | Rel 13w % | Rel 26w % | RS pillar |",
             "|---|---|---|---|---|---|---|---|"]
    t = table.copy()
    t["_lvl"] = t["level"].map({"sector": 0, "sub-industry": 1}).fillna(2)
    for _, r in t.sort_values(["_lvl", "rel_ret_13w_pct"], ascending=[True, False]).iterrows():
        if r.get("status") == "NO DATA":
            lines.append(f"| {r['ticker']} | {r['name']} | NO DATA | | | | | |")
            continue
        lines.append(f"| {r['ticker']} | {r['name']} | {r['status']} | {r['quadrant']} ({r['quadrant_last_week']}) | "
                     f"{int(r['weeks_above_10w'])} | {r['rel_ret_13w_pct']:+.1f} | {r['rel_ret_26w_pct']:+.1f} | "
                     f"{'yes' if r['rs_pillar'] else 'no'} |")
    al = alerts(table)
    if al:
        lines += ["", "**Changes this run:**", *[f"- {a}" for a in al]]
    return "\n".join(lines) + "\n"
