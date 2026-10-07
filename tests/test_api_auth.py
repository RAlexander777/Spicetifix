import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spicetifix import api


def _make_handler(headers=None):
    h = object.__new__(api.SpicetifixAPIHandler)
    h.headers = headers or {}
    h.request = None
    h.client_address = ("127.0.0.1", 1234)
    return h


class TestApiAuth(unittest.TestCase):
    def setUp(self):
        api.set_auth_token("test-secret-token")

    def tearDown(self):
        api.set_auth_token("")

    def test_authorized_with_valid_token(self):
        h = _make_handler({"X-Auth-Token": "test-secret-token"})
        self.assertTrue(h._is_authorized())

    def test_unauthorized_with_wrong_token(self):
        h = _make_handler({"X-Auth-Token": "wrong-token"})
        self.assertFalse(h._is_authorized())

    def test_unauthorized_without_token(self):
        h = _make_handler({})
        self.assertFalse(h._is_authorized())

    def test_open_when_no_token_configured(self):
        api.set_auth_token("")
        h = _make_handler({})
        self.assertTrue(h._is_authorized())


class TestStaticFileTraversal(unittest.TestCase):
    def test_index_resolves(self):
        path = api._resolve_static_file("/")
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "index.html")

    def test_normal_asset_resolves(self):
        path = api._resolve_static_file("/app.js")
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "app.js")

    def test_traversal_rejected(self):
        self.assertIsNone(api._resolve_static_file("/../../../../Windows/win.ini"))

    def test_encoded_traversal_rejected(self):
        self.assertIsNone(api._resolve_static_file("/%2e%2e/%2e%2e/Windows/win.ini"))

    def test_absolute_path_rejected(self):
        self.assertIsNone(api._resolve_static_file("/C:/Windows/win.ini"))

    def test_unknown_file_returns_none(self):
        self.assertIsNone(api._resolve_static_file("/no_such_file_12345"))


class TestApiWorkingState(unittest.TestCase):
    def setUp(self):
        self._was_working = api._is_working
        self._logs = api._install_logs
        self._progress = api._install_progress
        api._is_working = False
        api._install_logs = []
        api._install_progress = 0.0

    def tearDown(self):
        api._is_working = self._was_working
        api._install_logs = self._logs
        api._install_progress = self._progress

    def test_begin_work_claims_slot(self):
        self.assertTrue(api._begin_work())
        self.assertFalse(api._begin_work())

    def test_end_work_releases_slot(self):
        api._begin_work()
        api._append_log("step 1")
        api._set_progress(0.5)
        api._end_work()
        self.assertTrue(api._begin_work())

    def test_begin_work_resets_logs_and_progress(self):
        api._append_log("old")
        api._set_progress(0.9)
        api._begin_work()
        is_working, progress, logs = api._get_state()
        self.assertTrue(is_working)
        self.assertEqual(progress, 0.0)
        self.assertEqual(logs, [])

    def test_get_state_returns_snapshot(self):
        api._begin_work()
        api._append_log("a")
        api._set_progress(0.3)
        is_working, progress, logs = api._get_state()
        self.assertTrue(is_working)
        self.assertEqual(progress, 0.3)
        self.assertEqual(logs, ["a"])


class TestEnrichCatalogItem(unittest.TestCase):
    def _patch_dirs(self, tmp):
        return patch.multiple(
            "spicetifix.core.utils",
            get_spicetify_extensions_dir=lambda: Path(tmp) / "Extensions",
            get_spicetify_themes_dir=lambda: Path(tmp) / "Themes",
            get_spicetify_custom_apps_dir=lambda: Path(tmp) / "CustomApps",
        )

    def test_app_installed_when_folder_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "CustomApps" / "My App").mkdir(parents=True)
            with self._patch_dirs(tmp), \
                 patch("spicetifix.core.config.load_user_config",
                       return_value={"extensions": [], "custom_apps": []}):
                item = api._enrich_catalog_item({"type": "app", "filename": "My App"})
        self.assertTrue(item["installed"])

    def test_app_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_dirs(tmp), \
                 patch("spicetifix.core.config.load_user_config",
                       return_value={"extensions": [], "custom_apps": []}):
                item = api._enrich_catalog_item({"type": "app", "filename": "Nope"})
        self.assertFalse(item["installed"])

    def test_app_installed_when_listed_in_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_dirs(tmp), \
                 patch("spicetifix.core.config.load_user_config",
                       return_value={"extensions": [], "custom_apps": ["Nope"]}):
                item = api._enrich_catalog_item({"type": "app", "filename": "Nope"})
        self.assertTrue(item["installed"])

    def test_install_meta_attached_to_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_dirs(tmp), \
                 patch("spicetifix.core.config.load_user_config",
                       return_value={
                           "extensions": [], "custom_apps": [],
                           "installed_meta": {"extension:x.js": {"user": "u", "repo": "r", "tag": "v2"}},
                       }):
                item = api._enrich_catalog_item({"type": "extension", "filename": "x.js"})
        self.assertEqual(item["meta"]["tag"], "v2")

    def test_meta_none_when_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_dirs(tmp), \
                 patch("spicetifix.core.config.load_user_config",
                       return_value={"extensions": [], "custom_apps": []}):
                item = api._enrich_catalog_item({"type": "extension", "filename": "x.js"})
        self.assertIsNone(item["meta"])


if __name__ == "__main__":
    unittest.main()
