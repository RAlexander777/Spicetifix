import io
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from spicetifix.core.utils import (
    add_to_user_path,
    close_spotify,
    ensure_adblock_extension,
    find_executable,
    get_installed_spicetify_version,
    get_latest_spicetify_version,
    get_spotify_version,
    get_user_config_path,
    parse_progress,
    run_cmd,
    run_spicetify,
    run_spicetify_apply,
    safe_basename,
    safe_extractall,
    safe_path_component,
    strip_ansi,
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


class TestTextHelpers(unittest.TestCase):
    def test_strip_ansi(self):
        self.assertEqual(strip_ansi("\x1b[32mOK\x1b[0m"), "OK")

    def test_parse_progress(self):
        self.assertAlmostEqual(parse_progress("[10/100] downloading"), 0.1)
        self.assertIsNone(parse_progress("no progress here"))
        self.assertIsNone(parse_progress("[5/0]"))


class TestRunCmd(unittest.TestCase):
    @patch("spicetifix.core.utils.subprocess.run")
    def test_returns_code_out_err(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="out", stderr="err")
        self.assertEqual(run_cmd(["echo", "hi"]), (0, "out", "err"))

    @patch("spicetifix.core.utils.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1))
    def test_timeout_is_reported(self, mock_run):
        code, out, _err = run_cmd(["x"])
        self.assertEqual((code, out), (-1, ""))

    @patch("spicetifix.core.utils.subprocess.run", side_effect=FileNotFoundError())
    def test_missing_binary_is_reported(self, mock_run):
        code, _out, err = run_cmd(["nope"])
        self.assertEqual(code, -1)
        self.assertIn("nope", err)


class TestRunSpicetify(unittest.TestCase):
    @patch("spicetifix.core.utils.run_cmd")
    @patch("spicetifix.core.utils.find_executable", return_value=None)
    def test_missing_exe_does_not_run(self, mock_find, mock_cmd):
        code, _out, _err = run_spicetify(["apply"])
        self.assertEqual(code, -1)
        mock_cmd.assert_not_called()

    @patch("spicetifix.core.utils.run_cmd", return_value=(0, "ok", ""))
    @patch("spicetifix.core.utils.find_executable", return_value="C:/sp.exe")
    def test_forwards_args_to_run_cmd(self, mock_find, mock_cmd):
        self.assertEqual(run_spicetify(["apply"]), (0, "ok", ""))
        mock_cmd.assert_called_once_with(["C:/sp.exe", "apply"], timeout=300)


class TestRunSpicetifyApply(unittest.TestCase):
    @patch("spicetifix.core.utils.run_spicetify")
    def test_succeeds_after_falling_back(self, mock_run):
        mock_run.side_effect = [(1, "", "a"), (1, "", "b"), (0, "ok", "")]
        self.assertEqual(run_spicetify_apply(), (0, "ok", ""))

    @patch("spicetifix.core.utils.run_spicetify")
    def test_returns_last_failure(self, mock_run):
        mock_run.side_effect = [(1, "", "a"), (1, "", "b"), (1, "", "c")]
        self.assertEqual(run_spicetify_apply(), (1, "", "c"))


class TestFindExecutable(unittest.TestCase):
    @patch("spicetifix.core.utils.get_spicetify_dir")
    @patch("spicetifix.core.utils.shutil.which", return_value="C:/bin/spicetify.exe")
    def test_prefers_path_lookup(self, mock_which, mock_dir):
        self.assertEqual(find_executable("spicetify"), "C:/bin/spicetify.exe")
        mock_dir.assert_not_called()

    @patch("spicetifix.core.utils.get_spicetify_dir")
    @patch("spicetifix.core.utils.shutil.which", return_value=None)
    def test_falls_back_to_spicetify_dir(self, mock_which, mock_dir):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "spicetify.exe").write_text("x", encoding="utf-8")
            mock_dir.return_value = Path(tmp)
            self.assertTrue(str(find_executable("spicetify")).endswith("spicetify.exe"))

    @patch("spicetifix.core.utils.get_spicetify_dir")
    @patch("spicetifix.core.utils.shutil.which", return_value=None)
    def test_none_when_missing(self, mock_which, mock_dir):
        with tempfile.TemporaryDirectory() as tmp:
            mock_dir.return_value = Path(tmp)
            self.assertIsNone(find_executable("spicetify"))


class TestCloseSpotify(unittest.TestCase):
    @patch("spicetifix.core.utils.run_cmd")
    def test_kills_all_known_processes(self, mock_cmd):
        close_spotify()
        killed = [call.args[0][3] for call in mock_cmd.call_args_list]
        self.assertIn("Spotify.exe", killed)
        self.assertGreaterEqual(len(killed), 3)


class TestGetSpotifyVersion(unittest.TestCase):
    @patch("spicetifix.core.utils.get_prefs_path")
    def test_reads_last_launched_version(self, mock_prefs):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "prefs"
            p.write_text('app.last-launched-version="1.2.3.4"\n', encoding="utf-8")
            mock_prefs.return_value = str(p)
            self.assertEqual(get_spotify_version(), "1.2.3.4")

    @patch("spicetifix.core.utils.get_prefs_path")
    def test_empty_when_prefs_missing(self, mock_prefs):
        with tempfile.TemporaryDirectory() as tmp:
            mock_prefs.return_value = str(Path(tmp) / "nope")
            self.assertEqual(get_spotify_version(), "")


class TestUserConfigPath(unittest.TestCase):
    @patch.dict("os.environ", {"APPDATA": "C:/Users/x/AppData/Roaming"})
    def test_uses_appdata(self):
        p = str(get_user_config_path()).replace("\\", "/")
        self.assertTrue(p.endswith("Spicetifix/spicetifix.yaml"))


class TestAddToUserPath(unittest.TestCase):
    @patch("spicetifix.core.utils.sys")
    def test_non_windows_is_a_noop_success(self, mock_sys):
        mock_sys.platform = "linux"
        self.assertTrue(add_to_user_path("C:/whatever"))


class TestEnsureAdblockExtension(unittest.TestCase):
    @patch("requests.get")
    @patch("spicetifix.core.utils.get_spicetify_extensions_dir")
    def test_downloads_when_missing(self, mock_dir, mock_get):
        with tempfile.TemporaryDirectory() as tmp:
            mock_dir.return_value = Path(tmp)
            resp = MagicMock()
            resp.content = b"/*js*/"
            mock_get.return_value = resp
            self.assertTrue(ensure_adblock_extension())
            self.assertEqual((Path(tmp) / "adblock.js").read_bytes(), b"/*js*/")

    @patch("requests.get")
    @patch("spicetifix.core.utils.get_spicetify_extensions_dir")
    def test_skips_when_present(self, mock_dir, mock_get):
        with tempfile.TemporaryDirectory() as tmp:
            mock_dir.return_value = Path(tmp)
            (Path(tmp) / "adblock.js").write_bytes(b"already here")
            self.assertTrue(ensure_adblock_extension())
            mock_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
