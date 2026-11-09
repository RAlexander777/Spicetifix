import io
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

from spicetifix.core.utils import (
    SPOTIFY_DOWNLOAD_URL,
    close_spotify,
    download_and_extract_spicetify,
    ensure_adblock_extension,
    ensure_spotify_prefs,
    find_executable,
    get_installed_spicetify_version,
    get_latest_spicetify_version,
    get_spotify_path,
    get_spicetify_dir,
    get_spicetify_themes_dir,
    parse_progress,
    run_cmd,
    run_spicetify,
    run_spicetify_apply,
    strip_ansi,
)
from spicetifix.core.themer import install_themes, set_theme
from spicetifix.core import i18n


class Installer:
    def __init__(self, log_callback=None, progress_callback=None):
        self._log = log_callback or (lambda msg: None)
        self._progress = progress_callback or (lambda pct: None)
        self._lang = "en"
        self._last_progress_line = ""

    def set_lang(self, lang: str) -> None:
        self._lang = lang
        i18n.set_lang(lang)

    def log(self, msg: str) -> None:
        try:
            self._log(msg)
        except UnicodeEncodeError:
            try:
                self._log(msg.encode("ascii", errors="replace").decode("ascii"))
            except Exception:
                pass
        except Exception:
            pass

    def _clean_log(self, text: str) -> None:
        clean = strip_ansi(text).strip()
        if not clean:
            return

        lines = clean.splitlines()
        for line in lines:
            pct = parse_progress(line)
            if pct is not None:
                self._progress(pct)
                label = line.split("[")[0].strip()
                key = f"{label}:{int(pct * 10)}"
                if key != self._last_progress_line:
                    self.log(line)
                    self._last_progress_line = key
            else:
                self.log(line)
                self._last_progress_line = ""

    def _reset_progress(self) -> None:
        self._progress(0)
        self._last_progress_line = ""

    def _tl(self, key: str, **kwargs) -> str:
        return i18n.t(key, **kwargs)

    def _ensure_extensions(self, user_config: dict | None = None) -> None:
        cfg = user_config or {}
        exts = cfg.get("extensions", [])
        ext_file = get_spicetify_dir() / "Extensions" / "adblock.js"
        if not ext_file.exists() or "adblock.js" in exts:
            ensure_adblock_extension(log_callback=self.log)

    def _step_marketplace_and_extensions(self, user_config: dict) -> bool:
        self._ensure_extensions(user_config)
        return self._install_marketplace(user_config)

    def install_all(self, user_config: dict) -> bool:
        steps = [
            (i18n.t("step_spotify"), self._ensure_spotify),
            (i18n.t("step_spicetify"), self._install_spicetify),
            (i18n.t("step_config"), lambda: self._configure_spicetify(user_config)),
            (i18n.t("step_backup"), self._run_backup),
            (i18n.t("step_themes"), lambda: self._install_themes(user_config)),
            (i18n.t("step_marketplace"), lambda: self._step_marketplace_and_extensions(user_config)),
            (i18n.t("step_apply"), self._run_apply),
        ]

        for label, step in steps:
            self.log(f"[{label}] {i18n.t('step_start')}")
            try:
                success = step()
                if not success:
                    self.log(f"[{label}] {i18n.t('step_failed')}")
                    return False
                self.log(f"[{label}] {i18n.t('step_done')} ✓")
            except Exception as e:
                self.log(f"[{label}] {i18n.t('step_error')} {e}")
                return False

        self._reset_progress()
        self.log(f"=== {i18n.t('step_done')} ===")
        return True

    def _close_spotify(self) -> None:
        """Closes any running Spotify processes so Spicetify can patch files without file locks."""
        close_spotify()

    def recover(self) -> bool:
        label = "spicetify restore backup apply"
        self._close_spotify()
        self.log(f"[{label}] {i18n.t('step_start')}")

        # Older Spicetifix builds rebuilt config-xpui.ini without spicetify's
        # [Backup]/[Patch] sections, which makes spicetify refuse to apply with a
        # "version mismatch" error. Regenerate the missing metadata so the
        # recovery cascade below can actually run.
        try:
            from spicetifix.core.config import repair_backup_metadata
            if repair_backup_metadata():
                self.log(i18n.t("backup_meta_repaired"))
        except Exception:
            pass

        # Ensure configured theme and essential components exist before recovering
        from spicetifix.core.config import load_user_config
        user_config = load_user_config()
        self._ensure_extensions(user_config)

        sp_dir = get_spicetify_dir()
        apps_dir = sp_dir / "CustomApps" / "marketplace"
        if not apps_dir.is_dir() or not any(apps_dir.iterdir()):
            self.log(i18n.t("marketplace_missing_downloading"))
            self._install_marketplace(user_config)

        theme_name = user_config.get("spicetify", {}).get("theme", "")
        if theme_name:
            from spicetifix.core.themer import get_all_theme_dirs, install_themes, set_theme
            theme_exists = False
            for d in get_all_theme_dirs():
                if (d / theme_name).is_dir():
                    theme_exists = True
                    break

            if not theme_exists:
                self.log(i18n.t("theme_not_found_downloading", theme=theme_name))
                install_themes()
                
                theme_exists = False
                for d in get_all_theme_dirs():
                    if (d / theme_name).is_dir():
                        theme_exists = True
                        break

                if not theme_exists:
                    self.log(i18n.t("theme_warn_fallback", theme=theme_name))
                    theme_name = "SpicetifyDefault"
                    if "spicetify" in user_config:
                        user_config["spicetify"]["theme"] = theme_name
                    from spicetifix.core.config import save_user_config, write_spicetify_config
                    try:
                        save_user_config(user_config)
                        write_spicetify_config(user_config)
                    except Exception:
                        pass
                    set_theme(theme_name)

        attempts = [
            (["restore", "backup", "apply"], "restore backup apply"),
            (["backup", "apply"], "backup apply"),
            (["apply"], "apply"),
        ]
        code = -1
        for args, label_short in attempts:
            code, out, err = run_spicetify(args)
            self._clean_log(out)
            if err:
                self._clean_log(err)
            if code == 0:
                self._reset_progress()
                self.log(f"[{label}] {i18n.t('step_done')} ✓ ({label_short})")
                return True
            self.log(i18n.t("spicetify_failed_retry", step=label_short, code=code))
        self._reset_progress()
        self.log(f"[{label}] {i18n.t('step_failed')} {i18n.t('code_suffix', code=code)}")
        return False

    def uninstall_spicetify(self) -> bool:
        self.log(i18n.t("uninstall_spicetify_header"))

        code, out, err = run_spicetify(["restore"])
        if code == 0:
            self.log(i18n.t("spicetify_restore_ok"))
        else:
            self.log(i18n.t("spicetify_restore_err", msg=err or out))

        sp_dir = get_spicetify_dir()
        if sp_dir.exists():
            try:
                shutil.rmtree(str(sp_dir), ignore_errors=True)
                self.log(i18n.t("deleted_path", path=sp_dir))
            except Exception as e:
                self.log(i18n.t("error_deleting", path=sp_dir, err=e))
                return False

        return True

    def uninstall_spotify(self) -> bool:
        self.log(i18n.t("uninstall_spotify_header"))

        code, out, err = run_cmd(
            ["winget", "uninstall", "--id", "Spotify.Spotify", "--silent"],
            timeout=120,
        )
        if code == 0:
            self.log(i18n.t("spotify_uninstalled_winget"))
            return True

        try:
            import winreg
            subkeys = [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            for hive, key_path in subkeys:
                with winreg.OpenKey(hive, key_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                display = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if "spotify" in display.lower():
                                    uninst = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                    self.log(i18n.t("running_cmd", cmd=uninst))
                                    code2, out2, err2 = run_cmd(
                                        [uninst, "/SILENT"], timeout=60
                                    )
                                    if code2 == 0:
                                        self.log(i18n.t("spotify_uninstalled_registry"))
                                        return True
                            except (FileNotFoundError, OSError):
                                continue
        except Exception as e:
            self.log(i18n.t("registry_lookup_failed", err=e))

        spotify_path = get_spotify_path()
        if spotify_path:
            updater = Path(spotify_path) / "Update.exe"
            if updater.exists():
                code, out, err = run_cmd(
                    [str(updater), "--uninstall", "-s"], timeout=60
                )
                if code == 0:
                    self.log(i18n.t("spotify_uninstalled_update_exe"))
                    return True

        for proc in ["Spotify.exe", "SpotifyWebHelper.exe"]:
            run_cmd(["taskkill", "/f", "/im", proc])

        self.log(i18n.t("spotify_processes_killed"))
        return True

    def _ensure_spotify(self) -> bool:
        path = get_spotify_path()
        if path:
            self.log(f"{self._tl('spotify_detected')} {path}")
            ensure_spotify_prefs()
            return True

        self.log(self._tl("spotify_not_found"))
        try:
            installer_path = Path(tempfile.gettempdir()) / "SpotifySetup.exe"
            self._download_file(SPOTIFY_DOWNLOAD_URL, installer_path)
            self.log(self._tl("spotify_installing"))
            code, out, err = run_cmd(
                [str(installer_path), "/Silent"], timeout=120
            )
            installer_path.unlink(missing_ok=True)

            # Wait up to 60 seconds for Spotify installation files to land on disk
            import time
            found_path = None
            for _ in range(30):
                time.sleep(2)
                found_path = get_spotify_path()
                if found_path:
                    break

            if not found_path:
                self.log(f"{self._tl('spotify_install_error')} {i18n.t('spotify_installed_timeout')}")
                return False

            self.log(f"{self._tl('spotify_installed')} ({found_path})")
            ensure_spotify_prefs()
            time.sleep(2)
            self._close_spotify()
            return True
        except Exception as e:
            self.log(f"{self._tl('spotify_install_error')} {e}")
            return False

    def _install_spicetify(self) -> bool:
        existing = find_executable("spicetify")
        if existing:
            installed = get_installed_spicetify_version()
            latest = get_latest_spicetify_version()
            if installed and latest and installed == latest:
                self.log(f"{self._tl('spicetify_already')} {existing} (v{installed})")
                return True
            # An existing install must not short-circuit the download: the CLI
            # release zip also ships the bundled CustomApps (lyrics-plus,
            # reddit, new-releases) and built-in Extensions, so skipping the
            # update left those apps frozen on whatever version was installed
            # first.
            if installed and latest:
                self.log(i18n.t("spicetify_updating", installed=installed, latest=latest))
            else:
                self.log(f"{self._tl('spicetify_already')} {existing}")

        success = download_and_extract_spicetify(log_callback=self.log)
        if not success:
            if existing:
                self.log(i18n.t("spicetify_update_failed_kept"))
                return True
            self.log(i18n.t("spicetify_install_failed"))
            return False
        installed = find_executable("spicetify")
        if not installed:
            self.log(i18n.t("spicetify_exe_missing"))
            return False
        self.log(i18n.t("spicetify_installed_at", path=installed))
        self._close_spotify()
        code, out, err = run_spicetify([])
        self._clean_log(out)
        if err:
            self._clean_log(err)
        if code != 0:
            self.log(i18n.t("spicetify_init_exit", code=code))
        return True

    def _configure_spicetify(self, user_config: dict) -> bool:
        from spicetifix.core.config import write_spicetify_config
        try:
            write_spicetify_config(user_config)
            return True
        except FileNotFoundError:
            return False

    def _run_backup(self) -> bool:
        self._close_spotify()
        code, out, err = run_spicetify(["restore", "backup"])
        self._clean_log(out)
        if err:
            self._clean_log(err)
        if code != 0:
            code, out, err = run_spicetify(["backup"])
            self._clean_log(out)
            if err:
                self._clean_log(err)
        self._reset_progress()
        return code == 0

    def _install_themes(self, user_config: dict) -> bool:
        theme_name = user_config.get("spicetify", {}).get("theme", "")
        if not theme_name:
            self.log(self._tl("no_theme"))
            return True
        if not install_themes():
            self.log(i18n.t("themes_download_skipped"))
        
        # Verify theme exists on disk
        from spicetifix.core.themer import get_all_theme_dirs
        theme_exists = False
        for d in get_all_theme_dirs():
            if (d / theme_name).is_dir():
                theme_exists = True
                break

        if not theme_exists:
            self.log(i18n.t("theme_warn_fallback", theme=theme_name))
            theme_name = "SpicetifyDefault"
            if "spicetify" in user_config:
                user_config["spicetify"]["theme"] = theme_name

        if not set_theme(theme_name):
            self.log(i18n.t("theme_not_found_dir", theme=theme_name))
        return True

    def _install_marketplace(self, user_config: dict | None = None) -> bool:
        sp_dir = get_spicetify_dir()
        apps_dir = sp_dir / "CustomApps" / "marketplace"
        themes_dir = get_spicetify_themes_dir() / "marketplace"

        apps_dir.mkdir(parents=True, exist_ok=True)
        themes_dir.mkdir(parents=True, exist_ok=True)

        self.log(i18n.t("marketplace_downloading"))
        zip_url = "https://github.com/spicetify/marketplace/releases/latest/download/marketplace.zip"
        try:
            resp = requests.get(zip_url, stream=True, timeout=120)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(apps_dir)
            self.log(i18n.t("marketplace_downloaded"))
        except Exception as e:
            self.log(i18n.t("marketplace_download_failed", err=e))
            return False

        # Move files from nested dist folder to apps root, overwriting the
        # previous version so an already-installed Marketplace actually updates
        # instead of staying frozen on its first extraction.
        dist_dir = apps_dir / "marketplace-dist"
        if dist_dir.exists():
            shutil.copytree(dist_dir, apps_dir, dirs_exist_ok=True)
            shutil.rmtree(dist_dir, ignore_errors=True)

        self.log(i18n.t("marketplace_theme_downloading"))
        color_url = "https://raw.githubusercontent.com/spicetify/marketplace/main/resources/color.ini"
        try:
            resp = requests.get(color_url, timeout=30)
            resp.raise_for_status()
            (themes_dir / "color.ini").write_bytes(resp.content)
            self.log(i18n.t("marketplace_theme_downloaded"))
        except Exception as e:
            self.log(i18n.t("marketplace_theme_download_failed", err=e))

        # Preserve marketplace app in user configuration so it persists across config saves
        if user_config is not None:
            custom_apps = user_config.get("custom_apps", [])
            if "marketplace" not in custom_apps:
                custom_apps.append("marketplace")
                user_config["custom_apps"] = custom_apps
            from spicetifix.core.config import save_user_config, write_spicetify_config
            try:
                save_user_config(user_config)
                write_spicetify_config(user_config)
            except Exception:
                pass

        self.log(i18n.t("marketplace_configuring"))
        run_spicetify(["config", "custom_apps", "marketplace"])
        run_spicetify(["config", "inject_css", "1", "replace_colors", "1"])

        self._close_spotify()

        self.log(i18n.t("running_backup_apply"))
        code, out, err = run_spicetify(["backup", "apply"])
        self._clean_log(out)
        if err:
            self._clean_log(err)

        if code != 0:
            code, out, err = run_spicetify(["apply"])
            self._clean_log(out)
            if err:
                self._clean_log(err)

        if code != 0:
            self.log(i18n.t("marketplace_apply_restart", code=code))
            return False
        self.log(i18n.t("marketplace_installed_ok"))
        return True

    def _run_apply(self) -> bool:
        self._close_spotify()
        code, out, err = run_spicetify_apply()
        self._clean_log(out)
        if err:
            self._clean_log(err)
        self._reset_progress()
        return code == 0

    def _download_file(self, url: str, dest: Path) -> None:
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded / total * 100)
                        self.log(i18n.t("downloading_spotify_pct", pct=pct))
