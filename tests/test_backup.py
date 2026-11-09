import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spicetifix.core.backup import export_backup_zip, import_backup_zip


class TestBackupModule(unittest.TestCase):
    def test_export_backup_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("os.startfile", create=True):
            dest = Path(tmpdir)
            ok, zip_path = export_backup_zip(dest_dir=dest)
            self.assertTrue(ok)
            self.assertTrue(Path(zip_path).exists())
            self.assertTrue(zip_path.endswith(".zip"))

    def test_import_backup_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("os.startfile", create=True):
            dest = Path(tmpdir)
            ok, zip_path = export_backup_zip(dest_dir=dest)
            self.assertTrue(ok)

            import_ok, msg = import_backup_zip(Path(zip_path))
            self.assertTrue(import_ok)

    def test_export_import_roundtrip_restores_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            themes = root / "Themes"
            (themes / "MyTheme").mkdir(parents=True)
            (themes / "MyTheme" / "color.ini").write_text("[Base]\nbg=#000\n", encoding="utf-8")
            extensions = root / "Extensions"
            extensions.mkdir()
            apps = root / "CustomApps"
            apps.mkdir()
            cfg = root / "spicetifix.yaml"
            cfg.write_text("language: en\n", encoding="utf-8")
            dest = root / "out"

            with patch("spicetifix.core.backup.get_spicetify_themes_dir", return_value=themes), \
                 patch("spicetifix.core.backup.get_spicetify_extensions_dir", return_value=extensions), \
                 patch("spicetifix.core.backup.get_spicetify_custom_apps_dir", return_value=apps), \
                 patch("spicetifix.core.backup.get_user_config_path", return_value=cfg), \
                 patch("spicetifix.core.backup.get_spicetify_config_path", return_value=None), \
                 patch("os.startfile", create=True):
                ok, zip_path = export_backup_zip(dest_dir=dest)
                self.assertTrue(ok)

                # Wipe the theme file to prove the import actually restores it.
                (themes / "MyTheme" / "color.ini").write_text("WIPED", encoding="utf-8")
                import_ok, msg = import_backup_zip(Path(zip_path))
                self.assertTrue(import_ok)
                self.assertIn(
                    "bg=#000",
                    (themes / "MyTheme" / "color.ini").read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
