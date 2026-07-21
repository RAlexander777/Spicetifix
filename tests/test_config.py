import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from automatify.core.config import (
    get_installed_extensions,
    get_installed_custom_apps,
    load_user_config,
    _default_config,
)


class TestConfigExtensionDetection(unittest.TestCase):
    @patch("automatify.core.config.read_spicetify_config")
    @patch("automatify.core.utils.get_spicetify_extensions_dir")
    def test_get_installed_extensions(self, mock_ext_dir, mock_read_config):
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

        mock_read_config.return_value = {
            "AdditionalOptions": {"extensions": "bookmark.js|marketplace.js"}
        }

        exts = get_installed_extensions()
        self.assertIn("marketplace.js", exts)
        self.assertIn("trashbin.mjs", exts)
        self.assertIn("bookmark.js", exts)

    @patch("automatify.core.config.get_installed_extensions")
    @patch("automatify.core.config.get_user_config_path")
    def test_load_user_config_auto_detects(self, mock_path, mock_get_installed):
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file

        mock_get_installed.return_value = ["marketplace.js", "bookmark.js"]

        cfg = load_user_config()
        self.assertEqual(cfg["extensions"], ["marketplace.js", "bookmark.js"])


if __name__ == "__main__":
    unittest.main()
