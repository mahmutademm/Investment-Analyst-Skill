# Investment Analyst: a Claude Code plugin

A top-down equity research workflow for a ~6-month horizon, from macro cycle to a single stock, that
**keeps every decision with you**. Python does the mechanical work (data pulls, ratios, scores, Excel),
the AI reads filings and news and drafts with citations, and scheduled GitHub Actions keep the data fresh.

```
/investment-analyst:macro-analysis   ->  cycle phase, 4-pillar sector scorecard, weights, sub-industries
        | config/state.yaml
/investment-analyst:sector-screening ->  peer-relative screen + "why is it cheap?" news check -> you pick 3-4
        |
/investment-analyst:pick-the-stock   ->  10-K reading, quality & credit gate, relative + intrinsic value, decision sheet
        |
/investment-analyst:portfolio-review ->  stops, tranche triggers, catalysts, monthly re-check, journal
```

Start with `/investment-analyst:setup`. Typing `/macro`, `/sector` or `/pick` in Claude Code's slash menu
finds the skills.

## Who does what

| | Python toolkit (`python -m iat`) | AI (Claude) | You |
|---|---|---|---|
| Macro | FRED pulls (CPI, core PCE, Fed, 10Y, curve, HY spreads, labor, activity), rule-based cycle vote, ETF relative strength / RRG, correlations | Fed statements, FedWatch, CPI detail, PMIs, FactSet sector revisions and valuations | Cycle call, sector weights, sub-industries |
| Screening | Yahoo universe, ~60 metrics per stock, percentile ranks within the sub-industry, flags | Universe sanity check, temporary-vs-structural news check, catalysts | The 3-4 names to deep-dive |
| Deep dive | SEC XBRL statements + filing pack, DuPont, Beneish, Piotroski, Altman, credit ratios, peers, DCF / reverse DCF / DDM / residual income, sizing; Excel with live formulas | Reads the 10-K/10-Q/proxy/earnings releases, moat, SWOT tied to assumptions, bear case, gate review | Peer set, life-cycle stage, assumptions, BUY / WATCH / PASS |
| Tracking | Daily/weekly jobs, watchlist checks, journal, SQLite | Explains alerts with evidence | Every trade |

## Install

Requirements: Claude Code, Python 3.10+, git (for GitHub Actions). Excel or LibreOffice to open the workbooks.

```bash
# from GitHub (after this repo is published)
/plugin marketplace add <github-user>/<this-repo>
/plugin install investment-analyst@investment-analyst

# or from a local clone while developing
/plugin marketplace add /path/to/this/repo
/plugin install investment-analyst@investment-analyst
```

Then run `/investment-analyst:setup`. It installs the toolkit (`pip install <plugin>/toolkit`), creates
your **private workspace** (a separate folder, by default outside this repo), asks for the SEC contact
string EDGAR requires, runs a health check and a smoke test, and can connect a private GitHub repo with
scheduled Actions.

## Privacy model

- This repository (the plugin) contains no personal data, keys or paths.
- Your workspace holds your settings, watchlist, journal and data. Keep its GitHub repo **private**.
- The SEC contact string lives in `config/local.yaml` (git-ignored) and the `SEC_USER_AGENT` repo secret.

## Data sources and limits

| Source | Used for | Limits |
|---|---|---|
| FRED (St. Louis Fed), no key | Macro series, 10Y risk-free rate | Monthly series lag by 2-6 weeks |
| Yahoo Finance via `yfinance` | Prices, ETF relative strength, screener universe, estimates and revisions, peer metrics | Unofficial; can rate-limit (especially from GitHub's IPs); vendor definitions |
| SEC EDGAR (XBRL companyfacts, submissions, archives) | Deep-dive statements, filings, 8-K red-flag items | Requires a contact User-Agent; tagging varies by company (checked on the workbook's Checks sheet) |
| Web (via Claude) | Fed, FedWatch, BLS/BEA detail, FactSet Earnings Insight, company IR, reputable news | Cited in every workbook |

## Outputs

- `Macro_<date>.xlsx`: Scorecard, Cycle Rules, Dashboard, Rotation, Correlation, Events & Fed, Sources
- `Screen_<key>_<date>.xlsx`: Ranking, News Check, Valuation, Quality, Expectations, Balance sheet & risk, Momentum, Methodology, Universe
- `<TICKER>_DeepDive_<date>.xlsx`: Summary, Decision, Gate, Valuation, Reverse DCF, Inputs, Peers, Business & Moat, SWOT, Bear Case, Filing Review, Catalysts, Financials, Ratios, Checks, Sources, XBRL Sources

Workbook conventions: blue cells are inputs, green cells were written by the AI (verify them), and
everything else is a live formula traceable to the SEC-sourced Financials sheet.

## Repository layout

```
.claude-plugin/marketplace.json
plugins/investment-analyst/
  .claude-plugin/plugin.json
  skills/{setup,macro-analysis,sector-screening,pick-the-stock,portfolio-review}/SKILL.md (+ references/)
  toolkit/                 pip-installable Python package `iat-toolkit` (CLI: python -m iat)
    iat/templates/workspace/   settings, sub-industry map, GitHub Actions workflows copied by `iat init`
    tests/
```

## Development

```bash
pip install -e plugins/investment-analyst/toolkit
python -m unittest discover -s plugins/investment-analyst/toolkit/tests
claude plugin validate plugins/investment-analyst
claude plugin validate .
```

## Publishing checklist

- [ ] Replace `REPLACE-WITH-YOUR-GITHUB-USERNAME` in `.claude-plugin/marketplace.json`
- [ ] Optionally add `"author": {"name": "..."}` to `plugin.json` (only what you want public)
- [ ] Add a LICENSE of your choice
- [ ] Confirm `git status` shows no workspace, `data/`, `filings/`, `output/` or `*.xlsx` files
- [ ] Bump `version` in `plugin.json`, `marketplace.json` and `toolkit/pyproject.toml` together

## Disclaimer

Educational and research tooling. Nothing produced by this plugin is investment advice. Data can be
wrong, late or incomplete, so verify important numbers in the filings. You are responsible for your
own decisions.
