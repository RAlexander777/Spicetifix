import unittest
import tempfile
from pathlib import Path
from automatify.core.backup import export_backup_zip, import_backup_zip


class TestBackupModule(unittest.TestCase):
    def test_export_backup_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            ok, zip_path = export_backup_zip(dest_dir=dest)
            self.assertTrue(ok)
            self.assertTrue(Path(zip_path).exists())
            self.assertTrue(zip_path.endswith(".zip"))

    def test_import_backup_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            ok, zip_path = export_backup_zip(dest_dir=dest)
            self.assertTrue(ok)
            
            # Test importing generated zip
            import_ok, msg = import_backup_zip(Path(zip_path))
            self.assertTrue(import_ok)


if __name__ == "__main__":
    unittest.main()
