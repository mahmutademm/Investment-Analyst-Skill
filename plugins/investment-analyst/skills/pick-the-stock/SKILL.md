---
name: pick-the-stock
description: Deep dive on 1-4 stocks the user chose. Pulls SEC XBRL financials and the filing pack (10-K, 10-Q, proxy, earnings releases, 8-Ks), reads the filings, builds business/moat and a SWOT tied to model assumptions, runs the earnings-quality and credit gate (5-step DuPont, CFO/NI, accruals, Beneish, Piotroski, Altman, leverage, coverage, maturities), compares relative value with the full sub-industry peer median and the stock's own history, values it by life-cycle stage (3-stage DCF, reverse DCF, scenarios and sensitivity, DDM, residual income, normalized earnings), and prepares a decision sheet (6-month expected return, catalyst, ATR stop, position size, scale-in). Produces <TICKER>_DeepDive_<date>.xlsx. Takes 1-4 tickers. Use for "deep dive", "analyze the 10-K", "is X a buy", "value X".
license: MIT
compatibility: Needs Python 3.10+ and internet access; run the investment-setup skill first.
metadata:
  plugin: investment-analyst
  repository: https://github.com/mahmutademm/Investment-Analyst-Skill
---

# Pick the stock: deep dive

You prepare the evidence; the user makes the call. Work in this order, because each step can stop the
next one:

1. Business and moat (a SWOT that feeds the assumptions)
2. Earnings quality and credit (**pass/fail gate**)
3. Relative value vs the **full peer median** and the stock's own history
4. Intrinsic value by life-cycle method, plus a reverse DCF and scenarios
5. Decision support: expected 6-month return, catalyst, position size, stops

Read first: the shared rules in `../investment-setup/references/operating-rules.md` (if that folder was not installed: https://github.com/mahmutademm/Investment-Analyst-Skill/blob/main/plugins/investment-analyst/skills/investment-setup/references/operating-rules.md).
This skill's `references/`:
`10k-reading-guide.md`, `earnings-quality.md`, `credit.md`, `valuation-lifecycle.md`,
`notes-schema.md`, `analysis-risks.md`.

| Step | Python | AI (you) | User |
|---|---|---|---|
| Data + filings | `iat company <T>` (~1 min) | checks warnings | confirms the peer set |
| Filing reading | section text files | reads, extracts, cites | verifies flagged numbers |
| Gate | 16 automated tests | 9+ filing-review items | decides on WATCH; any FAIL override |
| Relative value | peer table, medians, own history | explains premium or discount | - |
| Intrinsic value | live DCF, reverse DCF, sensitivity | proposes stage and assumptions with reasons | **approves the stage and assumptions** |
| Decision | sizing, stops, expected return | summarizes the trade-offs | **decides** |

## Workflow (per ticker; for several tickers, do step 0 for all first)

### 0. Data pull and sanity checks
1. `python -m iat status` (pull first if the workspace has a git remote).
2. `python -m iat company <T>` (add `--sub-industry <key>` if detection is wrong). It writes
   `output/companies/<T>/data.json`, `summary.md`, the filing pack under `filings/<T>/`, and a first
   workbook.
3. Read `summary.md` fully. Handle the warnings:
   - "falling back to Yahoo" -> tell the user. SEC data is preferred, so fix the SEC contact via setup if needed.
   - SEC vs Yahoo gaps > 5% -> definitions differ; note which figure you trust and why.
   - Missing critical fields -> find them in the 10-K and ask the user to confirm before typing over
     cells in `Financials`.
   - Foreign filer (20-F/IFRS), unusual fiscal year-end, LIFO inventory: note the comparability limits.
4. **Peer set (STOP and ask).** Show the auto-selected peers from the sub-industry universe. Peers must be
   the full comparable group (5-10 names), not the user's other picks. Ask to confirm or edit. If edited:
   `python -m iat company <T> --peers A,B,C,... --no-filings`.

### 1. Business and moat (read the filings; `references/10k-reading-guide.md`)
Use Grep/Read on `filings/<T>/text/sections/*.txt` (Item 1, 1A, 7, 7A, 8, 9A, auditor report) and the
earnings-release text. Do not load a whole 10-K at once; search for the notes you need (segments, revenue
recognition, debt, leases, contingencies, income taxes, stock compensation).
- Business: what it sells, to whom, segment revenue and **operating profit** shares (which segment makes the money).
- Moat check: switching costs, scale/cost advantage, network effects, brand, regulatory barriers, IP.
  Confirm in the numbers: ROIC above peers for 5+ years (`Ratios` ROIC row vs peer ROIC). XBRL gives
  about 5-6 years; say when the record is shorter.
- SWOT **tied to assumptions**: every item names the driver it moves (`g1`, `margin_target`,
  `sales_to_capital`, `ronic`, `wacc_adj`, `probability`) and the direction. "Pricing power" justifies a
  margin; "reimbursement cuts" lowers growth. An item that moves nothing does not belong.
- **Bear case first**, then the pre-mortem ("six months from now the stock is down 25%; what happened?"),
  then thesis stops (fundamental changes that would make the thesis wrong).

### 2. Earnings quality and credit gate (`references/earnings-quality.md`, `references/credit.md`)
- Automated tests are already in `summary.md` and on the `Gate` sheet: CFO/NI, accruals, Beneish,
  Piotroski, Altman Z/Z'', net debt/EBITDA incl. leases, EBIT/interest, CFO/debt, liquidity vs 24-month
  maturities, receivables vs revenue, inventory vs revenue, capex/D&A, SBC %, share count, ROIC vs WACC.
- Interpret the 5-step DuPont (`Ratios` sheet): ROE driven by margins and turnover is healthy; ROE driven
  by leverage is fragile. Buybacks shrink equity and inflate ROE, so check ROIC alongside it.
- Filing-review items (you fill `gate_review` with status + evidence + citation): auditor opinion and
  going concern, material weakness (Item 9A), critical audit matters, auditor changes, non-GAAP vs GAAP
  gap and recurring "one-time" charges, revenue-recognition changes, litigation and contingencies, debt
  mix (fixed/floating, covenants, maturity wall), credit ratings and outlook. Profile extras: banks (CET1,
  NPLs, NIM, loan/deposit), insurers (combined ratio, reserves), managed care (MLR, days claims payable).
- **If the gate is FAIL: stop.** Tell the user which test failed and why that undermines the valuation.
  Continue only if the user explicitly overrides; record it:
  `python -m iat journal <T> --action "OVERRIDE gate" --gate FAIL --reason "<user's reason>" --override "<what>"`.
- WATCH items need one written sentence each before you move on.

### 3. Relative value
From the `Peers` sheet: the target's premium or discount to the **peer median** on forward P/E, PEG (only
when consensus growth > 3%), EV/EBITDA, EV/EBIT, EV/sales, FCF yield, plus the own-history block (P/E
and FCF yield at fiscal year-ends). Explain *why* it trades at a premium or discount, using the
SWOT/news evidence: deserved or not?

### 4. Intrinsic value by life cycle (`references/valuation-lifecycle.md`)
1. **Stage (STOP and ask).** Show the toolkit's suggestion and its reason, plus your own view. Options:
   Early/unprofitable, High growth, Mature, Mature dividend payer, Financials, Cyclical, Declining.
2. **Assumptions (STOP and ask).** Propose Bear/Base/Bull drivers in a table, each with a reason tied to
   SWOT items, consensus (2-year EPS CAGR, revenue estimates), history (3-year revenue CAGR, margin range)
   and peers. Defaults in `data.json -> scenarios` are mechanical starting points, not a view. Get
   approval or edits, then write them to `notes.json -> assumptions` (with `rationale`).
3. Reverse DCF: compare the implied stage-1 growth with consensus and history. That gap is "what is
   priced in", the key question for a 6-month horizon.
4. Check the terminal-value share (warn when > 70%) and the WACC x g sensitivity. Use DDM only for stable
   dividend payers, residual income / justified P/B for banks and insurers, and normalized mid-cycle
   earnings for cyclicals.

### 5. Decision support (`Decision` sheet)
- Catalysts with dates inside the horizon. Without one, the default gap closure is 20% instead of 50%,
  and you should say why that matters.
- Expected 6-month return = probability-weighted targets; after tax if the user set a short-term rate.
- Price stop = entry - k x ATR(14) (k = `valuation.atr_multiple`); shares sized so a stop-out costs
  `risk_per_position_pct` of the portfolio, capped by `max_position_pct`; 3-tranche scale-in plan.
- Rate sensitivity (growth stocks): weekly move per +100bp in the 10Y, from `summary.md`.
- Concentration: does this pick overlap a sector or a high correlation with existing positions?

### 6. Write the notes, rebuild, hand over
1. `python -m iat notes-template company <T>` (if `notes.json` does not exist), then fill it following
   `references/notes-schema.md`. Every factual line gets a source.
2. `python -m iat excel company <T>` rebuilds the workbook with your notes (green cells) and the
   approved assumptions. The `Checks` sheet must show ~0 difference between Excel and Python.
3. Present: gate result, relative value, value range (bear/base/bull, probability-weighted), reverse DCF
   reading, catalyst, expected 6-month return, stop and size, top 3 risks, workbook path. **Do not
   recommend buy or sell.** Point the user to the yellow `Decision` cell.
4. Ask whether to record the decision (`python -m iat journal ...`) and add or update the watchlist
   (`python -m iat watch add <T> --status <watch|tranche1> --entry <price> --atr <atr> --price-stop <stop>
   --thesis "..." --thesis-stop "..." --catalyst "..." --catalyst-date <date> --sector "<Sector>"`).
5. Several tickers: end with a comparison table (gate, upside, expected return, catalyst date, rate
   sensitivity, sector) so the user can choose between them.

## Guardrails
- Earnings quality comes before valuation. A P/E on low-quality earnings is a misleading number.
- Do not adjust assumptions to reach a target price. If the user wants a different value, show which
  assumption would have to change and by how much (the sensitivity and reverse-DCF sheets).
- Quotes from filings are short (one or two lines) with section and page.
