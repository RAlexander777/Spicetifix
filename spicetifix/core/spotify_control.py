import ctypes
import sys

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


def _get_process_name(hwnd: int) -> str:
    """Retrieves executable name of process owning the window handle."""
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    # QUERY_LIMITED_INFORMATION = 0x1000
    h_process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
    if h_process:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(1024)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                path = buf.value
                return path.split("\\")[-1].lower()
        except Exception:
            pass
        finally:
            ctypes.windll.kernel32.CloseHandle(h_process)
    return ""


def get_spotify_now_playing() -> dict:
    """Queries Spotify window title on Windows to extract current track and artist strictly from Spotify.exe."""
    if sys.platform != "win32":
        return {"playing": False, "artist": "Spotify", "title": "Not active", "raw": ""}

    spotify_title = None

    def enum_proc(hwnd, lParam):
        nonlocal spotify_title
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            # Check process name to ONLY accept Spotify.exe
            pname = _get_process_name(hwnd)
            if pname == "spotify.exe":
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if " - " in title:
                    spotify_title = title
                elif title.strip() == "Spotify" and not spotify_title:
                    spotify_title = "Spotify"
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

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
