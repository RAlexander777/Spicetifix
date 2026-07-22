import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

_last_request_time = time.time()
_server_start_time = time.time()

from spicetifix.core.config import (
    load_user_config,
    save_user_config,
    check_config_health,
    get_installed_extensions,
    get_installed_custom_apps,
    read_spicetify_config,
)
from spicetifix.core.installer import Installer
from spicetifix.core.themer import list_available_themes, set_theme
from spicetifix.core.ui_theme import list_ui_theme_names, get_ui_theme, THEMES
from spicetifix.core import spotify_control


_install_logs = []
_install_progress = 0.0
_is_working = False


def _append_log(msg: str):
    global _install_logs
    _install_logs.append(msg)


def _set_progress(pct: float):
    global _install_progress
    _install_progress = pct


def _get_marketplace_catalog() -> list[dict]:
    from spicetifix.core.utils import get_spicetify_extensions_dir, get_spicetify_themes_dir
    from spicetifix.core.config import load_user_config, read_spicetify_config

    ext_dir = get_spicetify_extensions_dir()
    themes_dir = get_spicetify_themes_dir()
    cfg = load_user_config()
    user_exts = set(cfg.get("extensions", []))
    sc = read_spicetify_config()
    cur_theme = sc.get("Setting", {}).get("current_theme", "") if sc else ""

    items = [
        {
            "id": "adblock",
            "title": "Spicetify Adblock",
            "type": "extension",
            "author": "rxri / Spicetify",
            "description": "Bloquea anuncios de audio, banners y popups molestos dentro de Spotify.",
            "filename": "adblock.js",
            "url": "https://raw.githubusercontent.com/rxri/spicetify-extensions/refs/heads/main/adblock/adblock.js",
            "installed": (ext_dir / "adblock.js").exists() or "adblock.js" in user_exts,
        },
        {
            "id": "popup-lyrics",
            "title": "Popup Lyrics",
            "type": "extension",
            "author": "Spicetify Team",
            "description": "Muestra letras sincronizadas en tiempo real en una ventana flotante.",
            "filename": "popupLyrics.js",
            "url": "https://raw.githubusercontent.com/spicetify/spicetify-cli/main/Extensions/popupLyrics.js",
            "installed": (ext_dir / "popupLyrics.js").exists() or "popupLyrics.js" in user_exts,
        },
        {
            "id": "full-app-display",
            "title": "Full App Display",
            "type": "extension",
            "author": "Spicetify Team",
            "description": "Pantalla completa minimalista con portada gigante e interfaz inmersiva.",
            "filename": "fullAppDisplay.js",
            "url": "https://raw.githubusercontent.com/spicetify/spicetify-cli/main/Extensions/fullAppDisplay.js",
            "installed": (ext_dir / "fullAppDisplay.js").exists() or "fullAppDisplay.js" in user_exts,
        },
        {
            "id": "loopy-loop",
            "title": "Loopy Loop",
            "type": "extension",
            "author": "Spicetify Team",
            "description": "Bucle continuo A/B para repetir partes específicas de cualquier canción.",
            "filename": "loopyLoop.js",
            "url": "https://raw.githubusercontent.com/spicetify/spicetify-cli/main/Extensions/loopyLoop.js",
            "installed": (ext_dir / "loopyLoop.js").exists() or "loopyLoop.js" in user_exts,
        },
        {
            "id": "bookmark",
            "title": "Bookmark",
            "type": "extension",
            "author": "Spicetify Team",
            "description": "Guarda marcadores con marcas de tiempo en tus podcasts y canciones.",
            "filename": "bookmark.js",
            "url": "https://raw.githubusercontent.com/spicetify/spicetify-cli/main/Extensions/bookmark.js",
            "installed": (ext_dir / "bookmark.js").exists() or "bookmark.js" in user_exts,
        },
        {
            "id": "autoskip-explicit",
            "title": "Auto Skip Explicit",
            "type": "extension",
            "author": "Spicetify Team",
            "description": "Omite automáticamente las canciones etiquetadas como explícitas.",
            "filename": "autoSkipExplicit.js",
            "url": "https://raw.githubusercontent.com/spicetify/spicetify-cli/main/Extensions/autoSkipExplicit.js",
            "installed": (ext_dir / "autoSkipExplicit.js").exists() or "autoSkipExplicit.js" in user_exts,
        },
        {
            "id": "theme-text",
            "title": "Text Theme",
            "type": "theme",
            "author": "Spicetify Themes",
            "description": "Tema oscuro minimalista centrado en tipografía Consolas y estética retro.",
            "filename": "text",
            "url": "https://github.com/spicetify/spicetify-themes.git",
            "installed": (themes_dir / "text").is_dir(),
        },
        {
            "id": "theme-burnt-sienna",
            "title": "Burnt Sienna Theme",
            "type": "theme",
            "author": "Spicetify Themes",
            "description": "Tema cálido elegante con acentos terracota y alto contraste.",
            "filename": "BurntSienna",
            "url": "https://github.com/spicetify/spicetify-themes.git",
            "installed": (themes_dir / "BurntSienna").is_dir(),
        },
        {
            "id": "theme-sleek",
            "title": "Sleek Theme",
            "type": "theme",
            "author": "Spicetify Themes",
            "description": "Tema moderno, pulido y compacto para usuarios avanzados.",
            "filename": "Sleek",
            "url": "https://github.com/spicetify/spicetify-themes.git",
            "installed": (themes_dir / "Sleek").is_dir(),
        },
    ]
    return items


class SpicetifixAPIHandler(BaseHTTPRequestHandler):
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
        global _last_request_time
        _last_request_time = time.time()
        self._send_json({"status": "ok"})

    def do_GET(self):
        try:
            global _last_request_time
            _last_request_time = time.time()
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

        elif path == "/api/marketplace/catalog":
            catalog = _get_marketplace_catalog()
            self._send_json({"status": "ok", "catalog": catalog})

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
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._send_json({"error": "Endpoint or file not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        global _last_request_time, _is_working, _install_logs, _install_progress
        _last_request_time = time.time()
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {}

        if path == "/api/marketplace/install":
            item_type = body.get("type", "")
            filename = body.get("filename", "")
            url = body.get("url", "")
            if not filename or not url:
                self._send_json({"error": "Parámetros inválidos"}, 400)
                return

            try:
                from spicetifix.core.utils import (
                    get_spicetify_extensions_dir,
                    get_spicetify_themes_dir,
                    run_spicetify,
                )
                from spicetifix.core.config import (
                    load_user_config,
                    save_user_config,
                    write_spicetify_config,
                )
                from spicetifix.core.themer import install_themes, set_theme

                if item_type == "extension":
                    import requests
                    ext_dir = get_spicetify_extensions_dir()
                    ext_dir.mkdir(parents=True, exist_ok=True)
                    resp = requests.get(url, timeout=30)
                    resp.raise_for_status()
                    target_file = ext_dir / filename
                    target_file.write_bytes(resp.content)

                    cfg = load_user_config()
                    exts = set(cfg.get("extensions", []))
                    exts.add(filename)
                    cfg["extensions"] = list(exts)
                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    run_spicetify(["apply"])
                    self._send_json({"status": "ok", "message": f"Extensión {filename} instalada y aplicada"})

                elif item_type == "theme":
                    install_themes()
                    cfg = load_user_config()
                    cfg.setdefault("spicetify", {})["theme"] = filename
                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    set_theme(filename)
                    run_spicetify(["apply"])
                    self._send_json({"status": "ok", "message": f"Tema {filename} instalado y aplicado"})

                else:
                    self._send_json({"error": "Tipo no soportado"}, 400)

            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/marketplace/uninstall":
            item_type = body.get("type", "")
            filename = body.get("filename", "")
            if not filename:
                self._send_json({"error": "Parámetros inválidos"}, 400)
                return

            try:
                from spicetifix.core.utils import (
                    get_spicetify_extensions_dir,
                    get_spicetify_themes_dir,
                    run_spicetify,
                )
                from spicetifix.core.config import (
                    load_user_config,
                    save_user_config,
                    write_spicetify_config,
                )
                from spicetifix.core.themer import set_theme

                if item_type == "extension":
                    ext_dir = get_spicetify_extensions_dir()
                    target_file = ext_dir / filename
                    if target_file.exists():
                        target_file.unlink(missing_ok=True)

                    cfg = load_user_config()
                    exts = set(cfg.get("extensions", []))
                    exts.discard(filename)
                    cfg["extensions"] = list(exts)
                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    run_spicetify(["apply"])
                    self._send_json({"status": "ok", "message": f"Extensión {filename} desinstalada"})

                elif item_type == "theme":
                    themes_dir = get_spicetify_themes_dir()
                    target_dir = themes_dir / filename
                    if target_dir.exists() and filename.lower() not in ("spicetifydefault", "marketplace"):
                        import shutil
                        shutil.rmtree(target_dir, ignore_errors=True)

                    cfg = load_user_config()
                    if cfg.get("spicetify", {}).get("theme", "") == filename:
                        cfg["spicetify"]["theme"] = "SpicetifyDefault"
                        set_theme("SpicetifyDefault")

                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    run_spicetify(["apply"])
                    self._send_json({"status": "ok", "message": f"Tema {filename} desinstalado"})

                else:
                    self._send_json({"error": "Tipo no soportado"}, 400)

            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/player":
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
                from spicetifix.core.utils import get_spicetify_dir, get_spicetify_themes_dir
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
                    from spicetifix.core.backup import export_backup_zip
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
                    from spicetifix.core.backup import import_backup_zip, pick_and_import_backup
                    from pathlib import Path
                    if zip_path_str:
                        import_backup_zip(Path(zip_path_str), progress_callback=_set_progress, log_callback=_append_log)
                    else:
                        pick_and_import_backup(progress_callback=_set_progress, log_callback=_append_log)
                finally:
                    _is_working = False

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/themes/schemes":
            theme_name = body.get("theme", "")
            try:
                from spicetifix.core.themer import get_theme_color_schemes
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
                    from spicetifix.core.utils import run_spicetify
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


def _start_heartbeat_checker():
    def checker():
        while True:
            time.sleep(2)
            now = time.time()
            if now - _server_start_time < 20:
                continue
            if now - _last_request_time > 8:
                print("> No requests received for 8 seconds. Terminating Spicetifix API server process...")
                os._exit(0)

    t = threading.Thread(target=checker, daemon=True)
    t.start()


def run_api_server(port: int = 8765):
    _start_heartbeat_checker()
    server = HTTPServer(("127.0.0.1", port), SpicetifixAPIHandler)
    print(f"> Spicetifix Python Sidecar API running on http://127.0.0.1:{port}")
    server.serve_forever()


def make_server(port: int = 8765) -> HTTPServer:
    _start_heartbeat_checker()
    server = HTTPServer(("127.0.0.1", port), SpicetifixAPIHandler)
    print(f"> Spicetifix Python Sidecar API running on http://127.0.0.1:{port}")
    return server


if __name__ == "__main__":
    run_api_server()
