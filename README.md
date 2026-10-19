# Investment Analyst: agent skills for top-down equity research

A top-down equity research workflow for a ~6-month horizon, from macro cycle to a single stock, that
**keeps every decision with you**. Python does the mechanical work (data pulls, ratios, scores, Excel),
the AI reads filings and news and drafts with citations, and scheduled GitHub Actions keep the data fresh.

It works with **Claude Code, OpenAI Codex, Cursor, GitHub Copilot, Gemini CLI, Windsurf** and any other
tool that supports the open [Agent Skills](https://agentskills.io) format.

```
macro-analysis    ->  cycle phase, 4-pillar sector scorecard, weights, sub-industries
      | config/state.yaml
sector-screening  ->  peer-relative screen + "why is it cheap?" news check -> you pick 3-4
      |
pick-the-stock    ->  10-K reading, quality & credit gate, relative + intrinsic value, decision sheet
      |
portfolio-review  ->  stops, tranche triggers, catalysts, monthly re-check, journal
```

Start with the **investment-setup** skill. It walks the AI through the first run.

## Who does what

| | Python toolkit (`python -m iat`) | AI (your agent) | You |
|---|---|---|---|
| Macro | FRED pulls (CPI, core PCE, Fed, 10Y, curve, HY spreads, labor, activity), rule-based cycle vote, ETF relative strength / RRG, correlations | Fed statements, FedWatch, CPI detail, PMIs, FactSet sector revisions and valuations | Cycle call, sector weights, sub-industries |
| Screening | Yahoo universe, ~60 metrics per stock, percentile ranks within the sub-industry, flags | Universe sanity check, temporary-vs-structural news check, catalysts | The 3-4 names to deep-dive |
| Deep dive | SEC XBRL statements + filing pack, DuPont, Beneish, Piotroski, Altman, credit ratios, peers, DCF / reverse DCF / DDM / residual income, sizing; Excel with live formulas | Reads the 10-K/10-Q/proxy/earnings releases, moat, SWOT tied to assumptions, bear case, gate review | Peer set, life-cycle stage, assumptions, BUY / WATCH / PASS |
| Tracking | Daily/weekly jobs, watchlist checks, journal, SQLite | Explains alerts with evidence | Every trade |

## Install

Requirements: an AI coding tool, Python 3.10+, git, internet access. Excel or LibreOffice opens the workbooks.

| Your tool | Install | Then say / type |
|---|---|---|
| **Claude Code** | `/plugin marketplace add mahmutademm/Investment-Analyst-Skill`<br>`/plugin install investment-analyst@investment-analyst` | `/investment-analyst:investment-setup` |
| **OpenAI Codex** | `codex plugin marketplace add mahmutademm/Investment-Analyst-Skill`, then install *investment-analyst* from the plugin directory | `$investment-setup` |
| **Cursor** | Settings → Customize → *From GitHub Repository* → `https://github.com/mahmutademm/Investment-Analyst-Skill` | `/investment-setup` |
| **Any Agent Skills tool** (Copilot, Gemini CLI, Windsurf, OpenCode, Cline, Codex, Cursor, ...) | `npx skills add mahmutademm/Investment-Analyst-Skill` (pick your tool when asked; add `-g` for all projects) | "use the investment-setup skill" |
| **Manual** | Copy the five folders in `plugins/investment-analyst/skills/` into your tool's skills folder (`.agents/skills/`, `.claude/skills/`, `.cursor/skills/`, ...) | "use the investment-setup skill" |
| **No skill support** | Open this repository in the tool and ask it to follow `plugins/investment-analyst/skills/investment-setup/SKILL.md` | |

The setup skill installs the Python toolkit: from the plugin folder when your tool installed the full
plugin, otherwise straight from GitHub
(`pip install "git+https://github.com/mahmutademm/Investment-Analyst-Skill.git#subdirectory=plugins/investment-analyst/toolkit"`).
It then creates your **private workspace** (a separate folder), asks for the SEC contact string EDGAR
requires, runs a health check and a smoke test, and can connect a private GitHub repo with scheduled
Actions. The workspace gets an `AGENTS.md` (plus a `CLAUDE.md` that imports it), so whichever AI tool
you open there knows the rules and commands.

Tools that run commands in a sandbox (for example Codex) need network access approved for the toolkit's
data pulls. The skills ask for it when a command fails.

## Privacy model

- This repository contains no personal data, keys or paths.
- Your workspace holds your settings, watchlist, journal and data. Keep its GitHub repo **private**.
- The SEC contact string lives in `config/local.yaml` (git-ignored) and the `SEC_USER_AGENT` repo secret.

## Data sources and limits

| Source | Used for | Limits |
|---|---|---|
| FRED (St. Louis Fed), no key | Macro series, 10Y risk-free rate | Monthly series lag by 2-6 weeks |
| Yahoo Finance via `yfinance` | Prices, ETF relative strength, screener universe, estimates and revisions, peer metrics | Unofficial; can rate-limit (especially from GitHub's IPs); vendor definitions |
| SEC EDGAR (XBRL companyfacts, submissions, archives) | Deep-dive statements, filings, 8-K red-flag items | Requires a contact User-Agent; tagging varies by company (checked on the workbook's Checks sheet) |
| Web (via your AI tool) | Fed, FedWatch, BLS/BEA detail, FactSet Earnings Insight, company IR, reputable news | Cited in every workbook |

## Outputs

- `Macro_<date>.xlsx`: Scorecard, Cycle Rules, Dashboard, Rotation, Correlation, Events & Fed, Sources
- `Screen_<key>_<date>.xlsx`: Ranking, News Check, Valuation, Quality, Expectations, Balance sheet & risk, Momentum, Methodology, Universe
- `<TICKER>_DeepDive_<date>.xlsx`: Summary, Decision, Gate, Valuation, Reverse DCF, Inputs, Peers, Business & Moat, SWOT, Bear Case, Filing Review, Catalysts, Financials, Ratios, Checks, Sources, XBRL Sources

Workbook conventions: blue cells are inputs, green cells were written by the AI (verify them), and
everything else is a live formula traceable to the SEC-sourced Financials sheet.

## Repository layout

```
.claude-plugin/marketplace.json    Claude Code marketplace (Codex reads it too)
.cursor-plugin/marketplace.json    Cursor marketplace
.agents/plugins/marketplace.json   Codex marketplace
AGENTS.md, CLAUDE.md               instructions for AI tools working on this repository
plugins/investment-analyst/
  plugin.json                      Agent Plugins open-standard manifest (Codex's entry point)
  .claude-plugin/plugin.json       Claude Code manifest
  .cursor-plugin/plugin.json       Cursor manifest
  skills/{investment-setup,macro-analysis,sector-screening,pick-the-stock,portfolio-review}/SKILL.md (+ references/)
  toolkit/                         pip-installable Python package `iat-toolkit` (CLI: python -m iat)
    iat/templates/workspace/       settings, sub-industry map, workflows, AGENTS.md copied by `iat init`
    tests/
scripts/bump_version.py            sets the version in every manifest at once
```

## Development

```bash
pip install -e plugins/investment-analyst/toolkit
python -m unittest discover -s plugins/investment-analyst/toolkit/tests   # includes spec + manifest checks
claude plugin validate plugins/investment-analyst                          # if Claude Code is installed
claude plugin validate .
npx skills add . --list                                                    # what other tools will see
```

## Publishing checklist

- [x] Marketplace owner, plugin author and MIT `LICENSE` (root copy for GitHub, `toolkit/LICENSE` ships with the pip package and the vendored `.toolkit`)
- [ ] Run `git status --short --ignored`: no workspace, `data/`, `filings/`, `output/` or `*.xlsx` files may
      appear as new, and nothing under `plugins/` may show as ignored (`!!`), or it will be missing from GitHub
- [ ] `python scripts/bump_version.py X.Y.Z` (the tests fail if any manifest disagrees), commit, push,
      then `git tag vX.Y.Z && git push --tags`

## License

[MIT](LICENSE) © 2026 Mahmut A Ergin. If you change the copyright line, change it in both `LICENSE` and
`plugins/investment-analyst/toolkit/LICENSE` (a test checks they match).

## Disclaimer

Educational and research tooling. Nothing produced by these skills is investment advice. Data can be
wrong, late or incomplete, so verify important numbers in the filings. You are responsible for your
own decisions.
