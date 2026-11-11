import json
import re
import unittest
from pathlib import Path

import spicetifix

ROOT = Path(__file__).resolve().parent.parent


class TestVersionConsistency(unittest.TestCase):
    """The version lives in several files; a release must never ship them out of
    sync. ``spicetifix.__version__`` is the single source of truth."""

    def test_pyproject_matches_dunder(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
        self.assertIsNotNone(match, "version not found in pyproject.toml")
        self.assertEqual(match.group(1), spicetifix.__version__)

    def test_changelog_latest_entry_matches(self):
        data = json.loads((ROOT / "web" / "changelog.json").read_text(encoding="utf-8"))
        self.assertEqual(data[0]["version"], spicetifix.__version__)

    def test_index_html_placeholder_matches(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"v{spicetifix.__version__}", html)


if __name__ == "__main__":
    unittest.main()
