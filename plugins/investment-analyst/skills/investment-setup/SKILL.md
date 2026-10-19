---
name: investment-setup
description: First-run setup and maintenance for the investment-analyst skills (Claude Code, Codex, Cursor, Copilot, Gemini CLI and other Agent Skills tools). Installs the Python toolkit, creates the user's private investment workspace, records the SEC contact string and portfolio rules, runs a health check and smoke test, and optionally connects a private GitHub repo with scheduled Actions. Use when the user asks to set up the investment analyst, says "set up", "first run", "install", "update the plugin", when any other investment-analyst skill reports "No investment workspace found", or when the user wants to change sectors, thresholds or schedules. Takes an optional mode (first-run, update, github or doctor).
license: MIT
compatibility: Needs Python 3.10+, git and internet access (FRED, Yahoo Finance, SEC EDGAR); a GitHub account for scheduled jobs is optional.
metadata:
  plugin: investment-analyst
  repository: https://github.com/mahmutademm/Investment-Analyst-Skill
---

# Investment analyst: setup and first run

You are setting up a research workflow that the user will rely on for real money decisions. Be careful,
explicit and boring. Read `references/operating-rules.md` (in this skill's folder) before doing anything;
those rules apply to every investment-analyst skill. Section 8 there covers platform differences (Claude
Code, Codex, Cursor and other tools): how to ask questions, sandboxes, and how the user runs commands.

## How the system is built (explain this to the user in your own words on first run)

```
Skills + toolkit (public, read-only)        Workspace (private, the user's)
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

## Where the toolkit comes from

"This skill's folder" is the folder that contains this SKILL.md. Claude Code fills in
`${CLAUDE_SKILL_DIR}`; other tools show the path when the skill loads. If you cannot tell, ask the user.

- **Plugin install** (Claude Code, Codex or Cursor plugin marketplace): the toolkit ships next to the
  skills, at `<this skill's folder>/../../toolkit` (it contains `pyproject.toml`). Install from there.
- **Skills-only install** (`npx skills add`, Codex `$skill-installer`, or skill folders copied by hand):
  there is no toolkit folder, so install it from GitHub:
  `python -m pip install --upgrade "git+https://github.com/mahmutademm/Investment-Analyst-Skill.git#subdirectory=plugins/investment-analyst/toolkit"`

## First-run guide (follow in order; do not skip the questions)

### Step 1: Inspect, do not change anything yet
Run and read:
- `python --version` (needs 3.10+; on Windows also try `py -3 --version`)
- `python -m iat --version` (is the toolkit already installed?)
- `python -m iat status` (does a workspace already exist?)
- `git --version`, and `gh --version` (optional)

If a workspace already exists, switch to the "Maintenance" section below instead of re-initializing.
If commands fail with network or permission errors, your platform probably runs them in a sandbox
(operating rules, section 8): ask the user to allow network access or to run the commands in their own
terminal, and continue from their output.

### Step 2: Ask the user four questions
Use one structured question call if your platform has one (in Claude Code: AskUserQuestion, up to 4
questions); otherwise send one chat message with the four numbered questions and wait for the answers.
1. **Workspace folder.** Recommend a short path such as `%USERPROFILE%\InvestmentWorkspace` (Windows) or
   `~/InvestmentWorkspace`. Explain why: Excel cannot open files whose full path exceeds 218 characters,
   and cloud-sync folders (OneDrive/Dropbox) can lock files while Excel has them open.
2. **SEC contact string.** SEC EDGAR requires a User-Agent with a name and email on every request. It is
   stored only in `config/local.yaml` (git-ignored) and, if they use GitHub Actions, in a repo secret.
   Let the user type it as free text. Never guess or reuse an email from elsewhere.
3. **Portfolio rules.** Portfolio value (for position sizing; "skip" is fine), number of positions
   (default 15), risk per position (default 1%).
4. **Scheduling.** "GitHub Actions in a private repo (recommended)" / "Later" / "Manual runs only".

### Step 3: Install the toolkit
Tell the user what you are about to install, then run the command from "Where the toolkit comes from":
```
python -m pip install --upgrade "<this skill's folder>/../../toolkit"          # plugin install
python -m pip install --upgrade "git+https://github.com/mahmutademm/Investment-Analyst-Skill.git#subdirectory=plugins/investment-analyst/toolkit"   # skills-only
```
If they prefer isolation, create a virtual environment inside the workspace first
(`python -m venv <workspace>/.venv`) and use that interpreter for every command in every skill (note its
path in `config/settings.yaml` as a comment so later sessions know).

### Step 4: Create and configure the workspace
```
python -m iat init "<workspace folder>"
python -m iat config sec-agent "<the string the user gave>"
```
Then edit `<workspace>/config/settings.yaml` with your file-edit tool: `portfolio.value`,
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
call happens in the macro-analysis skill.

### Step 7: GitHub Actions (only if the user chose it)
Follow `references/github-actions.md` exactly. Ask before `git init`/commit, before creating the
repository (private only), before pushing, and before adding the secret. With `gh`, use
`gh secret set SEC_USER_AGENT` so the value is typed into gh's prompt by the user, not into the chat.
If `gh` is not installed, give the user the manual github.com steps and wait for the repo URL.
After the first green run: `python -m iat config data-owner actions`, commit, push.

### Step 8: Wrap up
Tell the user:
- the workspace path and what lives in it (point to its README.md);
- which commands they may want to run themselves in their terminal (`python -m iat weekly` for heavy screens);
- to open their AI tool in the workspace folder from now on: its `AGENTS.md` (and `CLAUDE.md`) carries the
  rules and commands, so even a tool without skill support behaves;
- the next step: the macro-analysis skill (how to run a skill on their platform: operating rules, section 8).

## Maintenance

- **Plugin or skills updated** (plugin marketplace update, or `npx skills update`): reinstall the toolkit
  (Step 3 command), then `python -m iat upgrade` (refreshes `.toolkit`, the workflows and `AGENTS.md`), then
  commit and push so Actions use the same version. `python -m iat doctor` warns when the vendored copy is stale.
- **Change sectors, sub-industries, thresholds or peers**: see `references/what-to-change.md`.
- **Move the workspace**: move the folder, then `python -m iat --workspace "<new path>" status` and
  re-run `python -m iat init "<new path>"` (it keeps existing config) to update the pointer file.
- **Something broke**: `python -m iat doctor`, then `IAT_DEBUG=1 python -m iat <command>` for a traceback.

## Guardrails
- Never commit or push without the user saying yes for that specific action.
- Never create a public repository, and never print the SEC contact string back into files inside the plugin folder.
- Do not edit files in the plugin or skills folders during setup; everything user-specific lives in the workspace.
