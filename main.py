import sys
import time
import threading
import webbrowser


def start():
    if "--api" in sys.argv or "--web" in sys.argv:
        from automatify.api import run_api_server
        if "--web" in sys.argv:
            def open_browser():
                time.sleep(0.8)
                webbrowser.open("http://127.0.0.1:8765")
            threading.Thread(target=open_browser, daemon=True).start()
        run_api_server(port=8765)
    else:
        from automatify.ui.app import main
        main()


if __name__ == "__main__":
    start()
