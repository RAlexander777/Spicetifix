# ❯ SPICETIFIX

> **Automated Spotify & Spicetify Setup, Extension Manager & Terminal Control Center for Windows.**

Spicetifix is a minimal, terminal-styled desktop application for installing, configuring, and managing **Spotify** and **Spicetify** on Windows. It uses a **Tauri web frontend** with a **Python sidecar API backend**.

---

## ⚡ Features

- **Automated Setup** — Installs Spotify, Spicetify CLI, themes, Marketplace, and configures everything in one click.
- **Native Marketplace Tab** — Browse, search, and 1-click install/uninstall extensions (e.g. *Adblock*, *Popup Lyrics*, *Full App Display*, *Loopy Loop*, *Bookmark*, *Auto Skip Explicit*) and themes directly as **persistent local files** (`.js`).
- **Persistent Extension Management** — Automatically downloads `.js` files to `Extensions/` and registers them in `config-xpui.ini` & `spicetifix.yaml`, ensuring 100% reboot/cache survival and full ZIP backup compatibility.
- **Extension Manager** — Auto-detects installed `.js`/`.mjs` extensions with live toggles.
- **Live Spotify Widget** — Now Playing display with Prev / Play-Pause / Next controls.
- **14 UI Themes** — Cyber Emerald, Dracula, Amber CRT, Nordic Frost, Matrix Void, Tokyo Night, Catppuccin Mocha, and more.
- **System Recovery** — One-click `spicetify restore backup apply` after Spotify updates.
- **Health Diagnostics** — Real-time checklist verifying all system paths.
- **Backup & Restore** — Export/import full Spicetify configuration as `.zip`.
- **Multilingual** — English & Spanish.

---

## 🚀 Quick Start

### Option 1: Run from Source

```bash
git clone https://github.com/RAlexander777/Spicetifix.git
cd Spicetifix
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Then open the Tauri shell (needs Rust + Node.js) or just visit `http://127.0.0.1:8765` in a browser.

### Option 2: Download Portable EXE

Download the latest `Spicetifix.zip` from [Releases](https://github.com/RAlexander777/Spicetifix/releases), extract, and run `Spicetifix.exe`.

---

## 🧪 Running Tests

```bash
python -m unittest discover -s tests
```

---

## 📦 Building Executable

```bash
.\venv\Scripts\activate
pip install pyinstaller
python scripts/build_exe.py
```

Output: `dist/Spicetifix/` (onedir) + `dist/Spicetifix.zip` (compressed archive).

---

## 🛠 Project Structure

```
spicetifix/
├── spicetifix/
│   ├── api.py                 # Python HTTP API server (sidecar)
│   ├── core/
│   │   ├── config.py          # Spicetify INI & YAML config handling
│   │   ├── i18n.py            # English / Spanish strings
│   │   ├── installer.py       # Installation & recovery engine
│   │   ├── spotify_control.py # Windows Win32 Spotify controls
│   │   ├── themer.py          # Spicetify theme manager
│   │   ├── ui_theme.py        # UI theme palettes
│   │   └── utils.py           # Helpers
├── src-tauri/
│   └── tauri.conf.json        # Tauri configuration
├── web/
│   ├── index.html             # Main UI (loaded in Tauri webview)
│   ├── app.js                 # Frontend logic
│   └── style.css              # Terminal-styled CSS
├── scripts/
│   └── build_exe.py           # PyInstaller build script
├── tests/                     # Unit tests
├── main.py                    # Entry point (starts API server)
├── pyproject.toml             # Python packaging metadata
├── requirements.txt           # Python dependencies
└── LICENSE                    # MIT License
```

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
