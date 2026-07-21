import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from automatify.core.utils import (
    get_spicetify_dir,
    get_spicetify_config_path,
    get_spicetify_themes_dir,
    get_spicetify_extensions_dir,
    get_spicetify_custom_apps_dir,
)
from automatify.core.config import get_user_config_path


def export_backup_zip(dest_dir: Path = None) -> tuple[bool, str]:
    """
    Creates a .zip archive containing Spicetify configuration, themes, extensions,
    custom apps, and Automatify user settings inside the project's backups/ directory.
    """
    try:
        if dest_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            dest_dir = project_root / "backups"

        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_name = f"automatify_backup_{timestamp}.zip"
        zip_path = dest_dir / zip_name

        spicetify_dir = get_spicetify_dir()
        config_ini = get_spicetify_config_path()
        themes_dir = get_spicetify_themes_dir()
        extensions_dir = get_spicetify_extensions_dir()
        custom_apps_dir = get_spicetify_custom_apps_dir()
        automatify_cfg = get_user_config_path()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add config-xpui.ini
            if config_ini and config_ini.exists():
                zf.write(config_ini, arcname="config-xpui.ini")

            # Add automatify_config.json
            if automatify_cfg and automatify_cfg.exists():
                zf.write(automatify_cfg, arcname="automatify_config.json")

            # Helper to zip subdirectories recursively
            def add_dir_to_zip(folder_path: Path, arc_prefix: str):
                if folder_path and folder_path.exists() and folder_path.is_dir():
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            full_file = Path(root) / file
                            rel_path = full_file.relative_to(folder_path)
                            zf.write(full_file, arcname=f"{arc_prefix}/{rel_path}")

            add_dir_to_zip(themes_dir, "Themes")
            add_dir_to_zip(extensions_dir, "Extensions")
            add_dir_to_zip(custom_apps_dir, "CustomApps")

        # Open directory highlighting created backup
        if os.name == "nt":
            try:
                os.startfile(str(dest_dir))
            except Exception:
                pass

        return True, str(zip_path)

    except Exception as e:
        return False, str(e)


def import_backup_zip(zip_path: Path) -> tuple[bool, str]:
    """
    Extracts a backup .zip archive and restores Spicetify configuration, themes,
    extensions, custom apps, and Automatify user settings.
    """
    try:
        zip_path = Path(zip_path)
        if not zip_path.exists():
            return False, "El archivo de respaldo ZIP no existe."

        config_ini = get_spicetify_config_path()
        themes_dir = get_spicetify_themes_dir()
        extensions_dir = get_spicetify_extensions_dir()
        custom_apps_dir = get_spicetify_custom_apps_dir()
        automatify_cfg = get_user_config_path()

        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                name = member.filename
                if name == "config-xpui.ini" and config_ini:
                    config_ini.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(config_ini, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                elif name == "automatify_config.json" and automatify_cfg:
                    automatify_cfg.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(automatify_cfg, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                elif name.startswith("Themes/") and themes_dir:
                    rel = Path(name).relative_to("Themes")
                    dest = themes_dir / rel
                    if member.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)

                elif name.startswith("Extensions/") and extensions_dir:
                    rel = Path(name).relative_to("Extensions")
                    dest = extensions_dir / rel
                    if member.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)

                elif name.startswith("CustomApps/") and custom_apps_dir:
                    rel = Path(name).relative_to("CustomApps")
                    dest = custom_apps_dir / rel
                    if member.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)

        return True, "Respaldo importado correctamente."
    except Exception as e:
        return False, str(e)
