# Risks in the analysis itself, and how this workflow handles them

| Risk | What goes wrong | Mitigation built in | What you still do |
|---|---|---|---|
| Stale data | A 10-K describes a year that ended months ago | TTM column from the latest 10-Q (FY + YTD - prior YTD); latest 10-Q in the filing pack | Read the latest 10-Q MD&A and the last earnings release |
| Vendor inconsistency | Sites define EPS, EBITDA and debt differently | Target figures from SEC XBRL with concept tags; SEC vs Yahoo gap check; one ratio definition for every company | Note when peers (Yahoo data) are not like-for-like |
| Comparability | Different fiscal year-ends, LIFO vs FIFO, IFRS vs US GAAP | Period-end dates shown; foreign/non-USD flags | Adjust or caveat (e.g. LIFO reserve in the inventory note) |
| Confirmation bias | Seeing only good news once you like a stock | Bear case written first; pre-mortem; thesis stops before buying | Give the bear evidence as much space as the bull evidence |
| Spreadsheet errors | Broken links, hardcoded numbers, an unbalanced balance sheet | Inputs separated (blue); every ratio a live formula; balance-sheet and gross-profit checks; Excel vs Python cross-check | Look at the Checks sheet before trusting outputs |
| Horizon mismatch | 30% undervalued, stays that way for 2 years | Catalyst requirement; gap-closure input; reverse DCF | Name the dated catalyst or lower expectations |
| Model overconfidence | Terminal value dominates; small input changes swing value | TV-share warning; WACC x g grid; scenarios | Prefer ranges and probabilities over a point target |
| Regime / timing | Right stock, wrong moment (sector false start) | Tranche plan tied to sector relative strength; daily alerts | Follow the plan; don't average down outside it |
