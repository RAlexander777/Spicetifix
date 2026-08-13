import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spicetifix.core.themer import get_theme_color_schemes, list_available_themes


def _make_theme_dir(root: Path, name: str, color_ini: str) -> Path:
    theme = root / name
    theme.mkdir(parents=True, exist_ok=True)
    if color_ini is not None:
        (theme / "color.ini").write_text(color_ini, encoding="utf-8")
    return theme


class TestThemer(unittest.TestCase):
    def test_list_available_themes_from_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _make_theme_dir(root, "Dracula", None)
            _make_theme_dir(root, "Nord", None)
            _make_theme_dir(root, ".hidden", None)

            with patch("spicetifix.core.themer.get_all_theme_dirs", return_value=[root]):
                themes = list_available_themes()

            self.assertIn("Dracula", themes)
            self.assertIn("Nord", themes)
            self.assertNotIn(".hidden", themes)

    def test_get_theme_color_schemes_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _make_theme_dir(
                root, "Dracula",
                "[dark]\nbase=#000000\n[light]\nbase=#ffffff\n",
            )

            with patch("spicetifix.core.themer.get_all_theme_dirs", return_value=[root]):
                schemes = get_theme_color_schemes("dracula")

            self.assertEqual(schemes, ["dark", "light"])

    def test_get_theme_color_schemes_fallback_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _make_theme_dir(
                root, "Catppuccin",
                "[frappe]\nbase=#000000\n[mocha]\nbase=#111111\n",
            )

            with patch("spicetifix.core.themer.get_all_theme_dirs", return_value=[root]):
                schemes = get_theme_color_schemes("mocha")

            self.assertIn("mocha", schemes)

    def test_set_theme_calls_spicetify(self):
        with patch("spicetifix.core.themer.run_spicetify", return_value=(0, "", "")) as mock_run:
            from spicetifix.core.themer import set_theme
            ok = set_theme("Dracula")
        self.assertTrue(ok)
        mock_run.assert_called_with(["config", "current_theme", "Dracula"])


if __name__ == "__main__":
    unittest.main()
