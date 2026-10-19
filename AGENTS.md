# AGENTS.md: investment-analyst repository

This repository publishes the investment-analyst Agent Skills, the Claude Code / Codex / Cursor plugin
that bundles them, and the `iat` Python toolkit they run.

## If the user wants to use the skills

Help them install for their tool (README, "Install"). If their tool has no skill support, follow
`plugins/investment-analyst/skills/investment-setup/SKILL.md` step by step. Never run the workflow inside
this repository: the setup skill creates a separate, private workspace for the user's data.

## If you are changing this repository

- **It is public.** Never add personal data: emails, local paths, portfolio values, positions, keys. The
  only personal details on purpose are the author name and GitHub username in `LICENSE` and the manifests.
- **Skills follow the Agent Skills spec** (agentskills.io): frontmatter only `name`, `description`,
  `license`, `compatibility`, `metadata`, `allowed-tools`. `name` equals the folder name, and the YAML must
  parse (no unquoted `: ` inside the description). Keep instructions platform-neutral: say "ask the user",
  not a tool name. Platform differences belong in `investment-setup/references/operating-rules.md`, section 8.
- **Numbers belong to Python.** Mechanical work goes in the toolkit, not in skill prose.
- **Versions**: `python scripts/bump_version.py X.Y.Z` updates every manifest and the toolkit.
- **Tests**: `python -m unittest discover -s plugins/investment-analyst/toolkit/tests` (these include the
  spec and manifest checks). With Claude Code installed, also run `claude plugin validate .`.
- **Before committing**: `git status --short --ignored`. Nothing under `plugins/` may show as ignored.
