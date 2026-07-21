import ctypes
import sys
import subprocess

# Correct Win32 Virtual-Key Codes for Media Control
VK_MEDIA_NEXT_TRACK = 0xB0  # 176
VK_MEDIA_PREV_TRACK = 0xB1  # 177
VK_MEDIA_PLAY_PAUSE = 0xB3  # 179

KEYEVENTF_KEYUP = 0x0002


def _send_key(vk_code: int) -> None:
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def play_pause() -> None:
    """Toggles play/pause for Spotify/active media player."""
    _send_key(VK_MEDIA_PLAY_PAUSE)


def next_track() -> None:
    """Skips to next track."""
    _send_key(VK_MEDIA_NEXT_TRACK)


def prev_track() -> None:
    """Skips to previous track."""
    _send_key(VK_MEDIA_PREV_TRACK)


def get_spotify_now_playing() -> dict:
    """Queries Spotify window title on Windows to extract current track and artist."""
    if sys.platform != "win32":
        return {"playing": False, "artist": "Spotify", "title": "Not active", "raw": ""}

    spotify_title = None

    def enum_proc(hwnd, lParam):
        nonlocal spotify_title
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if " - " in title and not title.endswith(".exe") and not title.startswith("automatify"):
                cls_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buff, 256)
                if cls_buff.value in ("Chrome_WidgetWin_0", "Chrome_WidgetWin_1") or "spotify" in title.lower():
                    spotify_title = title
            elif title.strip() == "Spotify" and not spotify_title:
                spotify_title = "Spotify"
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

    # Fallback to PowerShell Get-Process if EnumWindows didn't catch a title with ' - '
    if not spotify_title or " - " not in spotify_title:
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-Process Spotify -ErrorAction SilentlyContinue | Select-Object -ExpandProperty MainWindowTitle"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            for line in proc.stdout.splitlines():
                line = line.strip()
                if " - " in line:
                    spotify_title = line
                    break
                elif line and not spotify_title:
                    spotify_title = line
        except Exception:
            pass

    if spotify_title and " - " in spotify_title:
        parts = spotify_title.split(" - ", 1)
        return {
            "playing": True,
            "artist": parts[0].strip(),
            "title": parts[1].strip(),
            "raw": spotify_title,
        }
    elif spotify_title:
        return {
            "playing": False,
            "artist": "Spotify",
            "title": "Paused / Active",
            "raw": spotify_title,
        }

    return {
        "playing": False,
        "artist": "Spotify",
        "title": "Not Playing",
        "raw": "",
    }
