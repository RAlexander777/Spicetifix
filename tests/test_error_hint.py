import unittest

from spicetifix.core import i18n
from spicetifix.core.utils import spicetify_error_hint


class TestSpicetifyErrorHint(unittest.TestCase):
    def setUp(self):
        i18n.set_lang("es")

    def tearDown(self):
        i18n.set_lang("en")

    def test_returns_none_when_empty(self):
        self.assertIsNone(spicetify_error_hint())
        self.assertIsNone(spicetify_error_hint("", ""))

    def test_returns_none_when_no_mismatch(self):
        self.assertIsNone(spicetify_error_hint("some unrelated error"))

    def test_detects_version_mismatch_in_out(self):
        hint = spicetify_error_hint("version and backup version are mismatched")
        self.assertIsNotNone(hint)
        self.assertIn("respaldo", hint.lower())

    def test_detects_cannot_be_backed_up_in_err(self):
        hint = spicetify_error_hint("", "cannot be backed up at this state")
        self.assertIsNotNone(hint)
        self.assertIn("RECUPERAR SISTEMA", hint)

    def test_detects_restore_first_marker_case_insensitive(self):
        hint = spicetify_error_hint("Restore first then backup", "")
        self.assertIsNotNone(hint)

    def test_detects_clear_backup_marker(self):
        hint = spicetify_error_hint("", "please clear backup first")
        self.assertIsNotNone(hint)

    def test_hint_mentions_reinstall_recovery(self):
        hint = spicetify_error_hint("version and backup version are mismatched")
        self.assertIn("reinstala Spotify", hint)

    def test_hint_english_mode(self):
        i18n.set_lang("en")
        hint = spicetify_error_hint("version and backup version are mismatched")
        self.assertIsNotNone(hint)
        self.assertIn("RECOVER SYSTEM", hint)
        self.assertIn("reinstall Spotify", hint)


if __name__ == "__main__":
    unittest.main()
