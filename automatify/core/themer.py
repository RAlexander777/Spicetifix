import subprocess
import sys
from pathlib import Path

from automatify.core.utils import (
    SPICETIFY_THEMES_REPO,
    get_spicetify_themes_dir,
    run_cmd,
    run_spicetify,
)


def _git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return True
    except FileNotFoundError:
        return False


def install_themes() -> bool:
    themes_dir = get_spicetify_themes_dir()
    if themes_dir.exists() and any(themes_dir.iterdir()):
        return True

    if not _git_available():
        return False

    themes_dir.mkdir(parents=True, exist_ok=True)
    code, out, err = run_cmd(
        [
            "git",
            "clone",
            "--depth=1",
            SPICETIFY_THEMES_REPO,
            str(themes_dir),
        ],
        timeout=120,
    )
    return code == 0


def set_theme(name: str) -> bool:
    target = get_spicetify_themes_dir() / name
    if target.is_dir():
        code, out, err = run_spicetify(["config", "current_theme", name])
        return code == 0
    return False


def list_available_themes() -> list[str]:
    themes_dir = get_spicetify_themes_dir()
    if not themes_dir.exists():
        return []
    return sorted(
        d.name
        for d in themes_dir.iterdir()
        if d.is_dir()
        and (d / "color.ini").exists()
        and (d / "user.css").exists()
    )
