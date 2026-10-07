import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from spicetifix.api import make_server, set_auth_token

TOKEN = "marketplace-test-token"
PORT = 8801


class FakeResponse:
    def __init__(self, content=b"/* js */", status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
        return None


class TestMarketplaceInstall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        set_auth_token(TOKEN)
        cls.server = make_server(port=PORT, auth_token=TOKEN, idle_timeout=60)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        set_auth_token("")
        cls.server.shutdown()

    def _post(self, path, body):
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Auth-Token": TOKEN},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def _patch_env(self, tmpdir):
        # Point every spicetify path at the temp dir
        def fake_dir():
            return Path(tmpdir)

        return patch.multiple(
            "spicetifix.core.utils",
            get_spicetify_extensions_dir=fake_dir,
            get_spicetify_dir=fake_dir,
            get_spicetify_themes_dir=fake_dir,
            run_spicetify=lambda *a, **k: (0, "", ""),
            close_spotify=lambda *a, **k: None,
        )

    def test_install_extension_with_subfolder_is_flattened(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_env(tmpdir), \
                 patch("requests.get", return_value=FakeResponse()), \
                 patch("spicetifix.api.save_user_config"), \
                 patch("spicetifix.api._launch_spotify"), \
                 patch("spicetifix.core.config.write_spicetify_config"), \
                 patch("spicetifix.core.config.repair_backup_metadata"), \
                 patch("spicetifix.api.load_user_config", return_value={"extensions": []}):
                res = self._post("/api/marketplace/install", {
                    "type": "extension",
                    "filename": "adblock/adblock.js",
                    "url": "https://raw.githubusercontent.com/rxri/spicetify-extensions/main/adblock/adblock.js",
                })
            self.assertEqual(res.get("status"), "ok")
            target = Path(tmpdir) / "adblock.js"
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), b"/* js */")
            self.assertFalse((Path(tmpdir) / "adblock").exists())

    def test_install_extension_top_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_env(tmpdir), \
                 patch("requests.get", return_value=FakeResponse()), \
                 patch("spicetifix.api.save_user_config"), \
                 patch("spicetifix.api._launch_spotify"), \
                 patch("spicetifix.core.config.write_spicetify_config"), \
                 patch("spicetifix.core.config.repair_backup_metadata"), \
                 patch("spicetifix.api.load_user_config", return_value={"extensions": []}):
                res = self._post("/api/marketplace/install", {
                    "type": "extension",
                    "filename": "bookmark.js",
                    "url": "https://raw.githubusercontent.com/x/y/main/bookmark.js",
                })
            self.assertEqual(res.get("status"), "ok")
            self.assertTrue((Path(tmpdir) / "bookmark.js").exists())

    def test_versions_endpoint_returns_resolved(self):
        with patch(
            "spicetifix.core.marketplace_fetcher.resolve_versions",
            return_value={"a/b": {"tag": "v1.0.0", "updated_at": "2026-01-01T00:00:00Z"}},
        ) as mock_resolve:
            res = self._post("/api/marketplace/versions", {
                "repos": [{"user": "a", "repo": "b"}, {"user": "", "repo": "ignored"}],
            })
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res["versions"]["a/b"]["tag"], "v1.0.0")
        # entries without user/repo are dropped before resolving
        passed = mock_resolve.call_args[0][0]
        self.assertEqual(passed, [{"user": "a", "repo": "b", "updated_at": ""}])

    def test_versions_endpoint_handles_empty(self):
        with patch("spicetifix.core.marketplace_fetcher.resolve_versions", return_value={}):
            res = self._post("/api/marketplace/versions", {"repos": []})
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res["versions"], {})

    def test_open_spotify_is_throttled(self):
        with patch("os.startfile") as mock_start:
            first = self._post("/api/open/spotify", {})
            second = self._post("/api/open/spotify", {})
        self.assertEqual(first.get("status"), "ok")
        self.assertTrue(second.get("throttled"))
        self.assertEqual(mock_start.call_count, 1)


if __name__ == "__main__":
    unittest.main()
