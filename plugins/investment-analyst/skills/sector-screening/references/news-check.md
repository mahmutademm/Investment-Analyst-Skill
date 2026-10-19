# The "why is it cheap?" news check

News has one job here: decide whether the stock is cheap for a **temporary** or a **structural** reason,
and whether a **catalyst inside the horizon** could close the gap.

## 10-minute protocol per name

1. `python -m iat filings <T>`: periodic filings, the last two earnings releases (8-K item 2.02 /
   EX-99.1) and all 8-Ks in the last 9 months with their items.
2. Read both earnings releases: revenue/EPS vs guidance, guidance changes, segment trends, non-GAAP
   adjustments (are "one-time" items recurring?).
3. Scan the 8-K items: 1.01 material agreement, 2.01 deal closed, 2.03 new debt, 2.05 restructuring,
   2.06 impairment, **4.01 auditor change**, **4.02 non-reliance (restatement)**, 5.02 executive departures,
   8.01 other events.
4. Search news for the last 3-6 months (Reuters, Bloomberg, WSJ, FT, Barron's, CNBC, company IR).
   Note dates.
5. Classify and cite.

## Temporary vs structural

| Temporary (can fix itself) | Structural (business getting worse) |
|---|---|
| One-off earnings miss with an identified cause | Losing market share for several quarters |
| Sector-wide sell-off (rates, rotation) without company news | Technology or business-model disruption |
| Resolvable legal or regulatory overhang with a timeline | Pricing power gone; margins compressing for years |
| Product recall or plant outage with a remediation plan | Balance sheet it cannot refinance at today's rates |
| Index deletion / forced selling | Customer concentration loss, contract non-renewal |
| Guidance cut tied to a temporary input cost | Repeated guidance cuts, management turnover, restatements |

Use **Unclear** when the evidence is mixed, and say what would resolve it.

## Catalysts that can close the gap within ~6 months

Earnings results and guidance updates (dates from the screen's `next_earnings`), investor days, product
approvals (FDA PDUFA dates), spin-offs, buyback authorizations, asset sales, litigation rulings, rate
changes that help the sub-industry, index inclusion. Write a date or a window. If none, write "none
identified": a cheap stock without a catalyst can stay cheap past the horizon.

## Red flags to surface immediately

Auditor change or resignation, restatement / non-reliance, going-concern language, delayed filings
(NT 10-K / NT 10-Q), material weakness, SEC investigation, sudden CFO departure, covenant waivers.
