import queue
import threading

import customtkinter as ctk

from automatify.ui.home import HomeFrame
from automatify.ui.settings import SettingsPanel
from automatify.core.installer import Installer
from automatify.core.config import load_user_config
from automatify.core.i18n import t, get_lang
from automatify.core.ui_theme import get_ui_theme


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("automatify // system terminal")
        self.geometry("760x720")
        self.minsize(640, 580)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        cfg = load_user_config()
        self._lang = get_lang()
        self._ui_theme_key = cfg.get("ui_theme", "emerald")
        self._ui_theme = get_ui_theme(self._ui_theme_key)

        mode = self._ui_theme.get("mode", "dark")
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("dark-blue")

        self.configure(fg_color=self._ui_theme["bg"])

        self._queue: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self.installer = Installer(
            log_callback=self._enqueue_log,
            progress_callback=self._enqueue_progress,
        )
        self.installer.set_lang(self._lang)

        self.home = HomeFrame(
            self,
            on_install=self._start_install,
            on_recover=self._start_recover,
            on_uninstall_spicetify=self._start_uninstall_spicetify,
            on_uninstall_spotify=self._start_uninstall_spotify,
            on_open_settings=self._show_settings,
            theme=self._ui_theme,
        )
        self.home.set_lang(self._lang)

        self.settings = SettingsPanel(
            self,
            lang=self._lang,
            on_back=self._show_home,
            on_saved=self._on_settings_saved,
            theme=self._ui_theme,
        )

        self.home.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)
        self.settings.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)

        self._show_home()
        self._poll_queue()

    def _show_home(self) -> None:
        self.settings.grid_remove()
        self.home.grid()
        self.home.refresh_status()

    def _show_settings(self) -> None:
        self.home.grid_remove()
        self.settings.set_lang(self._lang)
        self.settings.load()
        self.settings.grid()

    def _on_settings_saved(self) -> None:
        cfg = load_user_config()
        new_lang = cfg.get("language", self._lang)
        new_theme_key = cfg.get("ui_theme", "emerald")

        if new_theme_key != self._ui_theme_key:
            self._ui_theme_key = new_theme_key
            self._ui_theme = get_ui_theme(new_theme_key)
            mode = self._ui_theme.get("mode", "dark")
            ctk.set_appearance_mode(mode)
            self.configure(fg_color=self._ui_theme["bg"])
            self.home.set_ui_theme(self._ui_theme)
            self.settings.set_ui_theme(self._ui_theme)

        if new_lang != self._lang:
            self._lang = new_lang
            self.installer.set_lang(new_lang)
            self.home.set_lang(new_lang)

        self._show_home()

    def _enqueue_log(self, msg: str) -> None:
        self._queue.put(("log", msg))

    def _enqueue_progress(self, pct: float) -> None:
        self._queue.put(("progress", pct))

    def _poll_queue(self) -> None:
        while not self._queue.empty():
            item = self._queue.get_nowait()
            kind, value = item
            if kind == "log":
                self.home.log(value)
            elif kind == "progress":
                self.home.progress.configure(mode="determinate")
                self.home.progress.set(value)

        if self._worker and self._worker.is_alive():
            self.after(100, self._poll_queue)
        elif self._worker and not self._worker.is_alive():
            self._on_worker_done()
            self._worker = None
            self.after(200, self._poll_queue)
        else:
            self.after(200, self._poll_queue)

    def _on_worker_done(self) -> None:
        self.home.set_loading(False)
        self.home.refresh_status()

    def _start_install(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.home.clear_log()
        self.home.set_loading(True)
        self.installer.set_lang(self._lang)
        self.installer.log(t(self._lang, "install_start"))

        user_config = load_user_config()

        def run():
            success = self.installer.install_all(user_config)
            msg = t(self._lang, "install_done") if success else t(self._lang, "install_failed")
            self._queue.put(("log", msg))

        self._worker = threading.Thread(target=run, daemon=True)
        self._worker.start()

    def _start_recover(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.home.clear_log()
        self.home.set_loading(True)
        self.installer.set_lang(self._lang)
        self.installer.log(t(self._lang, "recover_start"))

        def run():
            success = self.installer.recover()
            msg = t(self._lang, "recover_done") if success else t(self._lang, "recover_failed")
            self._queue.put(("log", msg))

        self._worker = threading.Thread(target=run, daemon=True)
        self._worker.start()

    def _start_uninstall_spicetify(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.home.clear_log()
        self.home.set_loading(True)
        self.installer.set_lang(self._lang)

        def run():
            success = self.installer.uninstall_spicetify()
            msg = t(self._lang, "uninstall_spicetify_done") if success else t(self._lang, "uninstall_spicetify_failed")
            self._queue.put(("log", msg))

        self._worker = threading.Thread(target=run, daemon=True)
        self._worker.start()

    def _start_uninstall_spotify(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.home.clear_log()
        self.home.set_loading(True)
        self.installer.set_lang(self._lang)

        def run():
            success = self.installer.uninstall_spotify()
            msg = t(self._lang, "uninstall_spotify_done") if success else t(self._lang, "uninstall_spotify_failed")
            self._queue.put(("log", msg))

        self._worker = threading.Thread(target=run, daemon=True)
        self._worker.start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
