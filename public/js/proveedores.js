function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));
}

const app = document.getElementById('app');

async function checkSession() {
  try {
    const res = await fetch('/api/session');
    const data = await res.json();
    if (!data.authenticated) {
      window.location.href = '/admin-login.html?next=/proveedores.html';
      return false;
    }
    return true;
  } catch {
    window.location.href = '/admin-login.html';
    return false;
  }
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return iso;
  }
}

async function init() {
  const ok = await checkSession();
  if (!ok) return;

  try {
    const res = await fetch('/api/supplier-stats');
    const data = await res.json();

    if (!res.ok) {
      app.innerHTML = `<div class="card alert-error">${escapeHtml(data.error || 'Error al cargar')}</div>`;
      return;
    }

    render(data.stats || []);
  } catch {
    app.innerHTML = '<div class="card alert-error">Error de conexión.</div>';
  }
}

function render(stats) {
  if (stats.length === 0) {
    app.innerHTML = '<div class="card text-center muted">Aún no hay proveedores registrados.</div>';
    return;
  }

  const rows = stats
    .map(
      (s, idx) => `
      <tr>
        <td><span class="rank-badge">${idx + 1}</span></td>
        <td>
          <strong>${escapeHtml(s.company)}</strong>
          <span class="muted" style="display:block; font-size:0.75rem;">📞 ${escapeHtml(s.phone)}</span>
        </td>
        <td>${s.quotesInvited}</td>
        <td>${s.bidsGiven}</td>
        <td>${s.timesLowestPrice}</td>
        <td><strong>${s.timesChosenWinner}</strong></td>
        <td>${formatDate(s.lastSubmittedAt)}</td>
      </tr>
    `
    )
    .join('');

  app.innerHTML = `
    <div class="card table-scroll">
      <table class="stats-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Proveedor</th>
            <th>Veces invitado</th>
            <th>Precios enviados</th>
            <th>Veces más barato</th>
            <th>Veces elegido ganador</th>
            <th>Última vez</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p class="muted" style="margin-top:10px; font-size:0.78rem;">
      "Veces más barato" cuenta repuestos donde este proveedor tuvo el precio unitario más bajo
      (aunque no lo hayas elegido formalmente). "Veces elegido ganador" cuenta solo lo que
      marcaste con el botón "Elegir" en cada cotización.
    </p>
  `;
}

init();
