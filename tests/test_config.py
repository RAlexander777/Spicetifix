import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from spicetifix.core.config import (
    get_installed_extensions,
    get_installed_custom_apps,
    load_user_config,
    save_user_config,
    write_spicetify_config,
    repair_backup_metadata,
    _default_config,
    _merge_live_entries,
)


class TestConfigExtensionDetection(unittest.TestCase):
    @patch("spicetifix.core.utils.get_spicetify_extensions_dir")
    def test_get_installed_extensions(self, mock_ext_dir):
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True

        file1 = MagicMock(spec=Path)
        file1.is_file.return_value = True
        file1.suffix = ".js"
        file1.name = "marketplace.js"

        file2 = MagicMock(spec=Path)
        file2.is_file.return_value = True
        file2.suffix = ".mjs"
        file2.name = "trashbin.mjs"

        mock_dir.iterdir.return_value = [file1, file2]
        mock_ext_dir.return_value = mock_dir

        exts = get_installed_extensions()
        self.assertIn("marketplace.js", exts)
        self.assertIn("trashbin.mjs", exts)
        self.assertEqual(len(exts), 2)

    @patch("spicetifix.core.utils.get_spicetify_extensions_dir")
    def test_get_installed_extensions_flattens_subfolders(self, mock_ext_dir):
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True

        subfolder = MagicMock(spec=Path)
        subfolder.is_file.return_value = False
        subfolder.is_dir.return_value = True
        subfolder.name = "adblock"

        nested_file = MagicMock(spec=Path)
        nested_file.is_file.return_value = True
        nested_file.suffix = ".js"
        nested_file.name = "adblock.js"

        subfolder.iterdir.return_value = [nested_file]
        mock_dir.iterdir.return_value = [subfolder]
        mock_ext_dir.return_value = mock_dir

        exts = get_installed_extensions()
        self.assertEqual(exts, ["adblock.js"])

    @patch("spicetifix.core.config.get_installed_extensions")
    @patch("spicetifix.core.config.get_user_config_path")
    @patch("spicetifix.core.config.read_spicetify_config", return_value=None)
    def test_load_user_config_auto_detects(self, mock_read, mock_path, mock_get_installed):
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file

        mock_get_installed.return_value = ["marketplace.js", "bookmark.js"]

        cfg = load_user_config()
        self.assertEqual(cfg["extensions"], ["marketplace.js", "bookmark.js"])


class TestMergeLiveEntries(unittest.TestCase):
    def setUp(self):
        self.live = {
            "AdditionalOptions": {
                "extensions": "popupLyrics.js|adblock.js|externalApp.js",
                "custom_apps": "marketplace|lyrics-plus",
            }
        }
        self.disk_exts = {"popupLyrics.js", "adblock.js", "externalApp.js"}
        self.disk_apps = {"marketplace", "lyrics-plus"}

    def test_preserves_external_entries_not_in_yaml(self):
        with patch("spicetifix.core.config.read_spicetify_config", return_value=self.live), \
             patch("spicetifix.core.config.get_installed_extensions", return_value=list(self.disk_exts)), \
             patch("spicetifix.core.config.get_installed_custom_apps", return_value=list(self.disk_apps)):
            cfg = _merge_live_entries({"extensions": ["adblock.js"], "custom_apps": []})
        self.assertEqual(
            set(cfg["extensions"]),
            {"adblock.js", "popupLyrics.js", "externalApp.js"},
        )
        self.assertEqual(set(cfg["custom_apps"]), {"marketplace", "lyrics-plus"})

    def test_drops_live_entry_whose_file_was_removed(self):
        disk_exts = self.disk_exts - {"externalApp.js"}
        with patch("spicetifix.core.config.read_spicetify_config", return_value=self.live), \
             patch("spicetifix.core.config.get_installed_extensions", return_value=list(disk_exts)), \
             patch("spicetifix.core.config.get_installed_custom_apps", return_value=list(self.disk_apps)):
            cfg = _merge_live_entries({"extensions": [], "custom_apps": []})
        self.assertNotIn("externalApp.js", cfg["extensions"])

    def test_keeps_yaml_entries_and_avoids_duplicates(self):
        with patch("spicetifix.core.config.read_spicetify_config", return_value=self.live), \
             patch("spicetifix.core.config.get_installed_extensions", return_value=list(self.disk_exts)), \
             patch("spicetifix.core.config.get_installed_custom_apps", return_value=list(self.disk_apps)):
            cfg = _merge_live_entries({"extensions": ["popupLyrics.js"], "custom_apps": []})
        self.assertEqual(cfg["extensions"].count("popupLyrics.js"), 1)

    def test_no_live_config_returns_yaml_unchanged(self):
        with patch("spicetifix.core.config.read_spicetify_config", return_value=None):
            cfg = _merge_live_entries({"extensions": ["a.js"], "custom_apps": []})
        self.assertEqual(cfg["extensions"], ["a.js"])


class TestLoadUserConfigMergesLiveEntries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.yaml_path = Path(self.tmp.name) / "spicetify.yaml"
        self.yaml_path.write_text(
            "language: en\n"
            "ui_theme: emerald\n"
            "spicetify:\n"
            "  theme: text\n"
            "  color_scheme: ''\n"
            "  spotify_launch_flags: --no-update\n"
            "extensions:\n"
            "  - autoSkipVideo.js\n"
            "custom_apps:\n"
            "  - marketplace\n",
            encoding="utf-8",
        )
        self.live = {
            "AdditionalOptions": {
                "extensions": "autoSkipVideo.js|lyrics-overlay.js",
                "custom_apps": "marketplace|lyrics-plus",
            }
        }

    def test_load_user_config_reflects_live_config_entries(self):
        with patch("spicetifix.core.config.get_user_config_path", return_value=self.yaml_path), \
             patch("spicetifix.core.config.get_installed_extensions",
                   return_value=["autoSkipVideo.js", "lyrics-overlay.js"]), \
             patch("spicetifix.core.config.get_installed_custom_apps",
                   return_value=["marketplace", "lyrics-plus"]), \
             patch("spicetifix.core.config.read_spicetify_config", return_value=self.live):
            cfg = load_user_config()
        self.assertIn("lyrics-overlay.js", cfg["extensions"])
        self.assertIn("lyrics-plus", cfg["custom_apps"])


class TestWriteSpicetifyConfigPreservesSections(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sp_dir = Path(self.tmp.name) / "spicetify"
        self.sp_dir.mkdir()
        self.cfg_path = self.sp_dir / "config-xpui.ini"
        self.cfg_path.write_text(
            "[Setting]\n"
            "spotify_path=C:\\Spotify\n"
            "prefs_path=C:\\prefs\n"
            "current_theme=text\n"
            "color_scheme=\n"
            "inject_css=1\n"
            "inject_theme_js=0\n"
            "replace_colors=1\n"
            "overwrite_assets=0\n"
            "spotify_launch_flags=--no-update\n"
            "always_enable_devtools=0\n"
            "check_spicetify_update=0\n"
            "[Preprocesses]\n"
            "disable_sentry=1\n"
            "disable_ui_logging=1\n"
            "remove_rtl_rule=1\n"
            "expose_apis=1\n"
            "[AdditionalOptions]\n"
            "extensions=autoSkipVideo.js\n"
            "custom_apps=marketplace\n"
            "sidebar_config=1\n"
            "home_config=1\n"
            "experimental_features=1\n"
            "[Patch]\n"
            "xpui=9a9a9a9a\n"
            "[Backup]\n"
            "version=2.44.0\n",
            encoding="utf-8",
        )
        self.cfg = {
            "spicetify": {"theme": "text", "color_scheme": "", "spotify_launch_flags": ""},
            "extensions": ["autoSkipVideo.js"],
            "custom_apps": ["marketplace"],
            "preprocesses": {},
            "options": {},
        }

    def _patched_write(self, cfg, **kwargs):
        with patch("spicetifix.core.config.get_spicetify_config_dir", return_value=self.sp_dir), \
             patch("spicetifix.core.config.get_spotify_path", return_value=Path("C:/Spotify")), \
             patch("spicetifix.core.config.get_prefs_path", return_value=Path("C:/prefs")), \
             patch("spicetifix.core.config._merge_live_entries", side_effect=lambda c: c):
            write_spicetify_config(cfg, **kwargs)

    def test_preserves_patch_and_backup_sections(self):
        self._patched_write(self.cfg)
        content = self.cfg_path.read_text(encoding="utf-8")
        self.assertIn("[Patch]", content)
        self.assertIn("9a9a9a9a", content)
        self.assertIn("[Backup]", content)
        self.assertIn("2.44.0", content)

    def test_merge_live_false_does_not_rea_add_removed_entry(self):
        removed = dict(self.cfg)
        removed["extensions"] = []
        self._patched_write(removed, merge_live=False)
        content = self.cfg_path.read_text(encoding="utf-8")
        self.assertNotIn("autoSkipVideo.js", content.split("[AdditionalOptions]")[1])
        self.assertIn("[Patch]", content)
        self.assertIn("[Backup]", content)


class TestRepairBackupMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sp_dir = Path(self.tmp.name) / "spicetify"
        self.sp_dir.mkdir()
        self.cfg_path = self.sp_dir / "config-xpui.ini"
        self.backup_dir = self.sp_dir / "Backup"
        self.backup_dir.mkdir()
        (self.backup_dir / "xpui.spa").write_bytes(b"x")

    def _write_cfg(self, has_backup):
        body = (
            "[Setting]\n"
            "spotify_path=C:\\Spotify\n"
            "prefs_path=C:\\prefs\n"
            "current_theme=text\n"
            "color_scheme=\n"
            "[Preprocesses]\n"
            "disable_sentry=1\n"
            "[AdditionalOptions]\n"
            "extensions=autoSkipVideo.js\n"
            "custom_apps=marketplace\n"
            "sidebar_config=1\n"
            "home_config=1\n"
            "experimental_features=1\n"
        )
        if has_backup:
            body += "[Backup]\nversion=1.2.3\nwith=2.44.0\n"
        self.cfg_path.write_text(body, encoding="utf-8")

    @patch("spicetifix.core.config.get_spicetify_config_path")
    @patch("spicetifix.core.utils.get_spicetify_dir")
    @patch("spicetifix.core.utils.get_spotify_version")
    def test_creates_backup_section_when_missing(self, mock_ver, mock_dir, mock_path):
        self._write_cfg(has_backup=False)
        mock_path.return_value = self.cfg_path
        mock_dir.return_value = self.sp_dir
        mock_ver.return_value = "1.2.97.270.ge94a76a2"
        result = repair_backup_metadata()
        content = self.cfg_path.read_text(encoding="utf-8")
        self.assertTrue(result)
        self.assertIn("[Backup]", content)
        self.assertIn("1.2.97.270.ge94a76a2", content)

    @patch("spicetifix.core.config.get_spicetify_config_path")
    def test_skips_when_backup_section_exists(self, mock_path):
        self._write_cfg(has_backup=True)
        mock_path.return_value = self.cfg_path
        result = repair_backup_metadata()
        self.assertFalse(result)
        self.assertIn("1.2.3", self.cfg_path.read_text(encoding="utf-8"))

    @patch("spicetifix.core.config.get_spicetify_config_path")
    @patch("spicetifix.core.utils.get_spicetify_dir")
    def test_skips_when_no_backup_files(self, mock_dir, mock_path):
        self._write_cfg(has_backup=False)
        (self.backup_dir / "xpui.spa").unlink()
        self.backup_dir.rmdir()
        mock_path.return_value = self.cfg_path
        mock_dir.return_value = self.sp_dir
        result = repair_backup_metadata()
        self.assertFalse(result)
        self.assertNotIn("[Backup]", self.cfg_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
