# Credit analysis

Equity investors often skip this, and it is where blowups come from, especially when rates are elevated
and debt must be refinanced.

| Area | Calculation (Ratios sheet key) | Rough comfort zone (non-financials) |
|---|---|---|
| Leverage | Net debt incl. leases / EBITDA (`net_debt_to_ebitda`) | < ~3x; > 4x high risk (midstream/utilities run higher) |
| Leverage | Debt / total capital (`debt_to_capital`) | Compare to peers; a rising trend is a warning |
| Coverage | EBIT / interest (`interest_coverage`) | > ~4x; < 2x weak |
| Coverage | (EBITDA - capex) / interest (`ebitda_capex_coverage`) | Coverage after required reinvestment |
| Cash vs debt | CFO / total debt (`cfo_to_debt`), FCF / debt (`fcf_to_debt`) | > ~25% solid |
| Liquidity | Current ratio, quick ratio | Compare to sub-industry norms |
| Liquidity | (Cash + STI + undrawn revolver) / debt due in 24 months (`liquidity_vs_24m`) | Should comfortably cover near-term maturities |
| Refinancing | Maturity schedule (`maturity_y1`..`y5`), fixed vs floating mix (debt note, Item 7A) | Large maturities soon or heavy floating-rate debt = rate risk |
| Distress | Altman Z (manufacturers) / Z'' (others) | Z > 2.99 safe, < 1.81 distress (original model) |
| External view | S&P and Moody's ratings and outlook (company IR, press releases, news) | Negative outlook or recent downgrade = red flag |
| Cost of debt | Interest / avg debt (`implied_interest_rate`) vs today's rates | A big gap means refinancing will raise interest cost |

**Leases**: net debt includes operating leases (ASC 842). Check the debt note to see whether finance
leases are already inside total debt, to avoid double counting. Revolver capacity is often not tagged in
XBRL, so read it in the liquidity section and put it in the gate evidence.

## Financials and special sectors

| Sector | Use instead |
|---|---|
| Banks | CET1 ratio vs requirement and buffer, nonperforming loans and charge-offs, net interest margin, loan-to-deposit ratio, deposit mix (uninsured share), securities losses (AOCI) |
| Insurers | Combined ratio (< 100% = underwriting profit), reserve development, investment portfolio quality, RBC/solvency ratios |
| Managed care | Medical loss ratio trend, days claims payable, statutory capital, risk-adjustment / rate notices |
| REITs | Net debt / EBITDAre, fixed-charge coverage, unencumbered assets, maturities |

## The ratios that matter most (if you only track a handful)

ROIC vs WACC (does it create value?), CFO / net income (are earnings real?), revenue growth together with
the margin trend, net debt/EBITDA and interest coverage (does it survive a bad year?), DSO and DIO trends
(early warnings), and the share-count trend (are buybacks real?).
