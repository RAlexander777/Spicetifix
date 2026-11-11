import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from spicetifix.api import make_server, set_auth_token

TOKEN = "endpoints-test-token"
PORT = 8802


class TestApiEndpoints(unittest.TestCase):
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

    def setUp(self):
        # Deterministic language regardless of the machine's real config.
        p = patch("spicetifix.api.get_language", return_value="en")
        p.start()
        self.addCleanup(p.stop)

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}{path}",
            data=data,
            headers={"Content-Type": "application/json", "X-Auth-Token": TOKEN},
            method=method,
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_status_returns_core_fields(self):
        with patch("spicetifix.api.load_user_config", return_value={"language": "en"}), \
             patch("spicetifix.api.check_config_health",
                   return_value=[{"label": "config_file", "ok": True, "detail": "x"}]), \
             patch("spicetifix.api.read_spicetify_config", return_value=None), \
             patch("spicetifix.api.spotify_control.get_spotify_now_playing",
                   return_value={"playing": False, "artist": "Spotify", "title": "np", "raw": ""}):
            status, body = self._req("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertTrue(body["version"])
        self.assertEqual(body["current_theme"], "None")
        self.assertEqual(body["health"][0]["label"], "config_file")
        self.assertEqual(body["config"]["language"], "en")
        for key in ("is_working", "progress", "logs", "now_playing"):
            self.assertIn(key, body)

    def test_themes_lists_ui_and_spicetify_themes(self):
        with patch("spicetifix.api.list_available_themes", return_value=["text"]), \
             patch("spicetifix.api.load_user_config", return_value={"ui_theme": "emerald"}):
            status, body = self._req("GET", "/api/themes")
        self.assertEqual(status, 200)
        self.assertEqual(body["spicetify_themes"], ["text"])
        self.assertIn("emerald", body["ui_themes"])
        self.assertEqual(body["current_ui_theme"], "emerald")

    def test_extensions_merges_detected_and_user(self):
        with patch("spicetifix.api.load_user_config",
                   return_value={"extensions": ["adblock.js"], "custom_apps": []}), \
             patch("spicetifix.api.get_installed_extensions", return_value=["adblock.js", "x.js"]), \
             patch("spicetifix.api.get_installed_custom_apps", return_value=[]):
            status, body = self._req("GET", "/api/extensions")
        self.assertEqual(status, 200)
        names = {e["name"] for e in body["extensions"]}
        self.assertEqual(names, {"adblock.js", "x.js"})
        self.assertTrue(next(e for e in body["extensions"] if e["name"] == "adblock.js")["enabled"])

    def test_config_save_persists_language_and_theme(self):
        with patch("spicetifix.api.load_user_config", return_value={"language": "en"}), \
             patch("spicetifix.core.config.write_spicetify_config") as mock_write, \
             patch("spicetifix.api.save_user_config") as mock_save:
            status, body = self._req(
                "POST", "/api/config/save", {"language": "es", "ui_theme": "dracula"}
            )
        self.assertEqual(status, 200)
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved["language"], "es")
        self.assertEqual(saved["ui_theme"], "dracula")
        # The config must reach config-xpui.ini (regression: a wrong module path
        # made this call silently never happen).
        self.assertTrue(mock_write.called)

    def test_player_returns_now_playing(self):
        playing = {"playing": True, "artist": "a", "title": "t", "raw": "a - t"}
        with patch("spicetifix.api.spotify_control.play_pause"), \
             patch("spicetifix.api.spotify_control.get_spotify_now_playing", return_value=playing):
            status, body = self._req("POST", "/api/player", {"action": "play_pause"})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["now_playing"]["playing"])

    def test_marketplace_install_missing_params_is_400(self):
        status, body = self._req("POST", "/api/marketplace/install", {"type": "extension"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "Invalid parameters")

    def test_marketplace_install_rejects_traversal_filename(self):
        body = {"type": "theme", "filename": "../../evil", "url": "http://x/y.css"}
        status, resp = self._req("POST", "/api/marketplace/install", body)
        self.assertEqual(status, 400)
        self.assertEqual(resp["error"], "Invalid parameters")

    def test_marketplace_uninstall_rejects_traversal_filename(self):
        body = {"type": "theme", "filename": "..\\..\\evil"}
        status, resp = self._req("POST", "/api/marketplace/uninstall", body)
        self.assertEqual(status, 400)
        self.assertEqual(resp["error"], "Invalid parameters")

    def test_open_folder_unknown_target_is_404(self):
        status, body = self._req("POST", "/api/open/folder", {"target": "nope"})
        self.assertEqual(status, 404)

    def test_open_external_rejects_non_http(self):
        status, body = self._req("POST", "/api/open/external", {"url": "ftp://example.com"})
        self.assertEqual(status, 400)

    def test_backup_import_rejects_disallowed_path(self):
        status, body = self._req("POST", "/api/backup/import", {"zip_path": "C:/Windows/win.ini"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "Invalid parameters")

    def test_unknown_post_endpoint_is_404(self):
        status, body = self._req("POST", "/api/does-not-exist", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
