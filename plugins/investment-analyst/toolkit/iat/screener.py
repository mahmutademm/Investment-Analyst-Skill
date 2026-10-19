"""Mechanical sub-industry screen: pull, compute, rank within peers, flag. Never a buy list.

Logic the ranking supports (the AI news check and the user finish it):
    cheap -> estimates not falling -> discount is temporary -> catalyst inside the horizon
"""
from __future__ import annotations

import datetime as dt
import json
import time

import numpy as np
import pandas as pd
import yfinance as yf

from iat import fundamentals, ratios, rotation, store
from iat.config import SECTOR_ETFS, Workspace

INFO_KEYS = [
    "longName", "sector", "industry", "country", "financialCurrency", "currency", "currentPrice",
    "regularMarketPrice", "marketCap", "enterpriseValue", "forwardPE", "trailingPE", "trailingPegRatio",
    "enterpriseToEbitda", "enterpriseToRevenue", "priceToBook", "bookValue", "freeCashflow", "operatingCashflow",
    "totalDebt", "totalCash", "ebitda", "netIncomeToCommon", "totalRevenue", "returnOnEquity", "returnOnAssets",
    "operatingMargins", "grossMargins", "profitMargins", "revenueGrowth", "earningsGrowth", "beta",
    "shortPercentOfFloat", "shortRatio", "numberOfAnalystOpinions", "recommendationMean", "targetMeanPrice",
    "dividendYield", "payoutRatio", "sharesOutstanding", "averageVolume", "forwardEps", "trailingEps",
    "heldPercentInsiders", "heldPercentInstitutions", "auditRisk", "overallRisk",
]

PROFILE_METRICS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "standard": {
        "valuation": [("fwd_pe", "low"), ("ev_ebitda", "low"), ("peg", "low"), ("pe_vs_own_hist", "low"),
                      ("fcf_yield", "high")],
        "quality": [("roic", "high"), ("roe", "high"), ("op_margin_std", "low"), ("cfo_to_ni", "high"),
                    ("accruals_ratio", "low"), ("gross_margin", "high")],
    },
    "managed_care": {
        "valuation": [("fwd_pe", "low"), ("peg", "low"), ("pe_vs_own_hist", "low"), ("fcf_yield", "high")],
        "quality": [("roe", "high"), ("roic", "high"), ("op_margin_std", "low"), ("cfo_to_ni", "high")],
    },
    "bank": {
        "valuation": [("p_tbv", "low"), ("fwd_pe", "low"), ("pe_vs_own_hist", "low")],
        "quality": [("rotce", "high"), ("roa", "high"), ("net_margin_std", "low")],
    },
    "insurer": {
        "valuation": [("p_b", "low"), ("fwd_pe", "low"), ("pe_vs_own_hist", "low")],
        "quality": [("roe", "high"), ("roa", "high"), ("net_margin_std", "low")],
    },
    "reit": {
        "valuation": [("p_ffo", "low"), ("ev_ebitda", "low"), ("dividend_yield", "high")],
        "quality": [("operating_margin", "high"), ("net_debt_to_ebitda", "low"), ("op_margin_std", "low")],
    },
    "energy": {
        "valuation": [("ev_ebitda", "low"), ("fcf_yield", "high"), ("fwd_pe", "low")],
        "quality": [("roic", "high"), ("net_debt_to_ebitda", "low"), ("cfo_to_ni", "high")],
    },
    "early_growth": {
        "valuation": [("ev_sales", "low"), ("ev_sales_to_growth", "low")],
        "quality": [("gross_margin", "high"), ("revenue_growth", "high"), ("rule_of_40", "high"),
                    ("sbc_pct_revenue", "low")],
    },
}
MOMENTUM_METRICS = [("eps_rev_30d", "high"), ("eps_rev_90d", "high"), ("net_revisions_30d", "high"),
                    ("beats_4q", "high"), ("rel_6m_vs_etf", "high"), ("price_vs_200d", "high")]
FINANCIAL_PROFILES = {"bank", "insurer"}


# ---------------------------------------------------------------------------
# fetching with cache
# ---------------------------------------------------------------------------

def _frame_dict(df: pd.DataFrame | None) -> dict:
    if df is None or getattr(df, "empty", True):
        return {}
    out = {}
    for r in df.index:
        out[str(r)] = {(c.date().isoformat() if hasattr(c, "date") else str(c)): (None if pd.isna(v) else float(v))
                       for c, v in df.loc[r].items()}
    return out


def _table_dict(df: pd.DataFrame | None) -> dict:
    if df is None or getattr(df, "empty", True):
        return {}
    df = df.copy()
    df.index = [str(i.date()) if hasattr(i, "date") else str(i) for i in df.index]
    return json.loads(df.to_json(orient="index"))


def fetch_ticker(t: str) -> dict:
    tk = yf.Ticker(t)
    out: dict = {"ticker": t, "fetched": store.now(), "errors": {}}

    def grab(name, fn):
        try:
            out[name] = fn()
        except Exception as exc:  # one failed endpoint should not kill the ticker
            out["errors"][name] = f"{type(exc).__name__}: {exc}"[:300]
            if "Too Many Requests" in str(exc) or "RateLimit" in type(exc).__name__:
                raise

    grab("info", lambda: {k: tk.info.get(k) for k in INFO_KEYS})
    grab("eps_trend", lambda: _table_dict(tk.eps_trend))
    grab("eps_revisions", lambda: _table_dict(tk.eps_revisions))
    grab("earnings_estimate", lambda: _table_dict(tk.earnings_estimate))
    grab("earnings_history", lambda: _table_dict(tk.earnings_history))
    grab("calendar", lambda: {k: [str(x) for x in v] if isinstance(v, list) else str(v)
                              for k, v in (tk.calendar or {}).items()})
    grab("income", lambda: _frame_dict(tk.income_stmt))
    grab("balance", lambda: _frame_dict(tk.balance_sheet))
    grab("cashflow", lambda: _frame_dict(tk.cashflow))
    return out


def fetch_cached(ws: Workspace, t: str, max_age_days: float, refresh: bool = False) -> dict:
    path = ws.cache / "yahoo" / f"{t}.json"
    if path.exists() and not refresh:
        raw = store.read_json(path)
        age = (dt.datetime.now() - dt.datetime.fromisoformat(raw["fetched"])).total_seconds() / 86400
        if age <= max_age_days and "info" in raw:
            return raw
    delays = [30, 90, 240]
    for attempt in range(len(delays) + 1):
        try:
            raw = fetch_ticker(t)
            store.write_json(path, raw)
            return raw
        except Exception as exc:
            if attempt == len(delays):
                return {"ticker": t, "fetched": store.now(), "errors": {"fatal": str(exc)[:300]}}
            time.sleep(delays[attempt])
    return {}


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def _num(x):
    try:
        f = float(x)
        return f if np.isfinite(f) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _pos(x):
    x = _num(x)
    return x if x > 0 else np.nan


def _chg(cur, ago):
    cur, ago = _num(cur), _num(ago)
    if np.isnan(cur) or np.isnan(ago) or ago == 0:
        return np.nan
    return (cur - ago) / abs(ago)


def compute_metrics(raw: dict, profile: str, close: pd.Series | None, etf_close: pd.Series | None,
                    high: pd.Series | None, low: pd.Series | None, volume: pd.Series | None,
                    thresholds: dict) -> dict:
    info = raw.get("info", {}) or {}
    m: dict = {"ticker": raw["ticker"], "name": info.get("longName"), "country": info.get("country"),
               "currency": info.get("financialCurrency"), "fetch_errors": "; ".join(raw.get("errors", {}).keys())}
    price = _num(info.get("currentPrice") or info.get("regularMarketPrice"))
    mcap = _num(info.get("marketCap"))
    m.update(price=price, market_cap=mcap, enterprise_value=_num(info.get("enterpriseValue")), beta=_num(info.get("beta")))

    # --- valuation from quote data
    m["fwd_pe"] = _pos(info.get("forwardPE"))
    m["ttm_pe"] = _pos(info.get("trailingPE"))
    m["ev_ebitda"] = _pos(info.get("enterpriseToEbitda"))
    m["ev_sales"] = _pos(info.get("enterpriseToRevenue"))
    m["p_b"] = _pos(info.get("priceToBook"))
    m["fcf_yield"] = _num(info.get("freeCashflow")) / mcap if mcap else np.nan
    m["dividend_yield"] = _num(info.get("dividendYield"))
    if m["dividend_yield"] == m["dividend_yield"] and m["dividend_yield"] > 1:  # some yfinance versions return %
        m["dividend_yield"] /= 100
    m["yahoo_peg"] = _num(info.get("trailingPegRatio"))

    # --- expectations
    trend = raw.get("eps_trend", {}) or {}
    revs = raw.get("eps_revisions", {}) or {}
    est = raw.get("earnings_estimate", {}) or {}
    fy1 = trend.get("+1y", {})
    m["eps_rev_30d"] = _chg(fy1.get("current"), fy1.get("30daysAgo"))
    m["eps_rev_90d"] = _chg(fy1.get("current"), fy1.get("90daysAgo"))
    fy0 = trend.get("0y", {})
    m["eps_rev_30d_fy0"] = _chg(fy0.get("current"), fy0.get("30daysAgo"))
    r1 = revs.get("+1y", {})
    up, down = _num(r1.get("upLast30days")), _num(r1.get("downLast30days"))
    m["revisions_up_30d"], m["revisions_down_30d"] = up, down
    m["net_revisions_30d"] = (up - down) / (up + down) if (up + down) > 0 else (0.0 if up == up else np.nan)
    e1, e0 = est.get("+1y", {}), est.get("0y", {})
    m["analysts"] = _num(e1.get("numberOfAnalysts")) if e1 else _num(info.get("numberOfAnalystOpinions"))
    avg1, lo1, hi1 = _num(e1.get("avg")), _num(e1.get("low")), _num(e1.get("high"))
    m["estimate_dispersion"] = (hi1 - lo1) / abs(avg1) if avg1 else np.nan
    base_eps = _num(e0.get("yearAgoEps"))
    m["eps_growth_2y_cagr"] = ((avg1 / base_eps) ** 0.5 - 1) if (base_eps > 0 and avg1 > 0) else np.nan
    g = m["eps_growth_2y_cagr"]
    m["peg"] = m["fwd_pe"] / (g * 100) if (g == g and g > 0.03 and m["fwd_pe"] == m["fwd_pe"]) else np.nan
    hist = raw.get("earnings_history", {}) or {}
    diffs = [_num(v.get("epsDifference")) for v in hist.values()]
    surpr = [_num(v.get("surprisePercent")) for v in hist.values()]
    diffs = [d for d in diffs if d == d]
    m["beats_4q"] = float(sum(d > 0 for d in diffs[-4:])) if diffs else np.nan
    m["avg_surprise_pct"] = float(np.nanmean(surpr[-4:]) * 100) if any(s == s for s in surpr) else np.nan
    cal = raw.get("calendar", {}) or {}
    ed = cal.get("Earnings Date")
    m["next_earnings"] = ed[0] if isinstance(ed, list) and ed else (ed or "")
    try:
        m["days_to_earnings"] = (dt.date.fromisoformat(str(m["next_earnings"])[:10]) - dt.date.today()).days
    except ValueError:
        m["days_to_earnings"] = np.nan

    # --- statements -> standardized -> shared ratio definitions
    try:
        fx = fundamentals.from_yahoo(raw["ticker"], raw, prices=close, market_cap=mcap)
        tbl = ratios.evaluate(fx)
        last = ratios.latest_values(tbl)
        for k in ("roic", "roe", "roa", "rotce", "gross_margin", "operating_margin", "cfo_to_ni", "fcf_to_ni",
                  "accruals_ratio", "net_debt_to_ebitda", "interest_coverage", "debt_to_capital", "current_ratio",
                  "sbc_pct_revenue", "revenue_growth", "beneish_m", "piotroski_f", "altman_z", "altman_z2",
                  "share_count_change", "capex_to_da", "receivables_vs_revenue"):
            m[k] = last.get(k, np.nan)
        ebit_last = _num(last.get("ebit"))
        m["ev_ebit"] = m["enterprise_value"] / ebit_last if ebit_last > 0 else np.nan
        m["op_margin_std"] = ratios.series_stat(tbl, "operating_margin", np.nanstd, 4)
        m["net_margin_std"] = ratios.series_stat(tbl, "net_margin", np.nanstd, 4)
        m["revenue_cagr_3y"] = ratios.series_stat(tbl, "revenue_growth", np.nanmean, 3)
        pes = tbl.loc["pe_at_period_end", fx.annual_columns].astype(float)
        pes = pes[(pes > 0) & (pes < 200)]
        m["own_pe_median_hist"] = float(pes.median()) if len(pes) >= 2 else np.nan
        m["own_pe_years"] = int(len(pes))
        m["pe_vs_own_hist"] = (m["ttm_pe"] / m["own_pe_median_hist"] - 1) if m["own_pe_median_hist"] == m["own_pe_median_hist"] else np.nan
        teq = last.get("tangible_equity", np.nan)
        m["p_tbv"] = mcap / teq if (teq and teq == teq and teq > 0) else np.nan
        ni, da = fx.latest("net_income"), fx.latest("da")
        ffo = ni + da if (ni == ni and da == da) else np.nan
        m["p_ffo"] = mcap / ffo if (ffo == ffo and ffo > 0) else np.nan
        m["negative_equity"] = bool(fx.latest("equity") < 0) if fx.latest("equity") == fx.latest("equity") else False
        m["fy_latest"] = fx.annual_columns[-1] if fx.annual_columns else ""
    except Exception as exc:
        m["fetch_errors"] = (m["fetch_errors"] + f"; statements: {exc}").strip("; ")
    m["fcf_ttm"] = _num(info.get("freeCashflow"))
    m["nd_ebitda_quote"] = ((_num(info.get("totalDebt")) - _num(info.get("totalCash"))) / _num(info.get("ebitda"))
                            if _num(info.get("ebitda")) > 0 else np.nan)
    if m.get("net_debt_to_ebitda") is None or m.get("net_debt_to_ebitda") != m.get("net_debt_to_ebitda"):
        m["net_debt_to_ebitda"] = m["nd_ebitda_quote"]
    rg = _num(m.get("revenue_growth"))
    m["ev_sales_to_growth"] = m["ev_sales"] / (rg * 100) if (rg == rg and rg > 0.05) else np.nan
    fcf_margin = m["fcf_ttm"] / _num(info.get("totalRevenue")) if _num(info.get("totalRevenue")) else np.nan
    m["rule_of_40"] = (rg + fcf_margin) * 100 if (rg == rg and fcf_margin == fcf_margin) else np.nan

    # --- momentum and trading
    if close is not None and len(close.dropna()) > 130:
        c = close.dropna()
        m["ret_6m"] = c.iloc[-1] / c.iloc[-127] - 1
        m["ret_12m"] = c.iloc[-1] / c.iloc[-253] - 1 if len(c) > 253 else np.nan
        if etf_close is not None and len(etf_close.dropna()) > 253:
            e = etf_close.dropna()
            m["rel_6m_vs_etf"] = m["ret_6m"] - (e.iloc[-1] / e.iloc[-127] - 1)
            m["rel_12m_vs_etf"] = (m["ret_12m"] - (e.iloc[-1] / e.iloc[-253] - 1)) if m["ret_12m"] == m["ret_12m"] else np.nan
        ma200 = c.rolling(200).mean().iloc[-1]
        m["price_vs_200d"] = c.iloc[-1] / ma200 - 1 if ma200 == ma200 else np.nan
        if high is not None and low is not None:
            a = rotation.atr(high, low, close).dropna()
            m["atr14"] = float(a.iloc[-1]) if len(a) else np.nan
            m["atr14_pct"] = m["atr14"] / c.iloc[-1] if len(a) else np.nan
        if volume is not None:
            m["adv_usd_20d"] = float((c * volume).dropna().iloc[-20:].mean())
    m["short_pct_float"] = _num(info.get("shortPercentOfFloat"))
    m["flags"] = "; ".join(_flags(m, profile, thresholds))
    return m


def _flags(m: dict, profile: str, th: dict) -> list[str]:
    f = []

    def v(k):
        x = m.get(k)
        return np.nan if x is None else _num(x)

    if v("eps_rev_30d") < th["estimate_cut_pct"] or v("net_revisions_30d") < -0.3:
        f.append("ESTIMATES FALLING")
    if v("analysts") < th["min_analysts"]:
        f.append(f"LOW COVERAGE ({int(v('analysts')) if v('analysts') == v('analysts') else 0} analysts)")
    if v("estimate_dispersion") > th["dispersion_watch"]:
        f.append("WIDE ESTIMATE RANGE")
    if profile not in FINANCIAL_PROFILES:
        if v("net_debt_to_ebitda") > th["net_debt_ebitda_watch"]:
            f.append(f"LEVERAGE {v('net_debt_to_ebitda'):.1f}x")
        if v("interest_coverage") < th["interest_cover_pass"]:
            f.append(f"COVERAGE {v('interest_coverage'):.1f}x")
        if v("fcf_ttm") < 0:
            f.append("NEGATIVE FCF")
    if v("beneish_m") > th["beneish_fail"]:
        f.append(f"M-SCORE {v('beneish_m'):.2f}")
    if v("accruals_ratio") > th["accruals_fail"]:
        f.append("HIGH ACCRUALS")
    if v("price_vs_200d") < 0 and v("rel_6m_vs_etf") < -0.10:
        f.append("DOWNTREND")
    if 0 <= v("days_to_earnings") <= th["earnings_soon_days"]:
        f.append(f"EARNINGS IN {int(v('days_to_earnings'))}d")
    if v("short_pct_float") > th["short_interest_watch"]:
        f.append(f"SHORT INTEREST {v('short_pct_float') * 100:.0f}%")
    if m.get("negative_equity"):
        f.append("NEGATIVE EQUITY (ROE meaningless)")
    if (m.get("currency") or "USD") != "USD":
        f.append(f"NON-USD REPORTING ({m.get('currency')}; likely 20-F/IFRS)")
    elif (m.get("country") or "United States") != "United States":
        f.append(f"NON-US DOMICILE ({m.get('country')}; confirm 10-K vs 20-F)")
    if np.isnan(v("fwd_pe")) and profile not in ("early_growth", "reit"):
        f.append("NO POSITIVE FORWARD EPS")
    if m.get("fetch_errors"):
        f.append("PARTIAL DATA")
    return f


# ---------------------------------------------------------------------------
# ranking
# ---------------------------------------------------------------------------

def rank(df: pd.DataFrame, profile: str) -> pd.DataFrame:
    spec = PROFILE_METRICS.get(profile, PROFILE_METRICS["standard"])
    groups = {"valuation": spec["valuation"], "quality": spec["quality"], "momentum": MOMENTUM_METRICS}
    out = df.copy()
    for gname, metrics in groups.items():
        cols = []
        for key, better in metrics:
            if key not in out:
                continue
            s = pd.to_numeric(out[key], errors="coerce")
            pc = s.rank(pct=True, ascending=(better == "high"))
            out[f"pct_{key}"] = pc
            cols.append(f"pct_{key}")
        if cols:
            avail = out[cols].notna().sum(axis=1)
            score = out[cols].mean(axis=1, skipna=True)
            out[f"{gname}_score"] = score.where(avail >= max(1, len(cols) // 2))
        else:
            out[f"{gname}_score"] = np.nan
    all_metrics = [k for g in groups.values() for k, _ in g if k in out]
    out["data_completeness"] = out[all_metrics].apply(pd.to_numeric, errors="coerce").notna().mean(axis=1)
    out["composite"] = out[["valuation_score", "quality_score", "momentum_score"]].mean(axis=1, skipna=False)
    out["rank"] = out["composite"].rank(ascending=False, method="min")
    own = pd.to_numeric(out.get("pe_vs_own_hist"), errors="coerce")
    out["step1_cheap"] = np.where(out["valuation_score"] >= 0.5,
                                  np.where(own.isna() | (own <= 0), "Yes", "Partial (above own history)"), "No")
    rev30 = pd.to_numeric(out["eps_rev_30d"], errors="coerce")
    rev90 = pd.to_numeric(out["eps_rev_90d"], errors="coerce")
    net = pd.to_numeric(out["net_revisions_30d"], errors="coerce")
    ok = (rev90.fillna(0) >= -0.01) & (rev30.fillna(0) >= -0.01) & (net.fillna(0) >= 0)
    out["step2_estimates_ok"] = np.where(rev30.isna() & rev90.isna(), "No data", np.where(ok, "Yes", "No"))
    out["step3_temporary_discount"] = "AI news check"
    out["step4_catalyst_6m"] = "AI news check"
    return out.sort_values(["rank", "market_cap"], ascending=[True, False])


def run(ws: Workspace, key: str, refresh: bool = False, limit: int | None = None,
        progress: bool = True) -> pd.DataFrame:
    sub = ws.sub_industry(key)
    cfg, th = ws.settings["screening"], ws.settings["thresholds"]
    from iat import universe

    uni = universe.load(ws, key, rebuild_if_older_than_days=30)
    tickers = uni[uni["status"].str.startswith("included")]["ticker"].dropna().tolist()
    tickers = tickers[: (limit or int(cfg["max_tickers"]))]
    if not tickers:
        raise ValueError(f"Universe for '{key}' is empty after filters. Review data/universes/{key}.csv")
    etf = sub.get("etf") or SECTOR_ETFS.get(sub.get("sector", ""), "SPY")
    px = rotation.download(tickers + [etf, "SPY"], period="5y")
    rows = []
    started = store.now()
    for i, t in enumerate(tickers, 1):
        raw = fetch_cached(ws, t, float(cfg["cache_days"]), refresh=refresh)
        cached = raw.get("fetched", "") < started
        get = lambda f: px[f][t] if (f in px and t in px[f]) else None  # noqa: E731
        m = compute_metrics(raw, sub["profile"], get("Close"), px["Close"].get(etf), get("High"), get("Low"),
                            get("Volume"), th)
        m["sub_industry"], m["profile"], m["benchmark_etf"] = key, sub["profile"], etf
        rows.append(m)
        if progress:
            print(f"[{i}/{len(tickers)}] {t}{' (cached)' if cached else ''}"
                  f"{' errors: ' + m['fetch_errors'] if m.get('fetch_errors') else ''}", flush=True)
        if not cached:
            time.sleep(float(cfg["sleep_seconds"]))
    df = rank(pd.DataFrame(rows), sub["profile"])
    n = int(cfg["news_check_top_n"])
    df["news_check"] = np.where(df["rank"] <= n, "YES", "")
    folder = ws.out_dir("screens") / key
    store.write_csv(folder / f"{store.today()}.csv", df)
    store.write_latest_csv(ws, f"screen_{key}", df)
    keep = ["ticker", "composite", "valuation_score", "quality_score", "momentum_score", "rank", "fwd_pe",
            "eps_rev_30d", "eps_rev_90d", "flags"]
    h = df[[c for c in keep if c in df]].copy()
    h.insert(0, "sub_industry", key)
    h.insert(0, "date", store.today())
    store.append_history(ws, "screen_scores", h, keys=["date", "sub_industry", "ticker"])
    return df


def markdown(df: pd.DataFrame, key: str, top: int = 10) -> str:
    lines = [f"## Screen: {key} ({store.today()}) - {len(df)} names", "",
             "| Rank | Ticker | Composite | Val | Qual | Mom | Fwd P/E | EPS rev 30d | Cheap? | Est. OK? | Flags |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]

    def f(x, pct=False):
        x = _num(x)
        return "" if np.isnan(x) else (f"{x * 100:+.1f}%" if pct else f"{x:.2f}")

    for _, r in df.head(top).iterrows():
        lines.append(f"| {int(r['rank']) if r['rank'] == r['rank'] else ''} | {r['ticker']} | {f(r['composite'])} | "
                     f"{f(r['valuation_score'])} | {f(r['quality_score'])} | {f(r['momentum_score'])} | "
                     f"{f(r.get('fwd_pe'))} | {f(r.get('eps_rev_30d'), True)} | {r['step1_cheap']} | "
                     f"{r['step2_estimates_ok']} | {r.get('flags', '')} |")
    lines += ["", "Ranking = average of valuation, quality and revisions/momentum percentiles within this "
                  "sub-industry. It decides who gets a news check, not what to buy."]
    return "\n".join(lines) + "\n"
