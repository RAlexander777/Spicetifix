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

    def test_language_is_per_thread(self):
        import threading

        i18n.set_lang("es")
        seen = {}

        def worker():
            seen["fresh"] = i18n.get_lang()
            i18n.set_lang("en")
            seen["after"] = i18n.get_lang()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        self.assertEqual(seen["fresh"], "en")   # a new thread starts at the default
        self.assertEqual(seen["after"], "en")
        self.assertEqual(i18n.get_lang(), "es")  # the main thread is unaffected


if __name__ == "__main__":
    unittest.main()
