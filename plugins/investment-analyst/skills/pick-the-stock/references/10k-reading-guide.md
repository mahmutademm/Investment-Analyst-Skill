# Reading the 10-K, 10-Q, proxy and earnings releases

Files produced by `iat company <T>`, listed in `filings/<T>/manifest.json`:
- `filings/<T>/text/10-K_<period>.txt` (full text), `filings/<T>/text/sections/item_*.txt` (split
  heuristically; if a section looks wrong or empty, Grep the full text instead), `auditor_report.txt`
- the prior-year 10-K (to spot policy changes), the latest 10-Q, the latest DEF 14A (proxy), and the last
  two earnings releases (8-K EX-99.1)

Search, don't scroll: `Grep` for "critical audit matter", "material weakness", "going concern",
"segment", "remaining performance obligation", "covenant", "floating", "variable rate", "revolving credit",
"contingenc", "litigation", "restructuring", "related party", "change in accounting", "allowance for".

## What to extract, section by section

| Section | Extract | Red flags |
|---|---|---|
| Item 1 Business | Products, customers, segments, competition, regulation, seasonality | Customer concentration > 10%, single-supplier dependence |
| Item 1A Risk factors | New or reworded risks vs the prior 10-K | New going-concern, liquidity or regulatory risk language |
| Item 3 Legal proceedings + Contingencies note | Cases, amounts accrued vs possible losses | Large "reasonably possible" losses not accrued |
| Item 7 MD&A | Drivers of revenue/margin; liquidity and capital resources; **critical accounting estimates** (where management uses the most judgment) | Estimates that changed and boosted earnings; liquidity reliance on revolver |
| Item 7A Market risk | Rate, FX and commodity sensitivity; share of floating-rate debt | Large unhedged floating debt in a rising-rate world |
| Item 8 Notes | Segments (profit by segment), revenue recognition, debt (maturities, rates, covenants), leases, income taxes, stock compensation, goodwill impairment testing | Policy changes; segment that makes all the profit shrinking; covenant headroom thin |
| Auditor's report | Opinion type; **critical audit matters** (hardest areas to verify); going-concern paragraph | Going concern; CAMs on revenue recognition, reserves, impairments |
| Item 9A Controls | Management's assessment of internal control over financial reporting | **Material weakness**; remediation still open |
| Proxy (DEF 14A) | Pay metrics (adjusted EPS? ROIC? TSR?), related-party transactions, auditor fees and tenure | Pay tied to adjusted metrics management defines; big related-party dealings |
| Earnings releases | GAAP to non-GAAP reconciliation; guidance | "One-time" charges every quarter; widening GAAP/adjusted gap |
| 8-K items | 4.01 auditor change, 4.02 non-reliance, 2.06 impairment, 5.02 departures | Any 4.01/4.02 |

## Through an auditor's lens

You read the auditor's report every time: opinion, CAMs, going concern, plus Item 9A and any 8-K 4.01.
Also note auditor tenure and changes (proxy), and whether audit fees jumped (a sign of trouble).

## Citing

Use "10-K FY2025, Note 9 Debt" or "10-Q Q2 2026, MD&A Liquidity" plus a 1-2 line quote. Put the URL from
`manifest.json` in `notes.json -> sources`.

## Cross-check numbers against XBRL

The `Financials` sheet comes from XBRL tags, and the concept used for each cell is on `XBRL Sources`.
When the filing's face statements differ (wrong tag chosen, a missing total, a restatement), tell the user
the exact cell and the value in the filing, and let them type over it. Do not edit silently.
