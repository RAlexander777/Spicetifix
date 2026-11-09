import unittest

from spicetifix.core import i18n


class TestI18n(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("en")

    def test_en_es_key_parity(self):
        self.assertEqual(set(i18n.STRINGS["en"]), set(i18n.STRINGS["es"]))

    def test_fallback_to_key_when_missing(self):
        i18n.set_lang("en")
        self.assertEqual(i18n.t("__does_not_exist__"), "__does_not_exist__")

    def test_format_kwargs_are_localized(self):
        i18n.set_lang("en")
        self.assertEqual(i18n.t("code_suffix", code=7), "(code 7)")
        i18n.set_lang("es")
        self.assertEqual(i18n.t("code_suffix", code=7), "(código 7)")

    def test_set_lang_normalizes_unknown(self):
        i18n.set_lang("fr")
        self.assertEqual(i18n.get_lang(), "en")

    def test_switching_language_changes_output(self):
        i18n.set_lang("en")
        self.assertEqual(i18n.t("extension_uninstalled", name="x.js"), "Extension x.js uninstalled")
        i18n.set_lang("es")
        self.assertEqual(i18n.t("extension_uninstalled", name="x.js"), "Extensión x.js desinstalada")


if __name__ == "__main__":
    unittest.main()
