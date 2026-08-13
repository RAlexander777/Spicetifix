import unittest
from unittest.mock import patch, MagicMock

from spicetifix.core.installer import Installer


class TestInstaller(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.progress = []
        self.installer = Installer(
            log_callback=self.logs.append,
            progress_callback=self.progress.append,
        )
        self.installer.set_lang("en")

    def test_clean_log_parses_progress_and_dedupes(self):
        self.installer._clean_log("Downloading [10/100] files...\n[20/100]\nDone")
        self.assertIn("Downloading [10/100] files...", self.logs)
        self.assertIn("Done", self.logs)
        self.assertEqual(self.progress, [0.1, 0.2])

    def test_clean_log_strips_ansi(self):
        self.installer._clean_log("\x1b[32m[30/100] \x1b[0mGreen")
        self.assertEqual(self.progress, [0.3])

    def test_install_all_runs_all_steps(self):
        with patch.object(self.installer, "_ensure_spotify", return_value=True) as s1, \
             patch.object(self.installer, "_install_spicetify", return_value=True) as s2, \
             patch.object(self.installer, "_configure_spicetify", return_value=True) as s3, \
             patch.object(self.installer, "_run_backup", return_value=True) as s4, \
             patch.object(self.installer, "_install_themes", return_value=True) as s5, \
             patch.object(self.installer, "_install_marketplace", return_value=True) as s6, \
             patch.object(self.installer, "_run_apply", return_value=True) as s7:
            ok = self.installer.install_all({})
            self.assertTrue(ok)
            for step in (s1, s2, s3, s4, s5, s6, s7):
                step.assert_called_once()

    def test_install_all_stops_on_failure(self):
        with patch.object(self.installer, "_ensure_spotify", return_value=False) as s1, \
             patch.object(self.installer, "_install_spicetify", return_value=True) as s2:
            ok = self.installer.install_all({})
            self.assertFalse(ok)
            s1.assert_called_once()
            s2.assert_not_called()

    @patch("spicetifix.core.installer.run_spicetify")
    @patch("spicetifix.core.installer.run_cmd")
    def test_recover_runs_restore_backup_apply(self, mock_run_cmd, mock_run_spicetify):
        mock_run_spicetify.return_value = (0, "ok", "")
        mock_run_cmd.return_value = (0, "", "")
        with patch("spicetifix.core.config.load_user_config", return_value={"spicetify": {"theme": ""}}):
            ok = self.installer.recover()
        self.assertTrue(ok)
        mock_run_spicetify.assert_called_with(["restore", "backup", "apply"])

    @patch("spicetifix.core.installer.run_spicetify")
    @patch("spicetifix.core.installer.run_cmd")
    def test_recover_fails_on_nonzero_exit(self, mock_run_cmd, mock_run_spicetify):
        mock_run_spicetify.return_value = (1, "", "boom")
        mock_run_cmd.return_value = (0, "", "")
        with patch("spicetifix.core.config.load_user_config", return_value={"spicetify": {"theme": ""}}):
            ok = self.installer.recover()
        self.assertFalse(ok)

    def test_uninstall_spicetify_removes_dir(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            sp_dir = Path(tmpdir) / "spicetify"
            sp_dir.mkdir()
            with patch("spicetifix.core.installer.run_spicetify", return_value=(0, "", "")), \
                 patch("spicetifix.core.installer.get_spicetify_dir", return_value=sp_dir):
                ok = self.installer.uninstall_spicetify()
            self.assertTrue(ok)
            self.assertFalse(sp_dir.exists())


if __name__ == "__main__":
    unittest.main()
