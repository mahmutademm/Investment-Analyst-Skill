"""Macro dashboard from FRED (no API key) and a transparent business-cycle rule vote.

The rule vote is a *suggestion*. The skill shows every rule with its evidence and the user makes
the final cycle call. Thresholds are deliberately simple so they can be audited and changed.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
import pandas as pd

from iat import http, store
from iat.config import Workspace

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# id: (label, group, frequency)
SERIES: dict[str, tuple[str, str, str]] = {
    "CPIAUCSL": ("CPI, all items (index)", "Inflation", "M"),
    "CPILFESL": ("Core CPI (index)", "Inflation", "M"),
    "PCEPILFE": ("Core PCE price index (Fed target measure)", "Inflation", "M"),
    "T10YIE": ("10Y breakeven inflation", "Inflation", "D"),
    "DFF": ("Effective fed funds rate", "Policy", "D"),
    "DFEDTARU": ("Fed funds target, upper bound", "Policy", "D"),
    "DGS3MO": ("3M Treasury yield", "Rates", "D"),
    "DGS2": ("2Y Treasury yield", "Rates", "D"),
    "DGS10": ("10Y Treasury yield", "Rates", "D"),
    "DFII10": ("10Y TIPS real yield", "Rates", "D"),
    "T10Y2Y": ("10Y minus 2Y spread", "Curve", "D"),
    "T10Y3M": ("10Y minus 3M spread", "Curve", "D"),
    "BAMLH0A0HYM2": ("High-yield OAS (credit stress)", "Credit", "D"),
    "NFCI": ("Chicago Fed financial conditions (neg = loose)", "Credit", "W"),
    "UNRATE": ("Unemployment rate", "Labor", "M"),
    "SAHMREALTIME": ("Sahm rule recession indicator", "Labor", "M"),
    "ICSA": ("Initial jobless claims", "Labor", "W"),
    "PAYEMS": ("Nonfarm payrolls (thousands)", "Labor", "M"),
    "INDPRO": ("Industrial production (index)", "Growth", "M"),
    "CFNAI": ("Chicago Fed National Activity Index", "Growth", "M"),
    "PERMIT": ("Building permits (thousands, SAAR)", "Growth", "M"),
    "UMCSENT": ("UMich consumer sentiment", "Growth", "M"),
    "DTWEXBGS": ("Broad trade-weighted US dollar", "Markets", "D"),
    "DCOILWTICO": ("WTI crude oil ($/bbl)", "Markets", "D"),
    "USREC": ("NBER recession flag (lagging)", "Growth", "M"),
}

PHASES = ["Early recovery", "Mid cycle", "Late cycle", "Contraction"]

# Starting map only. The pattern breaks often; the scorecard's other pillars must confirm.
PHASE_SECTORS = {
    "Early recovery": ["Financials", "Consumer Discretionary", "Industrials", "Real Estate", "Materials"],
    "Mid cycle": ["Technology", "Communication Services", "Industrials"],
    "Late cycle": ["Energy", "Materials", "Health Care", "Consumer Staples"],
    "Contraction": ["Consumer Staples", "Utilities", "Health Care"],
}
PHASE_AVOID = {
    "Early recovery": ["Utilities", "Consumer Staples", "Health Care"],
    "Mid cycle": ["Utilities"],
    "Late cycle": ["Consumer Discretionary", "Technology", "Real Estate"],
    "Contraction": ["Industrials", "Technology", "Materials", "Consumer Discretionary", "Financials"],
}


def fetch_series(series_id: str, start: str = "2010-01-01") -> pd.Series:
    r = http.get(FRED_CSV, params={"id": series_id, "cosd": start}, timeout=60)
    df = pd.read_csv(io.StringIO(r.text))
    date_col = df.columns[0]
    s = pd.to_numeric(df[series_id].replace(".", np.nan), errors="coerce")
    s.index = pd.to_datetime(df[date_col])
    return s.dropna().rename(series_id)


def fetch_all(start: str = "2010-01-01") -> tuple[dict[str, pd.Series], dict[str, str]]:
    data, errors = {}, {}
    for sid in SERIES:
        try:
            data[sid] = fetch_series(sid, start)
        except Exception as exc:  # keep going; report what failed
            errors[sid] = f"{type(exc).__name__}: {exc}"
    return data, errors


# ---- derived metrics -----------------------------------------------------------

def _val_at(s: pd.Series, when: pd.Timestamp) -> float:
    s = s[s.index <= when]
    return float(s.iloc[-1]) if len(s) else np.nan


def _ago(s: pd.Series, months: int) -> float:
    if s.empty:
        return np.nan
    return _val_at(s, s.index[-1] - pd.DateOffset(months=months))


def _yoy(s: pd.Series) -> pd.Series:
    return (s / s.shift(12) - 1) * 100


def _ann3m(s: pd.Series) -> pd.Series:
    return ((s / s.shift(3)) ** 4 - 1) * 100


@dataclass
class Indicator:
    key: str
    label: str
    group: str
    latest: float
    date: str
    chg_3m: float
    chg_6m: float
    chg_12m: float
    note: str = ""


def _ind(key, label, group, s: pd.Series, note="") -> Indicator:
    if s is None or s.dropna().empty:
        return Indicator(key, label, group, np.nan, "", np.nan, np.nan, np.nan, "no data")
    s = s.dropna()
    last = float(s.iloc[-1])
    return Indicator(key, label, group, last, s.index[-1].date().isoformat(),
                     last - _ago(s, 3), last - _ago(s, 6), last - _ago(s, 12), note)


def build_dashboard(data: dict[str, pd.Series]) -> tuple[list[Indicator], dict[str, float]]:
    g = data.get
    inds: list[Indicator] = []
    m: dict[str, float] = {}

    if g("CPIAUCSL") is not None:
        yoy, a3 = _yoy(g("CPIAUCSL")), _ann3m(g("CPIAUCSL"))
        inds += [_ind("cpi_yoy", "Headline CPI YoY %", "Inflation", yoy),
                 _ind("cpi_3m_ann", "Headline CPI 3m annualized %", "Inflation", a3)]
        m["cpi_yoy"], m["cpi_3m_ann"] = yoy.dropna().iloc[-1], a3.dropna().iloc[-1]
    if g("CPILFESL") is not None:
        yoy, a3 = _yoy(g("CPILFESL")), _ann3m(g("CPILFESL"))
        inds += [_ind("core_cpi_yoy", "Core CPI YoY %", "Inflation", yoy),
                 _ind("core_cpi_3m_ann", "Core CPI 3m annualized %", "Inflation", a3,
                      "3m annualized above YoY = re-accelerating")]
        m["core_cpi_yoy"], m["core_cpi_3m_ann"] = yoy.dropna().iloc[-1], a3.dropna().iloc[-1]
        m["core_cpi_yoy_6m_chg"] = m["core_cpi_yoy"] - _ago(yoy.dropna(), 6)
    if g("PCEPILFE") is not None:
        yoy, a3 = _yoy(g("PCEPILFE")), _ann3m(g("PCEPILFE"))
        inds += [_ind("core_pce_yoy", "Core PCE YoY % (Fed target 2%)", "Inflation", yoy),
                 _ind("core_pce_3m_ann", "Core PCE 3m annualized %", "Inflation", a3)]
        m["core_pce_yoy"], m["core_pce_3m_ann"] = yoy.dropna().iloc[-1], a3.dropna().iloc[-1]
        m["core_pce_yoy_6m_chg"] = m["core_pce_yoy"] - _ago(yoy.dropna(), 6)
    if g("T10YIE") is not None:
        inds.append(_ind("breakeven_10y", "10Y breakeven inflation %", "Inflation", g("T10YIE")))

    if g("DFF") is not None:
        ff = g("DFF")
        inds.append(_ind("fed_funds", "Effective fed funds %", "Policy", ff,
                         "6m change < -0.25 = easing, > +0.25 = tightening"))
        m["fed_funds"] = float(ff.iloc[-1])
        m["fed_funds_6m_chg"] = m["fed_funds"] - _ago(ff, 6)
        m["fed_funds_12m_chg"] = m["fed_funds"] - _ago(ff, 12)
        if "core_pce_yoy" in m:
            m["real_fed_funds"] = m["fed_funds"] - m["core_pce_yoy"]
    if g("DFEDTARU") is not None:
        tgt = g("DFEDTARU")
        m["fed_target"] = float(tgt.iloc[-1])
        m["fed_target_6m_chg"] = m["fed_target"] - _ago(tgt, 6)
    if g("DGS2") is not None and g("DFF") is not None:
        implied = (g("DGS2") - g("DFF").reindex(g("DGS2").index, method="ffill")).dropna()
        inds.append(_ind("two_year_minus_ff", "2Y yield minus fed funds (market-implied path)", "Policy", implied,
                         "Below -0.25 = market prices cuts; above +0.25 = prices hikes. Confirm on CME FedWatch."))
        m["two_year_minus_ff"] = float(implied.iloc[-1])

    for sid, key in (("DGS3MO", "y3m"), ("DGS2", "y2"), ("DGS10", "y10"), ("DFII10", "real10")):
        if g(sid) is not None:
            inds.append(_ind(key, SERIES[sid][0] + " %", "Rates", g(sid)))
            m[key] = float(g(sid).iloc[-1])
    if g("DGS10") is not None:
        y10 = g("DGS10")
        ma50, ma200 = y10.rolling(50).mean().iloc[-1], y10.rolling(200).mean().iloc[-1]
        m["y10_vs_ma50"], m["y10_vs_ma200"] = m["y10"] - ma50, m["y10"] - ma200
        m["y10_3m_chg"] = m["y10"] - _ago(y10, 3)
        trend = "rising" if m["y10_vs_ma50"] > 0 and m["y10_vs_ma200"] > 0 else (
            "falling" if m["y10_vs_ma50"] < 0 and m["y10_vs_ma200"] < 0 else "mixed")
        m["y10_trend"] = trend  # type: ignore[assignment]

    for sid, key in (("T10Y2Y", "curve_10y2y"), ("T10Y3M", "curve_10y3m")):
        if g(sid) is not None:
            inds.append(_ind(key, SERIES[sid][0] + " (pp)", "Curve", g(sid)))
            m[key] = float(g(sid).iloc[-1])
            m[key + "_6m_chg"] = m[key] - _ago(g(sid), 6)
            m[key + "_min_24m"] = float(g(sid)[g(sid).index >= g(sid).index[-1] - pd.DateOffset(months=24)].min())

    if g("BAMLH0A0HYM2") is not None:
        hy = g("BAMLH0A0HYM2")
        inds.append(_ind("hy_oas", "High-yield OAS %", "Credit", hy, "Widening = rising default fears"))
        m["hy_oas"] = float(hy.iloc[-1])
        m["hy_oas_3m_chg"] = m["hy_oas"] - _ago(hy, 3)
        m["hy_oas_median"] = float(hy.median())
    if g("NFCI") is not None:
        inds.append(_ind("nfci", "Chicago Fed NFCI (neg = looser than avg)", "Credit", g("NFCI")))
        m["nfci"] = float(g("NFCI").iloc[-1])

    if g("UNRATE") is not None:
        u = g("UNRATE")
        inds.append(_ind("unrate", "Unemployment rate %", "Labor", u))
        m["unrate"] = float(u.iloc[-1])
        m["unrate_vs_12m_low"] = m["unrate"] - float(u[u.index >= u.index[-1] - pd.DateOffset(months=12)].min())
    if g("SAHMREALTIME") is not None:
        inds.append(_ind("sahm", "Sahm rule (>= 0.50 = recession signal)", "Labor", g("SAHMREALTIME")))
        m["sahm"] = float(g("SAHMREALTIME").iloc[-1])
    if g("ICSA") is not None:
        c4 = g("ICSA").rolling(4).mean().dropna()
        chg = (c4 / c4.shift(26) - 1) * 100
        inds.append(_ind("claims_4wk", "Initial claims, 4-week avg", "Labor", c4))
        inds.append(_ind("claims_26w_chg", "Claims 4wk avg vs 26 weeks ago %", "Labor", chg.dropna(),
                         "> +15% has preceded recessions"))
        m["claims_26w_chg"] = float(chg.dropna().iloc[-1])
    if g("PAYEMS") is not None:
        p3 = g("PAYEMS").diff().rolling(3).mean().dropna()
        inds.append(_ind("payrolls_3m_avg", "Payroll gains, 3m avg (thousands)", "Labor", p3))
        m["payrolls_3m_avg"] = float(p3.iloc[-1])

    if g("CFNAI") is not None:
        c3 = g("CFNAI").rolling(3).mean().dropna()
        inds.append(_ind("cfnai_3m", "CFNAI 3m avg (< -0.70 = recession risk; > 0 = above trend)", "Growth", c3))
        m["cfnai_3m"] = float(c3.iloc[-1])
        m["cfnai_3m_6m_chg"] = m["cfnai_3m"] - _ago(c3, 6)
    if g("INDPRO") is not None:
        ip = _yoy(g("INDPRO")).dropna()
        inds.append(_ind("indpro_yoy", "Industrial production YoY %", "Growth", ip))
        m["indpro_yoy"] = float(ip.iloc[-1])
    if g("PERMIT") is not None:
        pm = _yoy(g("PERMIT")).dropna()
        inds.append(_ind("permits_yoy", "Building permits YoY % (leading)", "Growth", pm))
        m["permits_yoy"] = float(pm.iloc[-1])
    if g("UMCSENT") is not None:
        inds.append(_ind("sentiment", "UMich consumer sentiment", "Growth", g("UMCSENT")))
    if g("USREC") is not None:
        m["nber_recession"] = float(g("USREC").iloc[-1])

    if g("DTWEXBGS") is not None:
        d = g("DTWEXBGS")
        inds.append(_ind("usd", "Broad US dollar index", "Markets", d))
        m["usd_6m_pct"] = (float(d.iloc[-1]) / _ago(d, 6) - 1) * 100
    if g("DCOILWTICO") is not None:
        o = g("DCOILWTICO")
        inds.append(_ind("wti", "WTI crude $/bbl", "Markets", o))
        m["wti_6m_pct"] = (float(o.iloc[-1]) / _ago(o, 6) - 1) * 100
    return inds, m


# ---- cycle rules ---------------------------------------------------------------

def _has(m, *keys):
    return all(k in m and m[k] is not None and not (isinstance(m[k], float) and np.isnan(m[k])) for k in keys)


def cycle_votes(m: dict[str, float]) -> list[dict]:
    """Each rule: (phase, weight, description, evidence). Only rules with data are evaluated."""
    R: list[dict] = []

    def rule(phase, weight, desc, cond, evidence):
        R.append({"phase": phase, "weight": weight, "rule": desc, "fired": bool(cond), "evidence": evidence})

    if _has(m, "cfnai_3m", "cfnai_3m_6m_chg"):
        c, d = m["cfnai_3m"], m["cfnai_3m_6m_chg"]
        ev = f"CFNAI 3m avg {c:.2f} (6m change {d:+.2f})"
        rule("Contraction", 2, "Activity well below trend (CFNAI 3m < -0.70)", c < -0.70, ev)
        rule("Early recovery", 2, "Activity below trend but improving (CFNAI 3m < 0, rising)", c < 0 and d > 0.15, ev)
        rule("Mid cycle", 2, "Activity at/above trend and steady (CFNAI 3m >= -0.1, |6m chg| < 0.3)",
             c >= -0.1 and abs(d) < 0.3, ev)
        rule("Late cycle", 1, "Activity positive but decelerating (CFNAI 3m > -0.3, falling)", c > -0.3 and d < -0.15, ev)
    if _has(m, "sahm"):
        rule("Contraction", 3, "Sahm rule triggered (>= 0.50)", m["sahm"] >= 0.5, f"Sahm {m['sahm']:.2f}")
    if _has(m, "unrate_vs_12m_low"):
        x = m["unrate_vs_12m_low"]
        ev = f"Unemployment {m.get('unrate', np.nan):.1f}%, {x:+.1f}pp vs 12m low"
        rule("Late cycle", 1, "Unemployment starting to rise from lows (+0.2 to +0.4pp)", 0.2 <= x < 0.5, ev)
        rule("Mid cycle", 1, "Unemployment at/near cycle low (< +0.2pp)", x < 0.2, ev)
    if _has(m, "claims_26w_chg"):
        x = m["claims_26w_chg"]
        ev = f"Claims 4wk avg {x:+.1f}% vs 26w ago"
        rule("Contraction", 1, "Jobless claims up > 15% in 6 months", x > 15, ev)
        rule("Early recovery", 1, "Jobless claims falling > 10% in 6 months", x < -10, ev)
    if _has(m, "core_pce_yoy", "core_pce_yoy_6m_chg"):
        x, d = m["core_pce_yoy"], m["core_pce_yoy_6m_chg"]
        ev = f"Core PCE {x:.2f}% YoY ({d:+.2f}pp in 6m)"
        rule("Late cycle", 2, "Inflation elevated and not falling (core PCE > 2.75%, 6m chg >= 0)", x > 2.75 and d >= 0, ev)
        rule("Mid cycle", 1, "Inflation near target and stable (core PCE 1.5-2.75%)", 1.5 <= x <= 2.75 and abs(d) < 0.3, ev)
    pol_key = "fed_target_6m_chg" if _has(m, "fed_target_6m_chg") else "fed_funds_6m_chg"
    if _has(m, pol_key):
        x = m[pol_key]
        ev = (f"Fed target upper {m.get('fed_target', np.nan):.2f}% ({x:+.2f}pp in 6m)" if pol_key == "fed_target_6m_chg"
              else f"Fed funds {m.get('fed_funds', np.nan):.2f}% ({x:+.2f}pp in 6m)")
        rule("Late cycle", 2, "Fed tightening (6m change >= +0.25pp)", x >= 0.25, ev)
        rule("Early recovery", 1, "Fed easing (6m change <= -0.25pp)", x <= -0.25, ev)
        rule("Contraction", 1, "Fed cutting aggressively (6m change < -1.0pp)", x < -1.0, ev)
        rule("Mid cycle", 1, "Fed on hold (no change in 6m)", abs(x) < 0.125, ev)
    if _has(m, "core_cpi_3m_ann", "core_cpi_yoy"):
        a, y = m["core_cpi_3m_ann"], m["core_cpi_yoy"]
        rule("Late cycle", 1, "Core inflation re-accelerating (core CPI 3m annualized > YoY + 0.5pp)", a > y + 0.5,
             f"Core CPI 3m ann. {a:.2f}% vs YoY {y:.2f}%")
    if _has(m, "wti_6m_pct"):
        x = m["wti_6m_pct"]
        rule("Late cycle", 1, "Commodity squeeze (WTI up > 20% in 6m)", x > 20, f"WTI {x:+.1f}% in 6m")
    if _has(m, "y10_3m_chg", "y10_vs_ma200"):
        d, v = m["y10_3m_chg"], m["y10_vs_ma200"]
        rule("Late cycle", 1, "Long yields rising (10Y +0.40pp in 3m and above 200d avg)", d > 0.4 and v > 0,
             f"10Y {m.get('y10', np.nan):.2f}% ({d:+.2f}pp in 3m, {v:+.2f} vs 200d)")
    if _has(m, "real_fed_funds"):
        x = m["real_fed_funds"]
        rule("Late cycle", 1, "Policy restrictive (real fed funds > 1.5%)", x > 1.5, f"Real fed funds {x:.2f}%")
    if _has(m, "two_year_minus_ff"):
        x = m["two_year_minus_ff"]
        ev = f"2Y minus fed funds {x:+.2f}pp"
        rule("Early recovery", 1, "Market pricing meaningful cuts (2Y < FF by > 0.50pp)", x < -0.5, ev)
        rule("Late cycle", 1, "Market pricing hikes (2Y > FF by > 0.25pp)", x > 0.25, ev)
    if _has(m, "curve_10y3m", "curve_10y3m_6m_chg", "curve_10y3m_min_24m"):
        c, d, lo = m["curve_10y3m"], m["curve_10y3m_6m_chg"], m["curve_10y3m_min_24m"]
        ev = f"10Y-3M {c:+.2f}pp (6m {d:+.2f}, 24m low {lo:+.2f})"
        rule("Late cycle", 2, "Curve flat or inverted (10Y-3M < 0.25pp)", c < 0.25, ev)
        rule("Early recovery", 2, "Curve steepening out of inversion (24m low < 0, now > 0, 6m chg > +0.5)",
             lo < 0 and c > 0 and d > 0.5, ev)
        rule("Mid cycle", 1, "Curve positive and stable (> 0.75pp, |6m chg| < 0.5)", c > 0.75 and abs(d) < 0.5, ev)
    if _has(m, "hy_oas", "hy_oas_3m_chg", "hy_oas_median"):
        x, d, med = m["hy_oas"], m["hy_oas_3m_chg"], m["hy_oas_median"]
        ev = f"HY OAS {x:.2f}% (3m {d:+.2f}, sample median {med:.2f})"
        rule("Contraction", 2, "Credit stress (HY OAS > 6% or +1.5pp in 3m)", x > 6 or d > 1.5, ev)
        rule("Early recovery", 1, "Spreads elevated but tightening (> median, 3m chg < -0.5)", x > med and d < -0.5, ev)
        rule("Mid cycle", 1, "Spreads tight and stable (< median, |3m chg| < 0.3)", x < med and abs(d) < 0.3, ev)
        rule("Late cycle", 1, "Spreads widening (3m chg > +0.3pp, not yet stress)", d > 0.3 and not (x > 6 or d > 1.5), ev)
    if _has(m, "permits_yoy"):
        x = m["permits_yoy"]
        ev = f"Permits {x:+.1f}% YoY"
        rule("Early recovery", 1, "Housing turning up (permits YoY > +5%)", x > 5, ev)
        rule("Late cycle", 1, "Housing rolling over (permits YoY < -10%)", x < -10, ev)
    if _has(m, "nber_recession"):
        rule("Contraction", 3, "NBER recession flag on (lagging, confirms only)", m["nber_recession"] >= 1,
             f"USREC {m['nber_recession']:.0f}")
    return R


def tally(rules: list[dict]) -> dict:
    scores = {p: 0 for p in PHASES}
    for r in rules:
        if r["fired"]:
            scores[r["phase"]] += r["weight"]
    total = sum(scores.values())
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    lead, second = ranked[0], ranked[1]
    conf = (lead[1] / total) if total else 0.0
    margin = lead[1] - second[1]
    return {
        "scores": scores,
        "suggested_phase": lead[0] if total else "Undetermined",
        "runner_up": second[0],
        "confidence_share": round(conf, 2),
        "margin": margin,
        "ambiguous": total == 0 or margin <= 1 or conf < 0.4,
        "favored_sectors": PHASE_SECTORS.get(lead[0], []),
        "unfavored_sectors": PHASE_AVOID.get(lead[0], []),
    }


def run(ws: Workspace, start: str = "2010-01-01") -> dict:
    data, errors = fetch_all(start)
    inds, metrics = build_dashboard(data)
    rules = cycle_votes(metrics)
    summary = tally(rules)
    as_of = store.now()
    result = {
        "as_of": as_of,
        "metrics": metrics,
        "indicators": [i.__dict__ for i in inds],
        "rules": rules,
        "cycle": summary,
        "errors": errors,
        "sources": {sid: f"https://fred.stlouisfed.org/series/{sid}" for sid in SERIES},
    }
    store.write_latest_json(ws, "macro", result)
    hist = pd.DataFrame([{"date": store.today(), **{k: v for k, v in metrics.items() if not isinstance(v, str)},
                          "suggested_phase": summary["suggested_phase"],
                          **{f"score_{p.split()[0].lower()}": s for p, s in summary["scores"].items()}}])
    store.append_history(ws, "macro", hist, keys=["date"])
    return result


def markdown(result: dict) -> str:
    c = result["cycle"]
    lines = [f"## Macro snapshot ({result['as_of'][:10]})", "",
             f"**Rule-based phase suggestion:** {c['suggested_phase']} "
             f"(share of votes {c['confidence_share']:.0%}, runner-up {c['runner_up']}"
             f"{', AMBIGUOUS' if c['ambiguous'] else ''})", "",
             "| Phase | Score |", "|---|---|"]
    lines += [f"| {p} | {s} |" for p, s in c["scores"].items()]
    lines += ["", "| Indicator | Latest | 3m chg | 6m chg | 12m chg | As of |", "|---|---|---|---|---|---|"]
    for i in result["indicators"]:
        def f(x):
            return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.2f}"
        lines.append(f"| {i['label']} | {f(i['latest'])} | {f(i['chg_3m'])} | {f(i['chg_6m'])} | {f(i['chg_12m'])} | {i['date']} |")
    if result.get("errors"):
        lines += ["", "**Series that failed to download:** " + ", ".join(result["errors"])]
    return "\n".join(lines) + "\n"
