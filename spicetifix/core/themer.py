import os
import shutil
import subprocess
import sys
from pathlib import Path

from spicetifix.core.utils import (
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


def get_all_theme_dirs() -> list[Path]:
    """Returns all potential Spicetify Themes directories (LOCALAPPDATA and APPDATA)."""
    dirs = []
    local_dir = get_spicetify_themes_dir()
    if local_dir.exists():
        dirs.append(local_dir)

    appdata_themes = Path(os.environ.get("APPDATA", "")) / "spicetify" / "Themes"
    if appdata_themes.exists() and appdata_themes not in dirs:
        dirs.append(appdata_themes)

    return dirs


def install_themes() -> bool:
    """Clones or updates official Spicetify themes (text, Onepunch, Sleek, Catppuccin, etc.)."""
    themes_dir = get_spicetify_themes_dir()
    text_theme_path = themes_dir / "text"
    onepunch_path = themes_dir / "Onepunch"

    # If official themes already exist, return True
    if text_theme_path.exists() and onepunch_path.exists():
        return True

    if not _git_available():
        return False

    temp_clone_dir = themes_dir.parent / "spicetify-themes-tmp"
    shutil.rmtree(temp_clone_dir, ignore_errors=True)

    code, out, err = run_cmd(
        [
            "git",
            "clone",
            "--depth=1",
            SPICETIFY_THEMES_REPO,
            str(temp_clone_dir),
        ],
        timeout=120,
    )

    if code == 0 and temp_clone_dir.exists():
        themes_dir.mkdir(parents=True, exist_ok=True)
        for item in temp_clone_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                target = themes_dir / item.name
                if not target.exists():
                    shutil.copytree(item, target)
        shutil.rmtree(temp_clone_dir, ignore_errors=True)
        return True

    return False


def set_theme(name: str) -> bool:
    """Sets current theme in Spicetify configuration."""
    if not name:
        return True
    code, out, err = run_spicetify(["config", "current_theme", name])
    return code == 0


def get_theme_color_schemes(theme_name: str) -> list[str]:
    """Reads color.ini for the specified theme (case-insensitive) and returns all section names (schemes)."""
    schemes = []
    if not theme_name:
        return schemes

    target_lower = theme_name.lower().strip()

    for themes_dir in get_all_theme_dirs():
        if not themes_dir.exists():
            continue
        for sub in themes_dir.iterdir():
            if sub.is_dir() and sub.name.lower() == target_lower:
                color_ini = sub / "color.ini"
                if color_ini.exists():
                    try:
                        import configparser
                        parser = configparser.ConfigParser(strict=False)
                        parser.read(color_ini, encoding="utf-8")
                        schemes.extend(parser.sections())
                    except Exception:
                        pass

    if schemes:
        return list(dict.fromkeys(schemes))

    # Fallback search across all themes for matching schemes
    for themes_dir in get_all_theme_dirs():
        if not themes_dir.exists():
            continue
        for sub in themes_dir.iterdir():
            if sub.is_dir() and not sub.name.startswith("."):
                color_ini = sub / "color.ini"
                if color_ini.exists():
                    try:
                        import configparser
                        parser = configparser.ConfigParser(strict=False)
                        parser.read(color_ini, encoding="utf-8")
                        for sec in parser.sections():
                            if target_lower in sec.lower() or sec.lower().startswith(target_lower):
                                schemes.append(sec)
                    except Exception:
                        pass

    return list(dict.fromkeys(schemes))


def set_color_scheme(scheme_name: str) -> bool:
    """Sets current color_scheme in Spicetify configuration."""
    if not scheme_name:
        return True
    code, out, err = run_spicetify(["config", "color_scheme", scheme_name])
    return code == 0


def list_available_themes() -> list[str]:
    """Scans all theme directories and config files to return all available Spicetify themes."""
    themes = set()
    for themes_dir in get_all_theme_dirs():
        if themes_dir.exists() and themes_dir.is_dir():
            for d in themes_dir.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    themes.add(d.name)

    # Include current active themes from config files so they are never hidden
    try:
        from spicetifix.core.config import read_spicetify_config, load_user_config
        sc = read_spicetify_config()
        if sc and "Setting" in sc:
            cur = sc["Setting"].get("current_theme", "").strip()
            if cur:
                themes.add(cur)

        cfg = load_user_config()
        user_theme = cfg.get("spicetify", {}).get("theme", "").strip()
        if user_theme:
            themes.add(user_theme)
    except Exception:
        pass

    return sorted(list(themes))
