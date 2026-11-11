import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
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


# ---- In-place update (packaged app only) --------------------------------

def _install_dir() -> Path | None:
    """Directory of the running app (the onedir folder). None when not frozen."""
    if not getattr(sys, "frozen", False):
        return None
    try:
        return Path(sys.executable).resolve().parent
    except Exception:
        return None


def _update_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "Spicetifix" / "update"


def _powershell() -> str:
    exe = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        "System32", "WindowsPowerShell", "v1.0", "powershell.exe",
    )
    return exe if os.path.exists(exe) else "powershell"


def _can_write(path: Path) -> bool:
    try:
        probe = path / ".spicetifix_write_test"
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        probe.unlink()
        return True
    except Exception:
        return False


def _find_stage_dir(root: Path) -> Path | None:
    """Find the extracted folder that holds Spicetifix.exe + _internal."""
    try:
        for exe in root.rglob("Spicetifix.exe"):
            parent = exe.parent
            if (parent / "_internal").is_dir():
                return parent
    except Exception:
        pass
    return None


def _write_helper(ps1: Path, staging: Path, app_dir: Path, stage_dir: Path, exe_name: str) -> None:
    def q(p) -> str:
        return str(p).replace("'", "''")

    script = f"""$ErrorActionPreference = 'Stop'
$parentPid = {os.getpid()}
$appDir = '{q(app_dir)}'
$stageDir = '{q(stage_dir)}'
$stageRoot = '{q(staging)}'
$exeName = '{q(exe_name)}'
$logDir = Join-Path $env:LOCALAPPDATA 'Spicetifix'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'apply.log'
function Log($m) {{ "$((Get-Date).ToString('s')) $m" | Out-File -Append -Encoding utf8 $log }}
try {{
  Log "waiting for pid $parentPid"
  while (Get-Process -Id $parentPid -ErrorAction SilentlyContinue) {{ Start-Sleep -Milliseconds 300 }}
  Start-Sleep -Milliseconds 800
  if (Test-Path "$appDir.bak") {{ Remove-Item "$appDir.bak" -Recurse -Force -ErrorAction SilentlyContinue }}
  robocopy $appDir "$appDir.bak" /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
  Log "backup copied"
  robocopy $stageDir $appDir /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) {{ throw "robocopy $LASTEXITCODE" }}
  Log "swapped"
  Start-Process (Join-Path $appDir $exeName)
  Remove-Item "$appDir.bak" -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
  Log "done"
}} catch {{
  Log "error: $_ ; rolling back"
  try {{
    if (Test-Path "$appDir.bak") {{ robocopy "$appDir.bak" $appDir /MIR /NFL /NDL /NJH /NJS /NP | Out-Null }}
    Start-Process (Join-Path $appDir $exeName)
  }} catch {{ Log "rollback failed: $_" }}
}}
"""
    ps1.write_text(script, encoding="utf-8")


def apply_update(asset_url: str) -> tuple[bool, str]:
    """Stage the release and spawn a detached helper that swaps the app folder
    after the current process exits. Returns (ok, reason)."""
    app_dir = _install_dir()
    if app_dir is None:
        return False, "source_mode"

    staging = _update_root()
    try:
        from spicetifix.core.utils import safe_extractall

        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        zip_path = download_release_zip(asset_url, dest_dir=staging)
        extract_dir = staging / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            safe_extractall(zf, extract_dir)

        stage_dir = _find_stage_dir(extract_dir)
        if stage_dir is None:
            return False, "bad_archive"

        if not _can_write(app_dir):
            return False, "no_permission"

        exe_name = Path(sys.executable).name
        ps1 = staging.parent / "apply.ps1"
        _write_helper(ps1, staging, app_dir, stage_dir, exe_name)

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        subprocess.Popen(
            [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-File", str(ps1)],
            cwd=str(ps1.parent),
            creationflags=flags,
            close_fds=True,
        )
        return True, "ok"
    except Exception as e:
        return False, str(e)
