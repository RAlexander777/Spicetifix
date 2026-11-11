const API_BASE = '';
const AUTH_TOKEN = new URLSearchParams(window.location.hash.slice(1)).get('token') || '';

const GITHUB_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="lucide gh-icon"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>`;

let currentUITheme = 'emerald';
let currentLang = 'en';
let systemConfig = {};
let isConnected = true;
let isConsoleExpanded = false;
let isUserScrolledUp = false;
let lastRenderedLogs = '';

function setConsoleExpanded(expanded, persist = true) {
  isConsoleExpanded = !!expanded;
  const panel = document.getElementById('console-panel');
  const btnToggle = document.getElementById('btn-toggle-console');
  const btnHeader = document.getElementById('btn-header-console');
  const toggleIcon = document.getElementById('console-toggle-icon');
  const bodyEl = document.body;

  if (!panel) return;

  if (isConsoleExpanded) {
    panel.classList.remove('is-collapsed');
    panel.classList.add('is-expanded');
    bodyEl.classList.add('has-console-expanded');
    if (btnToggle) btnToggle.setAttribute('aria-expanded', 'true');
    if (toggleIcon) toggleIcon.setAttribute('data-lucide', 'chevron-down');
    if (btnHeader) btnHeader.classList.add('active');

    const container = document.getElementById('console-box-container');
    if (container && !isUserScrolledUp) {
      setTimeout(() => {
        container.scrollTop = container.scrollHeight;
      }, 50);
    }
  } else {
    panel.classList.remove('is-expanded');
    panel.classList.add('is-collapsed');
    bodyEl.classList.remove('has-console-expanded');
    if (btnToggle) btnToggle.setAttribute('aria-expanded', 'false');
    if (toggleIcon) toggleIcon.setAttribute('data-lucide', 'chevron-up');
    if (btnHeader) btnHeader.classList.remove('active');
  }

  if (window.lucide && lucide.createIcons) lucide.createIcons();

  if (persist) {
    try {
      localStorage.setItem('spicetifix_console_expanded', isConsoleExpanded ? 'true' : 'false');
    } catch (_) {}
  }
}

function toggleConsole() {
  setConsoleExpanded(!isConsoleExpanded);
}
let consecutiveErrors = 0;
let statusErrors = 0;
let appVersion = '';
let lastTrack = null;
let wasWorking = false;

let isSpotifyInstalled = false;
let isSpicetifyInstalled = false;
let currentAction = null;

let I18N = { es: {}, en: {} };
let I18N_READY = false;

async function loadI18n() {
  if (I18N_READY) return;
  try {
    const [es, en] = await Promise.all([
      fetch('i18n/es.json').then(r => r.json()),
      fetch('i18n/en.json').then(r => r.json()),
    ]);
    I18N = { es, en };
    I18N_READY = true;
  } catch (err) {
    console.warn('i18n load failed:', err);
  }
}

function t(key) {
  const dict = I18N[currentLang] || I18N.es || {};
  return dict[key] !== undefined ? dict[key] : key;
}

async function apiFetch(endpoint, method = 'GET', body = null, timeoutMs = 30000) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (AUTH_TOKEN) {
    options.headers['X-Auth-Token'] = AUTH_TOKEN;
  }
  if (body) {
    options.body = JSON.stringify(body);
  }
  // Never let a single request hang the UI forever (e.g. a slow catalog build).
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  options.signal = controller.signal;
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) {
      consecutiveErrors++;
      console.warn(`API error (${endpoint}):`, res.status, data);
      return data ? { error: data.error || `HTTP ${res.status}`, ...data } : null;
    }
    consecutiveErrors = 0;
    return data;
  } catch (err) {
    consecutiveErrors++;
    console.warn(`API error (${endpoint}):`, err);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function openExternal(url) {
  if (!/^https?:\/\//i.test(url)) return;
  await apiFetch('/api/open/external', 'POST', { url });
}

let pendingUpdate = null;

// ---- Background action feedback -----------------------------------------
// Poll /api/status until the server-side worker finishes, then run onIdle.
function waitForBackendIdle(onIdle, { graceMs = 1500, maxMs = 180000 } = {}) {
  const started = Date.now();
  let sawWorking = false;
  const iv = setInterval(async () => {
    const data = await apiFetch('/api/status');
    const working = !!(data && data.is_working);
    if (working) sawWorking = true;
    const elapsed = Date.now() - started;
    if ((sawWorking && !working) || elapsed > maxMs || (!working && elapsed > graceMs)) {
      clearInterval(iv);
      onIdle();
    }
  }, 700);
}

// Show a subtle spinner on a chip button, then a brief check, then restore.
async function flashButtonBusy(btn, endpoint, onDone) {
  if (!btn || btn.dataset.busy === '1') return;
  btn.dataset.busy = '1';
  btn.disabled = true;
  const label = btn.querySelector('span');
  const original = label ? label.innerHTML : '';
  if (label) label.innerHTML = `${brailleHTML()} ${original}`;
  try {
    await apiFetch(endpoint, 'POST');
  } catch (_) { /* failures surface in the console */ }
  waitForBackendIdle(() => {
    if (onDone) onDone();
    if (label) label.innerHTML = `✓ ${original}`;
    setTimeout(() => {
      if (label) label.innerHTML = original;
      btn.disabled = false;
      delete btn.dataset.busy;
    }, 1600);
  });
}

async function checkForUpdate() {
  const data = await apiFetch('/api/update/check');
  const btn = document.getElementById('btn-update-check');
  if (!data || !data.update) {
    if (btn) btn.style.visibility = 'hidden';
    return;
  }
  pendingUpdate = data.update;
  if (btn) {
    btn.style.visibility = 'visible';
    const lbl = document.getElementById('lbl-update-check');
    if (lbl) {
      lbl.textContent = t('update_btn');
    }
    const current = data.update.current_version || '';
    const latest = data.update.latest_version || '';
    if (current && latest) {
      btn.title = `v${current} → v${latest}`;
    }
  }
}

function openUpdateModal() {
  if (!pendingUpdate) return;
  if (typeof Swal !== 'undefined') {
    const esc = (str) => (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const notes = (pendingUpdate.notes || '').trim();
    const cur = pendingUpdate.current_version || '';
    const latest = pendingUpdate.latest_version || '';
    let html = t('update_message').replace('{v}', `<b>${esc(latest)}</b>`);
    if (cur) {
      html += `<div class="cyber-versions">${esc(cur)} → <b>${esc(latest)}</b></div>`;
    }
    if (notes) {
      const lines = notes.split('\n').map(l => {
        const clean = esc(l.trim());
        if (clean.startsWith('-') || clean.startsWith('*')) {
          return `<li>${clean.replace(/^[-*]\s*/, '')}</li>`;
        }
        if (clean.startsWith('#')) {
          return `<h5 class="cyber-notes-heading">${clean.replace(/^#+\s*/, '')}</h5>`;
        }
        return clean ? `<li>${clean}</li>` : '';
      }).join('');
      html += `<div class="cyber-notes"><div class="cyber-notes-title">${t('update_new_in').replace('{v}', `<b>${esc(pendingUpdate.latest_version)}</b>`)}</div><ul>${lines}</ul></div>`;
    }
    const footer = pendingUpdate.release_url
      ? `<a href="#" class="cyber-swal-gh-link" data-release-url="${esc(pendingUpdate.release_url)}">${GITHUB_ICON_SVG} ${t('update_view_release')}</a>`
      : '';
    Swal.fire({
      title: t('update_title'),
      html,
      footer,
      showCancelButton: true,
      confirmButtonText: t('update_download'),
      cancelButtonText: t('update_dismiss'),
      buttonsStyling: false,
      customClass: {
        popup: 'cyber-swal-popup',
        title: 'cyber-swal-title',
        htmlContainer: 'cyber-swal-html',
        confirmButton: 'btn btn-accent',
        cancelButton: 'btn btn-outline',
      },
      didRender: (popup) => {
        const link = popup.querySelector('.cyber-swal-gh-link');
        if (link) {
          link.addEventListener('click', (e) => {
            e.preventDefault();
            openExternal(link.getAttribute('data-release-url'));
          });
        }
      },
    }).then((result) => {
      if (pendingUpdate && result.isConfirmed) runUpdateDownload();
    });
  }
}

async function runUpdateDownload() {
  if (!pendingUpdate || !pendingUpdate.asset_url) return;
  Swal.fire({
    title: t('update_downloading'),
    html: `<div style="font-size:1.5rem">${brailleHTML()}</div>`,
    allowOutsideClick: false,
    allowEscapeKey: false,
    showConfirmButton: false,
    customClass: { popup: 'cyber-swal-popup', title: 'cyber-swal-title', htmlContainer: 'cyber-swal-html' },
  });
  await apiFetch('/api/update/download', 'POST', { asset_url: pendingUpdate.asset_url });
  waitForBackendIdle(() => {
    pollStatus();
    Swal.fire({
      title: t('update_downloaded_title'),
      text: t('update_downloaded_help'),
      showCancelButton: true,
      confirmButtonText: t('update_open_folder'),
      cancelButtonText: t('btn_close'),
      buttonsStyling: false,
      customClass: {
        popup: 'cyber-swal-popup',
        title: 'cyber-swal-title',
        htmlContainer: 'cyber-swal-html',
        confirmButton: 'btn btn-accent',
        cancelButton: 'btn btn-outline',
      },
    }).then((r) => {
      if (r.isConfirmed) apiFetch('/api/open/folder', 'POST', { target: 'downloads' });
    });
  });
}

function toast(message, icon = 'success') {
  if (typeof Swal === 'undefined') return;
  Swal.fire({
    toast: true,
    position: 'bottom-end',
    icon,
    title: message,
    showConfirmButton: false,
    timer: 2600,
    timerProgressBar: true,
    customClass: { popup: 'cyber-toast' },
  });
}

// Show SweetAlert Cyberpunk Dialog
function showCyberAlert(title, text, confirmText, cancelText, onConfirm) {
  if (typeof Swal !== 'undefined') {
    Swal.fire({
      title,
      text,
      showCancelButton: true,
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
      buttonsStyling: false,
      customClass: {
        popup: 'cyber-swal-popup',
        title: 'cyber-swal-title',
        htmlContainer: 'cyber-swal-html',
        confirmButton: 'btn btn-danger-heavy',
        cancelButton: 'btn btn-outline',
      },
    }).then((result) => {
      if (result.isConfirmed && onConfirm) {
        onConfirm();
      }
    });
  } else {
    if (confirm(`${title}\n\n${text}`)) {
      if (onConfirm) onConfirm();
    }
  }
}

// Apply Language to UI
async function applyLanguage(lang) {
  await loadI18n();
  currentLang = I18N[lang] ? lang : 'es';
  const t = I18N[currentLang];

  const setTxt = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };
  const setPh = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.placeholder = text;
  };
  const setTitle = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.title = text;
  };
  const setAria = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.setAttribute('aria-label', text);
  };

  setTxt('system-badge', t.system_ready);
  setTxt('lbl-open-spotify', t.open_spotify);
  setTxt('lbl-refresh-status', t.refresh_btn);
  setTxt('lbl-open-options', t.options_btn);
  setTxt('lbl-open-about', t.about_btn);
  setTxt('lbl-update-check', t.update_btn);
  setTxt('lbl-ui-theme', t.ui_theme_lbl);
  setTxt('lbl-quick-access', t.quick_access);
  setTxt('lbl-spicetify-dir', t.spicetify_dir);
  setTxt('lbl-themes-dir', t.themes_dir);
  setTxt('lbl-export-backup', t.export_backup);
  setTxt('lbl-import-backup', t.import_backup);
  setTxt('lbl-tab-dashboard', t.tab_dashboard);
  setTxt('lbl-tab-marketplace', t.tab_marketplace);
  setTxt('lbl-dock-spotify', t.open_spotify);
  setTxt('lbl-prev', t.prev_btn);
  setTxt('lbl-play', t.play_btn);
  setTxt('lbl-next', t.next_btn);
  setTxt('sec-title-status', t.sec_status);
  setTxt('sec-title-health', t.sec_health);
  setTxt('lbl-card-theme-title', t.card_theme_title);
  setTxt('sec-title-actions', t.sec_actions);
  setTxt('lbl-btn-install', t.btn_install);
  setTxt('lbl-btn-recover', t.btn_recover);
  setTxt('sec-title-exts', t.sec_exts);
  setTxt('lbl-exts-header', t.lbl_exts_header);
  setTxt('lbl-btn-refresh-exts', t.btn_refresh);
  setTxt('lbl-btn-apply-exts', t.btn_apply_exts);
  setTxt('sec-title-logs', t.sec_logs);
  setTxt('lbl-copy-logs', t.lbl_copy_logs);
  setTxt('lbl-clear-logs', t.lbl_clear_logs);
  setTxt('lbl-save-logs', t.lbl_save_logs);
  setTxt('lbl-open-changelog', t.changelog_btn);
  setTxt('lbl-toggle-console', t.lbl_toggle_console);
  setTxt('lbl-scroll-bottom', t.lbl_scroll_bottom);
  setTxt('btn-close-changelog-footer', t.btn_close);
  setTxt('track-status-text', t.dock_idle);
  setTxt('mp-loading-msg', t.mp_loading);
  setTxt('console-output', t.console_prompt);
  setTxt('console-preview-text', t.console_prompt);
  setTxt('lbl-modal-opt-title', t.modal_opt_title);
  setTxt('opt-sec-gen', t.opt_sec_gen);
  setTxt('lbl-lang', t.lbl_lang);
  setTxt('lbl-spicetify-theme', t.lbl_spicetify_theme);
  setTxt('lbl-color-scheme', t.lbl_color_scheme);
  setTxt('opt-sec-flags', t.opt_sec_flags);
  setTxt('lbl-flag-css', t.lbl_flag_css);
  setTxt('lbl-flag-colors', t.lbl_flag_colors);
  setTxt('lbl-flag-assets', t.lbl_flag_assets);
  setTxt('lbl-flag-devtools', t.lbl_flag_devtools);
  setTxt('lbl-flag-sentry', t.lbl_flag_sentry);
  setTxt('desc-flag-css', t.desc_flag_css);
  setTxt('desc-flag-colors', t.desc_flag_colors);
  setTxt('desc-flag-assets', t.desc_flag_assets);
  setTxt('desc-flag-devtools', t.desc_flag_devtools);
  setTxt('desc-flag-sentry', t.desc_flag_sentry);
  setTxt('desc-spicetify-theme', t.desc_spicetify_theme);
  setTxt('desc-color-scheme', t.desc_color_scheme);
  setTxt('lbl-auto-backup', t.lbl_auto_backup);
  setTxt('desc-auto-backup', t.desc_auto_backup);
  setTxt('opt-sec-danger', t.opt_sec_danger);
  setTxt('lbl-btn-spicetify-apply', t.btn_spicetify_apply);
  setTxt('lbl-btn-uninstall-spicetify', t.btn_uninstall_spicetify);
  setTxt('lbl-btn-uninstall-spotify', t.btn_uninstall_spotify);
  setTxt('btn-save-options', t.btn_save_options);
  setTxt('btn-close-about-footer', t.btn_close);
  setTxt('lbl-refresh-catalog', t.mp_refresh);
  setTxt('lbl-sec-title-mp', t.sec_title_mp);
  setTxt('lbl-mp-filter-all', t.mp_filter_all);
  setTxt('lbl-mp-filter-ext', t.mp_filter_ext);
  setTxt('lbl-mp-filter-theme', t.mp_filter_theme);
  setTxt('lbl-mp-filter-app', t.mp_filter_app);
  setTxt('lbl-mp-filter-installed', t.mp_filter_installed);
  setTxt('lbl-mp-filter-updates', t.mp_filter_updates);
  setTxt('lbl-mp-update-all', t.mp_update_all);
  setTxt('lbl-mp-prev', t.mp_prev);
  setTxt('lbl-mp-next', t.mp_next);
  setTxt('lbl-mp-sort-relevance', t.mp_sort_relevance);
  setTxt('lbl-mp-sort-name', t.mp_sort_name);
  setTxt('lbl-mp-sort-updated', t.mp_sort_updated);
  setTxt('lbl-mp-sort-stars', t.mp_sort_stars);
  setPh('mp-search-input', t.mp_search_placeholder);

  // Tooltips (title attributes) & accessibility labels
  setTitle('btn-open-spotify', t.tip_open_spotify);
  setTitle('btn-refresh-status', t.tip_refresh_status);
  setTitle('btn-header-console', t.tip_toggle_console);
  setTitle('btn-toggle-console', t.tip_toggle_console);
  setTitle('btn-open-changelog', t.tip_changelog);
  setTitle('btn-update-check', t.tip_update);
  setTitle('console-header', t.tip_console_header);
  setTitle('btn-copy-logs', t.tip_copy_logs);
  setTitle('btn-clear-logs', t.tip_clear_logs);
  setTitle('btn-save-logs', t.tip_save_logs);
  setTitle('btn-scroll-bottom', t.tip_scroll_bottom);
  setTitle('btn-prev', t.tip_prev);
  setTitle('btn-play', t.tip_play);
  setTitle('btn-next', t.tip_next);
  setTitle('btn-dock-spotify', t.tip_dock_spotify);
  setAria('console-panel', t.aria_console_logs);

  document.documentElement.lang = currentLang;

  // About modal texts
  const modalAboutTitle = document.querySelector('#about-modal h2');
  if (modalAboutTitle) modalAboutTitle.textContent = t.modal_about_title;

  const aboutDesc = document.querySelector('.about-desc');
  if (aboutDesc) aboutDesc.textContent = t.about_desc;

  const details = document.querySelectorAll('.detail-item strong');
  if (details.length >= 6) {
    details[0].textContent = t.about_author_lbl;
    details[1].textContent = t.about_license_lbl;
    details[2].textContent = t.about_engine_lbl;
    details[3].textContent = t.about_repo_lbl;
    details[4].textContent = t.about_spicetify_web;
    details[5].textContent = t.about_spotify_web;
  }

  const featH4 = document.querySelector('.about-features h4');
  if (featH4) featH4.textContent = t.about_features_title;

  const changelogH4 = document.getElementById('changelog-title');
  if (changelogH4) changelogH4.textContent = t.about_changelog_title;

  const featLis = document.querySelectorAll('.about-features li');
  if (featLis.length >= 5) {
    featLis[0].textContent = t.about_feat_1;
    featLis[1].textContent = t.about_feat_2;
    featLis[2].textContent = t.about_feat_3;
    featLis[3].textContent = t.about_feat_4;
    featLis[4].textContent = t.about_feat_5;
  }

  const langSelect = document.getElementById('select-lang');
  if (langSelect && langSelect.value !== currentLang) {
    langSelect.value = currentLang;
  }
}

// Set Theme class on body
function applyUITheme(themeKey) {
  currentUITheme = themeKey;
  document.body.className = `theme-${themeKey}`;
  const select = document.getElementById('ui-theme-select');
  if (select && select.value !== themeKey) {
    select.value = themeKey;
  }
}

function updateActionButtons(isWorking) {
  const t = I18N[currentLang] || {};
  const btnInstall = document.getElementById('btn-install');
  const btnRecover = document.getElementById('btn-recover');

  if (isWorking) {
    if (currentAction === 'recover' && btnRecover) {
      btnRecover.classList.add('is-busy');
      btnRecover.innerHTML = `<span class="btn-spinner" aria-hidden="true"></span> <span>${t.btn_recovering}</span>`;
    } else if (btnInstall) {
      btnInstall.classList.add('is-busy');
      btnInstall.innerHTML = `<span class="btn-spinner" aria-hidden="true"></span> <span>${t.btn_installing}</span>`;
    }
  } else {
    currentAction = null;
    if (btnInstall) {
      btnInstall.classList.remove('is-busy');
      btnInstall.disabled = false;
      btnInstall.innerHTML = `<i data-lucide="download-cloud"></i> <span id="lbl-btn-install">${t.btn_install}</span>`;
    }
    if (btnRecover) {
      btnRecover.classList.remove('is-busy');
      btnRecover.disabled = false;
      btnRecover.innerHTML = `<i data-lucide="rotate-ccw"></i> <span id="lbl-btn-recover">${t.btn_recover}</span>`;
    }
    if (window.lucide && lucide.createIcons) lucide.createIcons();
  }
}

function healthActionFor(label) {
  if (label === 'spotify_path' || label === 'config_file' || label === 'spicetify_exe') {
    return {
      text: t('health_fix_install'),
      onClick: () => showCyberAlert(
        t('health_fix_title'), t('health_fix_msg'), t('health_fix_install'), t('btn_cancel'),
        () => startInstall(),
      ),
    };
  }
  if (label === 'theme') {
    return { text: t('health_fix_theme'), onClick: () => openOptionsModal() };
  }
  return null;
}

function startInstall() {
  setConsoleExpanded(true);
  currentAction = 'install';
  updateActionButtons(true);
  apiFetch('/api/install', 'POST').then((res) => {
    if (!res || res.error) updateActionButtons(false);
    pollStatus();
  });
}

function renderHealth(health) {
  const grid = document.getElementById('health-grid');
  if (!grid || !Array.isArray(health)) return;
  grid.innerHTML = '';
  health.forEach(h => {
    const row = document.createElement('div');
    row.className = `health-item ${h.ok ? 'ok' : 'err'}`;
    const dot = document.createElement('span');
    dot.className = 'health-dot';
    const label = document.createElement('span');
    label.className = 'health-label';
    label.textContent = h.label;
    const detail = document.createElement('span');
    detail.className = 'health-detail';
    detail.textContent = h.detail || '';
    detail.title = h.detail || '';
    row.append(dot, label, detail);
    if (!h.ok) {
      const act = healthActionFor(h.label);
      if (act) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'health-action btn btn-small btn-outline';
        btn.textContent = act.text;
        btn.addEventListener('click', act.onClick);
        row.appendChild(btn);
      }
    }
    grid.appendChild(row);
  });
}

function renderHealthLoading() {
  const grid = document.getElementById('health-grid');
  if (grid && !grid.querySelector('.health-item')) {
    grid.innerHTML = Array.from({ length: 6 }).map(() => `
      <div class="health-item">
        <span class="skeleton sk-dot"></span>
        <span class="skeleton sk-label"></span>
        <span class="skeleton sk-detail"></span>
      </div>`).join('');
  }
}

function renderDockLoading() {
  const trackInfo = document.getElementById('track-info');
  if (trackInfo) trackInfo.innerHTML = brailleHTML(t('loading_spotify'));
}

// ---- Shared braille spinner ---------------------------------------------
// One ticker animates every spinner on screen: the console status pill, the
// header badge, busy buttons (.btn-spinner), the marketplace loader
// (.mp-spinner) and inline <span class="braille" data-suffix="..."> nodes.
const SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
const SPINNER_SELECTOR = '.braille, .btn-spinner, .mp-spinner';
const prefersReducedMotion = (typeof window.matchMedia === 'function')
  ? window.matchMedia('(prefers-reduced-motion: reduce)')
  : null;
let spinnerFrame = 0;
let spinnerTimer = null;

function paintSpinners(glyph) {
  document.querySelectorAll(SPINNER_SELECTOR).forEach(el => {
    const suffix = el.dataset.suffix;
    el.textContent = suffix ? `${glyph} ${suffix}` : glyph;
  });
}

function spinTick() {
  if (document.querySelectorAll(SPINNER_SELECTOR).length === 0) {
    clearInterval(spinnerTimer);
    spinnerTimer = null;
    return;
  }
  paintSpinners(SPINNER_FRAMES[spinnerFrame++ % SPINNER_FRAMES.length]);
}

function ensureSpinners() {
  // Respect reduced-motion: draw a static glyph instead of animating.
  if (prefersReducedMotion && prefersReducedMotion.matches) {
    paintSpinners(SPINNER_FRAMES[0]);
    return;
  }
  if (!spinnerTimer && document.querySelector(SPINNER_SELECTOR)) {
    spinTick();
    spinnerTimer = setInterval(spinTick, 90);
  }
}

// Kick the ticker off as soon as any spinner element is inserted by a render.
const spinnerObserver = new MutationObserver(mutations => {
  for (const m of mutations) {
    for (const node of m.addedNodes) {
      if (node.nodeType === 1 &&
          (node.matches(SPINNER_SELECTOR) || node.querySelector(SPINNER_SELECTOR))) {
        ensureSpinners();
        return;
      }
    }
  }
});

function brailleHTML(suffix = '') {
  const safe = String(suffix).replace(/&/g, '&amp;').replace(/"/g, '&quot;');
  return `<span class="braille" data-suffix="${safe}"></span>`;
}

// Subtle console status: a braille spinner while working, a muted mark when idle.
function setConsoleStatus(isWorking) {
  const pill = document.getElementById('console-status-pill');
  if (!pill) return;
  if (isWorking) {
    pill.classList.add('braille', 'pill-working');
    pill.classList.remove('pill-ready');
    pill.dataset.suffix = t('status_working');
    ensureSpinners();
  } else {
    pill.classList.remove('braille', 'pill-working');
    pill.classList.add('pill-ready');
    delete pill.dataset.suffix;
    pill.textContent = `✓ ${t('status_ready')}`;
  }
}

function setBadgeState(spinning, text, className) {
  const badge = document.getElementById('system-badge');
  if (!badge) return;
  badge.className = className;
  if (spinning) {
    badge.classList.add('braille');
    badge.dataset.suffix = text;
    ensureSpinners();
  } else {
    badge.classList.remove('braille');
    delete badge.dataset.suffix;
    badge.textContent = text;
  }
}

// Fetch and render status
async function pollStatus() {
  const data = await apiFetch('/api/status');
  if (!data || data.error) {
    statusErrors++;
    if (statusErrors <= 1) {
      setBadgeState(true, I18N[currentLang].status_connecting, 'badge badge-connecting');
    } else {
      setBadgeState(false, I18N[currentLang].system_disconnected, 'badge badge-disconnected');
    }
    const trackInfo = document.getElementById('track-info');
    trackInfo.textContent = I18N[currentLang].conn_error;
    isConnected = false;
    return;
  }
  statusErrors = 0;
  isConnected = true;

  if (data.version) {
    appVersion = data.version;
    const versionEl = document.getElementById('about-version');
    if (versionEl) versionEl.textContent = `v${appVersion} (Spicetifix / pywebview)`;
  }

  if (data.config) {
    systemConfig = data.config;
    if (systemConfig.language && systemConfig.language !== currentLang) {
      await applyLanguage(systemConfig.language);
    }
  }

  const t = I18N[currentLang];
  const workingNow = !!data.is_working;
  if (wasWorking && !workingNow) toast(t.op_finished);
  wasWorking = workingNow;
  if (data.is_working) {
    setBadgeState(true, t.status_working, 'badge badge-connecting');
  } else {
    setBadgeState(false, t.system_ready, 'badge');
  }

  // Now Playing (Bottom Dock Mini-Player)
  const trackInfo = document.getElementById('track-info');
  const playIcon = document.getElementById('icon-play-state');
  const trackStatusText = document.getElementById('track-status-text');
  const playerEq = document.getElementById('player-eq');
  const setEq = (on) => { if (playerEq) playerEq.classList.toggle('is-active', !!on); };

  const np = data.now_playing || null;
  const isPlaying = !!(np && np.playing);
  if (isPlaying && (np.title || np.artist)) {
    lastTrack = { artist: np.artist || '', title: np.title || '' };
  }
  // Spotify drops the window title when paused, so keep showing the last known
  // track instead of clearing it (it only reappears on play otherwise).
  const shown = isPlaying ? { artist: np.artist, title: np.title } : lastTrack;

  if (shown && (shown.title || shown.artist)) {
    if (trackInfo) {
      trackInfo.textContent = shown.title || '';
      trackInfo.title = [shown.artist, shown.title].filter(Boolean).join(' — ');
    }
    if (trackStatusText) trackStatusText.textContent = shown.artist || '';
  } else {
    if (trackInfo) {
      trackInfo.textContent = t.dock_idle;
      trackInfo.title = 'Spotify';
    }
    if (trackStatusText) trackStatusText.textContent = '';
  }

  setEq(isPlaying);
  if (playIcon) {
    const want = isPlaying ? 'pause' : 'play';
    if (playIcon.getAttribute('data-lucide') !== want) {
      playIcon.setAttribute('data-lucide', want);
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }
  }

  // Health / Cards
  isSpotifyInstalled = data.health.some(h => h.label === 'spotify_path' && h.ok);
  isSpicetifyInstalled = data.health.some(h => (h.label === 'config_file' || h.label === 'spicetify_exe') && h.ok);

  const cardSpotify = document.getElementById('card-spotify');
  const tagSpotify = document.getElementById('tag-spotify');
  const subSpotify = document.getElementById('sub-spotify');
  const actSpotify = document.getElementById('action-spotify');

  if (isSpotifyInstalled) {
    tagSpotify.textContent = t.tag_online;
    tagSpotify.style.color = 'var(--accent-color)';
    subSpotify.textContent = t.card_spotify_sub_ok;
    if (actSpotify) actSpotify.textContent = t.act_uninstall_spotify;
    if (cardSpotify) cardSpotify.classList.add('card-danger-hover');
  } else {
    tagSpotify.textContent = t.tag_missing;
    tagSpotify.style.color = 'var(--danger-color)';
    subSpotify.textContent = t.card_spotify_sub_err;
    if (actSpotify) actSpotify.textContent = t.act_install_spotify;
    if (cardSpotify) cardSpotify.classList.remove('card-danger-hover');
  }

  const cardSpicetify = document.getElementById('card-spicetify');
  const tagSpicetify = document.getElementById('tag-spicetify');
  const subSpicetify = document.getElementById('sub-spicetify');
  const actSpicetify = document.getElementById('action-spicetify');

  if (isSpicetifyInstalled) {
    tagSpicetify.textContent = t.tag_online;
    tagSpicetify.style.color = 'var(--accent-color)';
    subSpicetify.textContent = t.card_spicetify_sub_ok;
    if (actSpicetify) actSpicetify.textContent = t.act_uninstall_spicetify;
    if (cardSpicetify) cardSpicetify.classList.add('card-danger-hover');
  } else {
    tagSpicetify.textContent = t.tag_missing;
    tagSpicetify.style.color = 'var(--danger-color)';
    subSpicetify.textContent = t.card_spicetify_sub_err;
    if (actSpicetify) actSpicetify.textContent = t.act_install_spicetify;
    if (cardSpicetify) cardSpicetify.classList.remove('card-danger-hover');
  }

  const tagTheme = document.getElementById('tag-theme');
  const subTheme = document.getElementById('sub-theme');
  const actTheme = document.getElementById('action-theme');
  tagTheme.textContent = t.tag_active;
  tagTheme.style.color = 'var(--contrast-color)';
  subTheme.textContent = data.current_theme || t.none;
  if (actTheme) actTheme.textContent = t.act_change_theme;

  renderHealth(data.health);

  // Console Output & Progress
  if (data.logs && data.logs.length > 0) {
    const consoleBox = document.getElementById('console-output');
    const consoleContainer = document.getElementById('console-box-container') || (consoleBox ? consoleBox.parentElement : null);
    const newLogsText = data.logs.join('\n');

    const lastLine = data.logs[data.logs.length - 1] || '';
    const previewEl = document.getElementById('console-preview-text');
    if (previewEl && lastLine) {
      previewEl.textContent = lastLine;
    }

    if (consoleBox && newLogsText !== lastRenderedLogs) {
      lastRenderedLogs = newLogsText;
      consoleBox.textContent = newLogsText;

      // Smart auto-scroll: NEVER force scroll down if the user is scrolled up reading past logs!
      if (!isUserScrolledUp && consoleContainer) {
        consoleContainer.scrollTop = consoleContainer.scrollHeight;
      }
    }
  }

  setConsoleStatus(!!data.is_working);

  const pBar = document.getElementById('progress-bar');
  if (data.is_working && (!data.progress || data.progress <= 0)) {
    if (pBar) pBar.classList.add('is-indeterminate');
  } else {
    if (pBar) {
      pBar.classList.remove('is-indeterminate');
      if (data.progress !== undefined) {
        pBar.style.width = `${Math.round(data.progress * 100)}%`;
      }
    }
  }

  updateActionButtons(!!data.is_working);

  // Disable action buttons while operations are running
  const workingBtns = [
    'btn-install', 'btn-recover', 'btn-spicetify-apply',
    'btn-uninstall-spicetify', 'btn-uninstall-spotify',
    'btn-export-backup', 'btn-import-backup',
    'btn-refresh-status', 'btn-refresh-exts', 'btn-refresh-catalog'
  ];
  workingBtns.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !!data.is_working;
  });

  // Show working state in console if active
  if (data.is_working) {
    const consoleBox = document.getElementById('console-output');
    if (!data.logs || data.logs.length === 0) {
      consoleBox.textContent = `root@spicetifix:~$ ${t.console_working}\n`;
    }
  }
}

// Load color schemes for a theme
async function loadColorSchemes(themeName, selected = '') {
  const schemeSelect = document.getElementById('select-color-scheme');
  if (!schemeSelect) return;

  schemeSelect.innerHTML = `<option value="">${t('scheme_default')}</option>`;
  if (!themeName) return;

  const data = await apiFetch('/api/themes/schemes', 'POST', { theme: themeName });
  if (!data) {
    schemeSelect.innerHTML = `<option value="">${t('scheme_error')}</option>`;
    return;
  }
  if (data.schemes && data.schemes.length > 0) {
    data.schemes.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      schemeSelect.appendChild(opt);
    });
  }
  if (selected) schemeSelect.value = selected;
}

// Load extensions
let extDirty = false;

function appendConsole(text) {
  const consoleBox = document.getElementById('console-output');
  if (!consoleBox) return;
  const line = `root@spicetifix:~$ ${text}`;
  consoleBox.textContent += `\n${line}`;
  lastRenderedLogs = consoleBox.textContent;

  const previewEl = document.getElementById('console-preview-text');
  if (previewEl) previewEl.textContent = line;

  const consoleContainer = document.getElementById('console-box-container') || consoleBox.parentElement;
  if (!isUserScrolledUp && consoleContainer) {
    consoleContainer.scrollTop = consoleContainer.scrollHeight;
  }
}

function setExtApplyPending(pending) {
  extDirty = pending;
  const btn = document.getElementById('btn-apply-exts');
  if (!btn) return;
  btn.disabled = !pending;
  const label = btn.querySelector('span');
  if (label) label.textContent = t('btn_apply_exts');
}

let extTitleMap = null;

async function getExtTitleMap() {
  if (extTitleMap) return extTitleMap;

  const buildMap = (list) => {
    const map = {};
    (list || []).forEach(i => {
      if (i.filename && i.title) map[i.filename] = i.title;
    });
    return map;
  };

  if (currentMarketplaceCatalog.length > 0) {
    extTitleMap = buildMap(currentMarketplaceCatalog);
    return extTitleMap;
  }

  // Never block the extension list on the (possibly slow) catalog build: show
  // raw filenames now and upgrade them to friendly titles in the background.
  extTitleMap = {};
  requestCatalog().then(catalog => {
    const map = buildMap(catalog);
    if (Object.keys(map).length) {
      extTitleMap = map;
      loadExtensions();
    }
  });
  return extTitleMap;
}

// ---- Version / update comparison ---------------------------------------
let repoVersions = {};
const versionFetchTried = new Set();

function fmtRepoDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const locale = currentLang === 'es' ? 'es-ES' : 'en-US';
  return d.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' });
}

// Prefer the release tag; fall back to the last-updated date.
function versionLabel(info) {
  info = info || {};
  return info.tag || fmtRepoDate(info.updated_at);
}

function versionOutdated(installed, latest) {
  if (!installed) return false;
  const iTag = installed.tag || '';
  const lTag = (latest || {}).tag || '';
  if (iTag && lTag) return iTag !== lTag;
  const iDate = installed.updated_at || '';
  const lDate = (latest || {}).updated_at || '';
  return Boolean(iDate && lDate && lDate > iDate);
}

async function fetchRepoVersions(repos) {
  const clean = (repos || []).filter(r => {
    const key = `${r.user}/${r.repo}`;
    return r.user && r.repo && !repoVersions[key] && !versionFetchTried.has(key);
  });
  if (clean.length === 0) return {};
  clean.forEach(r => versionFetchTried.add(`${r.user}/${r.repo}`));
  const res = await apiFetch('/api/marketplace/versions', 'POST', { repos: clean });
  if (res && res.versions) {
    Object.assign(repoVersions, res.versions);
    return res.versions;
  }
  return {};
}

async function loadExtensions() {
  const extGrid = document.getElementById('ext-grid');
  if (extGrid && !extGrid.querySelector('.ext-item')) {
    extGrid.innerHTML = Array.from({ length: 6 }).map(() => `
      <div class="ext-item ext-item-skeleton">
        <div class="ext-item-main">
          <span class="skeleton sk-label"></span>
          <span class="skeleton sk-sub"></span>
        </div>
        <span class="skeleton sk-toggle"></span>
      </div>`).join('');
  }

  const data = await apiFetch('/api/extensions');
  if (!data) {
    if (extGrid) extGrid.innerHTML = `<div class="empty-msg">${t('conn_error')}</div>`;
    return;
  }

  if (!extGrid) return;
  extGrid.innerHTML = '';

  const allItems = [
    ...(data.extensions || []).map(e => ({ ...e, type: 'ext' })),
    ...(data.custom_apps || []).map(a => ({ ...a, type: 'app' })),
  ];

  if (allItems.length === 0) {
    extGrid.innerHTML = `<div class="empty-msg">${t('ext_empty')}</div>`;
    return;
  }

  const titleMap = await getExtTitleMap();
  const versionTargets = [];

  allItems.forEach(item => {
    const div = document.createElement('div');
    div.className = 'ext-item';

    const left = document.createElement('div');
    left.className = 'ext-item-main';

    const label =
      item.type === 'ext' && titleMap[item.name]
        ? `${titleMap[item.name]} (${item.name})`
        : item.name;
    const span = document.createElement('span');
    span.textContent = `● ${label}`;
    if (item.enabled) span.style.color = 'var(--accent-color)';

    const ver = document.createElement('span');
    ver.className = 'ext-item-version';
    left.appendChild(span);
    left.appendChild(ver);

    const chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.checked = item.enabled;
    chk.addEventListener('change', async () => {
      const res = await apiFetch('/api/extensions/toggle', 'POST', {
        name: item.name,
        type: item.type,
        enabled: chk.checked,
      });
      if (res && res.error) {
        appendConsole(`${t('ext_apply_err')} ${res.error}`);
      } else {
        setExtApplyPending(true);
        appendConsole(`${t('ext_apply_pending')}`);
      }
      loadExtensions();
    });

    div.appendChild(left);
    div.appendChild(chk);
    extGrid.appendChild(div);

    if (item.meta && item.meta.user && item.meta.repo) {
      versionTargets.push({ item, el: ver });
    } else {
      const local = item.meta ? fmtRepoDate(item.meta.updated_at) || fmtRepoDate(item.meta.installed_at) : '';
      if (local) ver.textContent = `${t('mp_version_installed')}: ${local}`;
    }
  });

  if (versionTargets.length) {
    await fetchRepoVersions(versionTargets.map(v => ({ user: v.item.meta.user, repo: v.item.meta.repo })));
    versionTargets.forEach(({ item, el }) => {
      const key = `${item.meta.user}/${item.meta.repo}`;
      const latest = repoVersions[key] || {};
      const instLabel = versionLabel(item.meta) || fmtRepoDate(item.meta.installed_at);
      const latestLabel = versionLabel(latest);
      const parts = [];
      if (instLabel) parts.push(`${t('mp_version_installed')}: ${instLabel}`);
      if (latestLabel) parts.push(`${t('mp_version_latest')}: ${latestLabel}`);
      el.textContent = parts.join(' · ');
      if (versionOutdated(item.meta, latest)) {
        el.appendChild(document.createTextNode(' '));
        const badge = document.createElement('span');
        badge.className = 'mp-update-badge';
        badge.textContent = t('mp_update_available');
        el.appendChild(badge);
      }
    });
  }
}

// Load themes info & populate options modal
async function loadThemes() {
  const data = await apiFetch('/api/themes');
  if (!data) {
    console.warn('loadThemes: no data from API');
    return;
  }

  if (data.current_ui_theme) {
    applyUITheme(data.current_ui_theme);
  }

  const spicetifySelect = document.getElementById('select-spicetify-theme');
  if (spicetifySelect && data.spicetify_themes) {
    spicetifySelect.innerHTML = '';
    data.spicetify_themes.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      spicetifySelect.appendChild(opt);
    });
    if (systemConfig && systemConfig.spicetify && systemConfig.spicetify.theme) {
      spicetifySelect.value = systemConfig.spicetify.theme;
      loadColorSchemes(systemConfig.spicetify.theme);
    }
  }
}

// Open Options Modal
function openOptionsModal() {
  const modal = document.getElementById('options-modal');
  if (!modal) return;

  const selectLang = document.getElementById('select-lang');
  if (selectLang && currentLang) selectLang.value = currentLang;

  const cfg = systemConfig || {};
  const opts = cfg.options || {};
  const pre = cfg.preprocesses || {};
  const setChk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
  setChk('chk-inject-css', opts.inject_css !== false);
  setChk('chk-replace-colors', opts.replace_colors !== false);
  setChk('chk-overwrite-assets', !!opts.overwrite_assets);
  setChk('chk-devtools', !!opts.always_enable_devtools);
  setChk('chk-sentry', pre.disable_sentry === false);
  setChk('chk-auto-backup', cfg.auto_backup !== false);

  const spicetifySelect = document.getElementById('select-spicetify-theme');
  if (spicetifySelect && cfg.spicetify && cfg.spicetify.theme) {
    spicetifySelect.value = cfg.spicetify.theme;
    loadColorSchemes(cfg.spicetify.theme, cfg.spicetify.color_scheme || '');
  }

  modal.classList.add('active');
}

// Close Options Modal
function closeOptionsModal() {
  const modal = document.getElementById('options-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

// Open About Modal
function openAboutModal() {
  const modal = document.getElementById('about-modal');
  if (modal) {
    const versionEl = document.getElementById('about-version');
    if (versionEl && appVersion) {
      versionEl.textContent = `v${appVersion} (Spicetifix / pywebview)`;
    }
    modal.classList.add('active');
  }
}

// Open Changelog Modal (releases only)
function openChangelogModal() {
  const modal = document.getElementById('changelog-modal');
  if (modal) {
    modal.classList.add('active');
    loadChangelogInfo();
  }
}

// Load release list (version + title + date) with expandable details
async function loadChangelogInfo() {
  const listEl = document.getElementById('changelog-list');
  if (!listEl) return;

  listEl.innerHTML = `<div class="empty-msg">${brailleHTML(t('changelog_loading'))}</div>`;

  try {
    const res = await fetch('changelog.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('changelog not found');
    const entries = await res.json();

    const esc = (str) => str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    listEl.innerHTML = entries.map((entry, idx) => `
      <div class="changelog-entry">
        <button type="button" class="changelog-head" data-toggle="${idx}" aria-expanded="false">
          <span class="changelog-version">v${esc(entry.version)}</span>
          <span class="changelog-title">${esc(entry.title)}</span>
          <span class="changelog-date">${esc(entry.date)}</span>
          <i data-lucide="chevron-down" class="changelog-chevron"></i>
        </button>
        <ul class="changelog-changes">
          ${(entry.changes || []).map(c => `<li>${esc(c)}</li>`).join('')}
        </ul>
      </div>
    `).join('');
    listEl.querySelectorAll('.changelog-head').forEach(btn => {
      btn.addEventListener('click', () => {
        const entry = btn.closest('.changelog-entry');
        const expanded = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', String(!expanded));
        entry.classList.toggle('open', !expanded);
      });
    });
    if (window.lucide && lucide.createIcons) lucide.createIcons();
  } catch (err) {
    listEl.innerHTML = `
      <div class="empty-msg">${t('changelog_error')}</div>
      <div style="text-align:center;margin-top:12px;">
        <button type="button" class="btn btn-small btn-outline" id="btn-changelog-retry">${t('changelog_retry')}</button>
      </div>`;
    const retry = document.getElementById('btn-changelog-retry');
    if (retry) retry.addEventListener('click', loadChangelogInfo);
  }
}

// Close About Modal
function closeAboutModal() {
  const modal = document.getElementById('about-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

// Close Changelog Modal
function closeChangelogModal() {
  const modal = document.getElementById('changelog-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

// Save Options Modal
async function saveOptions() {
  const selectLang = document.getElementById('select-lang');
  const selectSpicetifyTheme = document.getElementById('select-spicetify-theme');
  const selectColorScheme = document.getElementById('select-color-scheme');
  const chk = (id) => { const el = document.getElementById(id); return !!(el && el.checked); };

  const selectedLang = selectLang ? selectLang.value : 'en';
  await applyLanguage(selectedLang);

  const body = {
    language: selectedLang,
    spicetify_theme: selectSpicetifyTheme ? selectSpicetifyTheme.value : 'SpicetifyDefault',
    color_scheme: selectColorScheme ? selectColorScheme.value : '',
    ui_theme: currentUITheme,
    auto_backup: chk('chk-auto-backup'),
    options: {
      inject_css: chk('chk-inject-css'),
      replace_colors: chk('chk-replace-colors'),
      overwrite_assets: chk('chk-overwrite-assets'),
      always_enable_devtools: chk('chk-devtools'),
    },
    preprocesses: {
      disable_sentry: !chk('chk-sentry'),
    },
  };

  await apiFetch('/api/config/save', 'POST', body);
  closeOptionsModal();
  pollStatus();
}

// Initialize UI
document.addEventListener('DOMContentLoaded', async () => {
  await loadI18n();
  setBadgeState(true, I18N['en'].status_connecting, 'badge badge-connecting');

  await applyLanguage('en');
  renderHealthLoading();
  renderDockLoading();
  spinnerObserver.observe(document.body, { childList: true, subtree: true });
  ensureSpinners();
  loadThemes();
  loadExtensions();
  restoreMarketplacePrefs();
  pollStatus();
  setInterval(pollStatus, 1500);
  checkForUpdate();

  // Render Lucide SVG Icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // Update button
  const btnUpdateCheck = document.getElementById('btn-update-check');
  if (btnUpdateCheck) {
    btnUpdateCheck.addEventListener('click', openUpdateModal);
  }

  // Route external links through the Python sidecar (works in pywebview & browser)
  document.addEventListener('click', (e) => {
    const anchor = e.target.closest('a[target="_blank"]');
    if (anchor) {
      e.preventDefault();
      openExternal(anchor.href);
    }
  });

  // Spicetify theme selection change -> load schemes
  const selectSpicetifyTheme = document.getElementById('select-spicetify-theme');
  if (selectSpicetifyTheme) {
    selectSpicetifyTheme.addEventListener('change', (e) => {
      loadColorSchemes(e.target.value);
    });
  }

  // Open Spotify App button (guarded: repeated clicks must not spawn several
  // Spotify launches / burn CPU)
  const btnOpenSpotify = document.getElementById('btn-open-spotify');
  if (btnOpenSpotify) {
    let openingSpotify = false;
    btnOpenSpotify.addEventListener('click', async () => {
      if (openingSpotify) return;
      openingSpotify = true;
      btnOpenSpotify.disabled = true;
      btnOpenSpotify.classList.add('is-busy');
      const original = btnOpenSpotify.innerHTML;
      btnOpenSpotify.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>';
      try {
        await apiFetch('/api/open/spotify', 'POST');
      } finally {
        setTimeout(() => {
          openingSpotify = false;
          btnOpenSpotify.disabled = false;
          btnOpenSpotify.classList.remove('is-busy');
          btnOpenSpotify.innerHTML = original;
          if (window.lucide && lucide.createIcons) lucide.createIcons();
        }, 3000);
      }
    });
  }

  // Open Folder buttons
  const btnOpenSpicetifyDir = document.getElementById('btn-open-spicetify-dir');
  if (btnOpenSpicetifyDir) {
    btnOpenSpicetifyDir.addEventListener('click', async () => {
      await apiFetch('/api/open/folder', 'POST', { target: 'spicetify' });
    });
  }

  const btnOpenThemesDir = document.getElementById('btn-open-themes-dir');
  if (btnOpenThemesDir) {
    btnOpenThemesDir.addEventListener('click', async () => {
      await apiFetch('/api/open/folder', 'POST', { target: 'themes' });
    });
  }

  // Export Backup ZIP button
  const btnExportBackup = document.getElementById('btn-export-backup');
  if (btnExportBackup) {
    btnExportBackup.addEventListener('click', () =>
      flashButtonBusy(btnExportBackup, '/api/backup/export', pollStatus));
  }

  // Import Backup ZIP button (opens native Windows File Explorer dialog)
  const btnImportBackup = document.getElementById('btn-import-backup');
  if (btnImportBackup) {
    btnImportBackup.addEventListener('click', () =>
      flashButtonBusy(btnImportBackup, '/api/backup/import', () => {
        pollStatus();
        loadExtensions();
        loadThemes();
      }));
  }

  // Smart Console Scroll & Collapse Handlers
  const consoleContainer = document.getElementById('console-box-container');
  const btnScrollBottom = document.getElementById('btn-scroll-bottom');

  if (consoleContainer) {
    consoleContainer.addEventListener('scroll', () => {
      const distanceToBottom = consoleContainer.scrollHeight - consoleContainer.scrollTop - consoleContainer.clientHeight;
      isUserScrolledUp = distanceToBottom > 35;
      if (btnScrollBottom) {
        btnScrollBottom.classList.toggle('visible', isUserScrolledUp);
      }
    });
  }

  if (btnScrollBottom) {
    btnScrollBottom.addEventListener('click', (e) => {
      e.stopPropagation();
      if (consoleContainer) {
        consoleContainer.scrollTo({
          top: consoleContainer.scrollHeight,
          behavior: 'smooth'
        });
      }
      isUserScrolledUp = false;
      btnScrollBottom.classList.remove('visible');
    });
  }

  const consoleHeader = document.getElementById('console-header');
  if (consoleHeader) {
    consoleHeader.addEventListener('click', (e) => {
      if (e.target.closest('#btn-copy-logs') || e.target.closest('#btn-clear-logs')) {
        return;
      }
      toggleConsole();
    });
  }

  const btnHeaderConsole = document.getElementById('btn-header-console');
  if (btnHeaderConsole) {
    btnHeaderConsole.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleConsole();
    });
  }

  const btnToggleConsole = document.getElementById('btn-toggle-console');
  if (btnToggleConsole) {
    btnToggleConsole.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleConsole();
    });
  }

  // Restore console expansion preference
  try {
    const savedExpanded = localStorage.getItem('spicetifix_console_expanded');
    if (savedExpanded === 'true') {
      setConsoleExpanded(true, false);
    } else {
      setConsoleExpanded(false, false);
    }
  } catch (_) {
    setConsoleExpanded(false, false);
  }

  // Save Logs button
  const btnSaveLogs = document.getElementById('btn-save-logs');
  if (btnSaveLogs) {
    btnSaveLogs.addEventListener('click', async () => {
      const out = document.getElementById('console-output');
      const text = out ? out.textContent : '';
      const res = await apiFetch('/api/logs/export', 'POST', { text });
      if (res && res.status === 'ok') toast(t('logs_saved'));
      else toast(t('mp_failed'), 'error');
    });
  }

  // Copy Logs button
  const btnCopyLogs = document.getElementById('btn-copy-logs');
  if (btnCopyLogs) {
    btnCopyLogs.addEventListener('click', () => {
      const logs = document.getElementById('console-output').textContent;
      navigator.clipboard.writeText(logs).then(() => {
        const lbl = document.getElementById('lbl-copy-logs');
        if (lbl) {
          const oldTxt = lbl.textContent;
          lbl.textContent = t('copy_done');
          setTimeout(() => { lbl.textContent = oldTxt; }, 1500);
        }
      });
    });
  }

  // Clear Logs button
  const btnClearLogs = document.getElementById('btn-clear-logs');
  if (btnClearLogs) {
    btnClearLogs.addEventListener('click', () => {
      const clearedMsg = `root@spicetifix:~$ ${t('console_cleared')}`;
      const consoleBox = document.getElementById('console-output');
      if (consoleBox) {
        consoleBox.textContent = clearedMsg;
        lastRenderedLogs = clearedMsg;
        isUserScrolledUp = false;
        const btnScroll = document.getElementById('btn-scroll-bottom');
        if (btnScroll) btnScroll.classList.remove('visible');
        const consoleContainer = document.getElementById('console-box-container') || consoleBox.parentElement;
        if (consoleContainer) consoleContainer.scrollTop = consoleContainer.scrollHeight;
      }
      const previewEl = document.getElementById('console-preview-text');
      if (previewEl) previewEl.textContent = clearedMsg;
    });
  }

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeOptionsModal();
      closeAboutModal();
      closeChangelogModal();
    } else if ((e.ctrlKey && (e.key === '`' || e.key === 'j')) || e.key === 'F12') {
      if (e.key !== 'F12') e.preventDefault();
      toggleConsole();
    }
  });

  // Refresh Status button
  document.getElementById('btn-refresh-status').addEventListener('click', () => {
    pollStatus();
    loadExtensions();
    loadThemes();
    checkForUpdate();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  });

  // Card clicks: Spotify
  document.getElementById('card-spotify').addEventListener('click', async () => {
    const t = I18N[currentLang];
    if (isSpotifyInstalled) {
      showCyberAlert(
        t.confirm_spotify_title,
        t.confirm_spotify,
        t.btn_yes_uninstall,
        t.btn_cancel,
        async () => {
          await apiFetch('/api/uninstall/spotify', 'POST');
          pollStatus();
        }
      );
    } else {
      currentAction = 'install';
      updateActionButtons(true);
      await apiFetch('/api/install', 'POST');
      pollStatus();
    }
  });

  // Card clicks: Spicetify
  document.getElementById('card-spicetify').addEventListener('click', async () => {
    const t = I18N[currentLang];
    if (isSpicetifyInstalled) {
      showCyberAlert(
        t.confirm_spicetify_title,
        t.confirm_spicetify,
        t.btn_yes_uninstall,
        t.btn_cancel,
        async () => {
          await apiFetch('/api/uninstall/spicetify', 'POST');
          pollStatus();
        }
      );
    } else {
      currentAction = 'install';
      updateActionButtons(true);
      await apiFetch('/api/install', 'POST');
      pollStatus();
    }
  });

  document.getElementById('card-theme').addEventListener('click', openOptionsModal);

  // Player buttons
  document.getElementById('btn-prev').addEventListener('click', () => {
    apiFetch('/api/player', 'POST', { action: 'prev' }).then(pollStatus);
  });

  document.getElementById('btn-play').addEventListener('click', () => {
    apiFetch('/api/player', 'POST', { action: 'play_pause' }).then(pollStatus);
  });

  document.getElementById('btn-next').addEventListener('click', () => {
    apiFetch('/api/player', 'POST', { action: 'next' }).then(pollStatus);
  });

  const btnDockSpotify = document.getElementById('btn-dock-spotify');
  if (btnDockSpotify) {
    btnDockSpotify.addEventListener('click', () => {
      const btnOpen = document.getElementById('btn-open-spotify');
      if (btnOpen) btnOpen.click();
    });
  }

  // Action buttons
  document.getElementById('btn-install').addEventListener('click', async () => {
    setConsoleExpanded(true);
    const btn = document.getElementById('btn-install');
    if (btn && (btn.disabled || btn.classList.contains('is-busy'))) return;
    currentAction = 'install';
    updateActionButtons(true);
    const res = await apiFetch('/api/install', 'POST');
    if (!res || res.error) {
      updateActionButtons(false);
    }
    pollStatus();
  });

  document.getElementById('btn-recover').addEventListener('click', async () => {
    setConsoleExpanded(true);
    const btn = document.getElementById('btn-recover');
    if (btn && (btn.disabled || btn.classList.contains('is-busy'))) return;
    currentAction = 'recover';
    updateActionButtons(true);
    const res = await apiFetch('/api/recover', 'POST');
    if (!res || res.error) {
      updateActionButtons(false);
    }
    pollStatus();
  });

  document.getElementById('btn-refresh-exts').addEventListener('click', loadExtensions);

  const btnApply = document.getElementById('btn-apply-exts');
  if (btnApply) {
    btnApply.addEventListener('click', async () => {
      if (btnApply.disabled) return;
      btnApply.disabled = true;
      const label = btnApply.querySelector('span');
      if (label) label.innerHTML = `${brailleHTML()} ${t('btn_apply_exts_pending')}`;
      const res = await apiFetch('/api/extensions/apply', 'POST');
      if (res && res.error) {
        appendConsole(`${t('ext_apply_err')} ${res.error}`);
        btnApply.disabled = false;
        if (label) label.textContent = t('btn_apply_exts');
      } else {
        appendConsole(t('ext_apply_ok'));
        extDirty = false;
        setExtApplyPending(false);
        loadExtensions();
        pollStatus();
      }
    });
  }

  // Theme dropdown change
  document.getElementById('ui-theme-select').addEventListener('change', async (e) => {
    const selectedTheme = e.target.value;
    applyUITheme(selectedTheme);
    await apiFetch('/api/config/save', 'POST', { ui_theme: selectedTheme });
  });

  // Options Modal Handlers
  document.getElementById('btn-open-options').addEventListener('click', openOptionsModal);
  document.getElementById('btn-close-options').addEventListener('click', closeOptionsModal);
  document.getElementById('btn-save-options').addEventListener('click', saveOptions);

  document.getElementById('options-modal').addEventListener('click', (e) => {
    if (e.target.id === 'options-modal') closeOptionsModal();
  });

  // About Modal Handlers
  document.getElementById('btn-open-about').addEventListener('click', openAboutModal);
  document.getElementById('btn-close-about').addEventListener('click', closeAboutModal);
  document.getElementById('btn-close-about-footer').addEventListener('click', closeAboutModal);

  document.getElementById('about-modal').addEventListener('click', (e) => {
    if (e.target.id === 'about-modal') closeAboutModal();
  });

  // Changelog Modal Handlers
  document.getElementById('btn-open-changelog').addEventListener('click', openChangelogModal);
  const btnCloseChangelog = document.getElementById('btn-close-changelog');
  const btnCloseChangelogFooter = document.getElementById('btn-close-changelog-footer');
  if (btnCloseChangelog) btnCloseChangelog.addEventListener('click', closeChangelogModal);
  if (btnCloseChangelogFooter) btnCloseChangelogFooter.addEventListener('click', closeChangelogModal);

  const changelogModal = document.getElementById('changelog-modal');
  if (changelogModal) {
    changelogModal.addEventListener('click', (e) => {
      if (e.target.id === 'changelog-modal') closeChangelogModal();
    });
  }

  // Main Tab Buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Marketplace Search & Filters
  const searchInput = document.getElementById('mp-search-input');
  if (searchInput) {
    let searchDebounce = null;
    searchInput.addEventListener('input', () => {
      storeSet(STORE_KEYS.search, searchInput.value);
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        currentPage = 1;
        renderMarketplaceCatalog();
      }, 150);
    });
  }

  document.querySelectorAll('.chip-filter').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.chip-filter').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentMarketplaceFilter = chip.dataset.filter;
      storeSet(STORE_KEYS.filter, currentMarketplaceFilter);
      currentPage = 1;
      renderMarketplaceCatalog();
      scrollCatalogTop();
    });
  });

  const sortSelect = document.getElementById('mp-sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      currentMarketplaceSort = sortSelect.value;
      storeSet(STORE_KEYS.sort, currentMarketplaceSort);
      currentPage = 1;
      renderMarketplaceCatalog();
      scrollCatalogTop();
    });
  }

  const btnRefreshCatalog = document.getElementById('btn-refresh-catalog');
  if (btnRefreshCatalog) {
    btnRefreshCatalog.addEventListener('click', () => loadMarketplaceCatalog(true));
  }

  const btnUpdateAll = document.getElementById('btn-mp-update-all');
  if (btnUpdateAll) btnUpdateAll.addEventListener('click', updateAllOutdated);

  // Pagination
  const btnPrev = document.getElementById('btn-mp-prev');
  const btnNext = document.getElementById('btn-mp-next');
  if (btnPrev) btnPrev.addEventListener('click', () => { currentPage--; renderMarketplaceCatalog(); scrollCatalogTop(); });
  if (btnNext) btnNext.addEventListener('click', () => { currentPage++; renderMarketplaceCatalog(); scrollCatalogTop(); });

  // Danger Zone Actions
  document.getElementById('btn-spicetify-apply').addEventListener('click', async () => {
    closeOptionsModal();
    toast(t('applying'), 'info');
    await apiFetch('/api/spicetify/apply', 'POST');
    pollStatus();
  });

  document.getElementById('btn-uninstall-spicetify').addEventListener('click', async () => {
    const t = I18N[currentLang];
    showCyberAlert(
      t.confirm_spicetify_title,
      t.confirm_spicetify,
      t.btn_yes_uninstall,
      t.btn_cancel,
      async () => {
        closeOptionsModal();
        await apiFetch('/api/uninstall/spicetify', 'POST');
        pollStatus();
      }
    );
  });

  document.getElementById('btn-uninstall-spotify').addEventListener('click', async () => {
    const t = I18N[currentLang];
    showCyberAlert(
      t.confirm_spotify_title,
      t.confirm_spotify,
      t.btn_yes_uninstall,
      t.btn_cancel,
      async () => {
        closeOptionsModal();
        await apiFetch('/api/uninstall/spotify', 'POST');
        pollStatus();
      }
    );
  });
});

// MARKETPLACE & TAB SYSTEM LOGIC
let currentMarketplaceCatalog = [];
let currentMarketplaceFilter = 'all';
let currentMarketplaceSort = 'relevance';
let currentPage = 1;
const ITEMS_PER_PAGE = 12;
let isLoadingCatalog = false;
let catalogPromise = null;

const STORE_KEYS = {
  filter: 'spicetifix_mp_filter',
  search: 'spicetifix_mp_search',
  sort: 'spicetifix_mp_sort',
  tab: 'spicetifix_active_tab',
};

function storeGet(key) {
  try { return localStorage.getItem(key); } catch (_) { return null; }
}

function storeSet(key, value) {
  try { localStorage.setItem(key, value); } catch (_) {}
}

// Single shared catalog request: the extension list and the Marketplace tab both
// need it, so they must not each trigger a (slow) rebuild.
function requestCatalog() {
  if (currentMarketplaceCatalog.length > 0) {
    return Promise.resolve(currentMarketplaceCatalog);
  }
  if (!catalogPromise) {
    catalogPromise = apiFetch('/api/marketplace/catalog', 'GET', null, 90000)
      .then(data => {
        if (data && Array.isArray(data.catalog)) {
          currentMarketplaceCatalog = data.catalog;
        }
        return currentMarketplaceCatalog;
      })
      .catch(() => currentMarketplaceCatalog)
      .finally(() => { catalogPromise = null; });
  }
  return catalogPromise;
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.toggle('active', content.id === `content-${tabId}`);
  });
  if (tabId === 'marketplace') {
    // Never restart the load on every tab switch; only fetch if it has not
    // been loaded yet, and leave the in-progress spinner untouched so the
    // load does not look like it was cancelled. When the catalog was already
    // preloaded in the background (the extension list warms it up), the grid
    // may still hold its placeholder — render it instead of showing nothing.
    if (currentMarketplaceCatalog.length === 0) {
      if (!isLoadingCatalog) loadMarketplaceCatalog();
    } else if (!document.querySelector('#mp-catalog-grid .mp-card:not(.mp-card-skeleton)')) {
      renderMarketplaceCatalog();
    }
  }
  storeSet(STORE_KEYS.tab, tabId);
}

function renderMarketplaceLoading() {
  const grid = document.getElementById('mp-catalog-grid');
  const pagination = document.getElementById('mp-pagination');
  if (pagination) pagination.style.display = 'none';
  if (grid) {
    grid.innerHTML = Array.from({ length: 6 }).map(() => `
      <div class="mp-card mp-card-skeleton" aria-hidden="true">
        <div class="skeleton sk-title"></div>
        <div class="skeleton sk-sub"></div>
        <div class="skeleton sk-line"></div>
        <div class="skeleton sk-line short"></div>
        <div class="skeleton sk-btn"></div>
      </div>`).join('');
  }
}

function renderMarketplaceError() {
  const grid = document.getElementById('mp-catalog-grid');
  const pagination = document.getElementById('mp-pagination');
  if (pagination) pagination.style.display = 'none';
  if (!grid) return;
  grid.innerHTML = `
    <div class="mp-error-state">
      <div class="empty-msg">${t('mp_error')}</div>
      <button class="btn btn-small btn-accent" id="btn-mp-retry">
        <i data-lucide="refresh-cw"></i> ${t('mp_retry')}
      </button>
    </div>`;
  const retry = document.getElementById('btn-mp-retry');
  if (retry) retry.addEventListener('click', () => loadMarketplaceCatalog(true));
  if (window.lucide) window.lucide.createIcons();
}

async function loadMarketplaceCatalog(force = false) {
  if (isLoadingCatalog) return;
  if (force) currentMarketplaceCatalog = [];
  isLoadingCatalog = true;
  currentPage = 1;
  versionFetchTried.clear();
  renderMarketplaceLoading();

  try {
    const catalog = await requestCatalog();
    if (catalog && catalog.length) {
      currentMarketplaceCatalog = catalog;
      renderMarketplaceCatalog();
    } else {
      renderMarketplaceError();
    }
  } finally {
    isLoadingCatalog = false;
  }
}

function itemOutdated(item) {
  if (!item || !item.installed || item.type === 'app') return false;
  const latest = repoVersions[`${item.user}/${item.repo}`] || {};
  const latestInfo = { tag: latest.tag || '', updated_at: latest.updated_at || item.updated_at || '' };
  return versionOutdated(item.meta, latestInfo);
}

function getOutdatedItems() {
  return currentMarketplaceCatalog.filter(itemOutdated);
}

async function updateAllOutdated() {
  const items = getOutdatedItems();
  if (!items.length) return;
  showCyberAlert(
    t('mp_update_all_title'),
    t('mp_update_all_msg').replace('{n}', items.length),
    t('mp_update_all_confirm'),
    t('btn_cancel'),
    async () => {
      for (const item of items) {
        const cached = repoVersions[`${item.user}/${item.repo}`] || {};
        try {
          const res = await apiFetch('/api/marketplace/install', 'POST', {
            type: item.type,
            filename: item.filename,
            url: item.url,
            user: item.user,
            repo: item.repo,
            branch: item.branch,
            css_url: item.css_url,
            schemes_url: item.schemes_url,
            include: item.include,
            updated_at: cached.updated_at || item.updated_at || '',
            tag: cached.tag || '',
          });
          if (res && res.status === 'ok') {
            appendConsole(`${item.title} ${t('mp_installed_ok')}`);
          } else {
            appendConsole(`${t('mp_installed_err')} ${item.title}: ${res?.error || t('mp_failed')}`);
          }
        } catch (e) {
          appendConsole(`${t('mp_failed')}: ${e}`);
        }
      }
      pollStatus();
      await loadMarketplaceCatalog(true);
      toast(t('mp_update_all_done'));
    },
  );
}

function getFilteredCatalog() {
  const searchInput = document.getElementById('mp-search-input');
  const searchQuery = (searchInput ? searchInput.value : '').toLowerCase().trim();

  const filtered = currentMarketplaceCatalog.filter(item => {
    const matchesFilter =
      currentMarketplaceFilter === 'all' ||
      (currentMarketplaceFilter === 'installed'
        ? item.installed
        : currentMarketplaceFilter === 'updates'
          ? (item.installed && itemOutdated(item))
          : item.type === currentMarketplaceFilter);
    const matchesSearch = !searchQuery ||
      (item.title || '').toLowerCase().includes(searchQuery) ||
      (item.description || '').toLowerCase().includes(searchQuery) ||
      (item.author || '').toLowerCase().includes(searchQuery);
    return matchesFilter && matchesSearch;
  });

  return sortCatalog(filtered);
}

function sortCatalog(items) {
  const sorted = items.slice();
  switch (currentMarketplaceSort) {
    case 'name':
      sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
      break;
    case 'updated':
      sorted.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
      break;
    case 'stars':
      sorted.sort((a, b) => (b.stars || 0) - (a.stars || 0));
      break;
    default:
      break; // relevance: keep the catalog's own order
  }
  return sorted;
}

function scrollCatalogTop() {
  const grid = document.getElementById('mp-catalog-grid');
  if (grid && typeof grid.scrollIntoView === 'function') {
    grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function restoreMarketplacePrefs() {
  const filter = storeGet(STORE_KEYS.filter);
  if (filter) {
    currentMarketplaceFilter = filter;
    document.querySelectorAll('.chip-filter').forEach(c => {
      c.classList.toggle('active', c.dataset.filter === filter);
    });
  }

  const search = storeGet(STORE_KEYS.search);
  const searchInput = document.getElementById('mp-search-input');
  if (search && searchInput) searchInput.value = search;

  const sort = storeGet(STORE_KEYS.sort);
  const sortSelect = document.getElementById('mp-sort-select');
  if (sort && sortSelect) {
    currentMarketplaceSort = sort;
    sortSelect.value = sort;
  }

  const tab = storeGet(STORE_KEYS.tab);
  if (tab === 'marketplace') switchTab('marketplace');
}

function ensureMarketplaceVersions(items) {
  const repos = (items || [])
    .filter(i => i.user && i.repo)
    .map(i => ({ user: i.user, repo: i.repo, updated_at: i.updated_at || '' }));
  const pending = repos.some(r => {
    const key = `${r.user}/${r.repo}`;
    return !repoVersions[key] && !versionFetchTried.has(key);
  });
  if (!pending) return;
  fetchRepoVersions(repos).then(versions => {
    if (versions && Object.keys(versions).length) renderMarketplaceCatalog();
  });
}

function renderMarketplaceCatalog() {
  const grid = document.getElementById('mp-catalog-grid');
  const pagination = document.getElementById('mp-pagination');
  if (!grid) return;

  // While the (slow) catalog is still being built, keep showing the spinner
  // instead of flashing an empty "no results" state when a filter or search is
  // clicked — otherwise changing category looks like it cancelled the load.
  if (currentMarketplaceCatalog.length === 0) {
    if (isLoadingCatalog) renderMarketplaceLoading();
    else renderMarketplaceError();
    return;
  }

  // The "Updates" view needs release tags for installed items; resolve them.
  if (currentMarketplaceFilter === 'updates') {
    ensureMarketplaceVersions(currentMarketplaceCatalog.filter(i => i.installed));
  }

  const filtered = getFilteredCatalog();
  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));

  if (currentPage > totalPages) currentPage = totalPages;

  grid.innerHTML = '';
  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty-msg">${t('mp_no_results')}</div>`;
    if (pagination) pagination.style.display = 'none';
    return;
  }

  if (pagination) pagination.style.display = 'flex';

  const start = (currentPage - 1) * ITEMS_PER_PAGE;
  const pageItems = filtered.slice(start, start + ITEMS_PER_PAGE);

  pageItems.forEach(item => {
    const card = document.createElement('div');
    card.className = 'mp-card';
    card.id = `mp-card-${item.id}`;

    const isApp = item.type === 'app';
    let badgeClass = 'mp-badge-ext';
    let badgeText = t('mp_badge_ext');
    if (item.type === 'theme') {
      badgeClass = 'mp-badge-theme';
      badgeText = t('mp_badge_theme');
    } else if (isApp) {
      badgeClass = 'mp-badge-app';
      badgeText = t('mp_badge_app');
    }

    const statusText = item.installed ? t('mp_status_installed') : t('mp_status_available');
    const statusClass = item.installed ? 'mp-status-installed' : 'mp-status-available';
    const statusHtml = isApp ? '' : `<span class="mp-status-tag ${statusClass}">${statusText}</span>`;

    const repoUrl = `https://github.com/${item.user}/${item.repo}`;

    // Custom apps have no standard entry point/install layout, so they are
    // browse-only (like the official Marketplace): the action opens the repo
    // instead of installing.
    let actionHtml;
    if (isApp) {
      actionHtml = `
          <button class="btn btn-small btn-mp-open" data-id="${item.id}" title="${t('mp_gh_title')}">
            ${GITHUB_ICON_SVG} ${t('mp_view')}
          </button>`;
    } else {
      const btnClass = item.installed ? 'btn-danger' : 'btn-accent';
      const btnText = item.installed ? t('mp_uninstall') : t('mp_install');
      const btnIcon = item.installed ? 'trash-2' : 'download';
      actionHtml = `
          <button class="btn btn-small ${btnClass} btn-mp-action" data-id="${item.id}">
            <i data-lucide="${btnIcon}"></i> ${btnText}
          </button>`;
    }

    const repoKey = `${item.user}/${item.repo}`;
    const latest = repoVersions[repoKey] || {};
    const latestInfo = { tag: latest.tag || '', updated_at: latest.updated_at || item.updated_at || '' };
    const latestLabel = versionLabel(latestInfo);
    const installedLabel = item.installed ? versionLabel(item.meta) : '';
    const outdated = item.installed && versionOutdated(item.meta, latestInfo);

    const versionParts = [];
    if (installedLabel) versionParts.push(`${t('mp_version_installed')}: ${installedLabel}`);
    if (latestLabel) versionParts.push(`${t('mp_version_latest')}: ${latestLabel}`);
    const versionHtml = (versionParts.length || outdated)
      ? `<div class="mp-card-version">${versionParts.join(' · ')}${outdated ? ` <span class="mp-update-badge">${t('mp_update_available')}</span>` : ''}</div>`
      : '';

    card.innerHTML = `
      <div>
        <div class="mp-card-header">
          <span class="mp-card-title">${item.title}</span>
          <span class="mp-card-badge ${badgeClass}">${badgeText}</span>
        </div>
        <div class="mp-card-author">${t('mp_by')} ${item.author}</div>
        <div class="mp-card-desc">${item.description}</div>
        ${versionHtml}
      </div>
      <div class="mp-card-footer">
        ${statusHtml}
        <div class="mp-card-actions">
          ${isApp ? '' : `<button class="btn btn-small btn-mp-gh" title="${t('mp_gh_title')}">${GITHUB_ICON_SVG}</button>`}
          ${actionHtml}
        </div>
      </div>
    `;

    const ghBtn = card.querySelector('.btn-mp-gh');
    if (ghBtn) {
      ghBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openExternal(repoUrl);
      });
    }

    const openBtn = card.querySelector('.btn-mp-open');
    if (openBtn) {
      openBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openExternal(repoUrl);
      });
    }

    const actionBtn = card.querySelector('.btn-mp-action');
    if (actionBtn) {
      actionBtn.addEventListener('click', async () => {
        actionBtn.disabled = true;
        actionBtn.classList.add('is-busy');
        actionBtn.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span><span class="btn-busy-label">...</span>';
        if (window.lucide) lucide.createIcons();
        try {
          if (item.installed) {
            await uninstallMarketplaceItem(item);
          } else {
            await installMarketplaceItem(item);
          }
        } finally {
          actionBtn.classList.remove('is-busy');
        }
      });
    }

    grid.appendChild(card);
  });

  // Lazily resolve release tags / dates for the visible page, then re-render.
  ensureMarketplaceVersions(pageItems);

  // Update pagination info
  const pageInfo = document.getElementById('mp-page-info');
  if (pageInfo) pageInfo.textContent = t('mp_page').replace('{c}', currentPage).replace('{t}', totalPages);

  const prevBtn = document.getElementById('btn-mp-prev');
  const nextBtn = document.getElementById('btn-mp-next');
  if (prevBtn) prevBtn.disabled = currentPage <= 1;
  if (nextBtn) nextBtn.disabled = currentPage >= totalPages;

  const updateAllBtn = document.getElementById('btn-mp-update-all');
  if (updateAllBtn) {
    updateAllBtn.style.display = (currentMarketplaceFilter === 'updates' && getOutdatedItems().length)
      ? 'inline-flex' : 'none';
  }

  if (window.lucide) window.lucide.createIcons();
}

async function installMarketplaceItem(item) {
  const cached = repoVersions[`${item.user}/${item.repo}`] || {};
  const res = await apiFetch('/api/marketplace/install', 'POST', {
    type: item.type,
    filename: item.filename,
    url: item.url,
    user: item.user,
    repo: item.repo,
    branch: item.branch,
    css_url: item.css_url,
    schemes_url: item.schemes_url,
    include: item.include,
    updated_at: cached.updated_at || item.updated_at || '',
    tag: cached.tag || '',
  });
  if (res && res.status === 'ok') {
    appendConsole(`${item.title} ${t('mp_installed_ok')}`);
    pollStatus();
    await loadMarketplaceCatalog(true);
  } else {
    appendConsole(`${t('mp_installed_err')} ${item.title}: ${res?.error || t('mp_failed')}`);
    await loadMarketplaceCatalog(true);
  }
}

async function uninstallMarketplaceItem(item) {
  const res = await apiFetch('/api/marketplace/uninstall', 'POST', {
    type: item.type,
    filename: item.filename,
  });
  if (res && res.status === 'ok') {
    appendConsole(`${item.title} ${t('mp_uninstalled_ok')}`);
    pollStatus();
    await loadMarketplaceCatalog(true);
  } else {
    appendConsole(`${t('mp_uninstalled_err')} ${item.title}: ${res?.error || t('mp_failed')}`);
    await loadMarketplaceCatalog(true);
  }
}
