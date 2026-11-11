import ctypes
import os
import secrets
import subprocess
import sys
import threading
import time
import traceback
import webbrowser

DEFAULT_PORT = int(os.environ.get("SPICETIFIX_PORT", "8765"))
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


def _focus_existing_window(title: str = "SPICETIFIX") -> bool:
    """Bring an already-running Spicetifix window to the foreground (Windows)."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def _tray_log(msg: str) -> None:
    try:
        from spicetifix.core.utils import get_user_config_path
        p = get_user_config_path().parent / "tray.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _start_tray(window):
    """Create a system-tray icon (optional; needs pystray + Pillow)."""
    _tray_log("start")
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        _tray_log("import failed:\n" + traceback.format_exc())
        return None

    try:
        from spicetifix.core import i18n
        show_lbl = i18n.t("tray_show")
        hide_lbl = i18n.t("tray_hide")
        quit_lbl = i18n.t("tray_quit")
        tooltip = i18n.t("tray_tooltip")
    except Exception:
        show_lbl, hide_lbl, quit_lbl, tooltip = "Show", "Hide", "Quit", "Spicetifix"

    def _image():
        size = 64
        img = Image.new("RGBA", (size, size), (11, 15, 23, 255))
        draw = ImageDraw.Draw(img)
        draw.polygon([(18, 16), (46, 32), (18, 48)], fill=(0, 255, 157, 255))
        return img

    def _show(icon=None, item=None):
        try:
            window.show()
            window.restore()
        except Exception:
            pass

    def _hide(icon=None, item=None):
        try:
            window.hide()
        except Exception:
            pass

    def _quit(icon=None, item=None):
        try:
            icon.stop()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            pass
        os._exit(0)

    try:
        menu = pystray.Menu(
            pystray.MenuItem(show_lbl, _show, default=True),
            pystray.MenuItem(hide_lbl, _hide),
            pystray.MenuItem(quit_lbl, _quit),
        )
        icon = pystray.Icon("spicetifix", _image(), tooltip, menu)
        threading.Thread(target=icon.run, name="spicetifix-tray", daemon=True).start()

        def _probe():
            time.sleep(2)
            try:
                _tray_log(f"visible={getattr(icon, 'visible', '?')}")
            except Exception:
                _tray_log("probe failed:\n" + traceback.format_exc())

        threading.Thread(target=_probe, name="spicetifix-tray-probe", daemon=True).start()
        return icon
    except Exception:
        _tray_log("tray failed:\n" + traceback.format_exc())
        return None


def start():
    from spicetifix.api import make_server
    from spicetifix.core import i18n
    from spicetifix.core.config import get_language, migrate_legacy_config

    migrate_legacy_config()
    i18n.set_lang(get_language())
    token = secrets.token_hex(16)

    try:
        server = make_server(port=DEFAULT_PORT, auth_token=token, idle_timeout=HEARTBEAT_IDLE_TIMEOUT)
    except OSError as e:
        if _focus_existing_window():
            print(f"> {i18n.t('already_running')}")
            sys.exit(0)
        print(f"> {i18n.t('port_in_use', port=DEFAULT_PORT, err=e)}")
        sys.exit(1)

    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{DEFAULT_PORT}/#token={token}"

    if webview is not None:
        try:
            window = webview.create_window(
                "SPICETIFIX",
                url,
                width=1140,
                height=860,
                resizable=True,
                min_size=(700, 600),
                background_color="#0b0f17",
            )
            if window:
                kernel32 = ctypes.windll.kernel32
                kernel32.CreateEventW.restype = ctypes.c_void_p
                kernel32.CreateEventW.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_wchar_p,
                ]
                kernel32.SetEvent.restype = ctypes.c_int
                kernel32.SetEvent.argtypes = [ctypes.c_void_p]
                kernel32.WaitForSingleObject.restype = ctypes.c_ulong
                kernel32.WaitForSingleObject.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_ulong,
                ]
                kernel32.TerminateProcess.restype = ctypes.c_int
                kernel32.TerminateProcess.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_uint,
                ]
                kernel32.GetCurrentProcess.restype = ctypes.c_void_p
                kernel32.CreateThread.restype = ctypes.c_void_p
                kernel32.CreateThread.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_size_t,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    ctypes.c_ulong,
                    ctypes.POINTER(ctypes.c_ulong),
                ]

                _kill_event = kernel32.CreateEventW(None, False, False, None)
                _watchdog_proto = ctypes.WINFUNCTYPE(
                    ctypes.c_ulong, ctypes.c_void_p
                )

                def _watchdog(_):
                    kernel32.WaitForSingleObject(_kill_event, -1)
                    kernel32.TerminateProcess(kernel32.GetCurrentProcess(), 0)
                    return 0

                _watchdog = _watchdog_proto(_watchdog)
                kernel32.CreateThread(
                    None, 0, _watchdog, None, 0, None
                )

                def _closing():
                    kernel32.SetEvent(_kill_event)

                window.events.closing += _closing
                window.events.closed += lambda: os._exit(0)
            if window:
                _start_tray(window)
            webview.start(private_mode=False)
            os._exit(0)
        except Exception as e:
            print(f"> {i18n.t('pywebview_unavailable', err=e)}")

    _launch_browser_fallback(url)
    server.serve_forever()


if __name__ == "__main__":
    start()
