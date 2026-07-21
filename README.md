# ❯ AUTOMATIFY

> **Automated Spotify & Spicetify Setup, Extension Manager & Terminal Control Center for Windows.**

Automatify is a minimal, terminal-styled desktop application for installing, configuring, and managing **Spotify** and **Spicetify** on Windows. It uses a **Tauri web frontend** with a **Python sidecar API backend**.

---

## ⚡ Features

- **Automated Setup** — Installs Spotify, Spicetify CLI, themes, Marketplace, and configures everything in one click.
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
git clone https://github.com/RAlexander777/automatify.git
cd automatify
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Then open the Tauri shell (needs Rust + Node.js) or just visit `http://127.0.0.1:8765` in a browser.

### Option 2: Download Portable EXE

Download the latest `Automatify.zip` from [Releases](https://github.com/RAlexander777/automatify/releases), extract, and run `Automatify.exe`.

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

Output: `dist/Automatify/` (onedir) + `dist/Automatify.zip` (compressed archive).

---

## 🛠 Project Structure

```
automatify/
├── automatify/
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
