import unittest
from automatify.core.ui_theme import get_ui_theme, list_ui_theme_names, THEMES
from automatify.core.spotify_control import get_spotify_now_playing


class TestUITheme(unittest.TestCase):
    def test_get_ui_theme_valid(self):
        theme = get_ui_theme("dracula")
        self.assertEqual(theme["mode"], "dark")
        self.assertEqual(theme["accent"], "#cba6f7")

    def test_get_ui_theme_fallback(self):
        theme = get_ui_theme("non_existent_theme")
        self.assertEqual(theme["mode"], "dark")
        self.assertEqual(theme["accent"], "#00ff9d")

    def test_list_ui_theme_names(self):
        names = list_ui_theme_names()
        self.assertIn("emerald", names)
        self.assertIn("light_clean", names)

    def test_spotify_now_playing(self):
        res = get_spotify_now_playing()
        self.assertIn("playing", res)
        self.assertIn("artist", res)
        self.assertIn("title", res)


if __name__ == "__main__":
    unittest.main()
