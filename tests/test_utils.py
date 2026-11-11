import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from spicetifix.core.utils import (
    get_installed_spicetify_version,
    get_latest_spicetify_version,
    safe_basename,
    safe_extractall,
    safe_path_component,
)


class TestSafeExtractall(unittest.TestCase):
    def test_skips_escaping_members(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("ok.txt", "ok")
            zf.writestr("../escape.txt", "bad")
            zf.writestr("sub/../escape2.txt", "bad")
        buf.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out"
            with zipfile.ZipFile(buf) as zf:
                safe_extractall(zf, dest)
            self.assertEqual((dest / "ok.txt").read_text(encoding="utf-8"), "ok")
            self.assertFalse((Path(tmp) / "escape.txt").exists())
            self.assertFalse((Path(tmp) / "escape2.txt").exists())


class TestSafeBasename(unittest.TestCase):
    def test_flattens_subfolders(self):
        self.assertEqual(safe_basename("adblock/adblock.js"), "adblock.js")
        self.assertEqual(safe_basename("..\\..\\evil.js"), "evil.js")
        self.assertEqual(safe_basename("/abs/x.js"), "x.js")

    def test_rejects_empty_and_dots(self):
        for bad in ("", "   ", ".", "..", ".../.."):
            with self.assertRaises(ValueError):
                safe_basename(bad)

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            safe_basename(None)


class TestSafePathComponent(unittest.TestCase):
    def test_accepts_plain_names(self):
        self.assertEqual(safe_path_component("adblock.js"), "adblock.js")
        self.assertEqual(safe_path_component("MyTheme"), "MyTheme")
        self.assertEqual(safe_path_component("  spaced  "), "spaced")

    def test_rejects_traversal(self):
        for bad in ("..", "../evil", "..\\evil", "a/b", "a\\b", "/abs", "C:\\x", "", "   ", "."):
            with self.assertRaises(ValueError):
                safe_path_component(bad)

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            safe_path_component(None)


class TestSpicetifyVersionHelpers(unittest.TestCase):
    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_parses_bare_output(self, mock_run):
        mock_run.return_value = (0, "2.45.1\n", "")
        self.assertEqual(get_installed_spicetify_version(), "2.45.1")

    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_parses_prefixed_output(self, mock_run):
        mock_run.return_value = (0, "spicetify v2.45.3\n", "")
        self.assertEqual(get_installed_spicetify_version(), "2.45.3")

    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_empty_on_failure(self, mock_run):
        mock_run.return_value = (1, "", "not found")
        self.assertEqual(get_installed_spicetify_version(), "")

    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_empty_on_garbage(self, mock_run):
        mock_run.return_value = (0, "no version here", "")
        self.assertEqual(get_installed_spicetify_version(), "")

    @patch("requests.get")
    def test_latest_version_from_api(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"tag_name": "v2.45.3"}
        mock_get.return_value = resp
        self.assertEqual(get_latest_spicetify_version(), "2.45.3")

    @patch("requests.get")
    def test_latest_version_falls_back_to_redirect(self, mock_get):
        api_resp = MagicMock()
        api_resp.status_code = 500
        redirect_resp = MagicMock()
        redirect_resp.url = "https://github.com/spicetify/cli/releases/tag/v2.45.3"
        mock_get.side_effect = [api_resp, redirect_resp]
        self.assertEqual(get_latest_spicetify_version(), "2.45.3")

    @patch("requests.get")
    def test_latest_version_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("offline")
        self.assertEqual(get_latest_spicetify_version(), "")


if __name__ == "__main__":
    unittest.main()
