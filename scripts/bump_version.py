"""Set one version everywhere it lives: `python scripts/bump_version.py 0.3.0`.

The version is declared in the three plugin manifests (Claude Code, Cursor, Agent Plugins / Codex) and in
the toolkit's `iat/__init__.py` (pyproject.toml reads it from there). The test suite fails if they differ.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "investment-analyst"
MANIFESTS = [PLUGIN / ".claude-plugin" / "plugin.json", PLUGIN / ".cursor-plugin" / "plugin.json",
             PLUGIN / "plugin.json"]
INIT = PLUGIN / "toolkit" / "iat" / "__init__.py"


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", argv[0]):
        print(__doc__)
        return 2
    new = argv[0]
    for path in MANIFESTS:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = new
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)} -> {new}")
    text = INIT.read_text(encoding="utf-8")
    text, n = re.subn(r'^__version__ = "[^"]+"', f'__version__ = "{new}"', text, flags=re.M)
    if n != 1:
        print(f"could not find __version__ in {INIT}")
        return 1
    INIT.write_text(text, encoding="utf-8")
    print(f"{INIT.relative_to(ROOT)} -> {new}")
    print("Next: run the tests, commit, then tag the release: git tag v" + new)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
