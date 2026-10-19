# Connecting the workspace to GitHub Actions

Goal: a **private** repository holding the workspace, with two scheduled workflows that commit fresh
data. The user then only needs `git pull` before running a skill.

| Workflow | Schedule (UTC) | Runs | Typical time |
|---|---|---|---|
| `daily.yml` | 22:30 Mon-Fri | `iat daily`: FRED macro, ETF rotation, watchlist checks, `data/reports/daily_latest.md` | 1-2 min |
| `weekly.yml` | 14:00 Saturday | `iat weekly`: screens every key in `state.yaml -> screening.active` | 5-60 min |

Both can also be started by hand (Actions tab -> workflow -> Run workflow).

## Steps (ask before each outward-facing step)

1. **Check ignores first.** In the workspace: `git init` (if needed), then
   `git check-ignore config/local.yaml data/iat.db filings` must print all three. If not, fix `.gitignore`.
2. **First commit.** `git add -A`, then `git status` and show the user the file list. Confirm that no
   personal secrets are staged, then commit with `git commit -m "Initial investment workspace"`.
3. **Create the private repo.**
   - With GitHub CLI (`gh auth status` OK): `gh repo create <name> --private --source . --push`.
   - Without it: the user creates an empty **private** repo on github.com (no README), then
     `git remote add origin <url>` and `git push -u origin main` (or `master`).
4. **Add the secret.** Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
   name `SEC_USER_AGENT`, value = the same contact string as `config/local.yaml`. With gh:
   `gh secret set SEC_USER_AGENT` (it prompts; the value never appears in the chat or shell history).
5. **Allow the bot to push.** Repo -> Settings -> Actions -> General -> Workflow permissions ->
   "Read and write permissions". (The workflows also declare `permissions: contents: write`.)
6. **Run once by hand.** Actions -> daily-macro-rotation -> Run workflow. When it is green, run `git pull`.
7. **Switch the data owner.** `python -m iat config data-owner actions`, then commit and push
   `config/settings.yaml`. From now on local runs of macro/rotation/screen write to `data/local/`
   (git-ignored), so they never conflict with the bot's commits. Readers pick whichever copy is newer.

## Troubleshooting

- **Yahoo rate limits on GitHub's IPs** (weekly job fails or many `PARTIAL DATA` flags): lower
  `screening.max_tickers`, raise `sleep_seconds`, or run `python -m iat weekly` locally and push
  (set `data.owner: local` on that machine first, or copy the CSVs from `data/local/screens`).
- **Push rejected**: someone committed in between; the workflow already does `git pull --rebase`. Re-run.
- **Scheduled runs stopped**: GitHub disables schedules after 60 days without repository activity.
  Re-enable on the Actions tab.
- **Private repo minutes**: the free plan includes 2,000 Actions minutes a month for private repos; these
  jobs use roughly 100-300.
