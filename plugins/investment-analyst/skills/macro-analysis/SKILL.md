---
name: macro-analysis
description: Top-down macro and sector-rotation analysis for a ~6-month horizon. Reads inflation (CPI, core PCE), the Fed path (actual and market-implied), the 10-year yield and curve, credit spreads, labor and activity data; proposes a business-cycle phase; scores every sector on four pillars (cycle fit, earnings revisions, relative strength, valuation vs its own history); and helps the user set sector weights and the sub-industries to screen. Produces Macro_<date>.xlsx and records the decisions for the screening skill. Use for "what cycle are we in", "which sectors should I be in", "sector rotation", "monthly scorecard review". Takes an optional mode (full, review or scorecard-only).
license: MIT
compatibility: Needs Python 3.10+ and internet access; run the investment-setup skill first.
metadata:
  plugin: investment-analyst
  repository: https://github.com/mahmutademm/Investment-Analyst-Skill
---

# Macro analysis and sector rotation

Goal: decide **where we are in the cycle** and **which sectors and sub-industries deserve capital for the
next ~6 months**, while controlling timing risk. Markets price economic turns 6-9 months before the data
confirms them, so the job is to judge what is *already priced* versus what is *likely next*.

Read first: the shared rules in `../investment-setup/references/operating-rules.md` (if that folder was not installed: https://github.com/mahmutademm/Investment-Analyst-Skill/blob/main/plugins/investment-analyst/skills/investment-setup/references/operating-rules.md).
Detail lives in this skill's `references/`:
`cycle-playbook.md` (phases, indicators, sector map), `scorecard.md` (how each pillar is scored),
`timing-risk.md` (entry/exit discipline), `sources.md` (where to get each fact).

| Step | Python | AI (you) | User |
|---|---|---|---|
| Data | `iat macro`, `iat rotation` (~20 s) | read JSON/CSV | - |
| Research | - | Fed, FedWatch, CPI/PCE detail, PMIs, FactSet revisions and valuations, calendar | - |
| Cycle phase | rule vote | proposal with evidence for and against | **decides** |
| Scorecard | RS pillar, counts, verdicts | pillars 2 and 4 with sources | can override any cell |
| Weights and sub-industries | names per sector, caps check | proposal | **decides** |
| Workbook | `iat excel macro` | writes notes.json | reviews |

## Workflow

### 0. Preflight
1. `python -m iat status`. No workspace -> run the setup skill. If the workspace is a git repo with a
   remote: `git -C <workspace> pull --ff-only`.
2. If `macro` or `rotation` is older than one trading day (or missing), run `python -m iat macro` and
   `python -m iat rotation` yourself (fast).
3. If `config/state.yaml` already has a `cycle` call, this is a **review**: note the previous phase,
   weights and date, and look for what changed (step 7).

### 1. Read the mechanical picture
Open `<workspace>/data/latest/macro.json` and `data/latest/rotation.csv` (or the markdown printed by the
commands). Summarize in a short table:
- Inflation: headline and core CPI YoY and 3-month annualized, core PCE (the Fed's target measure),
  breakevens. Direction matters more than level.
- Policy: Fed target and its 6-month change; real fed funds; **2Y minus fed funds** (a free proxy for
  the market-implied path).
- Rates: 10Y level and trend (vs 50/200-day), real 10Y, 10Y-2Y and 10Y-3M curves.
- Credit and conditions: HY OAS level and 3-month change, NFCI.
- Labor and activity: unemployment vs its 12-month low, Sahm rule, claims trend, payrolls, CFNAI, permits.
- Markets: dollar, oil.
Then the rule vote (`cycle.scores`, the fired rules and their evidence). Say so if it is AMBIGUOUS.

### 2. Research what the data cannot show (cite everything)
Use your web search and page-fetch tools on the sources in `references/sources.md` (no web access on this
platform: ask the user to paste the pages, or mark the item `unknown`):
- Latest FOMC statement, minutes and the Summary of Economic Projections (dot plot); upcoming FOMC dates.
- Market-implied path from CME FedWatch (probabilities for the next 3-4 meetings). If it is unreachable,
  use the 2Y-minus-fed-funds proxy and say that you did.
- CPI/PCE release detail (core services, shelter, goods), next release dates.
- ISM manufacturing and services PMIs (new orders), which are not on FRED.
- **Sector earnings revisions and valuations**: FactSet *Earnings Insight* (weekly PDF) for forward
  12-month P/E by sector vs 5- and 10-year averages, and EPS estimate changes by sector. Yardeni or S&P
  as backup. These feed pillars 2 and 4.
- Optionally: one or two respected strategist views, clearly labeled as opinion.

### 3. Propose the cycle phase, then STOP and ask
Write a one-paragraph case for the leading phase and the runner-up: evidence for, evidence against, and
what the market seems to be pricing six months out. Then ask the user (operating rules, section 8): the four phases
(Early recovery / Mid cycle / Late cycle / Contraction), your recommendation first, with one-line reasons.
Record the answer: `python -m iat state set cycle "{phase: <phase>, date: <today>, confidence: <Low|Medium|High>}"`.

### 4. Score the four pillars for all 11 sectors (`references/scorecard.md`)
1. **Cycle fit**: from the phase map (Yes / Neutral / No). User overrides are allowed.
2. **Earnings revisions**: Yes if forward EPS estimates for the sector rose over the last 1-3 months,
   No if they fell, Neutral if flat. Source and number required.
3. **Relative strength**: Yes only when the rotation status is CONFIRMED or TURNING (`rs_pillar` true).
   "EARLY" means a possible false start, so it scores No until it persists.
4. **Valuation vs its own history**: Yes when the sector's forward P/E (or its premium to the S&P 500) is
   at or below its 10-year average, No when well above. Add the "already priced in?" comment.
Enter only when **3 of 4** agree (ENTER); 2 = WATCH; otherwise AVOID.

### 5. Propose weights and sub-industries, then STOP and ask
- Build a diversified proposal from ENTER (and selectively WATCH) sectors. Respect
  `portfolio.max_sector_pct`. Check the correlation sheet: two sectors correlated above ~0.85 are one bet.
- The user leans toward growth stocks. Keep the process the same, but say explicitly when long-duration
  growth exposure is fighting the rate trend (10Y rising, real yields rising).
- For each chosen sector, propose the sub-industries the thesis actually supports (keys from
  `config/sub_industries.yaml`), using the sub-industry ETF rows (`rel_to_parent_26w_pct`, status) and
  the cycle logic. Example: late cycle with rising rates may favor managed care and devices over biotech.
- Names per sector = weight x `target_positions` (the workbook computes it).
Ask the user to accept or edit the weights, then the sub-industries (two separate questions). Record:
```
python -m iat state set allocation "{Health Care: 25, Energy: 20, ...}"
python -m iat state set sub_industries "{Health Care: [medical-devices, managed-care], ...}"
python -m iat state set screening.active "[medical-devices, managed-care, ...]"
```
If a needed sub-industry is missing from `config/sub_industries.yaml`, follow
`../investment-setup/references/what-to-change.md` and confirm the Yahoo industry mapping with the user.

### 6. Write the notes and build the workbook
`python -m iat notes-template macro` creates `<workspace>/output/macro/notes.json`. Fill it (schema in the
file; keep sources). Then `python -m iat excel macro`. The workbook has: Scorecard, Cycle Rules, Dashboard,
Rotation, Correlation, Events & Fed, Sources.

### 7. Review mode (monthly, or when the daily report flags changes)
Compare with the recorded state: which pillars flipped, whether any **thesis stop** fired (sector
revisions turned negative, the curve or Fed path moved against the call), and which sectors moved from
EARLY to CONFIRMED (tranche-2 triggers) or from CONFIRMED to FADING. Propose changes; the user decides.
Review monthly, not daily: daily noise is not a regime change.

### 8. Hand-off
Tell the user the phase, a scorecard table (sector, 4 pillars, verdict, weight), the sub-industries, the
entry and exit rules from `references/timing-risk.md` applied to this call, and the workbook path.
Next step: the `sector-screening` skill. If GitHub Actions are set up, remind them to commit and
push `config/state.yaml` so the weekly screen picks up the new sub-industries.

## Guardrails
- The phase-to-sector map is a starting map, not a law; say when the current cycle breaks the pattern.
- Do not upgrade an EARLY relative-strength reading to Yes because the thesis is attractive.
- No sector weight is final until the user confirms it.
