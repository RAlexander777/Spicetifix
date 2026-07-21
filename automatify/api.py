import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from automatify.core.config import (
    load_user_config,
    save_user_config,
    check_config_health,
    get_installed_extensions,
    get_installed_custom_apps,
    read_spicetify_config,
)
from automatify.core.installer import Installer
from automatify.core.themer import list_available_themes, set_theme
from automatify.core.ui_theme import list_ui_theme_names, get_ui_theme, THEMES
from automatify.core import spotify_control


_install_logs = []
_install_progress = 0.0
_is_working = False


def _append_log(msg: str):
    global _install_logs
    _install_logs.append(msg)


def _set_progress(pct: float):
    global _install_progress
    _install_progress = pct


class AutomatifyAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard HTTP server console spam
        pass

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json({"status": "ok"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            cfg = load_user_config()
            health = check_config_health()
            now_playing = spotify_control.get_spotify_now_playing()
            sc = read_spicetify_config()

            theme_name = "None"
            if sc and "Setting" in sc:
                theme_name = sc["Setting"].get("current_theme", "None")

            self._send_json({
                "config": cfg,
                "health": health,
                "now_playing": now_playing,
                "current_theme": theme_name,
                "is_working": _is_working,
                "progress": _install_progress,
                "logs": _install_logs,
            })

        elif path == "/api/themes":
            spicetify_themes = list_available_themes()
            ui_themes = list_ui_theme_names()
            cfg = load_user_config()
            current_ui_key = cfg.get("ui_theme", "emerald")
            self._send_json({
                "spicetify_themes": spicetify_themes,
                "ui_themes": ui_themes,
                "current_ui_theme": current_ui_key,
                "ui_theme_palette": get_ui_theme(current_ui_key),
            })

        elif path == "/api/extensions":
            cfg = load_user_config()
            detected_exts = get_installed_extensions()
            user_exts = set(cfg.get("extensions", []))
            all_exts = sorted(list(set(detected_exts) | user_exts))

            ext_list = [
                {"name": name, "enabled": name in user_exts}
                for name in all_exts
            ]

            detected_apps = get_installed_custom_apps()
            user_apps = set(cfg.get("custom_apps", []))
            all_apps = sorted(list(set(detected_apps) | user_apps))

            app_list = [
                {"name": name, "enabled": name in user_apps}
                for name in all_apps
            ]

            self._send_json({
                "extensions": ext_list,
                "custom_apps": app_list,
            })

        else:
            from pathlib import Path
            web_dir = Path(__file__).parent.parent / "web"
            req_file = "index.html" if path == "/" else path.lstrip("/")
            file_path = web_dir / req_file
            if file_path.exists() and file_path.is_file():
                content_type = "text/html"
                if file_path.suffix == ".css":
                    content_type = "text/css"
                elif file_path.suffix == ".js":
                    content_type = "application/javascript"

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._send_json({"error": "Endpoint or file not found"}, 404)

    def do_POST(self):
        global _is_working, _install_logs, _install_progress
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {}

        if path == "/api/player":
            action = body.get("action", "")
            if action == "play_pause":
                spotify_control.play_pause()
            elif action == "next":
                spotify_control.next_track()
            elif action == "prev":
                spotify_control.prev_track()

            np = spotify_control.get_spotify_now_playing()
            self._send_json({"status": "ok", "now_playing": np})

        elif path == "/api/extensions/toggle":
            ext_name = body.get("name", "")
            enabled = body.get("enabled", False)
            cfg = load_user_config()
            exts = set(cfg.get("extensions", []))
            if enabled:
                exts.add(ext_name)
            else:
                exts.discard(ext_name)
            cfg["extensions"] = list(exts)
            save_user_config(cfg)
            self._send_json({"status": "ok", "extensions": cfg["extensions"]})

        elif path == "/api/config/save":
            cfg = load_user_config()
            if "ui_theme" in body:
                cfg["ui_theme"] = body["ui_theme"]
            if "spicetify_theme" in body:
                cfg.setdefault("spicetify", {})["theme"] = body["spicetify_theme"]
            if "language" in body:
                cfg["language"] = body["language"]
            save_user_config(cfg)
            self._send_json({"status": "ok", "config": cfg})

        elif path == "/api/install":
            if _is_working:
                self._send_json({"error": "Already working"}, 400)
                return

            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.install_all(cfg)
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/open/spotify":
            try:
                import os
                spotify_exe = os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe")
                if os.path.exists(spotify_exe):
                    os.startfile(spotify_exe)
                else:
                    os.startfile("spotify:")
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/open/folder":
            target = body.get("target", "")
            try:
                import os
                from automatify.core.utils import get_spicetify_dir, get_spicetify_themes_dir
                if target == "spicetify":
                    folder = get_spicetify_dir()
                elif target == "themes":
                    folder = get_spicetify_themes_dir()
                else:
                    folder = None

                if folder and folder.exists():
                    os.startfile(str(folder))
                    self._send_json({"status": "ok"})
                else:
                    self._send_json({"error": "Folder not found"}, 404)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/backup/export":
            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    from automatify.core.backup import export_backup_zip
                    export_backup_zip(progress_callback=_set_progress, log_callback=_append_log)
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/backup/import":
            zip_path_str = body.get("zip_path", "")
            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    from automatify.core.backup import import_backup_zip
                    from pathlib import Path
                    import_backup_zip(Path(zip_path_str), progress_callback=_set_progress, log_callback=_append_log)
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/themes/schemes":
            theme_name = body.get("theme", "")
            try:
                from automatify.core.themer import get_theme_color_schemes
                schemes = get_theme_color_schemes(theme_name)
                self._send_json({"status": "ok", "schemes": schemes})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/spicetify/apply":
            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    from automatify.core.utils import run_spicetify
                    _append_log("Running spicetify apply...")
                    code, out, err = run_spicetify(["apply"])
                    if out: _append_log(out)
                    if err: _append_log(err)
                    _append_log(f"Finished with exit code {code}")
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/uninstall/spicetify":
            if _is_working:
                self._send_json({"error": "Already working"}, 400)
                return

            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.uninstall_spicetify()
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/uninstall/spotify":
            if _is_working:
                self._send_json({"error": "Already working"}, 400)
                return

            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.uninstall_spicetify()
                    installer.uninstall_spotify()
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/recover":
            if _is_working:
                self._send_json({"error": "Already working"}, 400)
                return

            _is_working = True
            _install_logs.clear()
            _install_progress = 0.0

            def run():
                global _is_working
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.recover()
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        else:
            self._send_json({"error": "Endpoint not found"}, 404)


def run_api_server(port: int = 8765):
    server = HTTPServer(("127.0.0.1", port), AutomatifyAPIHandler)
    print(f"> Automatify Python Sidecar API running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_api_server()
