import shutil
import tempfile
from pathlib import Path

import requests

from spicetifix.core.utils import (
    SPOTIFY_DOWNLOAD_URL,
    SPICETIFY_INSTALL_PS1,
    MARKETPLACE_INSTALL_PS1,
    find_executable,
    get_spotify_path,
    get_spicetify_dir,
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
            (t(l, "step_config"), self._configure_spicetify),
            (t(l, "step_backup"), self._run_backup),
            (t(l, "step_themes"), lambda: self._install_themes(user_config)),
            (t(l, "step_marketplace"), self._install_marketplace),
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
            return True

        self.log(self._tl("spotify_not_found"))
        try:
            installer_path = Path(tempfile.gettempdir()) / "SpotifySetup.exe"
            self._download_file(SPOTIFY_DOWNLOAD_URL, installer_path)
            self.log(self._tl("spotify_installing"))
            code, out, err = run_cmd(
                [str(installer_path), "/Silent"], timeout=120
            )
            if code != 0:
                self.log(f"{self._tl('spotify_install_error')} {err}")
                return False
            installer_path.unlink(missing_ok=True)
            self.log(self._tl("spotify_installed"))
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
        if installed:
            self.log(f"Spicetify installed at: {installed}")
            return True
        self.log(f"Spicetify install failed (exit code {code})")
        return False

    def _configure_spicetify(self) -> bool:
        return init_spicetify_config()

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
            self.log("Git not found — install it from https://git-scm.com")
            return False
        if not set_theme(theme_name):
            self.log(f"Theme '{theme_name}' not found in Themes directory")
            return False
        return True

    def _install_marketplace(self) -> bool:
        code, out, err = run_ps1(MARKETPLACE_INSTALL_PS1)
        self._clean_log(out)
        if err:
            self._clean_log(err)
        return code == 0

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
