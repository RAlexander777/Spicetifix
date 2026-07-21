import os
import subprocess
import threading
import time
import webbrowser
from spicetifix.api import make_server


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
                return subprocess.Popen([browser_path, f"--app={url}"])
            except Exception:
                pass

    webbrowser.open(url)
    return None


def start():
    server = make_server(port=8765)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    time.sleep(0.6)
    proc = launch_web_ui("http://127.0.0.1:8765")

    try:
        if proc:
            proc.wait()
        else:
            thread.join()
    finally:
        server.shutdown()
        print("Spicetifix server stopped.")


if __name__ == "__main__":
    start()
