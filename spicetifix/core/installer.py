import io
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

from spicetifix.core.utils import (
    SPOTIFY_DOWNLOAD_URL,
    SPICETIFY_INSTALL_PS1,
    MARKETPLACE_INSTALL_PS1,
    ensure_spotify_prefs,
    find_executable,
    get_spotify_path,
    get_spicetify_dir,
    get_spicetify_themes_dir,
    parse_progress,
    run_cmd,
    run_ps1,
    run_spicetify,
    strip_ansi,
)
from spicetifix.core.config import init_spicetify_config
from spicetifix.core.themer import install_themes, set_theme
from spicetifix.core.i18n import t


class Installer:
    def __init__(self, log_callback=None, progress_callback=None):
        self._log = log_callback or (lambda msg: None)
        self._progress = progress_callback or (lambda pct: None)
        self._lang = "en"
        self._last_progress_line = ""

    def set_lang(self, lang: str) -> None:
        self._lang = lang

    def log(self, msg: str) -> None:
        self._log(msg)

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
        text = t(self._lang, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def install_all(self, user_config: dict) -> bool:
        l = self._lang
        steps = [
            (t(l, "step_spotify"), self._ensure_spotify),
            (t(l, "step_spicetify"), self._install_spicetify),
            (t(l, "step_config"), lambda: self._configure_spicetify(user_config)),
            (t(l, "step_backup"), self._run_backup),
            (t(l, "step_themes"), lambda: self._install_themes(user_config)),
            (t(l, "step_marketplace"), lambda: self._install_marketplace(user_config)),
            (t(l, "step_apply"), self._run_apply),
        ]

        for label, step in steps:
            self.log(f"[{label}] {t(l, 'step_start')}")
            try:
                success = step()
                if not success:
                    self.log(f"[{label}] {t(l, 'step_failed')}")
                    return False
                self.log(f"[{label}] {t(l, 'step_done')} ✓")
            except Exception as e:
                self.log(f"[{label}] Error: {e}")
                return False

        return True

    def _close_spotify(self) -> None:
        """Closes any running Spotify processes so Spicetify can patch files without file locks."""
        try:
            run_cmd(["taskkill", "/f", "/im", "Spotify.exe"])
        except Exception:
            pass

    def recover(self) -> bool:
        l = self._lang
        label = "spicetify restore backup apply"
        self._close_spotify()
        self.log(f"[{label}] {t(l, 'step_start')}")
        code, out, err = run_spicetify(["restore", "backup", "apply"])
        self._clean_log(out)
        if err:
            self._clean_log(err)
        self._reset_progress()
        if code != 0:
            self.log(f"[{label}] {t(l, 'step_failed')} (código {code})")
            return False
        self.log(f"[{label}] {t(l, 'step_done')} ✓")
        return True

    def uninstall_spicetify(self) -> bool:
        l = self._lang
        self.log("=== Spicetify uninstall ===")

        code, out, err = run_spicetify(["restore"])
        if code == 0:
            self.log("spicetify restore OK")
        else:
            self.log(f"spicetify restore: {err or out}")

        sp_dir = get_spicetify_dir()
        if sp_dir.exists():
            try:
                shutil.rmtree(str(sp_dir), ignore_errors=True)
                self.log(f"Deleted: {sp_dir}")
            except Exception as e:
                self.log(f"Error deleting {sp_dir}: {e}")
                return False

        return True

    def uninstall_spotify(self) -> bool:
        self.log("=== Spotify uninstall ===")

        code, out, err = run_cmd(
            ["winget", "uninstall", "--id", "Spotify.Spotify", "--silent"],
            timeout=120,
        )
        if code == 0:
            self.log("Spotify uninstalled via winget")
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
                                    self.log(f"Running: {uninst}")
                                    code2, out2, err2 = run_cmd(
                                        [uninst, "/SILENT"], timeout=60
                                    )
                                    if code2 == 0:
                                        self.log("Spotify uninstalled via registry")
                                        return True
                            except (FileNotFoundError, OSError):
                                continue
        except Exception as e:
            self.log(f"Registry lookup failed: {e}")

        spotify_path = get_spotify_path()
        if spotify_path:
            updater = Path(spotify_path) / "Update.exe"
            if updater.exists():
                code, out, err = run_cmd(
                    [str(updater), "--uninstall", "-s"], timeout=60
                )
                if code == 0:
                    self.log("Spotify uninstalled via Update.exe")
                    return True

        for proc in ["Spotify.exe", "SpotifyWebHelper.exe"]:
            run_cmd(["taskkill", "/f", "/im", proc])

        self.log("Spotify processes killed (manual cleanup may be needed)")
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
                self.log(f"{self._tl('spotify_install_error')} Timeout waiting for Spotify installation.")
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
            self.log(f"{self._tl('spicetify_already')} {existing}")
            return True
        code, out, err = run_ps1(SPICETIFY_INSTALL_PS1)
        self._clean_log(out)
        if err and "PromptForChoice" not in err:
            self._clean_log(err)
        installed = find_executable("spicetify")
        if not installed:
            self.log(f"Spicetify install failed (exit code {code})")
            return False
        self.log(f"Spicetify installed at: {installed}")
        self._close_spotify()
        code, out, err = run_spicetify([])
        self._clean_log(out)
        if err:
            self._clean_log(err)
        if code != 0:
            self.log(f"spicetify init exited with code {code}, continuing anyway")
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
            self.log("Themes download skipped or git missing — using current themes")
        if not set_theme(theme_name):
            self.log(f"Theme '{theme_name}' not found in Themes directory")
        return True

    def _install_marketplace(self, user_config: dict | None = None) -> bool:
        sp_dir = get_spicetify_dir()
        apps_dir = sp_dir / "CustomApps" / "marketplace"
        themes_dir = get_spicetify_themes_dir() / "marketplace"

        apps_dir.mkdir(parents=True, exist_ok=True)
        themes_dir.mkdir(parents=True, exist_ok=True)

        self.log("Downloading Marketplace...")
        zip_url = "https://github.com/spicetify/marketplace/releases/latest/download/marketplace.zip"
        try:
            resp = requests.get(zip_url, stream=True, timeout=120)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(apps_dir)
            self.log("Marketplace downloaded and extracted.")
        except Exception as e:
            self.log(f"Failed to download Marketplace: {e}")
            return False

        # Move files from nested dist folder to apps root
        dist_dir = apps_dir / "marketplace-dist"
        if dist_dir.exists():
            for item in dist_dir.iterdir():
                target = apps_dir / item.name
                if not target.exists():
                    shutil.move(str(item), str(target))
            shutil.rmtree(dist_dir, ignore_errors=True)

        self.log("Downloading Marketplace placeholder theme...")
        color_url = "https://raw.githubusercontent.com/spicetify/marketplace/main/resources/color.ini"
        try:
            resp = requests.get(color_url, timeout=30)
            resp.raise_for_status()
            (themes_dir / "color.ini").write_bytes(resp.content)
            self.log("Theme placeholder downloaded.")
        except Exception as e:
            self.log(f"Failed to download theme placeholder: {e}")

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

        self.log("Configuring Spicetify for Marketplace...")
        run_spicetify(["config", "custom_apps", "marketplace"])
        run_spicetify(["config", "inject_css", "1", "replace_colors", "1"])

        self._close_spotify()

        self.log("Running spicetify backup apply...")
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
            self.log(f"spicetify apply exited with code {code}, you may need to restart Spotify")
        else:
            self.log("Marketplace installed successfully! Restart Spotify to see it.")
        return True

    def _run_apply(self) -> bool:
        self._close_spotify()
        code, out, err = run_spicetify(["apply"])
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
                        self.log(f"Descargando Spotify... {pct}%")
