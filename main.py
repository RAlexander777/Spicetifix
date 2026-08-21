import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser

DEFAULT_PORT = 8765
HEARTBEAT_IDLE_TIMEOUT = 300  # Safety net; frontend polls every 1.5s

try:
    import webview
except ImportError:
    webview = None


def launch_web_ui(url: str):
    browser_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]

    for browser_path in browser_candidates:
        if os.path.exists(browser_path):
            try:
                subprocess.Popen([browser_path, f"--app={url}"])
                return
            except Exception:
                pass

    webbrowser.open(url)


def _launch_browser_fallback(url: str):
    def run():
        time.sleep(0.6)
        launch_web_ui(url)

    threading.Thread(target=run, daemon=True).start()


def start():
    from spicetifix.api import make_server

    token = secrets.token_hex(16)

    try:
        server = make_server(port=DEFAULT_PORT, auth_token=token, idle_timeout=HEARTBEAT_IDLE_TIMEOUT)
    except OSError as e:
        print(f"> ERROR: no se pudo abrir el puerto {DEFAULT_PORT} ({e}). "
              "Otra instancia de Spicetifix puede estar en ejecución.")
        sys.exit(1)

    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{DEFAULT_PORT}/#token={token}"

    if webview is not None:
        try:
            window = webview.create_window(
                "SPICETIFIX",
                url,
                width=1523,
                height=1188,
                resizable=True,
                min_size=(700, 600),
                background_color="#0b0f17",
            )
            if window:
                window.events.closed += lambda: os._exit(0)
            webview.start(private_mode=False)
            os._exit(0)
        except Exception as e:
            print(f"> pywebview no disponible ({e}). Usando navegador como respaldo.")

    _launch_browser_fallback(url)
    server.serve_forever()


if __name__ == "__main__":
    start()
