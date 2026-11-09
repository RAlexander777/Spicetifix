import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from spicetifix.core.utils import (
    get_spicetify_dir,
    get_spicetify_config_path,
    get_spicetify_themes_dir,
    get_spicetify_extensions_dir,
    get_spicetify_custom_apps_dir,
)
from spicetifix.core.config import get_user_config_path
from spicetifix.core import i18n


def export_backup_zip(dest_dir: Path = None, progress_callback=None, log_callback=None) -> tuple[bool, str]:
    """
    Creates a .zip archive containing Spicetify configuration, themes, extensions,
    custom apps, and Spicetifix user settings inside the project's backups/ directory.
    """
    try:
        def _log(msg):
            if log_callback: log_callback(msg)
        def _prog(pct):
            if progress_callback: progress_callback(pct)

        _log(i18n.t("backup_export_start"))
        _prog(0.1)

        if dest_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            dest_dir = project_root / "backups"

        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_name = f"spicetifix_backup_{timestamp}.zip"
        zip_path = dest_dir / zip_name

        config_ini = get_spicetify_config_path()
        themes_dir = get_spicetify_themes_dir()
        extensions_dir = get_spicetify_extensions_dir()
        custom_apps_dir = get_spicetify_custom_apps_dir()
        spicetifix_cfg = get_user_config_path()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            _log(i18n.t("backup_compress_config"))
            _prog(0.3)
            if config_ini and config_ini.exists():
                zf.write(config_ini, arcname="config-xpui.ini")

            if spicetifix_cfg and spicetifix_cfg.exists():
                zf.write(spicetifix_cfg, arcname="spicetifix_config.json")

            _log(i18n.t("backup_compress_themes"))
            _prog(0.5)
            def add_dir_to_zip(folder_path: Path, arc_prefix: str):
                if folder_path and folder_path.exists() and folder_path.is_dir():
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            full_file = Path(root) / file
                            rel_path = full_file.relative_to(folder_path)
                            zf.write(full_file, arcname=f"{arc_prefix}/{rel_path}")

            add_dir_to_zip(themes_dir, "Themes")

            _log(i18n.t("backup_compress_exts"))
            _prog(0.8)
            add_dir_to_zip(extensions_dir, "Extensions")
            add_dir_to_zip(custom_apps_dir, "CustomApps")

        _log(i18n.t("backup_export_ok", path=zip_path))
        _prog(1.0)

        if os.name == "nt":
            try:
                os.startfile(str(dest_dir))
            except Exception:
                pass

        return True, str(zip_path)

    except Exception as e:
        return False, str(e)


def import_backup_zip(zip_path: Path, progress_callback=None, log_callback=None) -> tuple[bool, str]:
    """
    Extracts a backup .zip archive and restores Spicetify configuration, themes,
    extensions, custom apps, and Spicetifix user settings.
    """
    try:
        def _log(msg):
            if log_callback: log_callback(msg)
        def _prog(pct):
            if progress_callback: progress_callback(pct)

        _log(i18n.t("backup_import_start", path=zip_path))
        _prog(0.1)

        zip_path = Path(zip_path)
        if not zip_path.exists():
            return False, i18n.t("backup_zip_missing")

        config_ini = get_spicetify_config_path()
        themes_dir = get_spicetify_themes_dir()
        extensions_dir = get_spicetify_extensions_dir()
        custom_apps_dir = get_spicetify_custom_apps_dir()
        spicetifix_cfg = get_user_config_path()

        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.infolist()
            total_members = len(members) or 1
            for idx, member in enumerate(members):
                pct = 0.1 + (0.8 * (idx / total_members))
                _prog(pct)
                name = member.filename
                if name == "config-xpui.ini" and config_ini:
                    config_ini.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(config_ini, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                elif name == "spicetifix_config.json" and spicetifix_cfg:
                    spicetifix_cfg.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(spicetifix_cfg, "wb") as dst:
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

        _log(i18n.t("backup_import_ok"))
        _prog(1.0)
        return True, i18n.t("backup_imported")
    except Exception as e:
        return False, str(e)


def pick_and_import_backup(progress_callback=None, log_callback=None) -> tuple[bool, str]:
    """
    Opens native Windows File Explorer dialog to pick a .zip backup file and imports it.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        project_root = Path(__file__).resolve().parent.parent.parent
        backups_dir = project_root / "backups"
        initial_dir = str(backups_dir) if backups_dir.exists() else None

        zip_file = filedialog.askopenfilename(
            title=i18n.t("backup_dialog_title"),
            initialdir=initial_dir,
            filetypes=[(i18n.t("backup_dialog_zip"), "*.zip"), (i18n.t("backup_dialog_all"), "*.*")]
        )
        root.destroy()

        if not zip_file:
            return False, i18n.t("backup_dialog_cancelled")

        return import_backup_zip(Path(zip_file), progress_callback=progress_callback, log_callback=log_callback)
    except Exception as e:
        return False, str(e)
