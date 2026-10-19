---
name: setup
description: First-run setup and maintenance for the investment-analyst plugin. Installs the Python toolkit, creates the user's private investment workspace, records the SEC contact string and portfolio rules, runs a health check and smoke test, and optionally connects a private GitHub repo with scheduled Actions. Use when the user runs /investment-analyst:setup, says "set up", "first run", "install", "update the plugin", when any other investment-analyst skill reports "No investment workspace found", or when the user wants to change sectors, thresholds or schedules.
argument-hint: "[first-run | update | github | doctor]"
---

# Investment analyst: setup and first run

You are setting up a research workflow that the user will rely on for real money decisions. Be careful,
explicit and boring. Read `references/operating-rules.md` (in this skill's folder) before doing anything;
those rules apply to every skill in this plugin.

## How the system is built (explain this to the user in your own words on first run)

```
Plugin (public, read-only)                  Workspace (private, the user's)
  skills/            <- instructions         config/settings.yaml   preferences
  toolkit/iat/       <- Python code          config/state.yaml      decisions recorded by skills
                         |                   config/local.yaml      SEC contact (git-ignored)
                         | pip install       data/                  CSV history (+ SQLite cache)
                         v                   filings/  output/      10-K text, Excel workbooks
               python -m iat <command>  ---> .github/workflows/     daily + weekly jobs (optional)
```

- Python does the mechanical work (pulls, ratios, scores, Excel). The AI reads filings and news and drafts
  with citations. The user makes every decision.
- Heavy recurring pulls run on GitHub Actions in the user's private repo (or in the user's own terminal),
  not inside the chat.

The plugin root is two folders above this skill: `${CLAUDE_SKILL_DIR}/../..`. The toolkit is in
`<plugin root>/toolkit`. If `${CLAUDE_SKILL_DIR}` was not substituted, use the "Base directory for this
skill" path shown when the skill loaded, or find `toolkit/pyproject.toml` under `~/.claude/plugins/`.

## First-run guide (follow in order; do not skip the questions)

### Step 1: Inspect, do not change anything yet
Run and read:
- `python --version` (needs 3.10+; on Windows also try `py -3 --version`)
- `python -m iat --version` (is the toolkit already installed?)
- `python -m iat status` (does a workspace already exist?)
- `git --version`, and `gh --version` (optional)

If a workspace already exists, switch to the "Maintenance" section below instead of re-initializing.

### Step 2: Ask the user (one AskUserQuestion call, up to 4 questions)
1. **Workspace folder.** Recommend a short path such as `%USERPROFILE%\InvestmentWorkspace` (Windows) or
   `~/InvestmentWorkspace`. Explain why: Excel cannot open files whose full path exceeds 218 characters,
   and cloud-sync folders (OneDrive/Dropbox) can lock files while Excel has them open.
2. **SEC contact string.** SEC EDGAR requires a User-Agent with a name and email on every request. It is
   stored only in `config/local.yaml` (git-ignored) and, if they use GitHub Actions, in a repo secret.
   Let the user type it in "Other". Never guess or reuse an email from elsewhere.
3. **Portfolio rules.** Portfolio value (for position sizing; "skip" is fine), number of positions
   (default 15), risk per position (default 1%).
4. **Scheduling.** "GitHub Actions in a private repo (recommended)" / "Later" / "Manual runs only".

### Step 3: Install the toolkit
Tell the user what you are about to install, then:
```
python -m pip install --upgrade "<plugin root>/toolkit"
```
If they prefer isolation, create a virtual environment inside the workspace first
(`python -m venv <workspace>/.venv`) and use that interpreter for every command in every skill (note its
path in `config/settings.yaml` as a comment so later sessions know).

### Step 4: Create and configure the workspace
```
python -m iat init "<workspace folder>"
python -m iat config sec-agent "<the string the user gave>"
```
Then edit `<workspace>/config/settings.yaml` with the Edit tool: `portfolio.value`,
`portfolio.target_positions`, `portfolio.risk_per_position_pct`. Leave everything else at defaults unless
the user asked. Show the user the diff.

### Step 5: Health check
`python -m iat doctor`. Every FAIL must be fixed before continuing; explain each WARN. Typical fixes:
- SEC FAIL with 403 -> the contact string is missing an email or is malformed.
- Yahoo FAIL -> temporary rate limit; wait a minute and retry once.
- FRED FAIL -> network/proxy problem; ask the user.

### Step 6: Smoke test (about 1 minute)
`python -m iat daily`. Show the user the rule-based cycle suggestion and the top of the rotation table
from the printed report, then say plainly that these are mechanical starting points and the real cycle
call happens in `/investment-analyst:macro-analysis`.

### Step 7: GitHub Actions (only if the user chose it)
Follow `references/github-actions.md` exactly. Ask before `git init`/commit, before creating the
repository (private only), before pushing, and before adding the secret. With `gh`, use
`gh secret set SEC_USER_AGENT` so the value is typed into gh's prompt by the user, not into the chat.
If `gh` is not installed, give the user the manual github.com steps and wait for the repo URL.
After the first green run: `python -m iat config data-owner actions`, commit, push.

### Step 8: Wrap up
Tell the user:
- the workspace path and what lives in it (point to its README.md);
- which commands they may want to run themselves (`! python -m iat weekly` for heavy screens);
- the next step: `/investment-analyst:macro-analysis`.

## Maintenance

- **Plugin updated**: reinstall the toolkit (Step 3 command), then `python -m iat upgrade`, then commit and
  push so Actions use the same version. `python -m iat doctor` warns when the vendored copy is stale.
- **Change sectors, sub-industries, thresholds or peers**: see `references/what-to-change.md`.
- **Move the workspace**: move the folder, then `python -m iat --workspace "<new path>" status` and
  re-run `python -m iat init "<new path>"` (it keeps existing config) to update the pointer file.
- **Something broke**: `python -m iat doctor`, then `IAT_DEBUG=1 python -m iat <command>` for a traceback.

## Guardrails
- Never commit or push without the user saying yes for that specific action.
- Never create a public repository, and never print the SEC contact string back into files inside the plugin folder.
- Do not edit files in the plugin folder during setup; everything user-specific lives in the workspace.
