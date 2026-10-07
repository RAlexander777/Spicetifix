import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from spicetifix.core.marketplace_fetcher import (
    _resolve_url,
    _get,
    _extract_extensions,
    _extract_themes,
    _extract_apps,
    fetch_catalog,
    fetch_manifest,
    resolve_repo_version,
    resolve_versions,
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
        self._tmp = tempfile.TemporaryDirectory()
        patcher = patch(
            "spicetifix.core.marketplace_fetcher._cache_dir",
            return_value=Path(self._tmp.name),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

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
    def test_extract_apps_requires_no_entry_point(self, mock_manifest):
        mock_manifest.return_value = [
            {"name": "My App", "description": "d", "preview": "p.png", "branch": "dist/my-app"},
            {"name": "An Extension", "description": "d", "main": "e.js"},
            {"name": "A Theme", "description": "d", "usercss": "user.css"},
            {"name": "No Description"},
        ]
        items = _extract_apps(_repo("user/app-repo"), set())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "app")
        self.assertEqual(items[0]["filename"], "My App")
        self.assertEqual(items[0]["branch"], "dist/my-app")
        self.assertTrue(items[0]["preview"].endswith("user/app-repo/dist/my-app/p.png"))

    @patch("spicetifix.core.marketplace_fetcher.fetch_manifest")
    def test_extract_apps_skips_blacklisted_and_archived(self, mock_manifest):
        mock_manifest.return_value = [{"name": "App", "description": "d"}]
        self.assertEqual(_extract_apps(_repo("user/bad"), {"user/bad"}), [])
        self.assertEqual(_extract_apps(_repo("user/arch", archived=True), set()), [])

    @patch("spicetifix.core.marketplace_fetcher.fetch_manifest")
    @patch("spicetifix.core.marketplace_fetcher.search_repos")
    @patch("spicetifix.core.marketplace_fetcher.fetch_blacklist", return_value=set())
    @patch("spicetifix.core.marketplace_fetcher._cached", return_value=None)
    @patch("spicetifix.core.marketplace_fetcher._set_cache")
    def test_fetch_catalog_combines_extensions_themes_and_apps(
        self, mock_set_cache, mock_cached, mock_blacklist, mock_search, mock_manifest
    ):
        mock_search.side_effect = [
            {"items": [_repo("user/ext-repo")], "total_count": 1},
            {"items": [_repo("user/theme-repo")], "total_count": 1},
            {"items": [_repo("user/app-repo")], "total_count": 1},
        ]

        def manifest_side_effect(user, repo, branch):
            if repo == "ext-repo":
                return [{"name": "Ext", "description": "d", "main": "e.js"}]
            if repo == "app-repo":
                return [{"name": "Some App", "description": "d"}]
            return [{"name": "Theme", "usercss": "user.css"}]

        mock_manifest.side_effect = manifest_side_effect

        catalog = fetch_catalog()
        types = {item["type"] for item in catalog}
        self.assertEqual(types, {"extension", "theme", "app"})

    @patch("spicetifix.core.marketplace_fetcher._SESSION.get")
    def test_resolve_repo_version_uses_release_tag(self, mock_get):
        resp = MagicMock()
        resp.url = "https://github.com/user/repo-tag/releases/tag/v1.2.3"
        mock_get.return_value = resp

        info = resolve_repo_version("user", "repo-tag", "2026-01-01T00:00:00Z")
        self.assertEqual(info["tag"], "v1.2.3")
        self.assertEqual(info["updated_at"], "2026-01-01T00:00:00Z")
        mock_get.assert_called_once()

    @patch("spicetifix.core.marketplace_fetcher._SESSION.get")
    def test_resolve_repo_version_without_release(self, mock_get):
        resp = MagicMock()
        resp.url = "https://github.com/user/repo-nodate/releases"
        mock_get.return_value = resp

        info = resolve_repo_version("user", "repo-nodate", "2026-05-05T00:00:00Z")
        self.assertEqual(info["tag"], "")
        self.assertEqual(info["updated_at"], "2026-05-05T00:00:00Z")

    @patch("spicetifix.core.marketplace_fetcher._SESSION.get")
    def test_resolve_repo_version_is_cached(self, mock_get):
        resp = MagicMock()
        resp.url = "https://github.com/user/repo-cached/releases/tag/v9"
        mock_get.return_value = resp

        first = resolve_repo_version("user", "repo-cached")
        second = resolve_repo_version("user", "repo-cached")
        self.assertEqual(first, second)
        self.assertEqual(mock_get.call_count, 1)

    @patch("spicetifix.core.marketplace_fetcher._SESSION.get")
    def test_get_retries_transient_then_succeeds(self, mock_get):
        ok = MagicMock()
        ok.status_code = 200
        ok.json.return_value = {"ok": True}
        mock_get.side_effect = [requests.exceptions.Timeout("slow"), ok]
        with patch("spicetifix.core.marketplace_fetcher.time.sleep"):
            data = _get("https://example.com/x")
        self.assertEqual(data, {"ok": True})
        self.assertEqual(mock_get.call_count, 2)

    @patch("spicetifix.core.marketplace_fetcher._SESSION.get")
    def test_get_does_not_retry_rate_limit(self, mock_get):
        rl = MagicMock()
        rl.status_code = 403
        mock_get.return_value = rl
        with self.assertRaises(RuntimeError):
            _get("https://example.com/x")
        self.assertEqual(mock_get.call_count, 1)

    @patch("spicetifix.core.marketplace_fetcher._SESSION.get")
    def test_fetch_manifest_is_cached(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"name": "X", "description": "d", "main": "x.js"}
        mock_get.return_value = resp

        first = fetch_manifest("user", "repo-mf", "main")
        second = fetch_manifest("user", "repo-mf", "main")
        self.assertEqual(first, second)
        self.assertEqual(mock_get.call_count, 1)

    @patch("spicetifix.core.marketplace_fetcher.resolve_repo_version")
    def test_resolve_versions_maps_by_repo(self, mock_resolve):
        mock_resolve.side_effect = lambda u, r, k="": {"tag": f"{u}/{r}", "updated_at": ""}
        out = resolve_versions([{"user": "a", "repo": "b"}, {"user": "c", "repo": "d"}])
        self.assertEqual(set(out.keys()), {"a/b", "c/d"})
        self.assertEqual(out["a/b"]["tag"], "a/b")


if __name__ == "__main__":
    unittest.main()
