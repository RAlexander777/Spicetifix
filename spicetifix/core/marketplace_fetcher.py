import json
import os
import posixpath
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
MANIFEST_WORKERS = 24
BLACKLIST_URL = "https://raw.githubusercontent.com/spicetify/marketplace/main/resources/blacklist.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

# A shared session keeps TLS connections alive across the hundreds of manifest
# fetches a catalog build performs; without it every request pays a fresh
# handshake and a cold build can take ~1 minute.
_SESSION = requests.Session()
_SESSION.mount("https://", requests.adapters.HTTPAdapter(
    pool_connections=MANIFEST_WORKERS, pool_maxsize=MANIFEST_WORKERS * 2, max_retries=0
))
_SESSION.mount("http://", requests.adapters.HTTPAdapter(
    pool_connections=MANIFEST_WORKERS, pool_maxsize=MANIFEST_WORKERS * 2, max_retries=0
))


def _cache_dir():
    d = Path(os.environ.get("LOCALAPPDATA", "")) / "spicetifix" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _headers():
    h = {"User-Agent": "Spicetifix/1.0"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _get(url, timeout=15, attempts=3):
    last_exc = None
    for attempt in range(attempts):
        try:
            resp = _SESSION.get(url, headers=_headers(), timeout=timeout)
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(0.6 * (attempt + 1))
            continue
        if resp.status_code == 403:
            raise RuntimeError(f"GitHub API rate limited. Set GITHUB_TOKEN env var or retry later.")
        try:
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(0.6 * (attempt + 1))
    raise last_exc if last_exc else RuntimeError(f"request failed: {url}")


def _mem_get(key):
    entry = _IN_MEMORY_CACHE.get(key)
    if entry and time.time() - entry["t"] < MEMORY_TTL:
        return entry["d"]
    return None


def _mem_set(key, data):
    _IN_MEMORY_CACHE[key] = {"d": data, "t": time.time()}


def _disk_get(key, ignore_ttl=False):
    p = _cache_dir() / f"{key}.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if ignore_ttl or time.time() - data.get("_ts", 0) < DISK_TTL:
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
    return _get(url, timeout=20, attempts=3)


def fetch_manifest(user, repo, branch):
    key = f"manifest:{user}/{repo}@{branch}"
    cached = _mem_get(key)
    if cached is not None:
        return cached
    url = f"https://{RAW_BASE}/{user}/{repo}/{branch}/manifest.json"
    try:
        data = _get(url, timeout=10, attempts=2)
        if isinstance(data, list):
            result = data
        else:
            result = [data] if isinstance(data, dict) else []
    except Exception:
        result = []
    # Only cache successes, so a transient failure is retried on the next build.
    if result:
        _mem_set(key, result)
    return result


def _parse_authors(m):
    authors = m.get("authors", [])
    return ", ".join(a.get("name", "") for a in authors if a.get("name"))


def _repo_updated(repo_data):
    return repo_data.get("pushed_at") or repo_data.get("updated_at") or ""


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
            "filename": posixpath.basename(fn),
            "url": _resolve_url(user, repo, branch, fn),
            "user": user,
            "repo": repo,
            "branch": branch,
            "stars": stars,
            "tags": m.get("tags", []),
            "preview": _resolve_url(user, repo, branch, m.get("preview", "")),
            "updated_at": _repo_updated(repo_data),
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
            "updated_at": _repo_updated(repo_data),
        })
    return items


def _extract_apps(repo_data, blacklist):
    full_name = repo_data.get("full_name", "")
    if full_name in blacklist or repo_data.get("archived"):
        return []
    user, repo = full_name.split("/")
    branch = repo_data.get("default_branch", "main")
    stars = repo_data.get("stargazers_count", 0)
    manifests = fetch_manifest(user, repo, branch)
    items = []
    for m in manifests:
        # A custom app has no entry point (`main`) and no stylesheet (`usercss`);
        # the whole repo (or the manifest `branch`) is the app. This mirrors how
        # the official Marketplace tells apps apart, so extensions/themes bundled
        # in the same repo are skipped.
        if not (m.get("name") and m.get("description")):
            continue
        if m.get("main") or m.get("usercss"):
            continue
        name = m["name"]
        item_branch = m.get("branch") or branch
        items.append({
            "id": f"{full_name}/app/{name}",
            "title": name,
            "type": "app",
            "author": _parse_authors(m) or user,
            "description": m["description"],
            "filename": name,
            "url": f"https://github.com/{user}/{repo}.git",
            "user": user,
            "repo": repo,
            "branch": item_branch,
            "stars": stars,
            "tags": m.get("tags", []),
            "preview": _resolve_url(user, repo, item_branch, m.get("preview", "")),
            "updated_at": _repo_updated(repo_data),
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
        with ThreadPoolExecutor(max_workers=MANIFEST_WORKERS) as pool:
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
    apps = _fetch_topic("spicetify-apps", _extract_apps, blacklist)

    catalog = extensions + themes + apps
    if catalog:
        _set_cache("catalog", catalog)
        return catalog

    # GitHub search is rate limited (10 req/min unauthenticated) and can also
    # fail transiently; serve the last successful catalog instead of nothing.
    stale = _disk_get("catalog", ignore_ttl=True)
    return stale if stale else []


def resolve_repo_version(user: str, repo: str, known_updated_at: str = "") -> dict:
    """Resolve the "current version" of a repo.

    Returns the latest release tag when the repo publishes releases; when it
    does not, ``tag`` is empty and callers fall back to ``updated_at`` (the
    repo's last push, which the catalog already knows from the search result).

    The tag is read from the github.com HTML redirect (``/releases/latest`` ->
    ``/releases/tag/<tag>``) on purpose: it does NOT count against the GitHub
    REST API rate limit (60 requests/hour unauthenticated). Querying the API per
    repo here used to exhaust that budget and make everything else 403. Results
    are cached in memory + on disk.
    """
    empty = {"tag": "", "updated_at": known_updated_at or ""}
    if not user or not repo:
        return empty

    key = f"version:{user}/{repo}"
    cached = _cached(key)
    if cached is not None:
        if not cached.get("updated_at") and known_updated_at:
            return {**cached, "updated_at": known_updated_at}
        return cached

    info = {"tag": "", "updated_at": known_updated_at or ""}
    try:
        resp = _SESSION.get(
            f"https://github.com/{user}/{repo}/releases/latest",
            headers={"User-Agent": "Spicetifix/1.0"},
            timeout=10,
            allow_redirects=True,
        )
        marker = "/releases/tag/"
        if marker in resp.url:
            info["tag"] = resp.url.split(marker, 1)[1].split("/")[0].split("?")[0]
    except Exception:
        pass

    _set_cache(key, info)
    return info


def resolve_versions(repos: list[dict]) -> dict:
    """Resolve versions for many repos in parallel.

    ``repos`` is a list of ``{"user", "repo", "updated_at"?}`` dicts; returns a
    mapping ``"user/repo" -> {"tag", "updated_at"}``."""
    results: dict[str, dict] = {}

    def work(item):
        user = item.get("user", "")
        repo = item.get("repo", "")
        if not user or not repo:
            return
        results[f"{user}/{repo}"] = resolve_repo_version(
            user, repo, item.get("updated_at", "")
        )

    if repos:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(work, repos))
    return results
