"""Ratio definitions written once, evaluated two ways.

* `evaluate(fx)` computes every ratio in Python (used by the screen and by the pass/fail gate).
* `excel_formula(...)` renders the same definition as an Excel formula that references the
  Financials sheet cells, so the workbook is auditable cell by cell.

Missing inputs give NaN in Python and "" in Excel (guarded with COUNT), never a silent zero.
`opt(...)` marks an input that may be missing and should then count as 0 (e.g. leases).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from iat.fundamentals import Fundamentals

NAN = float("nan")


def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


class Expr:
    def __add__(self, o): return Bin("+", self, lift(o))
    def __radd__(self, o): return Bin("+", lift(o), self)
    def __sub__(self, o): return Bin("-", self, lift(o))
    def __rsub__(self, o): return Bin("-", lift(o), self)
    def __mul__(self, o): return Bin("*", self, lift(o))
    def __rmul__(self, o): return Bin("*", lift(o), self)
    def __truediv__(self, o): return Bin("/", self, lift(o))
    def __rtruediv__(self, o): return Bin("/", lift(o), self)
    def __neg__(self): return Bin("-", Num(0), self)
    def __gt__(self, o): return Cmp(">", self, lift(o))
    def __lt__(self, o): return Cmp("<", self, lift(o))
    def __ge__(self, o): return Cmp(">=", self, lift(o))
    def __le__(self, o): return Cmp("<=", self, lift(o))

    def py(self, ctx) -> float: raise NotImplementedError
    def xl(self, ctx) -> str | None: raise NotImplementedError
    def required_cells(self, ctx) -> list[str]: return []


def lift(x) -> Expr:
    return x if isinstance(x, Expr) else Num(float(x))


@dataclass(eq=False)
class Num(Expr):
    v: float
    def py(self, ctx): return self.v
    def xl(self, ctx): return repr(self.v) if self.v >= 0 else f"({self.v!r})"


@dataclass(eq=False)
class F(Expr):
    """A Financials field, optionally lagged by one period. optional=True -> missing counts as 0."""
    name: str
    lag: int = 0
    optional: bool = False

    def py(self, ctx):
        v = ctx.field(self.name, self.lag)
        if _isnan(v):
            return 0.0 if (self.optional and ctx.has_period(self.lag)) else NAN
        return v

    def xl(self, ctx):
        ref = ctx.field_cell(self.name, self.lag)
        if ref is None:
            return None
        return f"N({ref})" if self.optional else ref

    def required_cells(self, ctx):
        if self.optional:
            return []
        ref = ctx.field_cell(self.name, self.lag)
        return [ref] if ref else []


@dataclass(eq=False)
class M(Expr):
    """Another ratio (same sheet), optionally lagged; default replaces a missing value."""
    name: str
    lag: int = 0
    default: float | None = None

    def py(self, ctx):
        v = ctx.metric(self.name, self.lag)
        if _isnan(v) and self.default is not None and ctx.has_period(self.lag):
            return self.default
        return v

    def xl(self, ctx):
        ref = ctx.metric_cell(self.name, self.lag)
        if ref is None:
            return repr(self.default) if self.default is not None else None
        if self.default is not None:
            return f"IF(ISNUMBER({ref}),{ref},{self.default!r})"
        return ref

    def required_cells(self, ctx):
        if self.default is not None:
            return []
        ref = ctx.metric_cell(self.name, self.lag)
        return [ref] if ref else []


@dataclass(eq=False)
class Bin(Expr):
    op: str
    a: Expr
    b: Expr

    def py(self, ctx):
        x, y = self.a.py(ctx), self.b.py(ctx)
        if _isnan(x) or _isnan(y):
            return NAN
        if self.op == "+": return x + y
        if self.op == "-": return x - y
        if self.op == "*": return x * y
        if y == 0:
            return NAN
        return x / y

    def xl(self, ctx):
        x, y = self.a.xl(ctx), self.b.xl(ctx)
        if x is None or y is None:
            return None
        return f"({x}{self.op}{y})"

    def required_cells(self, ctx):
        return self.a.required_cells(ctx) + self.b.required_cells(ctx)


@dataclass(eq=False)
class Cmp(Expr):
    op: str
    a: Expr
    b: Expr

    def py(self, ctx):
        x, y = self.a.py(ctx), self.b.py(ctx)
        if _isnan(x) or _isnan(y):
            return NAN
        return float({">": x > y, "<": x < y, ">=": x >= y, "<=": x <= y}[self.op])

    def xl(self, ctx):
        x, y = self.a.xl(ctx), self.b.xl(ctx)
        if x is None or y is None:
            return None
        return f"({x}{self.op}{y})"

    def required_cells(self, ctx):
        return self.a.required_cells(ctx) + self.b.required_cells(ctx)


@dataclass(eq=False)
class Fn(Expr):
    name: str  # MIN, MAX, ABS, IF
    args: tuple

    def py(self, ctx):
        vals = [a.py(ctx) for a in self.args]
        if self.name == "IF":
            c = vals[0]
            if _isnan(c):
                return NAN
            return vals[1] if c else vals[2]
        if any(_isnan(v) for v in vals):
            return NAN
        if self.name == "MIN": return min(vals)
        if self.name == "MAX": return max(vals)
        if self.name == "ABS": return abs(vals[0])
        if self.name == "POS": return vals[0] if vals[0] > 0 else NAN
        raise ValueError(self.name)

    def xl(self, ctx):
        parts = [a.xl(ctx) for a in self.args]
        if any(p is None for p in parts):
            return None
        if self.name == "POS":
            return f"IF({parts[0]}>0,{parts[0]},NA())"
        return f"{self.name}({','.join(parts)})"

    def required_cells(self, ctx):
        return [c for a in self.args for c in a.required_cells(ctx)]


def MIN(*a): return Fn("MIN", tuple(lift(x) for x in a))
def MAX(*a): return Fn("MAX", tuple(lift(x) for x in a))
def ABS(a): return Fn("ABS", (lift(a),))
def POS(a): return Fn("POS", (lift(a),))  # blank when the base is zero or negative
def IF(c, a, b): return Fn("IF", (lift(c), lift(a), lift(b)))
def avg(name): return (F(name) + F(name, 1)) / 2
def avgm(name): return (M(name) + M(name, 1)) / 2
def growth(name): return F(name) / F(name, 1) - 1
def opt(name, lag=0): return F(name, lag, optional=True)


@dataclass
class Ratio:
    key: str
    label: str
    group: str
    expr: Expr
    fmt: str = "0.00"   # Excel number format: "0.0%", "0.00x", "#,##0", ...
    note: str = ""
    better: str = ""    # "high" / "low" / "" for screens


R: list[Ratio] = []


def ratio(key, label, group, expr, fmt="0.00", note="", better=""):
    R.append(Ratio(key, label, group, expr, fmt, note, better))


PCT, X, DAYS, NUM, SCORE = "0.0%", '0.00"x"', "0", "#,##0", "0.00"

# ---- derived building blocks ---------------------------------------------------
ratio("ebit", "EBIT (operating income)", "Derived", F("operating_income"), NUM)
ratio("ebitda", "EBITDA", "Derived", M("ebit") + F("da"), NUM)
ratio("fcf", "Free cash flow (CFO - capex)", "Derived", F("cfo") - F("capex"), NUM)
ratio("total_debt_incl_leases", "Debt incl. leases", "Derived",
      F("total_debt") + opt("operating_lease_liab") + opt("finance_lease_liab"), NUM,
      "Check the debt note: finance leases may already be inside total debt")
ratio("net_debt", "Net debt (incl. leases)", "Derived",
      M("total_debt_incl_leases") - F("cash") - opt("st_investments"), NUM)
ratio("invested_capital", "Invested capital (net debt + equity)", "Derived",
      M("net_debt") + F("equity_incl_nci"), NUM)
ratio("tax_rate", "Effective tax rate (clipped 0-35%)", "Derived",
      MIN(MAX(F("income_tax") / F("pretax_income"), 0), 0.35), PCT)
ratio("nopat", "NOPAT", "Derived", M("ebit") * (1 - M("tax_rate")), NUM)
ratio("gross_receivables", "Gross receivables", "Derived", F("receivables") + opt("allowance_doubtful"), NUM)
ratio("tangible_equity", "Tangible equity", "Derived", F("equity") - opt("goodwill") - opt("intangibles"), NUM)
ratio("working_capital", "Working capital", "Derived", F("current_assets") - F("current_liabilities"), NUM)

# ---- growth -------------------------------------------------------------------
ratio("revenue_growth", "Revenue growth", "Growth", growth("revenue"), PCT, better="high")
ratio("ebit_growth", "EBIT growth", "Growth", M("ebit") / M("ebit", 1) - 1, PCT)
ratio("eps_growth", "Diluted EPS growth", "Growth", growth("eps_diluted"), PCT)
ratio("receivables_growth", "Receivables growth", "Growth", growth("receivables"), PCT)
ratio("inventory_growth", "Inventory growth", "Growth", growth("inventory"), PCT)
ratio("deferred_revenue_growth", "Deferred revenue growth", "Growth", growth("deferred_revenue"), PCT)
ratio("share_count_change", "Diluted share count change", "Growth", growth("shares_diluted"), PCT,
      "Negative = net buybacks; positive = dilution (often SBC)")

# ---- profitability -------------------------------------------------------------
ratio("gross_margin", "Gross margin", "Profitability", F("gross_profit") / F("revenue"), PCT, better="high")
ratio("operating_margin", "Operating (EBIT) margin", "Profitability", M("ebit") / F("revenue"), PCT, better="high")
ratio("net_margin", "Net margin", "Profitability", F("net_income") / F("revenue"), PCT)
ratio("sbc_pct_revenue", "SBC % of revenue", "Profitability", F("sbc") / F("revenue"), PCT,
      "A real cost even when excluded from adjusted EPS", better="low")
ratio("rnd_pct_revenue", "R&D % of revenue", "Profitability", F("rnd") / F("revenue"), PCT)

# ---- DuPont (5-step) -------------------------------------------------------------
ratio("tax_burden", "Tax burden (NI / EBT)", "DuPont", F("net_income") / F("pretax_income"), SCORE)
ratio("interest_burden", "Interest burden (EBT / EBIT)", "DuPont", F("pretax_income") / M("ebit"), SCORE)
ratio("dupont_margin", "Operating margin (EBIT / revenue)", "DuPont", M("operating_margin"), PCT)
ratio("asset_turnover", "Asset turnover (revenue / avg assets)", "DuPont", F("revenue") / avg("total_assets"), SCORE)
ratio("equity_multiplier", "Leverage (avg assets / avg equity)", "DuPont", avg("total_assets") / POS(avg("equity")), SCORE,
      "ROE driven by this line is fragile; buybacks shrink equity and inflate it")
ratio("roe_dupont", "ROE (product of the 5 steps)", "DuPont",
      M("tax_burden") * M("interest_burden") * M("dupont_margin") * M("asset_turnover") * M("equity_multiplier"), PCT)

# ---- returns --------------------------------------------------------------------
ratio("roe", "ROE (NI / avg equity)", "Returns", F("net_income") / POS(avg("equity")), PCT,
      "Meaningless when equity is negative or tiny", better="high")
ratio("roa", "ROA (NI / avg assets)", "Returns", F("net_income") / avg("total_assets"), PCT)
ratio("roic", "ROIC (NOPAT / avg invested capital)", "Returns", M("nopat") / POS(avgm("invested_capital")), PCT,
      "Unaffected by financing mix; compare with WACC", better="high")
ratio("rotce", "ROTCE (NI / avg tangible equity)", "Returns", F("net_income") / POS(avgm("tangible_equity")), PCT,
      "Key return metric for banks", better="high")

# ---- earnings quality -------------------------------------------------------------
ratio("cfo_to_ni", "CFO / net income", "Earnings quality", F("cfo") / POS(F("net_income")), X,
      "About 1.0x or higher, consistently", better="high")
ratio("accruals_ratio", "Accruals ratio ((NI - CFO) / avg assets)", "Earnings quality",
      (F("net_income") - F("cfo")) / avg("total_assets"), PCT, "High or rising = warning (Sloan)", better="low")
ratio("fcf_to_ni", "FCF conversion (FCF / NI)", "Earnings quality", M("fcf") / POS(F("net_income")), X, better="high")
ratio("capex_to_da", "Capex / D&A", "Earnings quality", F("capex") / F("da"), X,
      "Far above 1 for years can mean costs are being capitalized")
ratio("allowance_pct_receivables", "Allowance % of gross receivables", "Earnings quality",
      F("allowance_doubtful") / M("gross_receivables"), PCT, "Falling share can flatter earnings")
ratio("receivables_vs_revenue", "Receivables growth minus revenue growth", "Earnings quality",
      M("receivables_growth") - M("revenue_growth"), PCT, "> +10pp: sales pulled forward or weaker collections")
ratio("inventory_vs_revenue", "Inventory growth minus revenue growth", "Earnings quality",
      M("inventory_growth") - M("revenue_growth"), PCT, "> +15pp: demand weakening or write-down coming")
ratio("deferred_rev_vs_revenue", "Deferred revenue growth minus revenue growth", "Earnings quality",
      M("deferred_revenue_growth") - M("revenue_growth"), PCT, "Negative at a subscription business = slowing")

# ---- working capital ----------------------------------------------------------------
ratio("dso", "Days sales outstanding", "Working capital", F("receivables") / F("revenue") * 365, DAYS)
ratio("dio", "Days inventory outstanding", "Working capital", F("inventory") / F("cogs") * 365, DAYS)
ratio("dpo", "Days payables outstanding", "Working capital", F("accounts_payable") / F("cogs") * 365, DAYS)
ratio("ccc", "Cash conversion cycle", "Working capital", M("dso") + M("dio") - M("dpo"), DAYS)

# ---- credit ---------------------------------------------------------------------------
ratio("net_debt_to_ebitda", "Net debt / EBITDA (incl. leases)", "Credit", M("net_debt") / POS(M("ebitda")), X,
      "< 3x comfortable, > 4x high risk (non-financials)", better="low")
ratio("debt_to_capital", "Debt / total capital", "Credit",
      M("total_debt_incl_leases") / (M("total_debt_incl_leases") + F("equity_incl_nci")), PCT, better="low")
ratio("interest_coverage", "EBIT / interest", "Credit", M("ebit") / POS(F("interest_expense")), X,
      "> 4x comfortable, < 2x weak", better="high")
ratio("ebitda_capex_coverage", "(EBITDA - capex) / interest", "Credit", (M("ebitda") - F("capex")) / F("interest_expense"), X)
ratio("cfo_to_debt", "CFO / total debt", "Credit", F("cfo") / M("total_debt_incl_leases"), PCT, "> 25% solid", better="high")
ratio("fcf_to_debt", "FCF / total debt", "Credit", M("fcf") / M("total_debt_incl_leases"), PCT)
ratio("implied_interest_rate", "Implied interest rate (interest / avg debt)", "Credit",
      F("interest_expense") / avg("total_debt"), PCT, "Proxy for pre-tax cost of debt")
ratio("debt_due_24m", "Debt due within 24 months", "Credit", F("maturity_y1") + opt("maturity_y2"), NUM)
ratio("liquidity_vs_24m", "(Cash + STI + undrawn revolver) / debt due 24m", "Credit",
      (F("cash") + opt("st_investments") + opt("revolver_remaining")) / M("debt_due_24m"), X,
      "Should comfortably exceed 1x; revolver often not tagged, check the debt note")
ratio("current_ratio", "Current ratio", "Liquidity", F("current_assets") / F("current_liabilities"), X)
ratio("quick_ratio", "Quick ratio", "Liquidity",
      (F("cash") + opt("st_investments") + opt("receivables")) / F("current_liabilities"), X)

# ---- Beneish M-score (8 variables) -------------------------------------------------------
ratio("b_dsri", "DSRI (receivables / sales index)", "Beneish",
      (F("receivables") / F("revenue")) / (F("receivables", 1) / F("revenue", 1)), SCORE)
ratio("b_gmi", "GMI (gross margin index; 1 if n/a)", "Beneish", M("gross_margin", 1) / M("gross_margin"), SCORE)
ratio("b_aqi", "AQI (asset quality index)", "Beneish",
      (1 - (F("current_assets") + F("ppe_net")) / F("total_assets"))
      / (1 - (F("current_assets", 1) + F("ppe_net", 1)) / F("total_assets", 1)), SCORE)
ratio("b_sgi", "SGI (sales growth index)", "Beneish", F("revenue") / F("revenue", 1), SCORE)
ratio("b_depi", "DEPI (depreciation index; 1 if n/a)", "Beneish",
      (F("da", 1) / (F("da", 1) + F("ppe_net", 1))) / (F("da") / (F("da") + F("ppe_net"))), SCORE)
ratio("b_sgai", "SGAI (SG&A index; 1 if n/a)", "Beneish",
      (F("sga") / F("revenue")) / (F("sga", 1) / F("revenue", 1)), SCORE)
ratio("b_lvgi", "LVGI (leverage index)", "Beneish",
      ((F("current_liabilities") + opt("debt_longterm")) / F("total_assets"))
      / ((F("current_liabilities", 1) + opt("debt_longterm", 1)) / F("total_assets", 1)), SCORE)
ratio("b_tata", "TATA (total accruals / assets)", "Beneish", (F("net_income") - F("cfo")) / F("total_assets"), SCORE)
ratio("beneish_m", "Beneish M-score (> -1.78 = manipulation risk)", "Beneish",
      -4.84 + 0.920 * M("b_dsri") + 0.528 * M("b_gmi", default=1.0) + 0.404 * M("b_aqi") + 0.892 * M("b_sgi")
      + 0.115 * M("b_depi", default=1.0) - 0.172 * M("b_sgai", default=1.0) + 4.679 * M("b_tata")
      - 0.327 * M("b_lvgi"), SCORE, better="low")

# ---- Piotroski F-score ---------------------------------------------------------------------
ratio("roa_begin", "ROA on beginning assets", "Piotroski", F("net_income") / F("total_assets", 1), PCT)
ratio("lt_leverage", "LT debt / avg assets", "Piotroski", opt("debt_longterm") / avg("total_assets"), PCT)
ratio("turnover_begin", "Revenue / beginning assets", "Piotroski", F("revenue") / F("total_assets", 1), SCORE)
ratio("p1_roa", "F1 ROA > 0", "Piotroski", IF(M("roa_begin") > 0, 1, 0), "0")
ratio("p2_cfo", "F2 CFO > 0", "Piotroski", IF(F("cfo") > 0, 1, 0), "0")
ratio("p3_droa", "F3 ROA improved", "Piotroski", IF(M("roa_begin") > M("roa_begin", 1), 1, 0), "0")
ratio("p4_accrual", "F4 CFO > NI", "Piotroski", IF(F("cfo") > F("net_income"), 1, 0), "0")
ratio("p5_leverage", "F5 LT leverage not up", "Piotroski", IF(M("lt_leverage") <= M("lt_leverage", 1), 1, 0), "0")
ratio("p6_liquidity", "F6 Current ratio improved", "Piotroski", IF(M("current_ratio") > M("current_ratio", 1), 1, 0), "0")
ratio("p7_dilution", "F7 No dilution", "Piotroski", IF(F("shares_diluted") <= F("shares_diluted", 1), 1, 0), "0")
ratio("p8_margin", "F8 Gross margin improved", "Piotroski", IF(M("gross_margin") > M("gross_margin", 1), 1, 0), "0")
ratio("p9_turnover", "F9 Asset turnover improved", "Piotroski",
      IF(M("turnover_begin") > M("turnover_begin", 1), 1, 0), "0")
ratio("piotroski_f", "Piotroski F-score (0-9; >= 7 strong, <= 3 weak)", "Piotroski",
      M("p1_roa") + M("p2_cfo") + M("p3_droa") + M("p4_accrual") + M("p5_leverage") + M("p6_liquidity")
      + M("p7_dilution") + M("p8_margin") + M("p9_turnover"), "0", better="high")

# ---- Altman ------------------------------------------------------------------------------------
ratio("altman_z", "Altman Z (manufacturers; > 2.99 safe, < 1.81 distress)", "Altman",
      1.2 * M("working_capital") / F("total_assets") + 1.4 * F("retained_earnings") / F("total_assets")
      + 3.3 * M("ebit") / F("total_assets") + 0.6 * F("market_cap") / F("total_liabilities")
      + 1.0 * F("revenue") / F("total_assets"), SCORE, "Uses current market cap: latest column only", better="high")
ratio("altman_z2", "Altman Z'' (non-manufacturers; > 2.60 safe, < 1.10 distress)", "Altman",
      6.56 * M("working_capital") / F("total_assets") + 3.26 * F("retained_earnings") / F("total_assets")
      + 6.72 * M("ebit") / F("total_assets") + 1.05 * F("equity_incl_nci") / F("total_liabilities"), SCORE,
      better="high")

# ---- valuation history ---------------------------------------------------------------------------
ratio("pe_at_period_end", "P/E at period end (price / diluted EPS)", "Valuation history",
      F("price_at_period_end") / POS(F("eps_diluted")), '0.0"x"')
ratio("fcf_yield_at_period_end", "FCF yield at period end", "Valuation history",
      M("fcf") / (F("price_at_period_end") * F("shares_diluted")), PCT)

RATIOS: dict[str, Ratio] = {r.key: r for r in R}


# ---------------------------------------------------------------------------
# Python evaluation
# ---------------------------------------------------------------------------

class PyCtx:
    def __init__(self, frame: pd.DataFrame, results: dict[str, list[float]], i: int, ttm_cols: set[int]):
        self.frame, self.results, self.i, self.ttm_cols = frame, results, i, ttm_cols

    def has_period(self, lag: int) -> bool:
        return self.i - lag >= 0 and not (lag and self.i in self.ttm_cols)

    def field(self, name, lag):
        if not self.has_period(lag) or name not in self.frame.index:
            return NAN
        v = self.frame.iat[self.frame.index.get_loc(name), self.i - lag]
        return NAN if pd.isna(v) else float(v)

    def metric(self, name, lag):
        if not self.has_period(lag):
            return NAN
        return self.results[name][self.i - lag]


def evaluate(fx: Fundamentals) -> pd.DataFrame:
    """Return DataFrame index = ratio keys, columns = same periods as fx.frame."""
    cols = list(fx.frame.columns)
    ttm = {i for i, c in enumerate(cols) if c == "TTM"}
    results: dict[str, list[float]] = {}
    for r in R:
        vals = []
        results[r.key] = vals
        for i in range(len(cols)):
            v = r.expr.py(PyCtx(fx.frame, results, i, ttm))
            vals.append(NAN if _isnan(v) or (isinstance(v, float) and math.isinf(v)) else v)
    return pd.DataFrame(results, index=cols).T


# ---------------------------------------------------------------------------
# Excel rendering
# ---------------------------------------------------------------------------

class XlCtx:
    def __init__(self, field_rows: dict[str, int], metric_rows: dict[str, int], col_letters: list[str],
                 i: int, ttm_cols: set[int], fin_sheet: str = "Financials"):
        self.field_rows, self.metric_rows, self.cols = field_rows, metric_rows, col_letters
        self.i, self.ttm_cols, self.fin_sheet = i, ttm_cols, fin_sheet

    def has_period(self, lag):
        return self.i - lag >= 0 and not (lag and self.i in self.ttm_cols)

    def field_cell(self, name, lag):
        if not self.has_period(lag) or name not in self.field_rows:
            return None
        return f"{self.fin_sheet}!{self.cols[self.i - lag]}{self.field_rows[name]}"

    def metric_cell(self, name, lag):
        if not self.has_period(lag) or name not in self.metric_rows:
            return None
        return f"{self.cols[self.i - lag]}{self.metric_rows[name]}"


def excel_formula(r: Ratio, ctx: XlCtx) -> str | None:
    body = r.expr.xl(ctx)
    if body is None:
        return None
    req = sorted(set(r.expr.required_cells(ctx)))
    inner = f"IFERROR({body},\"\")"
    if req:
        return f"=IF(COUNT({','.join(req)})<{len(req)},\"\",{inner})"
    return f"={inner}"


def groups() -> list[str]:
    seen: list[str] = []
    for r in R:
        if r.group not in seen:
            seen.append(r.group)
    return seen


def latest_values(table: pd.DataFrame, annual_only: bool = True) -> dict[str, float]:
    cols = [c for c in table.columns if not (annual_only and c == "TTM")]
    if not cols:
        return {}
    return {k: (None if pd.isna(v) else float(v)) for k, v in table[cols[-1]].items()}


def series_stat(table: pd.DataFrame, key: str, fn: Callable = np.nanmean, last_n: int = 3) -> float:
    cols = [c for c in table.columns if c != "TTM"][-last_n:]
    vals = table.loc[key, cols].astype(float).values
    vals = vals[~np.isnan(vals)]
    return float(fn(vals)) if len(vals) else NAN
