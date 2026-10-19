# Cycle playbook

## The four phases (what each usually looks like)

| Phase | Growth | Inflation | Fed | Curve | Credit | Labor | Typical leaders | Typical laggards |
|---|---|---|---|---|---|---|---|---|
| Early recovery | Below trend but improving | Falling or low | Cutting / just cut | Steepening out of inversion | Spreads wide but tightening | Unemployment high, claims falling | Financials, Consumer Discretionary, Industrials, Real Estate, Materials | Utilities, Staples, Health Care |
| Mid cycle | At or above trend, steady | Near target, stable | On hold / neutral | Positive, stable | Tight, stable | Near lows | Technology, Communication Services, Industrials | Utilities |
| Late cycle | Positive but slowing | Elevated or re-accelerating | Hiking or restrictive | Flat / inverted | Tight, starting to widen | Lows, starting to rise | Energy, Materials, Health Care, Staples | Discretionary, Tech, Real Estate |
| Contraction | Falling | Falling | Cutting fast | Bull steepening | Wide, widening | Rising (Sahm >= 0.5) | Staples, Utilities, Health Care | Industrials, Tech, Materials, Discretionary, Financials |

Treat this as a **starting map**. The pattern breaks often. Examples: a tech-led capex boom can keep
technology leading late into a cycle, and an energy supply shock can lift energy without a classic
late cycle.

## Indicators the toolkit computes (FRED, no key)

Inflation: CPI and core CPI (YoY and 3-month annualized), core PCE (YoY, 3-month annualized), 10Y
breakeven. Policy: effective fed funds, target upper bound, real fed funds (FF minus core PCE), 2Y minus fed funds
(market-implied path proxy). Rates: 3M/2Y/10Y, 10Y TIPS, 10Y trend vs 50/200-day MA. Curve: 10Y-2Y,
10Y-3M (and its 24-month low, to detect "steepening out of inversion"). Credit: HY OAS (level, 3-month
change), Chicago Fed NFCI. Labor: unemployment vs 12-month low, Sahm rule, claims (4-week average vs 26
weeks ago), payrolls 3-month average. Activity: CFNAI 3-month average, industrial production, building
permits, UMich sentiment. Markets: broad dollar, WTI.

## Added beyond the original CPI / fed funds / 10Y approach (and why)

| Addition | Why it matters for a 6-month call |
|---|---|
| **Core PCE**, not only CPI | It is the Fed's target measure; Fed reaction follows it |
| **3-month annualized** inflation | Shows re-acceleration months before YoY turns |
| **Market-implied Fed path** (CME FedWatch; 2Y minus FF proxy) | Stocks price the *expected* path; surprises vs that path move sectors |
| **Yield curve** (10Y-3M, 10Y-2Y) | The most reliable free recession signal; steepening from inversion often marks the late-to-contraction turn |
| **Real yields** (10Y TIPS) | Drive long-duration growth valuations more than nominal yields |
| **Credit spreads** (HY OAS) and NFCI | Real-time stress gauge; usually widen before equities break |
| **Labor turn** (Sahm rule, claims) | Unemployment rising off its low is the classic late-cycle tell |
| **Leading activity** (CFNAI, ISM new orders, permits) | Leads GDP, which lags |
| **Sector earnings revisions** (FactSet) | Pillar 2; revisions lead prices |
| **Sector valuation vs own history** (FactSet / Yardeni) | Pillar 4; checks what is already priced in |
| **Dollar and oil** | Multinationals, materials and energy sensitivity |
| **Event calendar** (FOMC, CPI, earnings season) | Binary dates inside the 6-month window |
| **Correlation between chosen sectors** | Avoids "diversified" picks that are one bet |
| **Rate sensitivity of growth stocks** | Growth is long-duration: rising real yields compress multiples |

## How the rule vote works

`iat macro` evaluates simple, auditable rules (for example "Curve flat or inverted: 10Y-3M < 0.25pp ->
Late cycle +2"). Each fired rule adds its weight to a phase. The output shows every rule, whether it fired
and the evidence. `ambiguous: true` means the top two phases are within 1 point or the leader has under
40% of the votes. In that case lean on the research and say so. The thresholds live in `iat/macro.py`
and can be changed openly.

## Growth-stock note

Valuations of long-duration growth stocks are most sensitive to **real** yields. If real 10Y yields are
rising, growth exposure needs either stronger revisions (pillar 2) or cheaper starting valuations
(pillar 4) to justify the same weight. The deep dive reports each stock's measured sensitivity
(weekly return per +100bp in the 10Y).
