// Preserve active filters when moving between pages.
document.querySelector('.sidebar nav [aria-current]')?.scrollIntoView({block: 'nearest', inline: 'nearest'});

document.querySelectorAll('[data-page]').forEach(link => {
  const url = new URL(window.location.href);
  url.searchParams.set('page', link.dataset.page);
  link.href = url.pathname + url.search;
});

// The form remains usable without JavaScript. Prevent accidental double submits.
document.querySelectorAll('form[data-busy]').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"], button:not([type])');
    if (!button) return;
    button.disabled = true;
    button.textContent = form.dataset.busy;
    form.setAttribute('aria-busy', 'true');
  });
});


// Only the waiting transaction page polls. Scoring never runs inside a request.
const pendingAnalysis = document.querySelector('[data-analysis-pending]');
if (pendingAnalysis) {
  let attempts = 0;
  const poll = async () => {
    try {
      const response = await fetch(pendingAnalysis.dataset.analysisPending, {headers: {'Accept': 'application/json'}});
      if (!response.ok) throw new Error('Status unavailable');
      const result = await response.json();
      if (result.status === 'completed' || result.status === 'failed') { window.location.reload(); return; }
    } catch (_) { /* Temporary network errors do not change the saved request. */ }
    if (++attempts < 60) setTimeout(poll, 1500);
    else pendingAnalysis.textContent = 'Analiza continuă în fundal. Reîncarcă pagina pentru rezultat.';
  };
  setTimeout(poll, 1000);
}


// Read-only lists refresh when new results arrive; never interrupt an edited form.
const monitor = document.querySelector('[data-monitor-revision]');
if (monitor) setInterval(async () => {
  if (document.hidden || document.activeElement?.matches('input, select, textarea')) return;
  try {
    const response = await fetch('/monitor/status/');
    if (!response.ok) return;
    const data = await response.json();
    if (data.revision !== monitor.dataset.monitorRevision) window.location.reload();
  } catch (_) { /* Keep the current results if the local connection is interrupted. */ }
}, 7000);


// Refresh only server-rendered monitoring panels; controls and focus remain stable.
const dashboard = document.querySelector('[data-dashboard]');
const playbackForm = document.querySelector('[data-playback]');
let refreshing = false;
const initialDashboardTime = Date.now();
const refreshDashboard = async () => {
  if (!dashboard || refreshing || document.hidden) return;
  refreshing = true;
  try {
    const response = await fetch(dashboard.dataset.dashboard, {headers: {'Accept': 'application/json'}});
    if (!response.ok) throw new Error('Dashboard unavailable');
    const data = await response.json();
    const incoming = document.createElement('template');
    incoming.innerHTML = data.html;
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
    const button = playbackForm?.querySelector('button');
    if (button) {
      button.value = data.playback === 'running' ? 'paused' : 'running';
      button.textContent = data.playback === 'running' ? 'Pauză scenariu' : data.playback === 'completed' ? 'Reia scenariul' : 'Pornește scenariul';
      button.classList.toggle('secondary', data.playback === 'running');
      button.disabled = false;
    }
    document.querySelector('#connection-status').textContent = 'Actualizare automată la 3 secunde · Date sintetice';
  } catch (_) {
    document.querySelector('#connection-status').textContent = 'Conexiune întreruptă. Reconectare automată…';
  } finally { refreshing = false; }
};
if (dashboard) setInterval(refreshDashboard, 3000);
playbackForm?.addEventListener('submit', async event => {
  event.preventDefault();
  const button = playbackForm.querySelector('button');
  const body = new FormData(playbackForm);
  body.set('action', button.value);
  button.disabled = true;
  try {
    const response = await fetch(playbackForm.getAttribute('action'), {method: 'POST', body, headers: {'Accept': 'application/json'}});
    if (!response.ok) throw new Error('Control unavailable');
    await refreshDashboard();
  } catch (_) {
    document.querySelector('#connection-status').textContent = 'Scenariul nu a fost modificat. Încearcă din nou.';
  } finally { button.disabled = false; }
});
