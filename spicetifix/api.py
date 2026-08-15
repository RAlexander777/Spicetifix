import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

_last_request_time = time.time()
_server_start_time = time.time()

_AUTH_TOKEN = ""


def set_auth_token(token: str) -> None:
    global _AUTH_TOKEN
    _AUTH_TOKEN = token

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
from spicetifix import __version__


_install_logs = []
_install_progress = 0.0
_is_working = False

_state_lock = threading.RLock()


def _append_log(msg: str):
    global _install_logs
    with _state_lock:
        _install_logs.append(msg)


def _set_progress(pct: float):
    global _install_progress
    with _state_lock:
        _install_progress = pct


def _begin_work() -> bool:
    """Atomically claim the single-worker slot. Returns False if already busy."""
    global _is_working, _install_logs, _install_progress
    with _state_lock:
        if _is_working:
            return False
        _is_working = True
        _install_logs.clear()
        _install_progress = 0.0
        return True


def _end_work():
    global _is_working
    with _state_lock:
        _is_working = False


def _get_state() -> tuple[bool, float, list]:
    with _state_lock:
        return _is_working, _install_progress, list(_install_logs)


def _resolve_static_file(path: str):
    from pathlib import Path
    web_dir = Path(__file__).parent.parent / "web"
    req_file = "index.html" if path in ("/", "") else path.lstrip("/")
    file_path = (web_dir / req_file).resolve()
    if not file_path.is_relative_to(web_dir.resolve()):
        return None
    if file_path.exists() and file_path.is_file():
        return file_path
    return None


def _enrich_catalog_item(item: dict) -> dict:
    from pathlib import Path
    from spicetifix.core.utils import get_spicetify_extensions_dir, get_spicetify_themes_dir
    from spicetifix.core.config import load_user_config

    ext_dir = get_spicetify_extensions_dir()
    themes_dir = get_spicetify_themes_dir()
    cfg = load_user_config()
    user_exts = set(cfg.get("extensions", []))

    typ = item.get("type", "")
    if typ == "extension":
        filename = item.get("filename", "")
        installed = (ext_dir / filename).exists() or filename in user_exts
    elif typ == "theme":
        theme_dirname = item.get("filename", "")
        installed = (themes_dir / theme_dirname).is_dir()
    else:
        installed = False

    item["installed"] = installed
    return item


def _get_marketplace_catalog() -> list[dict]:
    from spicetifix.core.marketplace_fetcher import fetch_catalog

    try:
        raw = fetch_catalog()
    except Exception:
        raw = []

    return [_enrich_catalog_item(item) for item in raw]


class SpicetifixAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard HTTP server console spam
        pass

    def _is_authorized(self) -> bool:
        if not _AUTH_TOKEN:
            return True
        return self.headers.get("X-Auth-Token", "") == _AUTH_TOKEN

    def _cors_headers(self) -> dict:
        origin = self.headers.get("Origin", "")
        if origin == "null" or "127.0.0.1" in origin:
            return {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
            }
        return {}

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in self._cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        global _last_request_time
        _last_request_time = time.time()
        self._send_json({"status": "ok"})

    def do_GET(self):
        global _last_request_time
        _last_request_time = time.time()
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/") and not self._is_authorized():
            self._send_json({"error": "Unauthorized"}, 401)
            return

        if path == "/api/status":
            cfg = load_user_config()
            health = check_config_health()
            now_playing = spotify_control.get_spotify_now_playing()
            sc = read_spicetify_config()

            theme_name = "None"
            if sc and "Setting" in sc:
                theme_name = sc["Setting"].get("current_theme", "None")

            is_working, progress, logs = _get_state()
            self._send_json({
                "version": __version__,
                "config": cfg,
                "health": health,
                "now_playing": now_playing,
                "current_theme": theme_name,
                "is_working": is_working,
                "progress": progress,
                "logs": logs,
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

        elif path == "/api/update/check":
            from spicetifix.core.updater import check_for_update
            update = check_for_update()
            self._send_json({"status": "ok", "update": update})

        else:
            file_path = _resolve_static_file(path)
            if file_path is not None:
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

    def do_POST(self):
        global _last_request_time
        _last_request_time = time.time()
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/") and not self._is_authorized():
            self._send_json({"error": "Unauthorized"}, 401)
            return

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
                    close_spotify,
                    get_spicetify_extensions_dir,
                    get_spicetify_themes_dir,
                    run_spicetify_apply,
                )
                from spicetifix.core.config import (
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
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_bytes(resp.content)

                    cfg = load_user_config()
                    exts = set(cfg.get("extensions", []))
                    exts.add(filename)
                    cfg["extensions"] = list(exts)
                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    close_spotify()
                    code, out, err = run_spicetify_apply()
                    if code != 0:
                        self._send_json({"error": f"spicetify apply falló (código {code}): {err or out}"}, 500)
                        return
                    self._send_json({"status": "ok", "message": f"Extensión {filename} instalada y aplicada"})

                elif item_type == "theme":
                    import requests
                    themes_dir = get_spicetify_themes_dir()
                    theme_dir = themes_dir / filename
                    theme_dir.mkdir(parents=True, exist_ok=True)

                    css_url = body.get("css_url", "")
                    if css_url:
                        resp = requests.get(css_url, timeout=30)
                        resp.raise_for_status()
                        (theme_dir / "user.css").write_bytes(resp.content)

                    schemes_url = body.get("schemes_url", "")
                    if schemes_url:
                        try:
                            resp = requests.get(schemes_url, timeout=30)
                            resp.raise_for_status()
                            (theme_dir / "color.ini").write_bytes(resp.content)
                        except Exception:
                            pass

                    for inc_url in body.get("include", []):
                        try:
                            resp = requests.get(inc_url, timeout=30)
                            resp.raise_for_status()
                            inc_name = inc_url.rstrip("/").split("/")[-1]
                            (theme_dir / inc_name).write_bytes(resp.content)
                        except Exception:
                            pass

                    cfg = load_user_config()
                    cfg.setdefault("spicetify", {})["theme"] = filename
                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    set_theme(filename)
                    close_spotify()
                    code, out, err = run_spicetify_apply()
                    if code != 0:
                        self._send_json({"error": f"spicetify apply falló (código {code}): {err or out}"}, 500)
                        return
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
                    close_spotify,
                    get_spicetify_extensions_dir,
                    get_spicetify_themes_dir,
                    run_spicetify_apply,
                )
                from spicetifix.core.config import (
                    write_spicetify_config,
                )
                from spicetifix.core.themer import set_theme

                if item_type == "extension":
                    ext_dir = get_spicetify_extensions_dir()
                    target_file = ext_dir / filename
                    if target_file.exists():
                        target_file.unlink(missing_ok=True)
                    if target_file.parent != ext_dir:
                        try:
                            target_file.parent.rmdir()
                        except OSError:
                            pass

                    cfg = load_user_config()
                    exts = set(cfg.get("extensions", []))
                    exts.discard(filename)
                    cfg["extensions"] = list(exts)
                    save_user_config(cfg)
                    write_spicetify_config(cfg)
                    close_spotify()
                    code, out, err = run_spicetify_apply()
                    if code != 0:
                        self._send_json({"error": f"spicetify apply falló (código {code}): {err or out}"}, 500)
                        return

                    still_present = target_file.exists() or filename in cfg["extensions"]
                    if still_present:
                        self._send_json({"error": f"La extensión {filename} se marcó para desinstalar pero sigue presente. Reintentá o usá Recover System."}, 500)
                        return
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
                    close_spotify()
                    code, out, err = run_spicetify_apply()
                    if code != 0:
                        self._send_json({"error": f"spicetify apply falló (código {code}): {err or out}"}, 500)
                        return
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
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.install_all(cfg)
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

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

        elif path == "/api/open/external":
            url = body.get("url", "")
            if not url.startswith(("http://", "https://")):
                self._send_json({"error": "Invalid URL"}, 400)
                return
            try:
                import webbrowser
                webbrowser.open(url)
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/backup/export":
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    from spicetifix.core.backup import export_backup_zip
                    export_backup_zip(progress_callback=_set_progress, log_callback=_append_log)
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/backup/import":
            zip_path_str = body.get("zip_path", "")
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    from spicetifix.core.backup import import_backup_zip, pick_and_import_backup
                    from pathlib import Path
                    if zip_path_str:
                        import_backup_zip(Path(zip_path_str), progress_callback=_set_progress, log_callback=_append_log)
                    else:
                        pick_and_import_backup(progress_callback=_set_progress, log_callback=_append_log)
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

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
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    from spicetifix.core.utils import run_spicetify_apply
                    _append_log("Running spicetify apply...")
                    code, out, err = run_spicetify_apply()
                    if out: _append_log(out)
                    if err: _append_log(err)
                    _append_log(f"Finished with exit code {code}")
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/uninstall/spicetify":
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.uninstall_spicetify()
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/uninstall/spotify":
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.uninstall_spicetify()
                    installer.uninstall_spotify()
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/update/download":
            asset_url = body.get("asset_url", "")
            if not asset_url.startswith("https://"):
                self._send_json({"error": "Invalid asset URL"}, 400)
                return
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    from spicetifix.core.updater import download_release_zip
                    _append_log("Descargando nueva versión...")
                    target = download_release_zip(asset_url)
                    _append_log(f"Descargado: {target}")
                    import os
                    os.startfile(str(target.parent))
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        elif path == "/api/recover":
            if not _begin_work():
                self._send_json({"error": "Already working"}, 400)
                return

            def run():
                try:
                    installer = Installer(log_callback=_append_log, progress_callback=_set_progress)
                    cfg = load_user_config()
                    installer.set_lang(cfg.get("language", "en"))
                    installer.recover()
                except Exception as e:
                    _append_log(f"ERROR: {e}")
                finally:
                    _end_work()

            threading.Thread(target=run, daemon=True).start()
            self._send_json({"status": "started"})

        else:
            self._send_json({"error": "Endpoint not found"}, 404)


def _start_heartbeat_checker(idle_timeout: int = 300):
    def checker():
        while True:
            time.sleep(5)
            now = time.time()
            if now - _server_start_time < 30:
                continue
            if now - _last_request_time > idle_timeout:
                print(f"> No requests received for {idle_timeout} seconds. Terminating Spicetifix API server process...")
                os._exit(0)

    t = threading.Thread(target=checker, daemon=True)
    t.start()


def run_api_server(port: int = 8765, auth_token: str = "", idle_timeout: int = 300):
    if auth_token:
        set_auth_token(auth_token)
    _start_heartbeat_checker(idle_timeout)
    server = HTTPServer(("127.0.0.1", port), SpicetifixAPIHandler)
    print(f"> Spicetifix Python Sidecar API running on http://127.0.0.1:{port}")
    server.serve_forever()


def make_server(port: int = 8765, auth_token: str = "", idle_timeout: int = 300) -> HTTPServer:
    if auth_token:
        set_auth_token(auth_token)
    _start_heartbeat_checker(idle_timeout)
    server = HTTPServer(("127.0.0.1", port), SpicetifixAPIHandler)
    print(f"> Spicetifix Python Sidecar API running on http://127.0.0.1:{port}")
    return server


if __name__ == "__main__":
    run_api_server()
