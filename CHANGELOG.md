# Changelog

All notable changes to this project are documented here. The app also shows
this changelog in the About dialog (see `web/changelog.json`, which mirrors
this file for the in-app view).

## [1.7.5] - 2026-09-15

### Added
- Immediate visual loading feedback: `FULL INSTALL / UPDATE` and `RECOVER SYSTEM` buttons now display an animated spinner with busy labels (`INSTALLING...` / `RECOVERING...`) instantly on click.
- Indeterminate glowing progress bar animation during the initialization phase of long background operations.

### Fixed
- Fixed Windows Defender detection: replaced PowerShell `iwr | iex` script execution with native GitHub release zip download and extraction via `requests`.
- Disabled UPX compression in build scripts and PyInstaller spec to avoid antivirus heuristic false positives.
- Fixed Spicetify re-apply post-Spotify-update: recovery cascade now automatically restores `marketplace` custom app and `adblock.js` extension if missing on disk.

## [1.7.4] - 2026-08-26

### Fixed
- Extensions with nested paths (e.g. `adblock/adblock.js`) are now installed flattened
  to `adblock.js`, matching how Spicetify v2 injects extensions. The patched client
  previously referenced a subfolder path that does not exist after `apply`, so the
  extension was silently skipped — adblock showed as active while audio ads kept playing.
- Extension detection now reports file basenames only, and the marketplace catalog shows
  flattened filenames, so installed state stays accurate.

## [1.7.0] - 2026-08-20

### Added
- Changelog is now one click away: a dedicated CHANGES button in the header.
- Update dialog shows the release notes and the installed → available version.
- "View release on GitHub" link in the update dialog, alongside the direct ZIP download.

### Fixed
- The "new version" button now glows 3 times instead of blinking forever.
- The app no longer waits ~3 seconds to close (WebView2 private mode disabled).

## [1.6.0] - 2026-08-14

### Changed
- License attribution: copyright notice now names the author (RAlexander777) instead
  of the generic "spicetify contributors", so derivatives must credit the author.
- Packaging metadata now declares the MIT license and the author.

## [1.5.0] - 2026-08-14

### Fixed
- Marketplace install/uninstall now runs `spicetify apply` with a recovery cascade
  (`restore backup apply` → `backup apply` → `apply`) so a Spotify auto-update can no
  longer silently block the change from taking effect.
- Uninstall now verifies the extension is actually gone after `apply` and reports a
  clear error if it is still present.
- Extensions and custom apps configured outside Spicetifix (e.g. via `spicetify config`)
  are preserved when rebuilding the config instead of being silently dropped.

### Changed
- Close all Spotify helper processes (`SpotifyWebHelper.exe`, `SpotifyCrashService.exe`,
  etc.) before patching, not just `Spotify.exe`.
- Show the app version and release notes (changelog) inside the About dialog.

## [1.4.0] - 2026-08-12

### Added
- JSON-based i18n (en/es) loaded dynamically.

### Fixed
- Marketplace install/uninstall: close Spotify before `spicetify apply` and report the
  real failure code instead of a silent "ok".

### Changed
- Visual hierarchy rework for cards and sections.
- Removed dead assets and leftover project files.

## [1.3.0] - 2026-08-05

### Added
- API auth token and path-traversal protection for static files.
- Built-in auto-update checker with release download.

### Fixed
- Marketplace extensions installed in subfolders.
- Recover System now cascades `spicetify restore/backup/apply` commands.
- pywebview bundled properly so the native window works.

## [1.2.0] - 2026-07-22

### Added
- Native pywebview window instead of a browser tab.
- API token authentication between the UI and the Python sidecar.

## [1.1.0] - 2026-07-20

### Added
- Marketplace tab with pagination, search, filters and GitHub links.
- Connection error UI when the app loses its backend.

### Fixed
- Heartbeat so the app stays alive.

## [1.0.0] - 2026-07-18

### Added
- Automated installer for Spotify, Spicetify CLI, Marketplace and Themes.
- Terminal-styled control center: status, extensions, custom apps, themes and backups.
- Integrated Spotify player controls via native Win32 API.
- Backup export and import (.zip).
