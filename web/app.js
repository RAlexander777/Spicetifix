const API_BASE = 'http://127.0.0.1:8765';

let currentUITheme = 'emerald';
let currentLang = 'es';
let systemConfig = {};

const I18N = {
  es: {
    system_ready: '[ SISTEMA_LISTO ]',
    about_btn: 'ℹ ACERCA DE',
    options_btn: '⚙ OPCIONES',
    ui_theme_lbl: 'Tema UI:',
    now_playing_title: '// REPRODUCIENDO EN SPOTIFY',
    loading_spotify: '🎵 Cargando estado de Spotify...',
    prev_btn: '⏮ ANTERIOR',
    play_btn: '⏯ REPRODUCIR / PAUSAR',
    next_btn: '⏭ SIGUIENTE',
    sec_status: '// ESTADO DEL SISTEMA',
    card_spotify_sub_ok: 'Instalado y detectado',
    card_spotify_sub_err: 'Spotify no encontrado',
    card_spicetify_sub_ok: 'Configurado (config-xpui.ini)',
    card_spicetify_sub_err: 'Spicetify no configurado',
    tag_online: '[ ONLINE ]',
    tag_missing: '[ FALTA ]',
    tag_active: '[ ACTIVO ]',
    sec_actions: '// ACCIONES DEL SISTEMA',
    btn_install: '▶ EJECUTAR INSTALACIÓN COMPLETA',
    btn_recover: '↺ RECUPERAR SISTEMA',
    sec_exts: '// GESTOR DE EXTENSIONES SPICETIFY',
    lbl_exts_header: 'Extensiones y Apps Detectadas:',
    btn_refresh: '↻ RECARGAR',
    sec_logs: '// CONSOLA DE LOGS',
    modal_opt_title: '⚙ OPCIONES Y CONFIGURACIÓN DEL SISTEMA',
    opt_sec_gen: '🌐 AJUSTES GENERALES',
    lbl_lang: 'Idioma / Language:',
    lbl_spicetify_theme: 'Tema de Spicetify:',
    opt_sec_flags: '⚡ BANDERAS AVANZADAS DE SPICETIFY',
    lbl_flag_css: 'Inyectar CSS',
    lbl_flag_colors: 'Reemplazar Colores',
    lbl_flag_assets: 'Sobrescribir Assets',
    lbl_flag_devtools: 'DevTools Siempre Activo',
    lbl_flag_sentry: 'Telemetría Sentry',
    opt_sec_danger: '🚨 ZONA DE PELIGRO (DESINSTALACIÓN Y RECUPERACIÓN)',
    btn_spicetify_apply: '⚡ APLICAR CAMBIOS DE SPICETIFY',
    btn_uninstall_spicetify: '🗑 DESINSTALAR SPICETIFY',
    btn_uninstall_spotify: '🔥 DESINSTALAR SPOTIFY Y SPICETIFY',
    btn_save_options: 'GUARDAR Y APLICAR OPCIONES',
    modal_about_title: 'ℹ ACERCA DE AUTOMATIFY',
    about_desc: 'Automatify es un centro de control terminal de diseño minimalista e instalador automatizado para Spotify y Spicetify en Windows.',
    about_author_lbl: 'Autor / Creador:',
    about_license_lbl: 'Licencia:',
    about_engine_lbl: 'Motor:',
    about_repo_lbl: 'Repositorio GitHub:',
    about_features_title: '🚀 Funcionalidades Principales:',
    about_feat_1: 'Instalación en 1-clic de Spotify, Spicetify CLI, Marketplace y Temas.',
    about_feat_2: 'Gestor visual de extensiones con interruptores en vivo.',
    about_feat_3: 'Reproductor integrado de Spotify mediante llamadas nativas Win32 API.',
    about_feat_4: 'Recuperación automatizada post-actualización de Spotify (spicetify restore backup apply).',
    about_feat_5: '7 Temas estéticos estilo cyberpunk con soporte para modo claro y oscuro.',
    btn_close: 'CERRAR',
    confirm_spicetify: '¿Desinstalar Spicetify y restaurar el parche de Spotify?',
    confirm_spotify: '⚠️ ATENCIÓN: Esto desinstalará completamente Spotify y Spicetify del sistema. ¿Deseas continuar?'
  },
  en: {
    system_ready: '[ SYSTEM_READY ]',
    about_btn: 'ℹ ABOUT',
    options_btn: '⚙ OPTIONS',
    ui_theme_lbl: 'UI Theme:',
    now_playing_title: '// SPOTIFY NOW PLAYING',
    loading_spotify: '🎵 Loading Spotify Status...',
    prev_btn: '⏮ PREV',
    play_btn: '⏯ PLAY / PAUSE',
    next_btn: '⏭ NEXT',
    sec_status: '// SYSTEM STATUS',
    card_spotify_sub_ok: 'Installed and detected',
    card_spotify_sub_err: 'Spotify not found',
    card_spicetify_sub_ok: 'Configured (config-xpui.ini)',
    card_spicetify_sub_err: 'Spicetify not configured',
    tag_online: '[ ONLINE ]',
    tag_missing: '[ MISSING ]',
    tag_active: '[ ACTIVE ]',
    sec_actions: '// SYSTEM ACTIONS',
    btn_install: '▶ RUN FULL INSTALL / UPDATE',
    btn_recover: '↺ RECOVER SYSTEM',
    sec_exts: '// SPICETIFY EXTENSION MANAGER',
    lbl_exts_header: 'Detected Extensions & Custom Apps:',
    btn_refresh: '↻ REFRESH',
    sec_logs: '// SYSTEM LOGS',
    modal_opt_title: '⚙ SYSTEM OPTIONS & CONFIGURATION',
    opt_sec_gen: '🌐 GENERAL SETTINGS',
    lbl_lang: 'Language / Idioma:',
    lbl_spicetify_theme: 'Spicetify Theme:',
    opt_sec_flags: '⚡ ADVANCED SPICETIFY FLAGS',
    lbl_flag_css: 'Inject CSS',
    lbl_flag_colors: 'Replace Colors',
    lbl_flag_assets: 'Overwrite Assets',
    lbl_flag_devtools: 'Always Enable DevTools',
    lbl_flag_sentry: 'Sentry Telemetry',
    opt_sec_danger: '🚨 DANGER ZONE (UNINSTALL & RECOVERY)',
    btn_spicetify_apply: '⚡ APPLY SPICETIFY CHANGES',
    btn_uninstall_spicetify: '🗑 UNINSTALL SPICETIFY',
    btn_uninstall_spotify: '🔥 UNINSTALL SPOTIFY & SPICETIFY',
    btn_save_options: 'SAVE & APPLY OPTIONS',
    modal_about_title: 'ℹ ABOUT AUTOMATIFY',
    about_desc: 'Automatify is a minimalist terminal-styled control center and automated installer for Spotify and Spicetify on Windows.',
    about_author_lbl: 'Author / Creator:',
    about_license_lbl: 'License:',
    about_engine_lbl: 'Engine:',
    about_repo_lbl: 'GitHub Repository:',
    about_features_title: '🚀 Key Features:',
    about_feat_1: '1-Click installation for Spotify, Spicetify CLI, Marketplace & Themes.',
    about_feat_2: 'Visual extension manager with live toggles.',
    about_feat_3: 'Integrated Spotify player using native Win32 API calls.',
    about_feat_4: 'Automated post-update recovery for Spotify.',
    about_feat_5: '7 Cyberpunk aesthetic themes with light & dark mode support.',
    btn_close: 'CLOSE',
    confirm_spicetify: 'Uninstall Spicetify and restore Spotify patch?',
    confirm_spotify: '⚠️ WARNING: This will completely uninstall Spotify and Spicetify from your system. Continue?'
  }
};

async function apiFetch(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API error (${endpoint}):`, err);
    return null;
  }
}

// Apply Language to UI
function applyLanguage(lang) {
  currentLang = lang in I18N ? lang : 'es';
  const t = I18N[currentLang];

  const setTxt = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setTxt('system-badge', t.system_ready);
  setTxt('btn-open-about', t.about_btn);
  setTxt('btn-open-options', t.options_btn);
  setTxt('btn-prev', t.prev_btn);
  setTxt('btn-play', t.play_btn);
  setTxt('btn-next', t.next_btn);
  setTxt('sec-title-status', t.sec_status);
  setTxt('sec-title-actions', t.sec_actions);
  setTxt('btn-install', t.btn_install);
  setTxt('btn-recover', t.btn_recover);
  setTxt('sec-title-exts', t.sec_exts);
  setTxt('lbl-exts-header', t.lbl_exts_header);
  setTxt('btn-refresh-exts', t.btn_refresh);
  setTxt('sec-title-logs', t.sec_logs);
  setTxt('modal-opt-title', t.modal_opt_title);
  setTxt('opt-sec-gen', t.opt_sec_gen);
  setTxt('lbl-lang', t.lbl_lang);
  setTxt('lbl-spicetify-theme', t.lbl_spicetify_theme);
  setTxt('opt-sec-flags', t.opt_sec_flags);
  setTxt('lbl-flag-css', t.lbl_flag_css);
  setTxt('lbl-flag-colors', t.lbl_flag_colors);
  setTxt('lbl-flag-assets', t.lbl_flag_assets);
  setTxt('lbl-flag-devtools', t.lbl_flag_devtools);
  setTxt('lbl-flag-sentry', t.lbl_flag_sentry);
  setTxt('opt-sec-danger', t.opt_sec_danger);
  setTxt('btn-spicetify-apply', t.btn_spicetify_apply);
  setTxt('btn-uninstall-spicetify', t.btn_uninstall_spicetify);
  setTxt('btn-uninstall-spotify', t.btn_uninstall_spotify);
  setTxt('btn-save-options', t.btn_save_options);
  setTxt('btn-close-about-footer', t.btn_close);

  // About modal texts
  const modalAboutTitle = document.querySelector('#about-modal h2');
  if (modalAboutTitle) modalAboutTitle.textContent = t.modal_about_title;

  const aboutDesc = document.querySelector('.about-desc');
  if (aboutDesc) aboutDesc.textContent = t.about_desc;

  const details = document.querySelectorAll('.detail-item strong');
  if (details.length >= 4) {
    details[0].textContent = t.about_author_lbl;
    details[1].textContent = t.about_license_lbl;
    details[2].textContent = t.about_engine_lbl;
    details[3].textContent = t.about_repo_lbl;
  }

  const featH4 = document.querySelector('.about-features h4');
  if (featH4) featH4.textContent = t.about_features_title;

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

// Fetch and render status
async function pollStatus() {
  const data = await apiFetch('/api/status');
  if (!data) return;

  if (data.config) {
    systemConfig = data.config;
    if (systemConfig.language && systemConfig.language !== currentLang) {
      applyLanguage(systemConfig.language);
    }
  }

  const t = I18N[currentLang];

  // Now Playing
  const trackInfo = document.getElementById('track-info');
  if (data.now_playing) {
    if (data.now_playing.playing) {
      trackInfo.textContent = `🎵 ${data.now_playing.artist} — ${data.now_playing.title}`;
    } else {
      trackInfo.textContent = `🎵 ${data.now_playing.title || 'Spotify: Not Playing'}`;
    }
  }

  // Health / Cards
  const spotifyOk = data.health.some(h => h.label === 'spotify_path' && h.ok);
  const spicetifyOk = data.health.some(h => h.label === 'config_file' && h.ok);

  const tagSpotify = document.getElementById('tag-spotify');
  const subSpotify = document.getElementById('sub-spotify');
  if (spotifyOk) {
    tagSpotify.textContent = t.tag_online;
    tagSpotify.style.color = 'var(--accent-color)';
    subSpotify.textContent = t.card_spotify_sub_ok;
  } else {
    tagSpotify.textContent = t.tag_missing;
    tagSpotify.style.color = 'var(--danger-color)';
    subSpotify.textContent = t.card_spotify_sub_err;
  }

  const tagSpicetify = document.getElementById('tag-spicetify');
  const subSpicetify = document.getElementById('sub-spicetify');
  if (spicetifyOk) {
    tagSpicetify.textContent = t.tag_online;
    tagSpicetify.style.color = 'var(--accent-color)';
    subSpicetify.textContent = t.card_spicetify_sub_ok;
  } else {
    tagSpicetify.textContent = t.tag_missing;
    tagSpicetify.style.color = 'var(--danger-color)';
    subSpicetify.textContent = t.card_spicetify_sub_err;
  }

  const tagTheme = document.getElementById('tag-theme');
  const subTheme = document.getElementById('sub-theme');
  tagTheme.textContent = t.tag_active;
  tagTheme.style.color = 'var(--contrast-color)';
  subTheme.textContent = data.current_theme || 'None';

  // Console Output & Progress
  if (data.logs && data.logs.length > 0) {
    const consoleBox = document.getElementById('console-output');
    consoleBox.textContent = data.logs.join('\n');
    consoleBox.parentElement.scrollTop = consoleBox.parentElement.scrollHeight;
  }

  if (data.progress !== undefined) {
    const pBar = document.getElementById('progress-bar');
    pBar.style.width = `${Math.round(data.progress * 100)}%`;
  }
}

// Load extensions
async function loadExtensions() {
  const data = await apiFetch('/api/extensions');
  if (!data) return;

  const extGrid = document.getElementById('ext-grid');
  extGrid.innerHTML = '';

  const allItems = [
    ...(data.extensions || []).map(e => ({ ...e, type: 'ext' })),
    ...(data.custom_apps || []).map(a => ({ ...a, type: 'app' })),
  ];

  if (allItems.length === 0) {
    extGrid.innerHTML = '<div class="empty-msg">No extensions detected.</div>';
    return;
  }

  allItems.forEach(item => {
    const div = document.createElement('div');
    div.className = 'ext-item';

    const span = document.createElement('span');
    span.textContent = `● ${item.name}`;
    if (item.enabled) span.style.color = 'var(--accent-color)';

    const chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.checked = item.enabled;
    chk.addEventListener('change', async () => {
      await apiFetch('/api/extensions/toggle', 'POST', {
        name: item.name,
        enabled: chk.checked,
      });
      loadExtensions();
    });

    div.appendChild(span);
    div.appendChild(chk);
    extGrid.appendChild(div);
  });
}

// Load themes info & populate options modal
async function loadThemes() {
  const data = await apiFetch('/api/themes');
  if (!data) return;

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
    }
  }
}

// Open Options Modal
function openOptionsModal() {
  const modal = document.getElementById('options-modal');
  if (modal) {
    const selectLang = document.getElementById('select-lang');
    if (selectLang && currentLang) {
      selectLang.value = currentLang;
    }

    const spicetifySelect = document.getElementById('select-spicetify-theme');
    if (spicetifySelect && systemConfig.spicetify && systemConfig.spicetify.theme) {
      spicetifySelect.value = systemConfig.spicetify.theme;
    }

    modal.classList.add('active');
  }
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
    modal.classList.add('active');
  }
}

// Close About Modal
function closeAboutModal() {
  const modal = document.getElementById('about-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

// Save Options Modal
async function saveOptions() {
  const selectLang = document.getElementById('select-lang');
  const selectSpicetifyTheme = document.getElementById('select-spicetify-theme');

  const selectedLang = selectLang ? selectLang.value : 'es';
  applyLanguage(selectedLang);

  const body = {
    language: selectedLang,
    spicetify_theme: selectSpicetifyTheme ? selectSpicetifyTheme.value : 'SpicetifyDefault',
    ui_theme: currentUITheme,
  };

  await apiFetch('/api/config/save', 'POST', body);
  closeOptionsModal();
  pollStatus();
}

// Initialize UI
document.addEventListener('DOMContentLoaded', () => {
  applyLanguage('es');
  loadThemes();
  loadExtensions();
  pollStatus();
  setInterval(pollStatus, 1500);

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

  // Action buttons
  document.getElementById('btn-install').addEventListener('click', async () => {
    await apiFetch('/api/install', 'POST');
    pollStatus();
  });

  document.getElementById('btn-recover').addEventListener('click', async () => {
    await apiFetch('/api/recover', 'POST');
    pollStatus();
  });

  document.getElementById('btn-refresh-exts').addEventListener('click', loadExtensions);

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

  // Danger Zone Actions
  document.getElementById('btn-spicetify-apply').addEventListener('click', async () => {
    closeOptionsModal();
    await apiFetch('/api/spicetify/apply', 'POST');
    pollStatus();
  });

  document.getElementById('btn-uninstall-spicetify').addEventListener('click', async () => {
    const t = I18N[currentLang];
    if (confirm(t.confirm_spicetify)) {
      closeOptionsModal();
      await apiFetch('/api/uninstall/spicetify', 'POST');
      pollStatus();
    }
  });

  document.getElementById('btn-uninstall-spotify').addEventListener('click', async () => {
    const t = I18N[currentLang];
    if (confirm(t.confirm_spotify)) {
      closeOptionsModal();
      await apiFetch('/api/uninstall/spotify', 'POST');
      pollStatus();
    }
  });
});
