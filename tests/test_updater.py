import unittest
from unittest.mock import patch

from spicetifix.core.updater import (
    _version_tuple,
    check_for_update,
    download_release_zip,
    get_current_version,
)


class TestUpdater(unittest.TestCase):
    def test_version_tuple_parsing(self):
        self.assertEqual(_version_tuple("1.2.3"), (1, 2, 3))
        self.assertEqual(_version_tuple("v2.0.0"), (2, 0, 0))
        self.assertEqual(_version_tuple("1.2"), (1, 2, 0))
        self.assertEqual(_version_tuple("garbage"), (0, 0, 0))

    @patch("spicetifix.core.updater.get_current_version", return_value="1.2.0")
    def test_check_for_update_returns_info_when_newer(self, _mock_ver):
        payload = {
            "tag_name": "v1.3.0",
            "html_url": "https://github.com/RAlexander777/Spicetifix/releases/tag/v1.3.0",
            "name": "v1.3.0",
            "body": "Notes",
            "assets": [{"name": "Spicetifix.zip", "browser_download_url": "https://example.com/Spicetifix.zip"}],
        }
        with patch("spicetifix.core.updater.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.raise_for_status = lambda: None
            mock_get.return_value.json.return_value = payload

            info = check_for_update("1.2.0")

        self.assertIsNotNone(info)
        self.assertEqual(info["latest_version"], "1.3.0")
        self.assertEqual(info["asset_url"], "https://example.com/Spicetifix.zip")

    @patch("spicetifix.core.updater.get_current_version", return_value="1.2.0")
    def test_check_for_update_returns_none_when_same(self, _mock_ver):
        payload = {"tag_name": "v1.2.0", "html_url": "", "assets": []}
        with patch("spicetifix.core.updater.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.raise_for_status = lambda: None
            mock_get.return_value.json.return_value = payload

            info = check_for_update("1.2.0")

        self.assertIsNone(info)

    @patch("spicetifix.core.updater.get_current_version", return_value="1.2.0")
    def test_check_for_update_returns_none_on_error(self, _mock_ver):
        with patch("spicetifix.core.updater.requests.get", side_effect=Exception("network")):
            info = check_for_update("1.2.0")
        self.assertIsNone(info)

    def test_get_current_version_reads_pyproject(self):
        version = get_current_version()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_download_release_zip_writes_file(self):
        import tempfile
        from pathlib import Path

        class FakeResp:
            def __init__(self):
                self.status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size=8192):
                yield b"PK\x03\x04zipdata"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("spicetifix.core.updater.requests.get", return_value=FakeResp()):
                target = download_release_zip("https://example.com/Spicetifix.zip", dest_dir=tmpdir)
            self.assertTrue(Path(target).exists())
            self.assertEqual(target.name, "Spicetifix.zip")


if __name__ == "__main__":
    unittest.main()
