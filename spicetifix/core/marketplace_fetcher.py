import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

_IN_MEMORY_CACHE = {}
MEMORY_TTL = 300  # 5 min
DISK_TTL = 3600   # 1 h

GITHUB_API = "https://api.github.com"
RAW_BASE = "raw.githubusercontent.com"

ITEMS_PER_PAGE = 100
BLACKLIST_URL = "https://raw.githubusercontent.com/spicetify/marketplace/main/resources/blacklist.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def _cache_dir():
    d = Path(os.environ.get("LOCALAPPDATA", "")) / "spicetifix" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _headers():
    h = {"User-Agent": "Spicetifix/1.0"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _get(url):
    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code == 403:
        raise RuntimeError(f"GitHub API rate limited. Set GITHUB_TOKEN env var or retry later.")
    resp.raise_for_status()
    return resp.json()


def _mem_get(key):
    entry = _IN_MEMORY_CACHE.get(key)
    if entry and time.time() - entry["t"] < MEMORY_TTL:
        return entry["d"]
    return None


def _mem_set(key, data):
    _IN_MEMORY_CACHE[key] = {"d": data, "t": time.time()}


def _disk_get(key):
    p = _cache_dir() / f"{key}.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if time.time() - data.get("_ts", 0) < DISK_TTL:
                return data.get("data")
        except Exception:
            pass
    return None


def _disk_set(key, data):
    p = _cache_dir() / f"{key}.json"
    try:
        p.write_text(json.dumps({"data": data, "_ts": time.time()}), encoding="utf-8")
    except Exception:
        pass


def _cached(key):
    return _mem_get(key) or _disk_get(key)


def _set_cache(key, data):
    _mem_set(key, data)
    _disk_set(key, data)


def _resolve_url(user, repo, branch, path):
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"https://{RAW_BASE}/{user}/{repo}/{branch}/{path}"


def fetch_blacklist():
    cached = _mem_get("blacklist")
    if cached is not None:
        return cached
    try:
        data = _get(BLACKLIST_URL)
        bl = set(data.get("repos", []))
        _mem_set("blacklist", bl)
        return bl
    except Exception:
        return set()


def search_repos(topic, page=1):
    url = f"{GITHUB_API}/search/repositories?q=topic:{topic}&sort=stars&order=desc&per_page={ITEMS_PER_PAGE}&page={page}"
    return _get(url)


def fetch_manifest(user, repo, branch):
    url = f"https://{RAW_BASE}/{user}/{repo}/{branch}/manifest.json"
    try:
        data = _get(url)
        if isinstance(data, list):
            return data
        return [data] if isinstance(data, dict) else []
    except Exception:
        return []


def _parse_authors(m):
    authors = m.get("authors", [])
    return ", ".join(a.get("name", "") for a in authors if a.get("name"))


def _extract_extensions(repo_data, blacklist):
    full_name = repo_data.get("full_name", "")
    if full_name in blacklist or repo_data.get("archived"):
        return []
    user, repo = full_name.split("/")
    branch = repo_data.get("default_branch", "main")
    stars = repo_data.get("stargazers_count", 0)
    manifests = fetch_manifest(user, repo, branch)
    items = []
    for m in manifests:
        if not (m.get("name") and m.get("description") and m.get("main")):
            continue
        fn = m["main"]
        items.append({
            "id": f"{full_name}/{fn}",
            "title": m["name"],
            "type": "extension",
            "author": _parse_authors(m) or user,
            "description": m["description"],
            "filename": fn,
            "url": _resolve_url(user, repo, branch, fn),
            "user": user,
            "repo": repo,
            "branch": branch,
            "stars": stars,
            "tags": m.get("tags", []),
            "preview": _resolve_url(user, repo, branch, m.get("preview", "")),
        })
    return items


def _extract_themes(repo_data, blacklist):
    full_name = repo_data.get("full_name", "")
    if full_name in blacklist or repo_data.get("archived"):
        return []
    user, repo = full_name.split("/")
    branch = repo_data.get("default_branch", "main")
    stars = repo_data.get("stargazers_count", 0)
    manifests = fetch_manifest(user, repo, branch)
    items = []
    for m in manifests:
        if not (m.get("name") and m.get("usercss")):
            continue
        tn = m["name"]
        items.append({
            "id": f"{full_name}/{tn}",
            "title": tn,
            "type": "theme",
            "author": _parse_authors(m) or user,
            "description": m.get("description", ""),
            "filename": tn,
            "url": f"https://github.com/{user}/{repo}.git",
            "user": user,
            "repo": repo,
            "branch": branch,
            "css_url": _resolve_url(user, repo, branch, m.get("usercss", "")),
            "schemes_url": _resolve_url(user, repo, branch, m.get("schemes", "")),
            "include": [_resolve_url(user, repo, branch, inc) for inc in m.get("include", [])],
            "preview": _resolve_url(user, repo, branch, m.get("preview", "")),
            "stars": stars,
            "tags": m.get("tags", []),
        })
    return items


def _fetch_topic(topic, extractor, blacklist, max_pages=1):
    items = []
    for page in range(1, max_pages + 1):
        try:
            result = search_repos(topic, page)
        except Exception:
            break
        repos = result.get("items", [])
        if not repos:
            break
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(extractor, r, blacklist) for r in repos]
            for f in as_completed(futures):
                try:
                    items.extend(f.result())
                except Exception:
                    pass
        total = result.get("total_count", 0)
        if page * ITEMS_PER_PAGE >= total:
            break
    return items


def fetch_catalog():
    cached = _cached("catalog")
    if cached is not None:
        return cached

    blacklist = fetch_blacklist()
    extensions = _fetch_topic("spicetify-extensions", _extract_extensions, blacklist)
    themes = _fetch_topic("spicetify-themes", _extract_themes, blacklist)

    catalog = extensions + themes
    _set_cache("catalog", catalog)
    return catalog
