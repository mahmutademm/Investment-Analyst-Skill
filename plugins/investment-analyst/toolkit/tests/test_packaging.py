"""Repository-level checks: skills follow the Agent Skills spec and every manifest agrees.

Skipped automatically when the toolkit is tested outside the repository (e.g. a vendored copy).
"""
import json
import re
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve()
ROOT = next((p for p in HERE.parents if (p / ".claude-plugin" / "marketplace.json").is_file()), None)
PLUGIN = ROOT / "plugins" / "investment-analyst" if ROOT else None
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

def _toolkit_version() -> str:
    text = (HERE.parent.parent / "iat" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'^__version__ = "([^"]+)"', text, re.M).group(1)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@unittest.skipUnless(ROOT, "not inside the plugin repository")
class SkillSpecTest(unittest.TestCase):
    def skills(self):
        found = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(found), 5)
        return found

    def test_frontmatter_follows_agent_skills_spec(self):
        for path in self.skills():
            text = path.read_text(encoding="utf-8")
            m = re.match(r"---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(m, path)
            fm = yaml.safe_load(m.group(1))
            self.assertLessEqual(set(fm), SPEC_FIELDS, f"{path}: non-spec fields {set(fm) - SPEC_FIELDS}")
            self.assertEqual(fm["name"], path.parent.name)
            self.assertRegex(fm["name"], NAME_RE)
            self.assertLessEqual(len(fm["name"]), 64)
            self.assertTrue(0 < len(fm["description"]) <= 1024, path)
            self.assertLessEqual(len(fm.get("compatibility", "")), 500)
            for k, v in (fm.get("metadata") or {}).items():
                self.assertIsInstance(v, str, f"{path}: metadata.{k} must be a string")
            self.assertLess(len(text.splitlines()), 500, f"{path}: keep SKILL.md under 500 lines")

    def test_instructions_are_platform_neutral(self):
        # Claude-only names may appear only where the platform differences are explained.
        setup = PLUGIN / "skills" / "investment-setup"
        rules = setup / "references" / "operating-rules.md"
        for path in (PLUGIN / "skills").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if path != rules:
                self.assertNotIn("/investment-analyst:", text, f"{path}: name the skill, not a Claude command")
            if path not in (rules, setup / "SKILL.md"):
                self.assertNotIn("AskUserQuestion", text, f"{path}: say 'ask the user' (rules, section 8)")

    def test_relative_references_exist(self):
        # `references/x.md` and `../other-skill/...` paths in SKILL.md resolve from the skill folder.
        for path in self.skills():
            for ref in re.findall(r"`((?:\.\./[\w-]+/)?references/[\w.-]+\.md)`", path.read_text(encoding="utf-8")):
                self.assertTrue((path.parent / ref).is_file(), f"{path}: missing {ref}")


@unittest.skipUnless(ROOT, "not inside the plugin repository")
class ManifestTest(unittest.TestCase):
    def test_versions_match(self):
        versions = {str(p.relative_to(ROOT)): _json(p)["version"]
                    for p in (PLUGIN / ".claude-plugin" / "plugin.json", PLUGIN / ".cursor-plugin" / "plugin.json",
                              PLUGIN / "plugin.json")}
        versions["toolkit/iat/__init__.py"] = _toolkit_version()
        self.assertEqual(len(set(versions.values())), 1,
                         f"versions differ, run scripts/bump_version.py: {versions}")

    def test_marketplaces_point_at_the_plugin(self):
        claude = _json(ROOT / ".claude-plugin" / "marketplace.json")
        cursor = _json(ROOT / ".cursor-plugin" / "marketplace.json")
        codex = _json(ROOT / ".agents" / "plugins" / "marketplace.json")
        sources = [claude["plugins"][0]["source"], cursor["plugins"][0]["source"],
                   codex["plugins"][0]["source"]["path"]]
        for src in sources:
            self.assertEqual((ROOT / src).resolve(), PLUGIN.resolve())
        for entry in (claude["plugins"][0], cursor["plugins"][0], codex["plugins"][0]):
            self.assertEqual(entry["name"], "investment-analyst")
        self.assertIn("installation", codex["plugins"][0]["policy"])
        self.assertTrue(codex["plugins"][0]["category"])

    def test_open_standard_manifest(self):
        m = _json(PLUGIN / "plugin.json")
        self.assertEqual(m["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
                   "keywords", "extensions"}
        self.assertLessEqual(set(m), allowed)
        self.assertRegex(m["name"], r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

    def test_license_copies_match(self):
        self.assertEqual((ROOT / "LICENSE").read_text(encoding="utf-8"),
                         (PLUGIN / "toolkit" / "LICENSE").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
