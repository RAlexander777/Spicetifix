# ❯ SPICETIFIX

> **Instalación automatizada de Spotify y Spicetify, gestor de extensiones y centro de control tipo terminal para Windows.**

[English](README.md) · **Español**

Spicetifix es una aplicación de escritorio minimalista con estilo de terminal para instalar, configurar y administrar **Spotify** y **Spicetify** en Windows. Usa una **ventana nativa de pywebview** (WebView2) que envuelve un **backend API en Python (sidecar)** servido en `127.0.0.1`.

---

## ⚡ Características

- **Ventana nativa de escritorio** — Corre en una ventana **pywebview** (WebView2), sin depender del navegador.
- **Instalación automatizada** — Instala Spotify, Spicetify CLI, temas y Marketplace, y configura todo con un clic.
- **Pestaña Marketplace nativa** — Explorá, buscá e instalá/desinstalá extensiones (por ejemplo *Adblock*, *Popup Lyrics*, *Full App Display*, *Loopy Loop*, *Bookmark*, *Auto Skip Explicit*) y temas con un clic, como **archivos locales persistentes** (`.js`).
- **Actualizaciones del Marketplace** — Un filtro "Updates" lista los elementos instalados con una versión más nueva, con "Update all" y orden (nombre / actualizados recientemente / estrellas).
- **Gestión persistente de extensiones** — Descarga los `.js` a `Extensions/` y los registra en `config-xpui.ini` y `spicetify.yaml`, garantizando que sobrevivan a reinicios/caché y compatibilidad total con el respaldo ZIP.
- **Gestor de extensiones** — Detecta automáticamente extensiones `.js`/`.mjs` instaladas con interruptores en vivo.
- **Widget de Spotify en vivo** — Now Playing con controles Anterior / Reproducir-Pausar / Siguiente.
- **14 temas de interfaz** — Cyber Emerald, Dracula, Amber CRT, Nordic Frost, Matrix Void, Tokyo Night, Catppuccin Mocha, y más.
- **Recuperación del sistema** — `spicetify restore backup apply` con un clic tras actualizaciones de Spotify.
- **Diagnóstico del sistema** — Checklist en tiempo real de todas las rutas del sistema, con acciones de reparación en un clic (instalar / cambiar).
- **Backup y restauración** — Exportá/importá toda la configuración de Spicetify como `.zip`.
- **Multiidioma** — Inglés y Español.

---

## 🚀 Inicio rápido

### Opción 1: Ejecutar desde el código fuente

```bash
git clone https://github.com/RAlexander777/Spicetifix.git
cd Spicetifix
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Ejecutar `python main.py` abre una **ventana nativa de pywebview** (WebView2). Si falta el runtime de
WebView2, usa un navegador como respaldo (modo `--app`). También podés visitar `http://127.0.0.1:8765`
directamente en cualquier navegador.

### Opción 2: Descargar el EXE portable

Descargá el último `Spicetifix.zip` desde [Releases](https://github.com/RAlexander777/Spicetifix/releases), descomprimilo y ejecutá `Spicetifix.exe`.

---

## 🧪 Ejecutar tests

```bash
python -m unittest discover -s tests
```

---

## 📦 Compilar el ejecutable

```bash
.\venv\Scripts\activate
pip install pyinstaller
python scripts/build_exe.py
```

Salida: `dist/Spicetifix/` (onedir) + `dist/Spicetifix.zip` (archivo comprimido).

---

## 🛠 Estructura del proyecto

```
spicetifix/
├── spicetifix/
│   ├── __init__.py            # Versión del paquete + User-Agent compartido
│   ├── api.py                 # Servidor HTTP API en Python (sidecar, auth por token)
│   ├── core/
│   │   ├── backup.py          # Exportación/importación de respaldos (.zip)
│   │   ├── config.py          # Manejo de config INI de Spicetify y YAML
│   │   ├── i18n.py            # Textos en inglés / español
│   │   ├── installer.py       # Motor de instalación y recuperación
│   │   ├── marketplace_fetcher.py # Obtención del catálogo del Marketplace
│   │   ├── spotify_control.py # Controles de Spotify vía Win32
│   │   ├── themer.py          # Gestor de temas de Spicetify
│   │   ├── ui_theme.py        # Paletas de temas de la interfaz
│   │   ├── updater.py         # Chequeo de releases de GitHub y descarga del ZIP
│   │   └── utils.py           # Utilidades
├── web/
│   ├── index.html             # UI principal (cargada en la ventana pywebview)
│   ├── app.js                 # Lógica del frontend
│   ├── style.css              # CSS estilo terminal
│   ├── changelog.json         # Notas de versión in-app (espejo de CHANGELOG.md)
│   └── i18n/
│       ├── es.json            # Traducciones al español
│       └── en.json            # Traducciones al inglés
├── scripts/
│   └── build_exe.py           # Script de build con PyInstaller
├── docs/
│   └── DESKTOP_APPS_GUIDE.md  # Guía reutilizable de apps de escritorio
├── tests/                     # Tests unitarios
├── .github/                   # Workflows de CI + release
├── main.py                    # Punto de entrada (ventana pywebview + API)
├── pyproject.toml             # Metadatos de empaquetado de Python
├── requirements.txt           # Dependencias de Python
├── spicetifix.yaml.example    # Config de ejemplo (copia viva: %APPDATA%\Spicetifix\spicetifix.yaml)
└── LICENSE                    # Licencia MIT
```

---

## 📄 Licencia

Distribuido bajo la **Licencia MIT**. Ver [`LICENSE`](LICENSE) para más detalles.

**Autor:** [RAlexander777](https://github.com/RAlexander777) · Copyright (c) 2026 RAlexander777

Si usás, hacés fork o construís sobre este proyecto, mantené el aviso de copyright y acreditá al autor.
