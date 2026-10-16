// Navigation collapses in the app panel and on phones; all links work without JS.
const navigation = document.querySelector('#workspace-navigation');
const navToggle = document.querySelector('.nav-toggle');
if (navigation && navToggle) {
  const compact = window.matchMedia('(max-width: 1023px)');
  document.documentElement.classList.add('nav-ready');
  const syncNavigation = () => {
    const expanded = !compact.matches || navToggle.getAttribute('aria-expanded') === 'true';
    navigation.hidden = !expanded;
  };
  navToggle.addEventListener('click', () => {
    navToggle.setAttribute('aria-expanded', String(navToggle.getAttribute('aria-expanded') !== 'true'));
    syncNavigation();
  });
  navigation.addEventListener('keydown', event => {
    if (event.key === 'Escape' && compact.matches) {
      navToggle.setAttribute('aria-expanded', 'false');
      syncNavigation();
      navToggle.focus();
    }
  });
  compact.addEventListener('change', syncNavigation);
  syncNavigation();
}

// Mobile records retain every value with its column label. Desktop stays tabular.
const prepareTables = root => root.querySelectorAll('table[data-responsive]').forEach(table => {
  const labels = Array.from(table.querySelectorAll('thead th'), th => th.textContent.trim());
  table.querySelectorAll('tbody tr').forEach(row => Array.from(row.cells).forEach((cell, index) => {
    if (!cell.hasAttribute('colspan')) cell.dataset.label = labels[index] || '';
  }));
  table.classList.add('mobile-ready');
});
prepareTables(document);

document.querySelectorAll('[data-page]').forEach(link => {
  const url = new URL(window.location.href);
  url.searchParams.set('page', link.dataset.page);
  link.href = url.pathname + url.search;
});
document.querySelector('[data-error-summary]')?.focus();
document.querySelectorAll('form[data-busy]').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"], button:not([type])');
    if (!button) return;
    button.disabled = true;
    button.textContent = form.dataset.busy;
    form.setAttribute('aria-busy', 'true');
  });
});
// Back/forward-cache restoration must also restore submit buttons.
window.addEventListener('pageshow', event => {
  if (event.persisted) window.location.reload();
});

const requestJSON = async (url, options = {}) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(url, {...options, signal: controller.signal,
      headers: {'Accept': 'application/json', ...options.headers}});
    if (response.redirected && new URL(response.url).pathname === '/login/') {
      const error = new Error('Sesiunea a expirat. Autentifică-te din nou.');
      error.sessionExpired = true;
      throw error;
    }
    if (!response.ok) throw new Error('Răspuns indisponibil');
    return await response.json();
  } finally { clearTimeout(timeout); }
};

const pendingAnalysis = document.querySelector('[data-analysis-pending]');
if (pendingAnalysis) {
  let attempts = 0;
  const poll = async () => {
    try {
      const result = await requestJSON(pendingAnalysis.dataset.analysisPending);
      if (result.status === 'completed' || result.status === 'failed') { window.location.reload(); return; }
    } catch (error) {
      if (error.sessionExpired) { pendingAnalysis.textContent = error.message; return; }
    }
    if (++attempts < 60) setTimeout(poll, 1500);
    else pendingAnalysis.textContent = 'Analiza continuă în fundal. Reîncarcă pagina pentru rezultat.';
  };
  setTimeout(poll, 1000);
}

// New records never reset a list while the analyst is reading or filtering it.
const monitor = document.querySelector('[data-monitor-revision]');
document.querySelector('[data-refresh-list]')?.addEventListener('click', () => window.location.reload());
if (monitor) {
  const listTimer = setInterval(async () => {
    if (document.hidden) return;
    try {
      const data = await requestJSON('/monitor/status/');
      if (data.revision !== monitor.dataset.monitorRevision) {
        document.querySelector('[data-list-update]').hidden = false;
        clearInterval(listTimer);
      }
    } catch (error) { if (error.sessionExpired) clearInterval(listTimer); }
  }, 7000);
}

// Only data panels refresh. Focus, open evidence and scrolled records stay stable.
const dashboard = document.querySelector('[data-dashboard]');
const playbackForm = document.querySelector('[data-playback]');
const connectionStatus = document.querySelector('#connection-status');
let refreshing = false;
let playbackBusy = false;
let controlVersion = 0;
let sessionExpired = false;
const initialDashboardTime = Date.now();
const showPlayback = status => {
  const button = playbackForm?.querySelector('button');
  if (!button) return;
  button.value = status === 'running' ? 'paused' : 'running';
  button.textContent = status === 'running' ? 'Pauză scenariu' : status === 'completed' ? 'Reia scenariul' : 'Pornește scenariul';
  button.classList.toggle('secondary', status === 'running');
};
const refreshDashboard = async () => {
  if (!dashboard || refreshing || document.hidden || sessionExpired) return;
  refreshing = true;
  const version = controlVersion;
  try {
    const data = await requestJSON(dashboard.dataset.dashboard);
    const incoming = document.createElement('template');
    incoming.innerHTML = data.html;
    prepareTables(incoming.content);
    incoming.content.querySelectorAll('[data-live]').forEach(next => {
      const current = dashboard.querySelector(`[data-live="${next.dataset.live}"]`);
      if (!current) return;
      const reading = current.contains(document.activeElement) || current.querySelector('details[open]') ||
        Array.from(current.querySelectorAll('.table-wrap')).some(table => table.scrollLeft > 0);
      if (reading) {
        current.dataset.frozenAt ||= current.dataset.updatedAt || String(initialDashboardTime);
        let note = current.querySelector('[data-stale]');
        if (!note) {
          note = document.createElement('p');
          note.dataset.stale = '';
          note.className = 'panel-stale';
          current.prepend(note);
        }
        const age = Math.round((Date.now() - Number(current.dataset.frozenAt)) / 1000);
        note.textContent = `Actualizare în pauză cât consulți panoul · date de acum ${age} s.`;
      } else {
        next.dataset.updatedAt = String(Date.now());
        current.replaceWith(next);
      }
    });
    if (!playbackBusy && version === controlVersion) showPlayback(data.playback);
    connectionStatus.textContent = 'Actualizare automată la 3 secunde · Date sintetice';
  } catch (error) {
    sessionExpired = !!error.sessionExpired;
    connectionStatus.textContent = error.sessionExpired ? error.message : 'Conexiune întreruptă. Reconectare automată…';
  } finally { refreshing = false; }
};
if (dashboard) setInterval(refreshDashboard, 3000);
playbackForm?.addEventListener('submit', async event => {
  event.preventDefault();
  if (playbackBusy) return;
  const button = playbackForm.querySelector('button');
  const body = new FormData(playbackForm);
  body.set('action', button.value);
  playbackBusy = true;
  controlVersion++;
  button.disabled = true;
  playbackForm.setAttribute('aria-busy', 'true');
  try {
    const result = await requestJSON(playbackForm.getAttribute('action'), {method: 'POST', body});
    showPlayback(result.status);
    await refreshDashboard();
  } catch (error) {
    connectionStatus.textContent = error.sessionExpired ? error.message : 'Starea nu a putut fi confirmată. Se verifică automat…';
  } finally {
    playbackBusy = false;
    button.disabled = false;
    playbackForm.removeAttribute('aria-busy');
  }
});
