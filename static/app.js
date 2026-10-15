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
