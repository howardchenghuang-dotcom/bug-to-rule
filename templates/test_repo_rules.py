"""Repo-wide rules. Each one is a bug we already paid for, turned into a check.

Copy to tests/test_repo_rules.py and keep only the rules that match a real
incident in your project. Add an exception to a rule's allowlist with the
reason it is safe; never loosen the pattern.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"tests", "__pycache__", ".git", "node_modules", ".venv", "venv", "build", "dist"}


def source_files() -> list[Path]:
    return [p for p in ROOT.rglob("*.py") if not SKIP_DIRS.intersection(p.relative_to(ROOT).parts)]


def hits(pattern: str, files: list[Path]) -> list[str]:
    rx = re.compile(pattern)
    out = []
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if rx.search(line):
                out.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()}")
    return out


def without(found: list[str], allow: dict[str, str]) -> list[str]:
    return [h for h in found if not any(h.startswith(k + ":") for k in allow)]


class ScanSeesCode(unittest.TestCase):
    """If the walk breaks, every rule below passes silently."""

    def test_walk_finds_known_files(self):
        files = {str(p.relative_to(ROOT)) for p in source_files()}
        self.assertGreater(len(files), 5)
        # self.assertIn("app/main.py", files)   # name two files you know exist


class TimeRules(unittest.TestCase):
    """Example: naive local timestamps were treated as UTC and orders were
    judged hours early or late (YYYY-MM-DD)."""

    ALLOW = {
        # "scripts/legacy_export.py": "format is fixed by the partner and really is UTC",
    }

    def test_naive_local_time_not_pinned_to_utc(self):
        found = hits(r"\.replace\(\s*tzinfo\s*=\s*(timezone\.)?(utc|UTC)\b", source_files())
        self.assertEqual(without(found, self.ALLOW), [],
                         "attach the real local zone with the project's helper instead")

    def test_no_wall_clock_glued_to_z(self):
        found = hits(r"""\[:19\]\s*\+\s*['"]Z['"]""", source_files())
        self.assertEqual(found, [], "a local wall clock + 'Z' is not UTC")


class StateOutsideTmp(unittest.TestCase):
    """Example: /tmp is cleared on reboot; cooldowns and health markers were
    lost and alerts started over (YYYY-MM-DD)."""

    ALLOW: dict[str, str] = {}

    def test_no_state_files_in_tmp(self):
        found = hits(r"""['"]/tmp/[^'"]*\.(json|sqlite|db)['"]""", source_files())
        self.assertEqual(without(found, self.ALLOW), [], "keep state in a persistent directory")


class TestsStayOffProduction(unittest.TestCase):
    """Example: tests locked the production lock file and either failed while
    the cron ran or blocked the cron (YYYY-MM-DD)."""

    PROD_PREFIX = "/tmp/myapp_"   # change to your production path prefix

    def test_tests_do_not_use_production_paths(self):
        tests = [p for p in (ROOT / "tests").glob("*.py") if p.name != Path(__file__).name]
        found = hits(r"""['"]""" + re.escape(self.PROD_PREFIX), tests)
        self.assertEqual(found, [], "use tempfile.mkdtemp() in tests")


if __name__ == "__main__":
    unittest.main()
