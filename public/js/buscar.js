function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));
}

const currency = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
});

const input = document.getElementById('search-input');
const resultsEl = document.getElementById('results');

async function checkSession() {
  try {
    const res = await fetch('/api/session');
    const data = await res.json();
    if (!data.authenticated) {
      window.location.href = '/admin-login.html?next=/buscar.html';
      return false;
    }
    return true;
  } catch {
    window.location.href = '/admin-login.html?next=/buscar.html';
    return false;
  }
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return iso;
  }
}

function renderLowest(lowest) {
  if (!lowest) return '';
  return `
    <div class="card" style="border-color: var(--green-700); background: var(--green-100); margin-bottom: 16px;">
      <p style="font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.03em; color: var(--green-800); margin:0;">
        💰 Precio más bajo histórico
      </p>
      <p style="font-size:1.4rem; font-weight:800; color: var(--green-800); margin:6px 0 0;">
        ${currency.format(lowest.price)}
      </p>
      <p style="margin:4px 0 0; color: var(--green-800); font-size:0.85rem;">
        <strong>${escapeHtml(lowest.company)}</strong>${lowest.phone ? ' · 📞 ' + escapeHtml(lowest.phone) : ''}
      </p>
      <p style="margin:2px 0 0; color: var(--green-800); font-size:0.8rem;">
        ${escapeHtml(lowest.partName)} — cotización "${escapeHtml(lowest.quoteTitle)}" · ${formatDate(lowest.date)}
      </p>
    </div>
  `;
}

function renderResultCard(item) {
  const badgeClass = item.quoteStatus === 'ACTIVE' ? 'badge-active' : 'badge-closed';
  const badgeLabel = item.quoteStatus === 'ACTIVE' ? 'Activa' : 'Cerrada';

  const bidsHtml = item.bids.length
    ? item.bids
        .map(
          (b, idx) => `
        <div class="row-between" style="padding: 6px 0; ${idx > 0 ? 'border-top: 1px solid var(--navy-100);' : ''}">
          <span style="font-size:0.85rem; color: var(--navy-700);">
            ${escapeHtml(b.company)}${b.phone ? ' · 📞 ' + escapeHtml(b.phone) : ''}
          </span>
          <span style="font-weight:700; font-size:0.85rem; ${idx === 0 ? 'color: var(--green-700);' : 'color: var(--navy-700);'}">
            ${currency.format(b.price)}
          </span>
        </div>
      `
        )
        .join('')
    : `<p class="muted" style="margin: 6px 0 0;">Sin precios recibidos todavía.</p>`;

  return `
    <div class="card">
      <div class="row-between">
        <div>
          <p style="font-weight:700; margin:0;">${escapeHtml(item.name)}</p>
          ${item.code ? `<p class="muted" style="margin:2px 0 0;">Código: ${escapeHtml(item.code)}</p>` : ''}
        </div>
        <a href="/results.html?uuid=${item.quoteUuid}" class="btn-secondary" style="white-space:nowrap;">Ver cotización</a>
      </div>
      <p class="muted" style="margin: 8px 0 4px;">
        En "${escapeHtml(item.quoteTitle)}"
        ${item.quoteStatus ? `<span class="badge ${badgeClass}" style="margin-left:6px;">${badgeLabel}</span>` : ''}
        · ${formatDate(item.quoteDate)}
      </p>
      <div style="margin-top: 8px;">
        ${bidsHtml}
      </div>
    </div>
  `;
}

let debounceTimer = null;

async function runSearch(query) {
  if (query.trim().length < 2) {
    resultsEl.innerHTML = query.trim().length === 0
      ? '<p class="muted text-center" style="padding: 24px 0;">Escribe al menos 2 letras para buscar.</p>'
      : '';
    return;
  }

  resultsEl.innerHTML = '<p class="spinner-text">Buscando…</p>';

  try {
    const res = await fetch(`/api/search-parts?q=${encodeURIComponent(query)}`);
    if (res.status === 401) {
      window.location.href = '/admin-login.html?next=/buscar.html';
      return;
    }
    const data = await res.json();

    if (!res.ok) {
      resultsEl.innerHTML = `<div class="card alert-error">${escapeHtml(data.error || 'Error al buscar')}</div>`;
      return;
    }

    if (data.results.length === 0) {
      resultsEl.innerHTML = '<div class="card text-center muted">No se encontraron repuestos con ese nombre o código.</div>';
      return;
    }

    resultsEl.innerHTML = renderLowest(data.lowest) + data.results.map(renderResultCard).join('');
  } catch {
    resultsEl.innerHTML = '<div class="card alert-error">Error de conexión. Intenta de nuevo.</div>';
  }
}

input.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  const query = input.value;
  debounceTimer = setTimeout(() => runSearch(query), 350);
});

(async function init() {
  const ok = await checkSession();
  if (ok) {
    resultsEl.innerHTML = '<p class="muted text-center" style="padding: 24px 0;">Escribe al menos 2 letras para buscar.</p>';
  }
})();
