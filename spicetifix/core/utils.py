import os
import re
import subprocess
import sys
import shutil
from pathlib import Path


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def parse_progress(text: str) -> float | None:
    m = re.search(r"\[(\d+)/(\d+)\]", text)
    if m:
        current = int(m.group(1))
        total = int(m.group(2))
        if total > 0:
            return current / total
    return None


SPICETIFY_INSTALL_PS1 = (
    "https://raw.githubusercontent.com/spicetify/cli/main/install.ps1"
)
MARKETPLACE_INSTALL_PS1 = (
    "https://raw.githubusercontent.com/spicetify/marketplace/main/resources/install.ps1"
)
SPOTIFY_DOWNLOAD_URL = "https://download.scdn.co/SpotifySetup.exe"
SPICETIFY_THEMES_REPO = "https://github.com/spicetify/spicetify-themes.git"


def get_spotify_path() -> str | None:
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "Spotify",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Spotify",
    ]

    for c in candidates:
        apps_dir = c / "Apps"
        if apps_dir.is_dir():
            return str(c)

    packages_root = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages"
    if packages_root.is_dir():
        for pkg in packages_root.iterdir():
            if pkg.name.startswith("SpotifyAB.SpotifyMusic"):
                roaming = pkg / "LocalCache" / "Roaming" / "Spotify"
                if (roaming / "Apps").is_dir():
                    return str(roaming)

    return None


def get_prefs_path() -> str:
    spotify_path = get_spotify_path()
    if spotify_path:
        prefs = Path(spotify_path) / "prefs"
        if prefs.is_file():
            return str(prefs)
    default = Path(os.environ.get("APPDATA", "")) / "Spotify" / "prefs"
    return str(default) if default.is_file() else ""


def get_spicetify_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "spicetify"


def get_spicetify_config_path() -> Path | None:
    cfg = get_spicetify_dir() / "config-xpui.ini"
    return cfg if cfg.exists() else None


def get_spicetify_themes_dir() -> Path:
    return get_spicetify_dir() / "Themes"


def get_spicetify_extensions_dir() -> Path:
    return get_spicetify_dir() / "Extensions"


def get_spicetify_custom_apps_dir() -> Path:
    return get_spicetify_dir() / "CustomApps"


def get_user_config_path() -> Path:
    return Path(__file__).parent.parent.parent / "spicetifix.yaml"


def find_executable(name: str) -> str | None:
    exe = shutil.which(name)
    if exe:
        return exe
    sp_dir = get_spicetify_dir()
    candidate = sp_dir / f"{name}.exe"
    if candidate.exists():
        return str(candidate)
    candidate = sp_dir / f"{name}.cmd"
    if candidate.exists():
        return str(candidate)
    return None


def run_ps1(script_url: str) -> tuple[int, str, str]:
    ps_cmd = (
        f"[Net.ServicePointManager]::SecurityProtocol = "
        f"[Net.SecurityProtocolType]::Tls12; "
        f"iwr -useb '{script_url}' | iex"
    )
    return run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd])


def run_cmd(cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    return proc.returncode, proc.stdout, proc.stderr


def run_spicetify(args: list[str], timeout: int = 300) -> tuple[int, str, str]:
    exe = find_executable("spicetify")
    if not exe:
        return -1, "", "spicetify no encontrado en PATH ni en %LOCALAPPDATA%\\spicetify"
    return run_cmd([exe, *args], timeout=timeout)
