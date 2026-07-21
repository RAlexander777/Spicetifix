import os
import sys
import time
import threading
import subprocess
import webbrowser


def launch_web_ui(url: str = "http://127.0.0.1:8765"):
    """Launches the Web UI in a standalone application window if Edge/Chrome is available, or opens default browser."""
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

    # Fallback to default system browser
    webbrowser.open(url)


def start():
    # If --gui is passed, optionally launch legacy CustomTkinter app
    if "--gui" in sys.argv:
        from automatify.ui.app import main
        main()
        return

    # Default mode: Launch Web Server & App Window
    def run_launcher():
        time.sleep(0.6)
        launch_web_ui("http://127.0.0.1:8765")

    threading.Thread(target=run_launcher, daemon=True).start()

    from automatify.api import run_api_server
    run_api_server(port=8765)


if __name__ == "__main__":
    start()
