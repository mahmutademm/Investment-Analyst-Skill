"""Standardized financial statements from SEC XBRL (deep dive) or Yahoo (screen).

Both builders return a `Fundamentals` object:
    frame   DataFrame, index = standard field names, columns = period labels (oldest -> newest,
            optional final "TTM" column)
    source  DataFrame of the same shape with the XBRL concept / Yahoo row used for each value
    meta    dict (period end dates, filing accession numbers, notes about derived values)

Sign conventions: capex, dividends and buybacks are positive numbers (cash spent).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# standard field -> description (order = display order in the workbook)
FIELDS: dict[str, str] = {
    "revenue": "Revenue",
    "cogs": "Cost of revenue",
    "gross_profit": "Gross profit",
    "sga": "SG&A",
    "rnd": "R&D",
    "da": "Depreciation & amortization",
    "operating_income": "Operating income (EBIT)",
    "interest_expense": "Interest expense",
    "pretax_income": "Pre-tax income",
    "income_tax": "Income tax expense",
    "net_income": "Net income (to common)",
    "eps_diluted": "Diluted EPS",
    "shares_diluted": "Diluted weighted shares",
    "cfo": "Cash from operations",
    "capex": "Capital expenditures",
    "sbc": "Stock-based compensation",
    "dividends_paid": "Dividends paid",
    "buybacks": "Share repurchases",
    "interest_paid": "Cash interest paid",
    "total_assets": "Total assets",
    "current_assets": "Current assets",
    "cash": "Cash & equivalents",
    "st_investments": "Short-term investments",
    "receivables": "Accounts receivable, net",
    "allowance_doubtful": "Allowance for doubtful accounts",
    "inventory": "Inventory",
    "ppe_net": "PP&E, net",
    "goodwill": "Goodwill",
    "intangibles": "Intangibles ex goodwill",
    "total_liabilities": "Total liabilities",
    "current_liabilities": "Current liabilities",
    "accounts_payable": "Accounts payable",
    "deferred_revenue": "Deferred revenue (current)",
    "debt_current": "Debt, current",
    "debt_longterm": "Debt, non-current",
    "total_debt": "Total debt (ex operating leases)",
    "operating_lease_liab": "Operating lease liabilities",
    "finance_lease_liab": "Finance lease liabilities (if separate)",
    "equity": "Shareholders' equity (parent)",
    "equity_incl_nci": "Equity incl. non-controlling interest",
    "minority_interest": "Non-controlling interest",
    "retained_earnings": "Retained earnings",
    "maturity_y1": "Debt maturing within 12 months",
    "maturity_y2": "Debt maturing in year 2",
    "maturity_y3": "Debt maturing in year 3",
    "maturity_y4": "Debt maturing in year 4",
    "maturity_y5": "Debt maturing in year 5",
    "maturity_after_y5": "Debt maturing after year 5",
    "revolver_remaining": "Undrawn revolver capacity",
    "price_at_period_end": "Share price at period end",
    "market_cap": "Market cap (latest only)",
}

FLOW_FIELDS = {"revenue", "cogs", "gross_profit", "sga", "rnd", "da", "operating_income", "interest_expense",
               "pretax_income", "income_tax", "net_income", "eps_diluted", "shares_diluted", "cfo", "capex", "sbc",
               "dividends_paid", "buybacks", "interest_paid"}


@dataclass
class Fundamentals:
    ticker: str
    frame: pd.DataFrame
    source: pd.DataFrame
    meta: dict = field(default_factory=dict)

    @property
    def annual_columns(self) -> list[str]:
        return [c for c in self.frame.columns if c != "TTM"]

    def latest(self, name: str) -> float:
        cols = self.annual_columns
        if name not in self.frame.index or not cols:
            return np.nan
        return self.frame.loc[name, cols[-1]]


def _empty(columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = pd.DataFrame(np.nan, index=list(FIELDS), columns=columns, dtype=float)
    s = pd.DataFrame("", index=list(FIELDS), columns=columns, dtype=object)
    return f, s


def _fill_derived(f: pd.DataFrame, s: pd.DataFrame) -> list[str]:
    notes = []

    def fill(target, values, label):
        mask = f.loc[target].isna() & values.notna()
        if mask.any():
            f.loc[target, mask] = values[mask]
            s.loc[target, mask] = label
            notes.append(f"{target}: {label} for {', '.join(map(str, f.columns[mask]))}")

    fill("gross_profit", f.loc["revenue"] - f.loc["cogs"], "derived: revenue - cogs")
    fill("operating_income", f.loc["pretax_income"] + f.loc["interest_expense"].fillna(0),
         "derived: pretax + interest (no operating income tag)")
    fill("equity_incl_nci", f.loc["equity"] + f.loc["minority_interest"].fillna(0), "derived: equity + NCI")
    fill("total_liabilities", f.loc["total_assets"] - f.loc["equity_incl_nci"], "derived: assets - equity")
    fill("total_debt", f.loc["debt_current"].fillna(0) + f.loc["debt_longterm"],
         "derived: current + non-current debt")
    return notes


# ---------------------------------------------------------------------------
# Yahoo (screen)
# ---------------------------------------------------------------------------

YAHOO_MAP: dict[str, list[tuple[str, str]]] = {
    # std: [(statement, row), ...] in priority order
    "revenue": [("income", "Total Revenue"), ("income", "Operating Revenue")],
    "cogs": [("income", "Cost Of Revenue"), ("income", "Reconciled Cost Of Revenue")],
    "gross_profit": [("income", "Gross Profit")],
    "sga": [("income", "Selling General And Administration")],
    "rnd": [("income", "Research And Development")],
    "da": [("cashflow", "Depreciation And Amortization"), ("cashflow", "Depreciation Amortization Depletion"),
           ("income", "Reconciled Depreciation")],
    "operating_income": [("income", "Operating Income"), ("income", "EBIT")],
    "interest_expense": [("income", "Interest Expense"), ("income", "Interest Expense Non Operating")],
    "pretax_income": [("income", "Pretax Income")],
    "income_tax": [("income", "Tax Provision")],
    "net_income": [("income", "Net Income Common Stockholders"), ("income", "Net Income")],
    "eps_diluted": [("income", "Diluted EPS")],
    "shares_diluted": [("income", "Diluted Average Shares")],
    "cfo": [("cashflow", "Operating Cash Flow")],
    "capex": [("cashflow", "Capital Expenditure")],
    "sbc": [("cashflow", "Stock Based Compensation")],
    "dividends_paid": [("cashflow", "Cash Dividends Paid")],
    "buybacks": [("cashflow", "Repurchase Of Capital Stock")],
    "interest_paid": [("cashflow", "Interest Paid Supplemental Data")],
    "total_assets": [("balance", "Total Assets")],
    "current_assets": [("balance", "Current Assets")],
    "cash": [("balance", "Cash And Cash Equivalents")],
    "receivables": [("balance", "Accounts Receivable"), ("balance", "Receivables")],
    "allowance_doubtful": [("balance", "Allowance For Doubtful Accounts Receivable")],
    "inventory": [("balance", "Inventory")],
    "ppe_net": [("balance", "Net PPE")],
    "goodwill": [("balance", "Goodwill")],
    "intangibles": [("balance", "Other Intangible Assets")],
    "total_liabilities": [("balance", "Total Liabilities Net Minority Interest")],
    "current_liabilities": [("balance", "Current Liabilities")],
    "accounts_payable": [("balance", "Accounts Payable")],
    "deferred_revenue": [("balance", "Current Deferred Revenue")],
    "debt_current": [("balance", "Current Debt And Capital Lease Obligation"), ("balance", "Current Debt")],
    "debt_longterm": [("balance", "Long Term Debt And Capital Lease Obligation"), ("balance", "Long Term Debt")],
    "total_debt": [("balance", "Total Debt")],
    "equity": [("balance", "Stockholders Equity"), ("balance", "Common Stock Equity")],
    "equity_incl_nci": [("balance", "Total Equity Gross Minority Interest")],
    "minority_interest": [("balance", "Minority Interest")],
    "retained_earnings": [("balance", "Retained Earnings")],
}
NEGATE_YAHOO = {"capex", "dividends_paid", "buybacks"}
ABS_YAHOO = {"allowance_doubtful", "interest_expense"}


def statement_frame(stmt: dict | None) -> pd.DataFrame:
    """Raw cached statement {row: {date: value}} -> DataFrame rows x ascending dates."""
    if not stmt:
        return pd.DataFrame()
    df = pd.DataFrame(stmt).T  # index = rows, columns = dates
    df.columns = pd.to_datetime(df.columns)
    df = df.reindex(sorted(df.columns), axis=1)
    return df.apply(pd.to_numeric, errors="coerce")


def from_yahoo(ticker: str, raw: dict, prices: pd.Series | None = None, market_cap: float | None = None) -> Fundamentals:
    stmts = {k: statement_frame(raw.get(k)) for k in ("income", "balance", "cashflow")}
    dates = sorted({d for df in stmts.values() for d in df.columns})
    cols = [d.date().isoformat() for d in dates]
    f, s = _empty(cols)
    for std, options in YAHOO_MAP.items():
        for stmt_name, row in options:
            df = stmts[stmt_name]
            if df.empty or row not in df.index:
                continue
            for d in df.columns:
                c = d.date().isoformat()
                v = df.loc[row, d]
                if pd.isna(f.loc[std, c]) and pd.notna(v):
                    v = float(v)
                    if std in NEGATE_YAHOO:
                        v = -v
                    if std in ABS_YAHOO:
                        v = abs(v)
                    f.loc[std, c], s.loc[std, c] = v, f"Yahoo {stmt_name}: {row}"
    bal = stmts["balance"]
    if not bal.empty and "Cash Cash Equivalents And Short Term Investments" in bal.index:
        for d in bal.columns:
            c = d.date().isoformat()
            tot = bal.loc["Cash Cash Equivalents And Short Term Investments", d]
            if pd.notna(tot) and pd.notna(f.loc["cash", c]):
                f.loc["st_investments", c] = max(float(tot) - f.loc["cash", c], 0.0)
                s.loc["st_investments", c] = "Yahoo: cash+STI minus cash"
    notes = _fill_derived(f, s)
    if prices is not None and not prices.empty:
        for c in cols:
            p = prices[prices.index <= pd.Timestamp(c)]
            if len(p):
                f.loc["price_at_period_end", c] = float(p.iloc[-1])
                s.loc["price_at_period_end", c] = "Yahoo price history"
    if market_cap and cols:
        f.loc["market_cap", cols[-1]] = float(market_cap)
        s.loc["market_cap", cols[-1]] = "Yahoo quote (current)"
    # Drop columns that are almost empty (Yahoo's oldest column is often blank)
    keep = [c for c in cols if f[c].notna().sum() >= 8]
    return Fundamentals(ticker, f[keep], s[keep], {"source": "yahoo", "notes": notes,
                                                    "lease_note": "Yahoo usually includes leases in Total Debt"})


# ---------------------------------------------------------------------------
# SEC XBRL companyfacts (deep dive)
# ---------------------------------------------------------------------------

G = "us-gaap"
SEC_MAP: dict[str, list[tuple[str, str]]] = {
    "revenue": [(G, "RevenueFromContractWithCustomerExcludingAssessedTax"), (G, "Revenues"),
                (G, "SalesRevenueNet"), (G, "RevenueFromContractWithCustomerIncludingAssessedTax"),
                (G, "SalesRevenueGoodsNet"), (G, "RevenuesNetOfInterestExpense")],
    "cogs": [(G, "CostOfGoodsAndServicesSold"), (G, "CostOfRevenue"), (G, "CostOfGoodsSold"),
             (G, "CostOfServices"), (G, "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization")],
    "gross_profit": [(G, "GrossProfit")],
    "sga": [(G, "SellingGeneralAndAdministrativeExpense"), (G, "GeneralAndAdministrativeExpense")],
    "rnd": [(G, "ResearchAndDevelopmentExpense"), (G, "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost")],
    "da": [(G, "DepreciationDepletionAndAmortization"), (G, "DepreciationAmortizationAndAccretionNet"),
           (G, "DepreciationAndAmortization"), (G, "Depreciation")],
    "operating_income": [(G, "OperatingIncomeLoss")],
    "interest_expense": [(G, "InterestExpense"), (G, "InterestExpenseNonoperating"), (G, "InterestExpenseDebt"),
                         (G, "InterestAndDebtExpense"), (G, "InterestExpenseNet")],
    "pretax_income": [(G, "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"),
                      (G, "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"),
                      (G, "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic")],
    "income_tax": [(G, "IncomeTaxExpenseBenefit")],
    "net_income": [(G, "NetIncomeLossAvailableToCommonStockholdersBasic"), (G, "NetIncomeLoss"), (G, "ProfitLoss")],
    "eps_diluted": [(G, "EarningsPerShareDiluted"), (G, "EarningsPerShareBasicAndDiluted")],
    "shares_diluted": [(G, "WeightedAverageNumberOfDilutedSharesOutstanding")],
    "cfo": [(G, "NetCashProvidedByUsedInOperatingActivities"),
            (G, "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")],
    "capex": [(G, "PaymentsToAcquirePropertyPlantAndEquipment"), (G, "PaymentsToAcquireProductiveAssets"),
              (G, "PaymentsForCapitalImprovements")],
    "sbc": [(G, "ShareBasedCompensation"), (G, "AllocatedShareBasedCompensationExpense")],
    "dividends_paid": [(G, "PaymentsOfDividendsCommonStock"), (G, "PaymentsOfDividends")],
    "buybacks": [(G, "PaymentsForRepurchaseOfCommonStock")],
    "interest_paid": [(G, "InterestPaidNet"), (G, "InterestPaid")],
    "total_assets": [(G, "Assets")],
    "current_assets": [(G, "AssetsCurrent")],
    "cash": [(G, "CashAndCashEquivalentsAtCarryingValue"), (G, "Cash"),
             (G, "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")],
    "st_investments": [(G, "ShortTermInvestments"), (G, "MarketableSecuritiesCurrent"),
                       (G, "AvailableForSaleSecuritiesDebtSecuritiesCurrent")],
    "receivables": [(G, "AccountsReceivableNetCurrent"), (G, "ReceivablesNetCurrent"),
                    (G, "AccountsNotesAndLoansReceivableNetCurrent")],
    "allowance_doubtful": [(G, "AllowanceForDoubtfulAccountsReceivableCurrent"),
                           (G, "AccountsReceivableAllowanceForCreditLossCurrent")],
    "inventory": [(G, "InventoryNet")],
    "ppe_net": [(G, "PropertyPlantAndEquipmentNet"),
                (G, "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization")],
    "goodwill": [(G, "Goodwill")],
    "intangibles": [(G, "IntangibleAssetsNetExcludingGoodwill"), (G, "FiniteLivedIntangibleAssetsNet")],
    "total_liabilities": [(G, "Liabilities")],
    "current_liabilities": [(G, "LiabilitiesCurrent")],
    "accounts_payable": [(G, "AccountsPayableCurrent"), (G, "AccountsPayableAndAccruedLiabilitiesCurrent")],
    "deferred_revenue": [(G, "ContractWithCustomerLiabilityCurrent"), (G, "DeferredRevenueCurrent")],
    "debt_current": [(G, "DebtCurrent"), (G, "LongTermDebtCurrent"), (G, "LongTermDebtAndCapitalLeaseObligationsCurrent")],
    "debt_longterm": [(G, "LongTermDebtNoncurrent"), (G, "LongTermDebtAndCapitalLeaseObligations")],
    "operating_lease_liab": [(G, "OperatingLeaseLiability")],
    "finance_lease_liab": [(G, "FinanceLeaseLiability")],
    "equity": [(G, "StockholdersEquity")],
    "equity_incl_nci": [(G, "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")],
    "minority_interest": [(G, "MinorityInterest")],
    "retained_earnings": [(G, "RetainedEarningsAccumulatedDeficit")],
    "maturity_y1": [(G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"),
                    (G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextRollingTwelveMonths")],
    "maturity_y2": [(G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"),
                    (G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInRollingYearTwo")],
    "maturity_y3": [(G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"),
                    (G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInRollingYearThree")],
    "maturity_y4": [(G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour"),
                    (G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInRollingYearFour")],
    "maturity_y5": [(G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive"),
                    (G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInRollingYearFive")],
    "maturity_after_y5": [(G, "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive"),
                          (G, "LongTermDebtMaturitiesRepaymentsOfPrincipalInRollingAfterYearFive")],
    "revolver_remaining": [(G, "LineOfCreditFacilityRemainingBorrowingCapacity")],
}
# Total debt is assembled from components (see _sec_total_debt)
DEBT_PARTS = {
    "combined": [(G, "DebtLongtermAndShorttermCombinedAmount")],
    "ltd_total": [(G, "LongTermDebt"), (G, "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities")],
    "stb": [(G, "ShortTermBorrowings")],
    "cp": [(G, "CommercialPaper")],
}
ANNUAL_FORMS = {"10-K", "10-K/A", "10-KT", "20-F", "40-F"}


def _rows(facts: dict, tax: str, concept: str) -> list[dict]:
    node = facts.get("facts", {}).get(tax, {}).get(concept)
    if not node:
        return []
    out = []
    for unit, rows in node.get("units", {}).items():
        for r in rows:
            out.append({**r, "unit": unit, "concept": concept})
    return out


def _days(r: dict) -> int | None:
    if not r.get("start"):
        return None
    return (dt.date.fromisoformat(r["end"]) - dt.date.fromisoformat(r["start"])).days


def _annual_flow(rows: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for r in rows:
        d = _days(r)
        if r.get("form") not in ANNUAL_FORMS or d is None or not (340 <= d <= 380):
            continue
        cur = best.get(r["end"])
        if cur is None or r.get("filed", "") > cur.get("filed", ""):
            best[r["end"]] = r
    return best


def _instant(rows: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for r in rows:
        if r.get("start"):
            continue
        cur = best.get(r["end"])
        if cur is None or r.get("filed", "") > cur.get("filed", ""):
            best[r["end"]] = r
    return best


def _near(target: str, candidates: dict[str, dict], tol_days: int = 7) -> dict | None:
    if target in candidates:
        return candidates[target]
    t = dt.date.fromisoformat(target)
    for k, v in candidates.items():
        if abs((dt.date.fromisoformat(k) - t).days) <= tol_days:
            return v
    return None


def _ytd(rows: list[dict], end: str, min_days: int, max_days: int) -> dict | None:
    best = None
    for r in rows:
        d = _days(r)
        if d is None or r["end"] != end or not (min_days <= d <= max_days):
            continue
        if best is None or d > _days(best) or (d == _days(best) and r.get("filed", "") > best.get("filed", "")):
            best = r
    return best


def from_sec(ticker: str, facts: dict, years: int = 6, prices: pd.Series | None = None,
             market_cap: float | None = None) -> Fundamentals:
    """Build annual (+TTM) standardized statements from SEC companyfacts JSON."""
    anchors: dict[str, dict] = {}
    for tax, concept in SEC_MAP["net_income"] + SEC_MAP["revenue"] + SEC_MAP["cfo"]:
        for end, r in _annual_flow(_rows(facts, tax, concept)).items():
            anchors.setdefault(end, r)
    ends = sorted(anchors)
    # collapse ends that are within a week of each other (52/53-week fiscal years)
    merged: list[str] = []
    for e in ends:
        if merged and (dt.date.fromisoformat(e) - dt.date.fromisoformat(merged[-1])).days < 300:
            merged[-1] = max(merged[-1], e)
        else:
            merged.append(e)
    ends = merged[-years:]
    if not ends:
        raise ValueError(f"{ticker}: no annual XBRL data found (foreign filer or non-standard tags?)")

    # TTM support: latest quarter end after the last fiscal year end
    last_fy = ends[-1]
    q_end = None
    for tax, concept in SEC_MAP["net_income"] + SEC_MAP["revenue"]:
        for r in _rows(facts, tax, concept):
            if r.get("form", "").startswith("10-Q") and r["end"] > last_fy and _days(r) and _days(r) >= 80:
                q_end = max(q_end or r["end"], r["end"])
    cols = ends + (["TTM"] if q_end else [])
    f, s = _empty(cols)
    meta: dict = {"source": "sec", "period_ends": {c: c for c in ends}, "notes": [], "concepts_tried": {}}
    if q_end:
        meta["period_ends"]["TTM"] = q_end

    for std, options in SEC_MAP.items():
        flow = std in FLOW_FIELDS
        for tax, concept in options:
            rows = _rows(facts, tax, concept)
            if not rows:
                continue
            series = _annual_flow(rows) if flow else _instant(rows)
            for e in ends:
                if pd.notna(f.loc[std, e]):
                    continue
                r = _near(e, series)
                if r is not None:
                    f.loc[std, e] = float(r["val"])
                    s.loc[std, e] = f"{concept} ({r.get('form')} filed {r.get('filed')}, accn {r.get('accn')})"
            if q_end and pd.isna(f.loc[std, "TTM"]):
                if flow:
                    fy_r = _near(last_fy, series)
                    cur = _ytd(rows, q_end, 80, 300)
                    if fy_r is not None and cur is not None:
                        prior_end = (dt.date.fromisoformat(q_end) - dt.timedelta(days=364)).isoformat()
                        prior = None
                        for cand in rows:
                            dd = _days(cand)
                            if dd and abs(dd - _days(cur)) <= 10 and abs(
                                    (dt.date.fromisoformat(cand["end"]) - dt.date.fromisoformat(prior_end)).days) <= 10:
                                if prior is None or cand.get("filed", "") > prior.get("filed", ""):
                                    prior = cand
                        if std == "shares_diluted":
                            f.loc[std, "TTM"] = float(cur["val"])
                            s.loc[std, "TTM"] = f"{concept} YTD to {q_end}"
                        elif prior is not None:
                            f.loc[std, "TTM"] = float(fy_r["val"]) + float(cur["val"]) - float(prior["val"])
                            s.loc[std, "TTM"] = f"{concept}: FY {last_fy} + YTD {q_end} - prior YTD"
                else:
                    r = _near(q_end, _instant(rows), tol_days=3)
                    if r is not None:
                        f.loc[std, "TTM"] = float(r["val"])
                        s.loc[std, "TTM"] = f"{concept} at {q_end} ({r.get('form')})"

    # Total debt from components
    parts = {}
    for name, options in DEBT_PARTS.items():
        vals = {}
        for tax, concept in options:
            inst = _instant(_rows(facts, tax, concept))
            for c in cols:
                end = meta["period_ends"][c]
                if c not in vals:
                    r = _near(end, inst, tol_days=3)
                    if r is not None:
                        vals[c] = (float(r["val"]), concept)
        parts[name] = vals
    for c in cols:
        if c in parts["combined"]:
            v, src = parts["combined"][c][0], parts["combined"][c][1]
        elif c in parts["ltd_total"]:
            v = parts["ltd_total"][c][0] + parts["stb"].get(c, (0.0,))[0] + parts["cp"].get(c, (0.0,))[0]
            src = "LongTermDebt (incl. current) + ShortTermBorrowings + CommercialPaper"
        else:
            continue
        f.loc["total_debt", c], s.loc["total_debt", c] = v, src
    if f.loc["debt_current"].isna().all():
        for c in cols:
            if c in parts["stb"]:
                f.loc["debt_current", c], s.loc["debt_current", c] = parts["stb"][c][0], "ShortTermBorrowings"

    meta["notes"] += _fill_derived(f, s)
    if prices is not None and not prices.empty:
        for c in cols:
            end = meta["period_ends"][c]
            p = prices[prices.index <= pd.Timestamp(end)]
            if len(p):
                f.loc["price_at_period_end", c] = float(p.iloc[-1])
                s.loc["price_at_period_end", c] = f"Yahoo close on/before {end}"
    if market_cap:
        f.loc["market_cap", cols[-1]] = float(market_cap)
        s.loc["market_cap", cols[-1]] = "Yahoo quote (current)"
    dei = facts.get("facts", {}).get("dei", {})
    so = dei.get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    if so:
        last = max(so, key=lambda r: (r["end"], r.get("filed", "")))
        meta["shares_outstanding"] = {"value": float(last["val"]), "as_of": last["end"], "source": "dei cover page"}
    meta["entity_name"] = facts.get("entityName")
    return Fundamentals(ticker, f, s, meta)


def checks(fx: Fundamentals) -> list[dict]:
    """Integrity checks shown on the workbook's Checks sheet."""
    out = []
    f = fx.frame
    for c in f.columns:
        ta, tl, eq = f.loc["total_assets", c], f.loc["total_liabilities", c], f.loc["equity_incl_nci", c]
        if pd.notna(ta) and pd.notna(tl) and pd.notna(eq) and ta:
            diff = (ta - tl - eq) / ta
            out.append({"period": c, "check": "Assets = Liabilities + Equity", "difference_pct": diff * 100,
                        "status": "OK" if abs(diff) < 0.02 else "CHECK (mezzanine equity or tagging gap?)"})
        rev, cogs, gp = f.loc["revenue", c], f.loc["cogs", c], f.loc["gross_profit", c]
        if pd.notna(rev) and pd.notna(cogs) and pd.notna(gp) and rev:
            diff = (rev - cogs - gp) / rev
            out.append({"period": c, "check": "Revenue - COGS = Gross profit", "difference_pct": diff * 100,
                        "status": "OK" if abs(diff) < 0.01 else "CHECK"})
    critical = ["revenue", "net_income", "cfo", "total_assets", "equity", "operating_income"]
    for name in critical:
        if name in f.index and f.loc[name, fx.annual_columns].isna().all():
            out.append({"period": "all", "check": f"Missing critical field: {name}", "difference_pct": None,
                        "status": "MISSING - read it from the 10-K and enter manually"})
    return out
