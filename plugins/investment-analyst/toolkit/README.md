# iat-toolkit

Python half of the `investment-analyst` Claude Code plugin. It does the mechanical, repeatable work:

| Command | What it does | Typical runtime |
|---|---|---|
| `iat doctor` | Checks Python packages, network access, workspace and SEC contact string | seconds |
| `iat init <path>` | Creates a private workspace (config, data folders, GitHub Actions workflows, vendored toolkit copy) | seconds |
| `iat status` | Shows data freshness, current cycle call, allocation, watchlist | seconds |
| `iat macro` | Pulls ~25 FRED series and scores the business-cycle rules | ~30 s |
| `iat rotation` | Sector and sub-industry ETF relative strength, 10/40-week MAs, RRG quadrants, correlations | ~15 s |
| `iat daily` | `macro` + `rotation` + `watch check` + markdown report (used by GitHub Actions) | ~1 min |
| `iat industries` | Lists Yahoo industry names you can map to sub-industries | instant |
| `iat universe <key>` | Builds the stock list for one sub-industry from the Yahoo screener | ~5 s |
| `iat screen <key>` | Pulls metrics for every stock in a sub-industry and ranks it vs peers | 1-15 min |
| `iat weekly` | Screens every active sub-industry (used by GitHub Actions) | 5-60 min |
| `iat company <TICKER>` | SEC XBRL financials, filings download, forensic scores, credit ratios, peers | ~1 min |
| `iat excel macro\|screen\|company` | Builds the Excel workbook, merging AI notes (JSON) when present | seconds |
| `iat watch add\|list\|check` | Watchlist with thesis and price stops | seconds |
| `iat sync` / `iat sql "<query>"` | Rebuilds the SQLite database from the CSV history and queries it | seconds |

All data comes from free sources: FRED (no key), Yahoo Finance via `yfinance` (unofficial; it can rate-limit), and SEC EDGAR (it requires a contact User-Agent, which you set at first run).

Install: `pip install <path-to-this-folder>` and then run `iat --help`.
