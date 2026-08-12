# 🖥️ Guía de Aplicaciones de Escritorio en Python

> **Estándar personal de desarrollo** para aplicaciones "de escritorio" en Windows con Python.
> Este documento es la referencia a mano para futuros proyectos. Reemplaza la época de
> **CustomTkinter** como estándar único: ahora el patrón recomendado es **Sidecar HTTP + WebView**.

---

## 1. Decidir el enfoque: ¿qué opción usar?

| Opción | UI | Bundle/EXE | Velocidad dev | Cuándo usarla |
|---|---|---|---|---|
| **pywebview** (⭐ recomendado) | HTML/CSS/JS en WebView2 nativo | Chico (~15-25 MB) | Alta | Apps con UI rica, dashboards, catálogos, terminal-style. El estándar actual. |
| **CustomTkinter / ttkbootstrap** | Widgets Tk modernos | Muy chico (~10 MB) | Media | Herramientas simples, utilidades de 1-2 ventanas, formularios. |
| **PyQt6 / PySide6** | Widgets nativos + QWebEngine | Grande (~50-80 MB) | Media | Apps de escritorio "de verdad" con tablas complejas, docks, menus MDI. |
| **Tauri** | WebView + Rust sidecar | Chico | Baja (Rust+Node) | Cuando quieras EXE nativo de alta calidad y estés dispuesto a aprender Rust. |
| **Flet** | Flutter widgets (webview) | Grande | Media | Apps tipo Flutter sin instalar Flutter. Niche. |
| **Electron** | Chromium completo | Muy grande (~150 MB+) | Alta | Apps tipo VS Code. Solo si ya dominas Node y el peso no importa. |

**Regla rápida:**
- ¿UI rica / moderna? → **pywebview** (web HTML/CSS).
- ¿Utilidad chica, sin diseño complejo? → **CustomTkinter** (o ttkbootstrap).
- ¿Necesitas accesibilidad/estilo nativo del SO a nivel widget? → **PyQt6/PySide6**.

---

## 2. Patrón estándar recomendado: "Sidecar HTTP + WebView"

La UI es una **página web servida por un servidor HTTP local en Python** y mostrada en una
**ventana nativa** (WebView2). El frontend y el backend se comunican por **HTTP JSON**.

```
proyecto/
├── main.py                 # Entry point: arranca servidor + ventana
├── <paquete>/
│   ├── api.py              # Servidor HTTP (http.server / Flask / FastAPI)
│   └── core/               # Lógica de negocio (sin GUI)
├── web/                    # Frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
├── scripts/
│   └── build_exe.py        # PyInstaller
└── tests/                  # unittest
```

### Flujo de arranque (crítico)

`pywebview` exige que la GUI corra en el **hilo principal**. El servidor va en un hilo aparte.

```python
import os, secrets, threading, webview
from tuapp.api import make_server

def start():
    token = secrets.token_hex(16)
    server = make_server(port=8765, auth_token=token)   # bindea puerto SÍNCRONO
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:8765/?token={token}"
    window = webview.create_window("MI APP", url, width=900, height=700,
                                   resizable=True, min_size=(700, 600))
    window.events.closed += lambda: os._exit(0)          # cierre limpio
    webview.start()

if __name__ == "__main__":
    start()
```

Puntos clave:
- `HTTPServer(...)` **vincula el puerto en el constructor** → no necesitas `sleep()` para "esperar el servidor".
- El evento `closed` reemplaza hacks tipo "heartbeat con `os._exit(0)`".
- Nunca pongas `webview.start()` en un hilo: GUI = hilo principal.

---

## 3. Seguridad local (obligatorio)

Un servidor HTTP local expone superficie de ataque. Mitigaciones mínimas:

1. **Bind a `127.0.0.1`** — nunca `0.0.0.0`.
2. **Token de sesión aleatorio** — generado al arrancar (`secrets.token_hex(16)`), entregado al
   frontend por query param (`?token=...`), enviado en cada petición como header `X-Auth-Token`.
3. **Validar token en todos los endpoints `/api/*`** → 401 si falla. Los estáticos (`/`, `.css`, `.js`) pueden ser públicos (mismo origen).
4. **CORS restringido** — no usar `Access-Control-Allow-Origin: *`. Reflejar solo orígenes locales
   (`null` para `file://` y `127.0.0.1`). Si el frontend se sirve desde el mismo origen, ni siquiera necesitas CORS.
5. **Validar inputs** en endpoints (URLs solo `http/https`, rutas permitidas, etc.).

```python
_AUTH_TOKEN = ""

def _is_authorized(handler) -> bool:
    return handler.headers.get("X-Auth-Token", "") == _AUTH_TOKEN
```

---

## 4. Frontend

- **Vanilla HTML/CSS/JS** es suficiente para la mayoría (así nació Spicetifix).
- Si la UI crece, usa **Vue/React** y compila a estáticos en `web/`.
- **API relativa**: `const API_BASE = ''` + `fetch('/api/...')`. El frontend vive en el mismo origen que la API.
- Librerías vía CDN (SweetAlert2, Lucide, etc.) funcionan con internet; para offline, descárgalas a `web/vendor/`.
- **Links externos**: en un webview `window.open('...', '_blank')` no abre el navegador. Intercepta
  clicks en `a[target="_blank"]` y `window.open` y encamínalos por un endpoint propio:

```js
// app.js
async function openExternal(url) {
  if (!/^https?:\/\//i.test(url)) return;
  await apiFetch('/api/open/external', 'POST', { url });
}
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[target="_blank"]');
  if (a) { e.preventDefault(); openExternal(a.href); }
});
```

```python
# api.py
elif path == "/api/open/external":
    url = body.get("url", "")
    if not url.startswith(("http://", "https://")):
        self._send_json({"error": "Invalid URL"}, 400); return
    import webbrowser; webbrowser.open(url)
    self._send_json({"status": "ok"})
```

---

## 5. Diálogos nativos (abrir archivos)

- **Opción A (rápida, sigue funcionando en pywebview):** tkinter en un hilo del servidor.
  ```python
  import tkinter as tk
  from tkinter import filedialog
  root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
  path = filedialog.askopenfilename(title="Seleccionar archivo")
  root.destroy()
  ```
- **Opción B (más integrada):** `<input type="file">` en el frontend. En pywebview el input expone
  la ruta real vía la propiedad `pywebviewFullPath` del elemento.

---

## 6. Packaging con PyInstaller

```bash
python scripts/build_exe.py   # onedir + ZIP portable
```

Flags base para un proyecto pywebview:

```python
cmd = [
  "PyInstaller",
  "--noconfirm", "--onedir", "--clean",
  "--name=MiApp",
  "--add-data=web;web",                  # frontend (Windows: ';' separa src;dest)
  "--collect-all=<tu_paquete>",
  "--collect-all=webview",               # pywebview
  "--hidden-import=pythonnet",           # backend Windows de pywebview
  "--hidden-import=clr_loader",
  "--exclude-module=PyQt5", "--exclude-module=PyQt6", "--exclude-module=Pyside6",  # reduce peso
  "main.py",
]
```

Notas:
- `--windowed` para ocultar la consola.
- **WebView2 Runtime** debe estar instalado (preinstalado en Windows 11; descargable para Win10).
- Verifica SIEMPRE el EXE empaquetado: ventana abre, API responde, cierre no deja procesos huérfanos.

---

## 7. Checklist de proyecto nuevo

- [ ] `make_server()` vincula puerto en el constructor; servidor en hilo daemon.
- [ ] `webview.start()` solo en el hilo principal.
- [ ] Token por sesión + header `X-Auth-Token` + 401 en `/api/*`.
- [ ] Bind `127.0.0.1`; CORS no wildcard.
- [ ] Cierre vía `window.events.closed` (sin heartbeats agresivos).
- [ ] Puerto ocupado → mensaje claro (evita doble instancia).
- [ ] Links externos vía endpoint `/api/open/external`.
- [ ] `API_BASE = ''` (mismo origen).
- [ ] Tests con `unittest` en `tests/`; `python -m unittest discover -s tests`.
- [ ] `build_exe.py` con `--collect-all=webview` + excludes.
- [ ] Smoke test del EXE final.

---

## 8. Errores comunes y cómo resolverlos

| Problema | Causa | Solución |
|---|---|---|
| `OSError: [Errno 10048]` al arrancar | Puerto ocupado por otra instancia | Detectar y avisar; guard de single-instance |
| La ventana no abre | WebView2 Runtime ausente | Instalar Evergreen runtime o hacer fallback a navegador (`--app`) |
| `webview.start()` se bloquea | Llamado en un hilo | Mover al hilo principal |
| `window.open` no hace nada | WebView no soporta popups | Interceptar y usar `/api/open/external` |
| EXE enorme | PyInstaller incluye librerías no usadas | `--exclude-module` para PyQt/Selenium/etc. |
| Proceso huérfano tras cerrar ventana | Sin hook de cierre | `window.events.closed` → salir |

---

## 9. Caso de estudio: Spicetifix (v1.2.0)

- Frontend `web/` (HTML/CSS/JS, tema terminal) servido por `http.server` en `spicetifix/api.py`.
- Ventana nativa con **pywebview** (antes: Edge/Chrome `--app`, inestable).
- Token por sesión, `X-Auth-Token`, endpoint `/api/open/external`, cierre por `events.closed`.
- Empaquetado: PyInstaller onedir + ZIP vía `.github/workflows/release.yml`.
- Referencias útiles: `main.py`, `spicetifix/api.py`, `scripts/build_exe.py`, `docs/`.
