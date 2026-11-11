import ctypes
import os
import secrets
import subprocess
import sys
import threading
import time
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


def _own_exe_name() -> str:
    try:
        return os.path.basename(sys.executable).lower()
    except Exception:
        return "spicetifix.exe"


def _process_name(pid: int) -> str:
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
        ]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        kernel32.CloseHandle(handle)
        return os.path.basename(buf.value) if ok else ""
    except Exception:
        return ""


def _find_own_window(title: str = "SPICETIFIX") -> int:
    """Find a visible top-level window titled exactly `title` that belongs to this
    same executable (the already-running instance).

    FindWindowW is case-insensitive and can match an unrelated window whose title
    only differs in case, so we enumerate and match precisely by title + process.
    """
    try:
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

        candidates = []

        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value == title:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                candidates.append((int(hwnd), pid.value))
            return True

        callback = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(_cb)
        user32.EnumWindows(callback, 0)

        own = _own_exe_name()
        for hwnd, pid in candidates:
            if _process_name(pid).lower() == own:
                return hwnd
        return candidates[0][0] if candidates else 0
    except Exception:
        return 0


def _focus_existing_window(title: str = "SPICETIFIX") -> bool:
    """Bring an already-running Spicetifix window to the foreground (Windows).

    SetForegroundWindow is denied for background processes (the Windows foreground
    lock), so we temporarily attach our input thread to the foreground thread and
    bounce the window through topmost to force it up.
    """
    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        hwnd = _find_own_window(title)
        if not hwnd:
            return False

        SW_RESTORE = 9
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        user32.ShowWindow(hwnd, SW_RESTORE)

        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        cur_thread = kernel32.GetCurrentThreadId()
        attached = False
        if fg_thread and fg_thread != cur_thread:
            attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))

        user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.SetWindowPos(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.BringWindowToTop(hwnd)
        ok = bool(user32.SetForegroundWindow(hwnd))

        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)
        return ok
    except Exception:
        return False


_MUTEX_HANDLE = None


def _is_second_instance() -> bool:
    """True when another instance owns the single-instance mutex.

    Windows allows a second socket to bind an in-use port when SO_REUSEADDR is set
    (which HTTPServer enables), so the port alone is not a reliable guard. A named
    mutex makes the check authoritative. The handle is kept alive for this process
    so the mutex exists for its whole lifetime (released automatically on exit).
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return False
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        handle = kernel32.CreateMutexW(None, False, "Spicetifix_SingleInstance")
        err = ctypes.get_last_error()
        _MUTEX_HANDLE = handle
        return err == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def start():
    from spicetifix.api import make_server
    from spicetifix.core import i18n
    from spicetifix.core.config import get_language, migrate_legacy_config

    migrate_legacy_config()
    i18n.set_lang(get_language())

    if _is_second_instance():
        _focus_existing_window()
        print(f"> {i18n.t('already_running')}")
        sys.exit(0)

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
            webview.start(private_mode=False)
            os._exit(0)
        except Exception as e:
            print(f"> {i18n.t('pywebview_unavailable', err=e)}")

    _launch_browser_fallback(url)
    server.serve_forever()


if __name__ == "__main__":
    start()
