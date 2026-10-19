# The four-pillar sector scorecard

Review monthly, not daily. Enter a sector only when **3 of 4** pillars agree.

| Pillar | Question | Yes when | Source |
|---|---|---|---|
| 1 Cycle phase | Does the confirmed phase historically favor this sector? | Sector is in the phase's leader list (user may override with a reason) | `cycle-playbook.md` + the user's call |
| 2 Earnings revisions | Are forward EPS estimates for the sector rising? | Forward 12-month or next-year EPS estimate up over the last 1-3 months; breadth of upward revisions > downward | FactSet Earnings Insight ("changes in estimates by sector"), Yardeni, LSEG |
| 3 Relative strength | Does the market agree? | Rotation status **CONFIRMED** (ETF/SPY above 10w and 40w MAs for 3+ weeks) or **TURNING** (RRG Improving/Leading and above 10w for 3+ weeks) | `iat rotation` (`rs_pillar`) |
| 4 Valuation vs its own history | Is there room left? | Forward P/E at or below its 10-year average, or its relative P/E to the S&P 500 at or below its 10-year average | FactSet Earnings Insight (sector forward P/E vs 5y/10y averages), Yardeni |

## Evidence standard for pillars 2 and 4

Write the number, the period and the source with its date, e.g.:
"Health Care CY2027 EPS estimate +1.1% since Jul 31 (FactSet Earnings Insight, Oct 10 2026)".
If you cannot find a number, mark the pillar `Neutral` with "no current data". Never infer it from price action.

## "Already priced in?" (write one line per sector)

Compare the sector's forward P/E premium or discount to the S&P 500 with its 10-year average. If it already
trades at a historically high premium **and** the rotation is consensus (headlines, fund-flow reports,
strategist overweights), the remaining 6-month upside is smaller. Say so even if 3 pillars agree.

## Verdicts

- **ENTER** (3-4 Yes): eligible for capital. Entry still follows the tranche plan in `timing-risk.md`.
- **WATCH** (2 Yes): keep on the list; usually waiting for relative strength or revisions.
- **AVOID** (0-1 Yes).

## Thesis versus confirmation

Pillars 1, 2 and 4 form the thesis (fundamental, forward-looking). Pillar 3 is the confirmation (price).
Tranche 1 can start when the thesis is in place. Tranche 2 waits for pillar 3. This trims false starts at
the cost of missing the first few percent of the move.
