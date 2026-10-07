import unittest
from unittest.mock import patch, MagicMock

from spicetifix.core.utils import (
    get_installed_spicetify_version,
    get_latest_spicetify_version,
)


class TestSpicetifyVersionHelpers(unittest.TestCase):
    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_parses_bare_output(self, mock_run):
        mock_run.return_value = (0, "2.45.1\n", "")
        self.assertEqual(get_installed_spicetify_version(), "2.45.1")

    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_parses_prefixed_output(self, mock_run):
        mock_run.return_value = (0, "spicetify v2.45.3\n", "")
        self.assertEqual(get_installed_spicetify_version(), "2.45.3")

    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_empty_on_failure(self, mock_run):
        mock_run.return_value = (1, "", "not found")
        self.assertEqual(get_installed_spicetify_version(), "")

    @patch("spicetifix.core.utils.run_spicetify")
    def test_installed_version_empty_on_garbage(self, mock_run):
        mock_run.return_value = (0, "no version here", "")
        self.assertEqual(get_installed_spicetify_version(), "")

    @patch("requests.get")
    def test_latest_version_from_api(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"tag_name": "v2.45.3"}
        mock_get.return_value = resp
        self.assertEqual(get_latest_spicetify_version(), "2.45.3")

    @patch("requests.get")
    def test_latest_version_falls_back_to_redirect(self, mock_get):
        api_resp = MagicMock()
        api_resp.status_code = 500
        redirect_resp = MagicMock()
        redirect_resp.url = "https://github.com/spicetify/cli/releases/tag/v2.45.3"
        mock_get.side_effect = [api_resp, redirect_resp]
        self.assertEqual(get_latest_spicetify_version(), "2.45.3")

    @patch("requests.get")
    def test_latest_version_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("offline")
        self.assertEqual(get_latest_spicetify_version(), "")


if __name__ == "__main__":
    unittest.main()
