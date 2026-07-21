from configparser import ConfigParser

import yaml

from automatify.core.utils import (
    get_spotify_path,
    get_prefs_path,
    get_spicetify_config_path,
    get_spicetify_dir,
    get_user_config_path,
)


DEFAULT_PREPROCESSES = {
    "disable_sentry": True,
    "disable_ui_logging": True,
    "remove_rtl_rule": True,
    "expose_apis": True,
}

DEFAULT_OPTIONS = {
    "inject_css": True,
    "inject_theme_js": False,
    "replace_colors": True,
    "overwrite_assets": False,
    "check_spicetify_update": False,
}


def get_installed_extensions() -> list[str]:
    """Scans Spicetify Extensions directory and config-xpui.ini for all installed extensions."""
    from automatify.core.utils import get_spicetify_extensions_dir
    ext_dir = get_spicetify_extensions_dir()
    extensions = set()

    if ext_dir.exists() and ext_dir.is_dir():
        for item in ext_dir.iterdir():
            if item.is_file() and item.suffix in (".js", ".mjs"):
                extensions.add(item.name)
            elif item.is_dir():
                for subitem in item.iterdir():
                    if subitem.is_file() and subitem.suffix in (".js", ".mjs"):
                        extensions.add(f"{item.name}/{subitem.name}")

    sc = read_spicetify_config()
    if sc and "AdditionalOptions" in sc:
        ext_str = sc["AdditionalOptions"].get("extensions", "")
        for e in ext_str.split("|"):
            e = e.strip()
            if e:
                extensions.add(e)

    return sorted(list(extensions))


def get_installed_custom_apps() -> list[str]:
    """Scans Spicetify CustomApps directory and config-xpui.ini for custom apps."""
    from automatify.core.utils import get_spicetify_custom_apps_dir
    apps_dir = get_spicetify_custom_apps_dir()
    apps = set()

    if apps_dir.exists() and apps_dir.is_dir():
        for item in apps_dir.iterdir():
            if item.is_dir():
                apps.add(item.name)

    sc = read_spicetify_config()
    if sc and "AdditionalOptions" in sc:
        apps_str = sc["AdditionalOptions"].get("custom_apps", "")
        for a in apps_str.split("|"):
            a = a.strip()
            if a:
                apps.add(a)

    return sorted(list(apps))


def load_user_config() -> dict:
    path = get_user_config_path()
    if not path.exists():
        cfg = _default_config()
    else:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or _default_config()

    # Auto-detect installed extensions if user config extensions is missing or empty
    installed_exts = get_installed_extensions()
    if installed_exts and not cfg.get("extensions"):
        sc = read_spicetify_config()
        if sc and "AdditionalOptions" in sc:
            active_str = sc["AdditionalOptions"].get("extensions", "")
            active = [e.strip() for e in active_str.split("|") if e.strip()]
            cfg["extensions"] = active if active else installed_exts
        else:
            cfg["extensions"] = installed_exts

    # Auto-detect installed custom apps if empty
    installed_apps = get_installed_custom_apps()
    if installed_apps and not cfg.get("custom_apps"):
        sc = read_spicetify_config()
        if sc and "AdditionalOptions" in sc:
            active_str = sc["AdditionalOptions"].get("custom_apps", "")
            active = [a.strip() for a in active_str.split("|") if a.strip()]
            cfg["custom_apps"] = active if active else installed_apps
        else:
            cfg["custom_apps"] = installed_apps

    return cfg


def save_user_config(config: dict) -> None:
    path = get_user_config_path()
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)


def _default_config() -> dict:
    return {
        "language": "en",
        "ui_theme": "emerald",
        "spicetify": {
            "theme": "Onepunch",
            "color_scheme": "dark",
            "spotify_launch_flags": "--no-update",
        },
        "extensions": [],
        "custom_apps": [],
        "preprocesses": {
            "disable_sentry": True,
            "disable_ui_logging": True,
            "remove_rtl_rule": True,
            "expose_apis": True,
        },
        "options": {
            "inject_css": True,
            "replace_colors": True,
            "check_spicetify_update": False,
        },
    }


def write_spicetify_config(user_config: dict | None = None) -> None:
    if user_config is None:
        user_config = load_user_config()

    spotify_path = get_spotify_path()
    if not spotify_path:
        raise FileNotFoundError(
            "No se pudo detectar la instalación de Spotify. Instalalo primero."
        )

    sp_dir = get_spicetify_dir()
    sp_dir.mkdir(parents=True, exist_ok=True)

    config_path = sp_dir / "config-xpui.ini"
    parser = ConfigParser()
    parser.optionxform = str  # preserve case

    sc = user_config.get("spicetify", {})

    parser["Setting"] = {
        "spotify_path": spotify_path,
        "prefs_path": get_prefs_path(),
        "current_theme": sc.get("theme", "Onepunch"),
        "color_scheme": sc.get("color_scheme", "dark"),
        "inject_css": _bool_to_str(user_config.get("options", {}).get("inject_css", True)),
        "inject_theme_js": _bool_to_str(user_config.get("options", {}).get("inject_theme_js", False)),
        "replace_colors": _bool_to_str(user_config.get("options", {}).get("replace_colors", True)),
        "overwrite_assets": _bool_to_str(user_config.get("options", {}).get("overwrite_assets", False)),
        "spotify_launch_flags": sc.get("spotify_launch_flags", ""),
        "always_enable_devtools": "0",
        "check_spicetify_update": _bool_to_str(
            user_config.get("options", {}).get("check_spicetify_update", False)
        ),
    }

    pp = user_config.get("preprocesses", {})
    parser["Preprocesses"] = {
        "disable_sentry": _bool_to_str(pp.get("disable_sentry", True)),
        "disable_ui_logging": _bool_to_str(pp.get("disable_ui_logging", True)),
        "remove_rtl_rule": _bool_to_str(pp.get("remove_rtl_rule", True)),
        "expose_apis": _bool_to_str(pp.get("expose_apis", True)),
    }

    parser["AdditionalOptions"] = {
        "extensions": "|".join(user_config.get("extensions", [])),
        "custom_apps": "|".join(user_config.get("custom_apps", [])),
        "sidebar_config": "1",
        "home_config": "1",
        "experimental_features": "1",
    }

    with open(config_path, "w", encoding="utf-8") as f:
        parser.write(f, space_around_delimiters=True)


def read_spicetify_config() -> dict | None:
    path = get_spicetify_config_path()
    if not path:
        return None
    parser = ConfigParser()
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return {s: dict(parser.items(s)) for s in parser.sections()}


def _bool_to_str(val: bool) -> str:
    return "1" if val else "0"


def init_spicetify_config() -> bool:
    try:
        write_spicetify_config()
        return True
    except FileNotFoundError:
        return False


def check_config_health() -> list[dict]:
    from pathlib import Path
    from automatify.core.utils import (
        get_spotify_path,
        get_prefs_path,
        get_spicetify_themes_dir,
        get_spicetify_extensions_dir,
        get_spicetify_custom_apps_dir,
    )

    sc = read_spicetify_config()
    if not sc:
        return [{"label": "config_file", "ok": False, "detail": "config-xpui.ini not found"}]

    setting = sc.get("Setting", {})
    extras = sc.get("AdditionalOptions", {})
    checks = []

    sp_path = setting.get("spotify_path", "")
    if sp_path and (Path(sp_path) / "Apps").is_dir():
        checks.append({"label": "spotify_path", "ok": True, "detail": sp_path})
    else:
        checks.append({"label": "spotify_path", "ok": False, "detail": sp_path or "not set"})

    pf_path = setting.get("prefs_path", "")
    if pf_path and Path(pf_path).is_file():
        checks.append({"label": "prefs_path", "ok": True, "detail": pf_path})
    else:
        checks.append({"label": "prefs_path", "ok": False, "detail": pf_path or "not set → changes won't persist"})

    theme = setting.get("current_theme", "")
    theme_dir = get_spicetify_themes_dir() / theme
    if theme and theme_dir.is_dir():
        checks.append({"label": "theme", "ok": True, "detail": theme})
    elif theme:
        checks.append({"label": "theme", "ok": False, "detail": f"{theme} (not installed)"})
    else:
        checks.append({"label": "theme", "ok": False, "detail": "none set"})

    ext_str = extras.get("extensions", "")
    ext_list = [e.strip() for e in ext_str.split("|") if e.strip()]
    ext_dir = get_spicetify_extensions_dir()
    for ext in ext_list:
        found = (ext_dir / ext).exists() or (ext_dir / ext.replace(".js", ".mjs")).exists()
        checks.append({
            "label": f"ext: {ext}",
            "ok": found,
            "detail": "installed" if found else "missing",
        })

    apps_str = extras.get("custom_apps", "")
    apps_list = [a.strip() for a in apps_str.split("|") if a.strip()]
    apps_dir = get_spicetify_custom_apps_dir()
    for app in apps_list:
        found = (apps_dir / app).is_dir()
        checks.append({
            "label": f"app: {app}",
            "ok": found,
            "detail": "installed" if found else "missing",
        })

    return checks
