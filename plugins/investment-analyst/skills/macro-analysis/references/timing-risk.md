# Timing risk in sector rotation

Timing risk means the thesis about which sector will lead is right, but the entry or exit still loses money.
Over a 6-month horizon it comes from three places, and each needs a different fix.

| Source | What happens | Fix built into the workflow |
|---|---|---|
| **Early or late** | Waiting for GDP/earnings to prove the turn means it is priced; acting on one early signal means sitting in a laggard for months | Split *thesis* (cycle + revisions + valuation) from *entry* (relative strength). Scale in over time |
| **Misreading the regime** | A 3-6 week outperformance on a rate scare or short squeeze reverses | RS must persist 3+ weeks (`confirm_weeks`); EARLY status counts as No; monthly review cadence |
| **Stock noise swamps the sector call** | Right sector, wrong stock: an earnings miss, lawsuit or policy change moves the stock more than the sector | Screen within sub-industries; earnings-quality gate; catalysts and binary dates checked; diversify names per sector |

## Entry: scale in

| Tranche | Trigger | Size |
|---|---|---|
| 1 | Thesis in place: scorecard >= 3 of 4 *or* thesis pillars strong with RS EARLY; stock passed the deep dive | 1/3 |
| 2 | Relative strength confirms (sector ETF/SPY CONFIRMED or TURNING). The daily report flags it | 1/3 |
| 3 | Pullback toward entry minus ~1x ATR, with the thesis intact | 1/3 |

## Exit rules: write both before buying

- **Thesis stop** (fundamental): e.g. sector or company forward EPS revisions turn negative for two
  consecutive monthly reviews; the yield curve or Fed path moves against the cycle call; the dated catalyst
  passes without closing the gap.
- **Price stop** (volatility): about 2-3x ATR(14) below entry, never a round number. Size the position so a
  stop-out costs a fixed 1-2% of the portfolio:
  `shares = (portfolio x risk%) / (entry - stop)`, capped at `max_position_pct`.

## What is already priced in

Before entering, compare the sector's forward P/E premium to the S&P 500 with its 10-year average. A high
premium plus a crowded narrative means a smaller remaining 6-month upside, so either size down or wait.
