"""Valuation math in Python. The Excel workbook implements the same model with live formulas;
these functions provide default assumptions, the reverse-DCF solve and a cross-check value.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

YEARS = 10


@dataclass
class Scenario:
    name: str
    g1: float                 # stage-1 revenue growth
    n1: int                   # stage-1 years (growth then fades linearly to terminal by year 10)
    g_terminal: float
    margin_target: float      # EBIT margin reached by `margin_years`
    margin_years: int
    sales_to_capital: float   # revenue added per $ of reinvestment
    ronic: float              # return on new invested capital in perpetuity (sets terminal reinvestment)
    wacc_adj: float = 0.0     # added to WACC for this scenario
    probability: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class Base:
    revenue0: float
    margin0: float
    tax_rate: float
    wacc: float
    net_debt: float
    minority: float
    shares: float
    price: float


def growth_path(s: Scenario) -> list[float]:
    out = []
    for t in range(1, YEARS + 1):
        if t <= s.n1:
            out.append(s.g1)
        else:
            out.append(s.g1 - (s.g1 - s.g_terminal) * (t - s.n1) / (YEARS - s.n1))
    return out


def dcf(b: Base, s: Scenario) -> dict:
    w = b.wacc + s.wacc_adj
    rev_prev, fcffs, pvs, revs, margins = b.revenue0, [], [], [], []
    for t, g in enumerate(growth_path(s), start=1):
        rev = rev_prev * (1 + g)
        m = b.margin0 + (s.margin_target - b.margin0) * min(t, s.margin_years) / s.margin_years
        nopat = rev * m * (1 - b.tax_rate)
        reinv = (rev - rev_prev) / s.sales_to_capital
        fcff = nopat - reinv
        fcffs.append(fcff)
        pvs.append(fcff / (1 + w) ** t)
        revs.append(rev)
        margins.append(m)
        rev_prev = rev
    nopat11 = revs[-1] * (1 + s.g_terminal) * s.margin_target * (1 - b.tax_rate)
    fcff11 = nopat11 * (1 - s.g_terminal / s.ronic)
    if w <= s.g_terminal:
        return {"error": "WACC must exceed terminal growth"}
    tv = fcff11 / (w - s.g_terminal)
    pv_tv = tv / (1 + w) ** YEARS
    ev = sum(pvs) + pv_tv
    equity = ev - b.net_debt - b.minority
    per_share = equity / b.shares
    return {"scenario": s.name, "wacc": w, "revenues": revs, "margins": margins, "fcff": fcffs,
            "pv_fcff": sum(pvs), "pv_tv": pv_tv, "ev": ev, "equity": equity, "per_share": per_share,
            "tv_share": pv_tv / ev if ev else math.nan, "upside": per_share / b.price - 1 if b.price else math.nan}


def reverse_dcf(b: Base, s: Scenario, lo: float = -0.20, hi: float = 0.60) -> dict:
    """Solve the stage-1 growth that makes DCF value per share equal the current price."""
    def f(g):
        s2 = Scenario(**{**s.to_dict(), "g1": g})
        return dcf(b, s2)["per_share"] - b.price
    f_lo, f_hi = f(lo), f(hi)
    if np.sign(f_lo) == np.sign(f_hi):
        return {"implied_g1": None, "note": f"No solution in [{lo:.0%}, {hi:.0%}]: value at low {f_lo + b.price:.2f}, "
                                            f"at high {f_hi + b.price:.2f}. Margins or reinvestment dominate."}
    for _ in range(80):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < 1e-6:
            break
        if np.sign(fm) == np.sign(f_lo):
            lo, f_lo = mid, fm
        else:
            hi = mid
    return {"implied_g1": (lo + hi) / 2, "note": "Stage-1 revenue growth implied by today's price, other base inputs held"}


def ddm(d0: float, r: float, g1: float, n: int, g_terminal: float) -> dict:
    if d0 <= 0 or r <= g_terminal:
        return {"value": None, "gordon": None}
    pv, d = 0.0, d0
    for t in range(1, n + 1):
        d *= 1 + g1
        pv += d / (1 + r) ** t
    tv = d * (1 + g_terminal) / (r - g_terminal)
    return {"value": pv + tv / (1 + r) ** n, "gordon": d0 * (1 + g_terminal) / (r - g_terminal)}


def justified_pb(roe: float, ke: float, g: float, bvps: float) -> dict:
    if ke <= g:
        return {"pb": None, "value": None}
    pb = (roe - g) / (ke - g)
    return {"pb": pb, "value": pb * bvps}


def residual_income(bv0: float, roe: float, ke: float, payout: float, g: float, shares: float, years: int = 5) -> dict:
    bv, pv = bv0, 0.0
    ri = 0.0
    for t in range(1, years + 1):
        ri = (roe - ke) * bv
        pv += ri / (1 + ke) ** t
        bv = bv * (1 + roe * (1 - payout))
    tv = ri * (1 + g) / (ke - g) / (1 + ke) ** years if ke > g else 0.0
    return {"value_per_share": (bv0 + pv + tv) / shares if shares else None}


def capm(rf: float, beta: float, erp: float) -> float:
    return rf + beta * erp


def wacc(ke: float, kd_after_tax: float, equity_value: float, debt_value: float) -> float:
    tot = equity_value + max(debt_value, 0)
    return (equity_value / tot) * ke + (max(debt_value, 0) / tot) * kd_after_tax if tot else ke


def lifecycle(profile: str, sector: str, revenue_cagr: float, net_income: float, ebit: float,
              payout: float, op_margin_std: float) -> tuple[str, str]:
    """Suggest a life-cycle stage. The user confirms or overrides it."""
    nz = lambda x: x if x == x else 0.0  # noqa: E731
    if profile in ("bank", "insurer"):
        return "Financials", "Bank/insurer profile: debt is raw material, so use residual income / justified P/B"
    if nz(net_income) <= 0 or nz(ebit) <= 0:
        return "Early / unprofitable", "Negative earnings: forward DCF is mostly guesswork; use EV/sales and reverse DCF"
    if nz(revenue_cagr) < -0.02:
        return "Declining", "Revenue shrinking: consider sum-of-the-parts or liquidation value"
    if sector in ("Energy", "Materials") or nz(op_margin_std) > 0.06:
        return "Cyclical", "Commodity sector or volatile margins: value on normalized mid-cycle earnings"
    if nz(revenue_cagr) > 0.15:
        return "High growth", "Revenue CAGR > 15%: 3-stage DCF with growth fading to terminal"
    if nz(payout) >= 0.4 and nz(revenue_cagr) < 0.06:
        return "Mature dividend payer", "Stable payout >= 40% and low growth: DDM, cross-check with 2-stage DCF"
    return "Mature", "Profitable, moderate growth: 2-stage DCF and FCF yield"


LIFECYCLE_METHODS = {
    "Early / unprofitable": ["EV/sales vs peers", "Reverse DCF"],
    "High growth": ["3-stage DCF", "Reverse DCF", "Scenarios"],
    "Mature": ["2-stage DCF", "FCF yield", "Reverse DCF"],
    "Mature dividend payer": ["DDM", "2-stage DCF"],
    "Financials": ["Justified P/B", "Residual income"],
    "Cyclical": ["Normalized earnings x multiple", "DCF on mid-cycle margin"],
    "Declining": ["Sum-of-the-parts", "Liquidation value"],
}


def default_scenarios(revenue_growth: float, eps_growth: float, margin0: float, sales_to_capital: float,
                      wacc_: float, g_terminal: float, probs: dict) -> list[Scenario]:
    """Starting assumptions only. The skill reviews them with the user and ties each change to SWOT/evidence."""
    vals = [v for v in (revenue_growth, eps_growth) if v == v and v is not None]
    g = float(np.clip(np.mean(vals) if vals else 0.05, -0.05, 0.30))
    s2c = float(np.clip(sales_to_capital if sales_to_capital == sales_to_capital and sales_to_capital > 0 else 1.5, 0.3, 5))
    m0 = float(margin0 if margin0 == margin0 else 0.10)
    ronic_base = max(wacc_ + 0.02, 0.08)
    return [
        Scenario("Bear", max(g - 0.05, -0.05), 5, g_terminal - 0.005, max(m0 - 0.02, 0.01), 5, s2c * 0.8,
                 max(wacc_, 0.06), 0.005, probs.get("bear", 0.25)),
        Scenario("Base", g, 5, g_terminal, m0, 5, s2c, ronic_base, 0.0, probs.get("base", 0.5)),
        Scenario("Bull", g + 0.05, 5, g_terminal + 0.005, m0 + 0.02, 5, s2c * 1.2, ronic_base + 0.03, -0.0025,
                 probs.get("bull", 0.25)),
    ]


def position_size(price: float, atr: float, k: float, portfolio: float | None, risk_pct: float,
                  max_pct: float) -> dict:
    stop = price - k * atr if atr == atr else math.nan
    rps = price - stop
    if not portfolio or not rps or rps != rps or rps <= 0:
        return {"stop": stop, "risk_per_share": rps, "shares": None}
    by_risk = math.floor(portfolio * risk_pct / 100 / rps)
    by_cap = math.floor(portfolio * max_pct / 100 / price)
    shares = min(by_risk, by_cap)
    return {"stop": stop, "risk_per_share": rps, "shares": shares, "position_value": shares * price,
            "pct_portfolio": shares * price / portfolio * 100, "capped": by_cap < by_risk}
