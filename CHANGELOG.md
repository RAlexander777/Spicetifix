# Changelog

All notable changes to this project are documented here. The app also shows
this changelog in the About dialog (see `web/changelog.json`, which mirrors
this file for the in-app view).

## [1.7.7] - 2026-10-07

### Added
- The Marketplace catalog now also lists **Custom Apps** (GitHub topic
  `spicetify-apps`) under a new **Apps** category. App cards are browse-only and
  open the repository, matching the official Marketplace, which does not install
  apps (their manifests have no standard entry point/install layout).
- Marketplace cards and the extension/app manager now show the **installed
  version** next to the **latest available version**, with an "update available"
  flag. The version is the GitHub release tag when the repo publishes releases,
  otherwise the repo's last-updated date. Install metadata (source repo, branch,
  dates and tag) is now recorded in `spicetify.yaml` when installing.

### Fixed
- Marketplace catalog requests now retry transient network timeouts (with
  backoff). A single flaky GitHub call was enough to drop a whole category —
  usually Extensions, since it is fetched first — leaving it empty in the
  Marketplace.
- Version lookups no longer call the GitHub REST API. Without a token that API
  allows only 60 requests/hour, and the per-item requests were exhausting it,
  which made the catalog search (and therefore the whole Marketplace) return
  errors/empty. Release tags are now read from the github.com HTML redirect,
  and a rate-limited catalog search falls back to the last cached catalog
  instead of showing nothing. Set a `GITHUB_TOKEN` env var to raise the search
  limit further.
- Extensions and Custom Apps no longer wait for the (slow) Marketplace catalog
  build to finish: the list renders immediately and upgrades the friendly titles
  in the background, so a cold/slow catalog can't leave the list empty.
- Marketplace catalog builds are much faster (shared HTTP session with connection
  reuse + higher fetch concurrency), and API requests now time out instead of
  hanging the UI indefinitely.
- The "Open Spotify" button is now guarded: it disables while opening, has a short
  cooldown, and the server ignores rapid repeats, so spamming it no longer
  launches several instances and spikes CPU.
- Spicetify CLI is now updated on install when a newer release exists, instead of
  being skipped when already present. The CLI release zip also ships the bundled
  CustomApps (*lyrics-plus*, *reddit*, *new-releases*) and the built-in Extensions,
  so those stayed frozen on the first installed version and never updated.
- Marketplace reinstall now overwrites the existing files, so an already-installed
  Marketplace actually updates (previously the freshly downloaded files were
  discarded and the old version was kept).

## [1.7.6] - 2026-09-30

### Fixed
- Multi-threaded API server: a slow request no longer freezes `/api/status` and the UI.
- Connection badge now reflects only `/api/status`, fixing false `[ DISCONNECTED ]`.
- CHANGES dialog shows a loading state and a RETRY button instead of loading empty.

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
