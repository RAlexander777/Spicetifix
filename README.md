# ❯ AUTOMATIFY

> **Automated Spotify & Spicetify Setup, Extension Manager & Terminal Control Center for Windows.**

Automatify is a sleek, minimalist terminal-styled desktop application designed to streamline installing, configuring, recovering, and managing **Spotify** and **Spicetify** on Windows systems.

---

## ⚡ Features

- **Automated Spicetify & Marketplace Setup**: Installs Spotify, Spicetify CLI, themes, marketplace, and configures everything in one click.
- **Spicetify Extension Manager**: Auto-detects installed `.js` and `.mjs` extensions in `%LOCALAPPDATA%\spicetify\Extensions` and `config-xpui.ini` with instant toggles.
- **Live Spotify Now Playing & Control Widget**: Integrated media controller displaying current track & artist with `⏮ PREV`, `⏯ PLAY/PAUSE`, and `⏭ NEXT` controls.
- **Customizable UI Themes**: Choose between 7 themes including *Cyber Emerald*, *Dracula*, *Amber CRT*, *Nordic Frost*, *Matrix Void*, *Light Clean*, and *Light Emerald* with live color previews.
- **Post-Update System Recovery**: One-click recovery (`spicetify restore backup apply`) after Spotify updates break Spicetify patches.
- **System Health Diagnostics**: Real-time checklist verifying `spotify_path`, `prefs_path`, active themes, and extension integrity.
- **Multilingual Support**: English & Spanish i18n out of the box.

---

## 🚀 Quick Start

### Option 1: Run from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/automatify.git
   cd automatify
   ```

2. **Set up Virtual Environment & Install Dependencies**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Launch Automatify**:
   ```bash
   python main.py
   ```

---

## 🛠 Project Structure

```
automatify/
├── automatify/
│   ├── core/
│   │   ├── config.py         # Spicetify INI & user YAML config handling
│   │   ├── i18n.py           # Internationalization strings (en/es)
│   │   ├── installer.py      # Automated setup & recovery engine
│   │   ├── spotify_control.py# Windows Win32 Spotify player controller & reader
│   │   ├── themer.py         # Spicetify themes downloader & manager
│   │   ├── ui_theme.py       # Automatify UI color theme palettes
│   │   └── utils.py          # Process execution & path helpers
│   └── ui/
│       ├── app.py            # Main Application window & event loop
│       ├── home.py           # Dashboard frame with Status cards & Spotify Widget
│       └── settings.py       # Configuration panel & Extension Manager
├── tests/                    # Unit test suite
├── main.py                   # Entry point
├── pyproject.toml            # Project packaging metadata
├── requirements.txt          # Python dependencies
├── LICENSE                   # MIT License
└── README.md
```

---

## 🧪 Running Unit Tests

Run the test suite locally:

```bash
python -m unittest discover -s tests
```

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
