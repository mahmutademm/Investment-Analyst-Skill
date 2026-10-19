---
name: sector-screening
description: Mechanical, peer-relative screening of the sub-industries chosen in macro-analysis (valuation, quality, estimate revisions, momentum, balance sheet, forensic flags), followed by a sourced "why is it cheap?" news check on the top names (temporary vs structural, catalyst inside 6 months). Produces Screen_<key>_<date>.xlsx. The user picks the 3-4 stocks for the deep dive. Use for "screen <sub-industry>", "find candidates in <sector>", "which stocks in medical devices". Takes optional sub-industry keys.
license: MIT
compatibility: Needs Python 3.10+ and internet access; run the investment-setup skill first.
metadata:
  plugin: investment-analyst
  repository: https://github.com/mahmutademm/Investment-Analyst-Skill
---

# Sector screening

Screen all of them, deep-dive only a few. The screen is **mechanical and cheap** to run across the whole
sub-industry. The expensive analysis (filings, peers, valuation) goes only to the survivors, and the user
picks them.

Read first: the shared rules in `../investment-setup/references/operating-rules.md` (if that folder was not installed: https://github.com/mahmutademm/Investment-Analyst-Skill/blob/main/plugins/investment-analyst/skills/investment-setup/references/operating-rules.md).
Detail: `references/screen-metrics.md` (indicators,
thresholds, sector-specific metrics), `references/news-check.md` (temporary vs structural protocol),
`references/sources.md`.

| Step | Python | AI (you) | User |
|---|---|---|---|
| Scope | names per sector from weights | proposes sub-industries/peers | **confirms** |
| Universe | `iat universe <key>` (~5 s) | sanity-checks classification | approves exclusions |
| Screen | `iat screen <key>` (~2 s/name) or weekly Action | reads results, never re-ranks | runs it if long |
| News check | `iat filings <T>` (8-K list, earnings releases) | reads, classifies, cites | judges |
| Shortlist | `iat excel screen <key>` | presents the evidence | **picks 3-4** |

## Workflow

### 0. Preflight
`python -m iat status` (pull first if the workspace has a git remote). Read `config/state.yaml`:
`sub_industries`, `allocation`, `screening.active`. If there is no recorded macro view, ask: "Run
the macro-analysis skill first (recommended) or screen sub-industries you name now?"

### 1. Confirm the scope (STOP and ask if anything is unclear)
- Sub-industries to screen and their profile (`standard`, `bank`, `insurer`, `reit`, `energy`,
  `early_growth`, `managed_care`). Narrow the sector first, because peers must be comparable
  (managed care vs managed care, not vs biotech).
- Shortlist size per sector from its weight: names = weight x `target_positions`. For example, with 15
  positions a 25% sector gets about 4 names and a 10% sector 1-2. The news check covers the top 3-5 per
  sub-industry (`screening.news_check_top_n`).
- A sub-industry missing from `config/sub_industries.yaml` -> `python -m iat industries --sector "<Sector>"`,
  propose an entry, and confirm the mapping with the user before adding it.

### 2. Build and sanity-check the universe
`python -m iat universe <key>`. Review the list for misclassified names (conglomerates, mixed business
models such as payment networks vs lenders), foreign filers (20-F/IFRS), recent IPOs or spin-offs with
under 3 years of history, and names below the tradability floor. Propose `include:`/`exclude:` edits with
reasons; edit `config/sub_industries.yaml` only after the user agrees, then rebuild.

### 3. Get the screen data (respect the user's time)
- If `data/latest/screen_<key>.csv` is under 7 days old (for example from the weekly Action), use it.
- Otherwise estimate the runtime (about 2 seconds per name; the first run has no cache). Under ~3 minutes:
  run `python -m iat screen <key>` yourself. Longer: ask the user to run
  `python -m iat screen <key>` in their own terminal, or run it in the background if your platform can. The per-ticker cache lets an interrupted
  or rate-limited run resume.
- Many `PARTIAL DATA` flags mean Yahoo throttling. Re-run later; do not fill gaps by hand.

### 4. Read the results; do not re-rank by intuition
From the printed markdown or the CSV, explain: the ranking (composite = average of valuation, quality and
revisions/momentum percentiles within the sub-industry), data completeness, the four-step columns
(`step1_cheap`, `step2_estimates_ok`) and every flag on the top names. Also look at the 2-3 names just
below the news-check cutoff (near misses) and any name the user asked about.

### 5. News check: "why is it cheap?" (about 10 minutes per name)
For each top name, follow `references/news-check.md`:
1. `python -m iat filings <T1> <T2> ...` lists the last 10-K/10-Q, the last two earnings releases
   (8-K item 2.02) and every 8-K with its items. Items 4.01 (auditor change), 4.02 (non-reliance) and
   2.06 (impairment) are red flags.
2. Read the last two earnings releases (fetch the EX-99.1 URL): guidance changes, what missed and why.
3. Search reputable news for the last 3-6 months.
4. Classify the discount as **Temporary** (one-off miss, sector-wide sell-off, resolvable legal or
   regulatory overhang), **Structural** (share loss, disruption, a balance sheet it can't refinance) or
   **Unclear**, with dated evidence.
5. Name a **catalyst inside the horizon** with a date or window (earnings, guidance update, product
   approval, spin-off, buyback, rate change that helps the sub-industry), or say there is none.
The chain is: cheap -> estimates not falling -> discount is temporary -> catalyst within 6 months. A name
that clears all four is a deep-dive candidate. The user still decides.

### 6. Write the notes and build the workbook
`python -m iat notes-template screen <key>` -> fill `output/screens/<key>_notes.json` (`news_check` list;
keep `sources`). Then `python -m iat excel screen <key>`. Sheets: Ranking, News Check, Valuation,
Quality, Expectations, Balance sheet & risk, Momentum & trading, Methodology, Universe.

### 7. Shortlist (STOP and ask)
Present a compact table (rank, ticker, composite, cheap?, estimates OK?, temporary/structural, catalyst
and date, key flags). Ask the user to choose the 3-4 names for the deep dive (a multiple-choice
question with the top candidates as options plus free text for names outside the list). Record:
`python -m iat state set shortlist.<key> "[T1, T2, T3]"` and add `user_shortlist` to the notes, then
rebuild the workbook. Optionally add them to the watchlist with `python -m iat watch add <T> --status watch ...`.
Next: the `pick-the-stock` skill with T1 T2 T3.

## How a screen can mislead, and what this skill does about it

| Risk | Countermeasure |
|---|---|
| Cheap because earnings are about to fall (value trap) | Valuation is paired with revisions (step 2) and the news check (step 3) |
| Vendor data definitions differ from filings | Flags + "PARTIAL DATA"; the deep dive recomputes everything from SEC XBRL |
| Peer group is not comparable | Sub-industry level universes, profiles, manual include/exclude |
| Small universe (< 8 names) makes percentiles noisy | Say so explicitly; lean on absolute thresholds and the news check |
| Momentum alone finds expensive stocks; quality alone ignores price | Composite needs all three groups |
| The cutoff hides good names | Review near misses; the user can add any name |
| Analyst Buy ratings look like a signal | Ratings are ignored; revisions (direction of estimates) are used instead |
| Low coverage looks like an opportunity | Flagged (< 5 analysts): possibly mispriced, but data is thinner |
| Binary events inside the window | Earnings date, short interest and 8-K items are flagged |

## Guardrails
- The ranking chooses who gets a news check, not what to buy. Say this when you present it.
- Never drop or promote a name silently. Every exclusion gets a reason the user can see.
- Do not invent catalysts or dates. Write "none identified" when there is none.
