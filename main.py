import os
import subprocess
import threading
import time
import webbrowser
from spicetifix.api import run_api_server


def launch_web_ui(url: str = "http://127.0.0.1:8765"):
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


def start():
    def run_launcher():
        time.sleep(0.6)
        launch_web_ui("http://127.0.0.1:8765")

    threading.Thread(target=run_launcher, daemon=True).start()
    run_api_server(port=8765)


if __name__ == "__main__":
    start()
