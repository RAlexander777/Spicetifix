const API_BASE = 'http://127.0.0.1:8765';

let currentUITheme = 'emerald';

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
    tagSpotify.textContent = '[ ONLINE ]';
    tagSpotify.style.color = 'var(--accent-color)';
    subSpotify.textContent = 'Installed and detected';
  } else {
    tagSpotify.textContent = '[ MISSING ]';
    tagSpotify.style.color = 'var(--danger-color)';
    subSpotify.textContent = 'Spotify not found';
  }

  const tagSpicetify = document.getElementById('tag-spicetify');
  const subSpicetify = document.getElementById('sub-spicetify');
  if (spicetifyOk) {
    tagSpicetify.textContent = '[ ONLINE ]';
    tagSpicetify.style.color = 'var(--accent-color)';
    subSpicetify.textContent = 'Configured (config-xpui.ini)';
  } else {
    tagSpicetify.textContent = '[ NOT CONFIG ]';
    tagSpicetify.style.color = 'var(--danger-color)';
    subSpicetify.textContent = 'Spicetify not configured';
  }

  const tagTheme = document.getElementById('tag-theme');
  const subTheme = document.getElementById('sub-theme');
  tagTheme.textContent = '[ ACTIVE ]';
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
    extGrid.innerHTML = '<div class="empty-msg">No extensions detected in Spicetify folder.</div>';
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

// Load themes info
async function loadThemes() {
  const data = await apiFetch('/api/themes');
  if (data && data.current_ui_theme) {
    applyUITheme(data.current_ui_theme);
  }
}

// Initialize UI
document.addEventListener('DOMContentLoaded', () => {
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
});
