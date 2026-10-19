# My investment workspace

Created by `iat init` from the investment-analyst Claude Code plugin. Keep this repository **private**:
it holds your settings, watchlist and decision journal.

| Folder | What lives there | Committed? |
|---|---|---|
| `config/settings.yaml` | Your preferences: portfolio size, risk per trade, thresholds | yes |
| `config/sub_industries.yaml` | Sub-industry definitions (Yahoo industries, ETF, valuation profile) | yes |
| `config/state.yaml` | Decisions the skills recorded: cycle call, sector weights, active screens | yes |
| `config/local.yaml` | SEC contact string and other machine-local secrets | **no** |
| `data/history`, `data/latest`, `data/reports` | CSV/JSON/Markdown from daily and weekly jobs | yes (by GitHub Actions) |
| `data/screens`, `data/universes` | Screen snapshots and stock universes | yes |
| `data/tracking` | Watchlist and decision journal | yes (by you) |
| `data/iat.db` | SQLite cache rebuilt from the CSVs with `iat sync` | no |
| `filings/` | Downloaded 10-K/10-Q/8-K documents | no |
| `output/` | Excel workbooks and AI notes | no (change in .gitignore) |
| `.toolkit/` | Copy of the Python toolkit that GitHub Actions installs | yes |

Daily routine: `git pull` -> open `data/reports/daily_latest.md` -> run a skill in Claude Code.

GitHub Actions need one secret: **Settings -> Secrets and variables -> Actions -> New repository secret**
named `SEC_USER_AGENT` with a value like `Your Name your@email.com`.
