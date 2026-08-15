import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from spicetifix.core.config import (
    get_installed_extensions,
    get_installed_custom_apps,
    load_user_config,
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

    @patch("spicetifix.core.config.get_installed_extensions")
    @patch("spicetifix.core.config.get_user_config_path")
    def test_load_user_config_auto_detects(self, mock_path, mock_get_installed):
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
                "extensions": "popupLyrics.js|adblock/adblock.js|externalApp.js",
                "custom_apps": "marketplace|lyrics-plus",
            }
        }
        self.disk_exts = {"popupLyrics.js", "adblock/adblock.js", "externalApp.js"}
        self.disk_apps = {"marketplace", "lyrics-plus"}

    def test_preserves_external_entries_not_in_yaml(self):
        with patch("spicetifix.core.config.read_spicetify_config", return_value=self.live), \
             patch("spicetifix.core.config.get_installed_extensions", return_value=list(self.disk_exts)), \
             patch("spicetifix.core.config.get_installed_custom_apps", return_value=list(self.disk_apps)):
            cfg = _merge_live_entries({"extensions": ["adblock/adblock.js"], "custom_apps": []})
        self.assertEqual(
            set(cfg["extensions"]),
            {"adblock/adblock.js", "popupLyrics.js", "externalApp.js"},
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


if __name__ == "__main__":
    unittest.main()
