---
name: portfolio-review
description: Ongoing tracking for the investment-analyst workflow. Reads the daily/weekly reports from GitHub Actions (or runs them), checks every watchlist name against its price stop, thesis stop, sector relative strength, catalyst and earnings dates, flags scale-in tranche triggers, runs the monthly scorecard re-check, and records decisions in the journal. Use for /investment-analyst:portfolio-review, "check my positions", "did anything trigger", "weekly review", "monthly review", "update my watchlist".
argument-hint: "[daily | weekly | monthly]"
---

# Portfolio review

Keep the process honest after the buy: the exits written before buying are only useful if someone checks
them. You surface triggers and evidence; the user decides any trade.

Read first: `../setup/references/operating-rules.md`.

## Workflow

### 0. Get the latest data
1. `python -m iat status`. If the workspace has a git remote: `git -C <workspace> pull --ff-only`.
2. Read `data/reports/daily_latest.md` (and `weekly_latest.md` on weekends). If the daily report is older
   than one trading day and Actions are not set up, run `python -m iat daily` (about 1 minute).
3. `python -m iat watch check` for fresh stop, relative-strength and date alerts.

### 1. Triage alerts (most urgent first)
| Alert | What it means | What you prepare for the user |
|---|---|---|
| PRICE STOP HIT | Price at or below the written stop | The stop rule as written, the current price, and a reminder that the rule was set in advance. The user acts |
| within 1 ATR of stop | Close to the stop | The latest news/8-Ks (`python -m iat filings <T>`): is anything thesis-relevant? |
| sector RS no longer confirms | Sector ETF/SPY fell out of CONFIRMED/TURNING | Is it noise (one week) or a trend (FADING for 3+ weeks)? Tranche 2/3 should wait |
| tranche 2 trigger | Sector relative strength is now CONFIRMED | The planned tranche size from the deep-dive Decision sheet; re-check that the thesis still holds |
| catalyst in Nd / earnings | A dated event is near | What the market expects (consensus, whisper if sourced) and what would confirm or break the thesis |
| catalyst date passed | The event happened | Did it close the gap? If not, is the thesis still valid inside the horizon? |

### 2. Thesis-stop check (weekly)
For each active name, check the thesis stop written in the watchlist (`thesis_stop`). Typical evidence:
FY+1 EPS revisions (re-screen the sub-industry, or `python -m iat company <T> --no-filings --no-excel` for
fresh estimates), guidance changes in the latest earnings release, sector revisions for macro stops. Report
"intact", "weakening (why)" or "triggered (why)", with sources.

### 3. Monthly review
- Re-run the macro scorecard in review mode (`/investment-analyst:macro-analysis review`): did any pillar
  flip for the sectors you hold?
- Re-screen the active sub-industries if the weekly Action is not running.
- Compare the 6-month expected return written at entry (journal) with progress so far.

### 4. Record what the user decides
Only after the user says what they did or will do:
```
python -m iat journal <T> --action "<BUY tranche 2 | TRIM | SELL | HOLD>" --price <p> --shares <n> --reason "<user's words>"
python -m iat watch update <T> --status <tranche2|full|closed> --price-stop <new stop if changed> --notes "<short>"
```
If the workspace syncs with GitHub, ask before committing and pushing `data/tracking/`.

### 5. Summarize
A short table per name (status, price vs entry, distance to stop in ATRs, sector RS, next date, thesis
status) and a list of decisions the user needs to make. Nothing else.

## Useful queries
`python -m iat sql "SELECT * FROM latest_watch_check"` and
`python -m iat sql "SELECT week, ticker, quadrant FROM history_rotation WHERE ticker='XLV' ORDER BY week DESC LIMIT 12"`
(run `python -m iat sync` first if the database looks stale).

## Guardrails
- Never place, recommend or imply a trade. Present rules, evidence and options.
- Moving a stop down or skipping a rule is an override: record it in the journal with the user's reason.
