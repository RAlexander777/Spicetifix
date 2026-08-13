import unittest
from unittest.mock import patch

from spicetifix.core.marketplace_fetcher import (
    _resolve_url,
    _extract_extensions,
    _extract_themes,
    fetch_catalog,
    _IN_MEMORY_CACHE,
)


def _repo(full_name, default_branch="main", archived=False, stars=42):
    return {
        "full_name": full_name,
        "default_branch": default_branch,
        "archived": archived,
        "stargazers_count": stars,
    }


class TestMarketplaceFetcher(unittest.TestCase):
    def setUp(self):
        _IN_MEMORY_CACHE.clear()

    def test_resolve_url(self):
        self.assertEqual(
            _resolve_url("user", "repo", "main", "ext.js"),
            "https://raw.githubusercontent.com/user/repo/main/ext.js",
        )
        self.assertIsNone(_resolve_url("user", "repo", "main", None))
        self.assertEqual(
            _resolve_url("user", "repo", "main", "https://cdn.example.com/x.js"),
            "https://cdn.example.com/x.js",
        )

    @patch("spicetifix.core.marketplace_fetcher.fetch_manifest")
    def test_extract_extensions_skips_blacklisted_and_archived(self, mock_manifest):
        blacklist = {"user/bad-repo"}
        mock_manifest.return_value = [
            {"name": "Good Ext", "description": "desc", "main": "good.js", "authors": [{"name": "Dev"}]},
        ]
        archived = _repo("user/archived", archived=True)
        bad = _repo("user/bad-repo")
        good = _repo("user/good-repo")

        self.assertEqual(_extract_extensions(archived, blacklist), [])
        self.assertEqual(_extract_extensions(bad, blacklist), [])
        items = _extract_extensions(good, blacklist)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "extension")
        self.assertEqual(items[0]["filename"], "good.js")
        self.assertEqual(items[0]["author"], "Dev")

    @patch("spicetifix.core.marketplace_fetcher.fetch_manifest")
    def test_extract_themes_requires_usercss(self, mock_manifest):
        mock_manifest.return_value = [
            {"name": "Nice Theme", "usercss": "user.css", "schemes": "color.ini", "include": ["x.css"]},
            {"name": "Broken", "main": "b.js"},
        ]
        items = _extract_themes(_repo("user/theme-repo"), set())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "theme")
        self.assertEqual(items[0]["filename"], "Nice Theme")
        self.assertTrue(items[0]["css_url"].endswith("/user.css"))
        self.assertTrue(items[0]["schemes_url"].endswith("/color.ini"))

    @patch("spicetifix.core.marketplace_fetcher.fetch_manifest")
    @patch("spicetifix.core.marketplace_fetcher.search_repos")
    @patch("spicetifix.core.marketplace_fetcher.fetch_blacklist", return_value=set())
    @patch("spicetifix.core.marketplace_fetcher._cached", return_value=None)
    @patch("spicetifix.core.marketplace_fetcher._set_cache")
    def test_fetch_catalog_combines_extensions_and_themes(
        self, mock_set_cache, mock_cached, mock_blacklist, mock_search, mock_manifest
    ):
        mock_search.side_effect = [
            {"items": [_repo("user/ext-repo")], "total_count": 1},
            {"items": [_repo("user/theme-repo")], "total_count": 1},
        ]

        def manifest_side_effect(user, repo, branch):
            if repo == "ext-repo":
                return [{"name": "Ext", "description": "d", "main": "e.js"}]
            return [{"name": "Theme", "usercss": "user.css"}]

        mock_manifest.side_effect = manifest_side_effect

        catalog = fetch_catalog()
        types = {item["type"] for item in catalog}
        self.assertEqual(types, {"extension", "theme"})


if __name__ == "__main__":
    unittest.main()
