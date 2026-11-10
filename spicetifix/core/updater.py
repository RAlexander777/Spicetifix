import os
import re
import tempfile
from pathlib import Path

import requests

from spicetifix import USER_AGENT

GITHUB_REPO = "RAlexander777/Spicetifix"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ZIP_ASSET_NAME = "Spicetifix.zip"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def get_current_version() -> str:
    """Returns the app version from the single source of truth
    (``spicetifix.__version__``), falling back to the installed package metadata
    and finally to ``pyproject.toml``. Returns ``""`` when it cannot be determined."""
    try:
        import spicetifix
        if getattr(spicetifix, "__version__", ""):
            return spicetifix.__version__
    except Exception:
        pass
    try:
        from importlib.metadata import version as _dist_version
        return _dist_version("spicetifix")
    except Exception:
        pass
    try:
        import tomllib
        pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "") or ""
    except Exception:
        pass
    return ""


def _version_tuple(version: str) -> tuple[int, ...]:
    match = re.match(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", version.strip())
    if not match:
        return (0, 0, 0)
    return tuple(int(g or 0) for g in match.groups())


def check_for_update(current_version: str | None = None) -> dict | None:
    """
    Queries the GitHub latest release and returns update info if a newer
    version exists. Returns None when up to date or on any failure.
    """
    current = current_version or get_current_version()
    if not current:
        return None

    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        resp = requests.get(RELEASES_URL, headers=headers, timeout=15)
        if resp.status_code == 403:
            return None  # rate limited
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    latest_tag = str(data.get("tag_name", "")).lstrip("v")
    if not latest_tag or _version_tuple(latest_tag) <= _version_tuple(current):
        return None

    zip_asset = None
    for asset in data.get("assets", []):
        if asset.get("name") == ZIP_ASSET_NAME:
            zip_asset = asset.get("browser_download_url")
            break

    return {
        "current_version": current,
        "latest_version": latest_tag,
        "release_url": data.get("html_url", ""),
        "asset_url": zip_asset or "",
        "name": data.get("name", ""),
        "notes": data.get("body", "") or "",
    }


def download_release_zip(asset_url: str, dest_dir: str | Path | None = None) -> Path:
    """Downloads the release ZIP asset to dest_dir (default: Downloads) and returns its path."""
    dest = Path(dest_dir) if dest_dir else Path(os.path.expanduser("~")) / "Downloads"
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / ZIP_ASSET_NAME

    with requests.get(asset_url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        with open(target, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    return target
