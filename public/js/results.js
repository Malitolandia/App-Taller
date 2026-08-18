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

const app = document.getElementById('app');
const uuid = new URLSearchParams(window.location.search).get('uuid');

let state = null; // { title, parts, suppliers, bids, winners }

function normalizeWhatsappPhone(phone) {
  const digits = String(phone || '').replace(/\D/g, '');
  if (digits.startsWith('57') && digits.length >= 12) return digits;
  if (digits.length === 10) return `57${digits}`;
  return digits;
}

function whatsappLink(phone, quoteTitle) {
  const number = normalizeWhatsappPhone(phone);
  const message = encodeURIComponent(
    `Hola, te escribo por la cotización "${quoteTitle}". ¿Cómo vas con los precios?`
  );
  return `https://wa.me/${number}?text=${message}`;
}

async function init() {
  if (!uuid) {
    app.innerHTML = '<div class="card alert-error">Falta el identificador de la cotización.</div>';
    return;
  }

  try {
    const res = await fetch(`/api/results?uuid=${encodeURIComponent(uuid)}`);

    if (res.status === 401) {
      window.location.href = `/admin-login.html?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      app.innerHTML = `<div class="card alert-error">${escapeHtml(data.error || 'Error al cargar resultados')}</div>`;
      return;
    }

    state = data;
    render();
  } catch {
    app.innerHTML = '<div class="card alert-error">Error de conexión. Intenta de nuevo.</div>';
  }
}

// ---------------------------------------------------------------------
// Estructuras derivadas
// ---------------------------------------------------------------------
function buildMaps() {
  const priceMap = {}; // priceMap[partId][supplierId] = price
  state.bids.forEach((b) => {
    if (!priceMap[b.partId]) priceMap[b.partId] = {};
    priceMap[b.partId][b.supplierId] = b.price;
  });

  const winnerMap = {}; // winnerMap[partId] = supplierId
  state.winners.forEach((w) => {
    winnerMap[w.partId] = w.supplierId;
  });

  return { priceMap, winnerMap };
}

function lowestForPart(priceMap, partId) {
  const row = priceMap[partId];
  if (!row) return null;
  const values = Object.values(row);
  return values.length ? Math.min(...values) : null;
}

// ---------------------------------------------------------------------
// Render principal
// ---------------------------------------------------------------------
function render() {
  const { title, parts, suppliers } = state;

  const header = `
    <h1>${escapeHtml(title)}</h1>
    <p class="muted">${suppliers.length} proveedor${suppliers.length === 1 ? '' : 'es'} · ${parts.length} repuesto${parts.length === 1 ? '' : 's'}</p>
  `;

  if (suppliers.length === 0) {
    app.innerHTML = `${header}<div class="card text-center muted" style="margin-top:16px;">Aún no hay cotizaciones de proveedores.</div>`;
    return;
  }

  const { priceMap, winnerMap } = buildMaps();

  app.innerHTML = `
    ${header}
    <div class="export-buttons" style="margin: 12px 0 0;">
      <button id="export-excel" class="btn-secondary">⬇️ Exportar Excel</button>
      <button id="export-pdf" class="btn-secondary">⬇️ Exportar PDF</button>
    </div>
    <div id="table-wrap"></div>
    <div id="purchase-wrap" style="margin-top:24px;"></div>
    <div style="margin-top:24px;">
      <h2>Contactos de proveedores</h2>
      <div id="contacts-wrap" class="contact-grid" style="margin-top:12px;"></div>
    </div>
  `;

  renderTable(priceMap, winnerMap);
  renderPurchaseList(priceMap, winnerMap);
  renderContacts();

  document.getElementById('export-excel').addEventListener('click', exportExcel);
  document.getElementById('export-pdf').addEventListener('click', exportPdf);
}

function renderTable(priceMap, winnerMap) {
  const { parts, suppliers } = state;

  const tableHeaders = suppliers.map((s) => `<th>${escapeHtml(s.company)}</th>`).join('');

  const tableRows = parts
    .map((part) => {
      const lowest = lowestForPart(priceMap, part.id);
      const cells = suppliers
        .map((s) => {
          const price = priceMap[part.id]?.[s.id];
          const isLowest = price !== undefined && price === lowest;
          const isWinner = winnerMap[part.id] === s.id;
          const cellClasses = [isLowest ? 'cell-lowest' : '', isWinner ? 'cell-winner' : ''].join(' ').trim();

          if (price === undefined) {
            return `<td class="${cellClasses}">—</td>`;
          }

          return `
            <td class="${cellClasses}">
              ${currency.format(price)}
              <button
                type="button"
                class="winner-btn ${isWinner ? 'is-winner' : ''}"
                data-part-id="${part.id}"
                data-supplier-id="${isWinner ? '' : s.id}"
              >${isWinner ? '✓ Elegido' : 'Elegir'}</button>
            </td>
          `;
        })
        .join('');
      return `
        <tr>
          <td class="sticky-col">
            ${escapeHtml(part.name)}
            ${part.code ? `<span class="muted" style="display:block; font-size:0.72rem;">${escapeHtml(part.code)}</span>` : ''}
            <span class="muted" style="display:block; font-size:0.72rem;">Cant: ${part.quantity}</span>
          </td>
          ${cells}
        </tr>
      `;
    })
    .join('');

  // Total = suma de precio unitario × cantidad por proveedor (informativo)
  const totals = {};
  suppliers.forEach((s) => {
    totals[s.id] = parts.reduce((sum, part) => {
      const price = priceMap[part.id]?.[s.id];
      const qty = part.quantity || 1;
      return price !== undefined ? sum + price * qty : sum;
    }, 0);
  });

  const totalCells = suppliers.map((s) => `<td>${currency.format(totals[s.id] || 0)}</td>`).join('');

  document.getElementById('table-wrap').innerHTML = `
    <div class="card table-scroll" style="margin-top:16px;">
      <p class="muted" style="margin: 0 0 10px;">
        Verde = precio unitario más bajo de esa fila. Haz click en "Elegir" para marcar con quién vas a comprar ese repuesto.
      </p>
      <table>
        <thead>
          <tr>
            <th class="sticky-col">Repuesto</th>
            ${tableHeaders}
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
        <tfoot>
          <tr>
            <td class="sticky-col">Total (precio × cantidad)</td>
            ${totalCells}
          </tr>
        </tfoot>
      </table>
    </div>
  `;

  document.querySelectorAll('.winner-btn').forEach((btn) => {
    btn.addEventListener('click', () => setWinner(btn.dataset.partId, btn.dataset.supplierId));
  });
}

async function setWinner(partId, supplierId) {
  try {
    await fetch('/api/set-winner', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quoteUuid: uuid, partId, supplierId: supplierId || null }),
    });
    // Actualiza estado local sin recargar todo desde el servidor
    state.winners = state.winners.filter((w) => w.partId !== partId);
    if (supplierId) state.winners.push({ partId, supplierId });
    render();
  } catch {
    alert('No se pudo guardar la selección. Intenta de nuevo.');
  }
}

function renderPurchaseList(priceMap, winnerMap) {
  const { parts, suppliers } = state;
  const wrap = document.getElementById('purchase-wrap');

  const chosenPartIds = Object.keys(winnerMap);
  if (chosenPartIds.length === 0) {
    wrap.innerHTML = `
      <h2>Lista de compra</h2>
      <div class="card muted text-center" style="margin-top:12px;">
        Aún no has elegido ganador para ningún repuesto. Usa el botón "Elegir" en la tabla de arriba.
      </div>
    `;
    return;
  }

  const bySupplier = {};
  let grandTotal = 0;

  parts.forEach((part) => {
    const supplierId = winnerMap[part.id];
    if (!supplierId) return;
    const price = priceMap[part.id]?.[supplierId];
    if (price === undefined) return;
    const qty = part.quantity || 1;
    const extended = price * qty;
    grandTotal += extended;

    if (!bySupplier[supplierId]) bySupplier[supplierId] = { items: [], total: 0 };
    bySupplier[supplierId].items.push({ part, price, qty, extended });
    bySupplier[supplierId].total += extended;
  });

  const groupsHtml = Object.entries(bySupplier)
    .map(([supplierId, group]) => {
      const supplier = suppliers.find((s) => s.id === supplierId);
      const itemsHtml = group.items
        .map(
          (it) => `
        <div class="row-between" style="padding: 4px 0; font-size:0.85rem;">
          <span>${escapeHtml(it.part.name)} × ${it.qty}</span>
          <span>${currency.format(it.extended)}</span>
        </div>
      `
        )
        .join('');

      return `
        <div class="purchase-group">
          <div class="row-between">
            <p style="font-weight:700; margin:0;">${escapeHtml(supplier ? supplier.company : 'Proveedor')}</p>
            <span class="purchase-group-total">${currency.format(group.total)}</span>
          </div>
          ${supplier ? `<p class="muted" style="margin:2px 0 8px;">📞 ${escapeHtml(supplier.phone)}</p>` : ''}
          ${itemsHtml}
        </div>
      `;
    })
    .join('');

  wrap.innerHTML = `
    <h2>Lista de compra</h2>
    <p class="muted" style="margin: 4px 0 12px;">Repuestos con ganador elegido, agrupados por proveedor.</p>
    ${groupsHtml}
    <div class="card" style="text-align:right;">
      <span class="muted" style="margin-right:8px;">Total general a pagar:</span>
      <span class="purchase-group-total" style="font-size:1.2rem;">${currency.format(grandTotal)}</span>
    </div>
  `;
}

function renderContacts() {
  const { suppliers, title } = state;
  const priceMap = buildMaps().priceMap;

  const totals = {};
  suppliers.forEach((s) => {
    totals[s.id] = state.parts.reduce((sum, part) => {
      const price = priceMap[part.id]?.[s.id];
      const qty = part.quantity || 1;
      return price !== undefined ? sum + price * qty : sum;
    }, 0);
  });

  document.getElementById('contacts-wrap').innerHTML = suppliers
    .map(
      (s) => `
      <div class="card">
        <p style="font-weight:700; margin:0;">${escapeHtml(s.company)}</p>
        <p class="muted" style="margin:4px 0 0;">📞 ${escapeHtml(s.phone)}</p>
        ${s.email ? `<p class="muted" style="margin:2px 0 0;">✉️ ${escapeHtml(s.email)}</p>` : ''}
        <p class="muted" style="margin-top:6px; font-size:0.75rem;">Total cotizado: ${currency.format(totals[s.id] || 0)}</p>
        <a class="whatsapp-btn" href="${whatsappLink(s.phone, title)}" target="_blank" rel="noopener">
          💬 WhatsApp
        </a>
      </div>
    `
    )
    .join('');
}

// ---------------------------------------------------------------------
// Exportar
// ---------------------------------------------------------------------
function exportExcel() {
  const { title, parts, suppliers } = state;
  const { priceMap } = buildMaps();

  const header = ['Repuesto', 'Código', 'Cantidad', ...suppliers.map((s) => s.company)];
  const rows = parts.map((part) => {
    const row = [part.name, part.code || '', part.quantity];
    suppliers.forEach((s) => {
      const price = priceMap[part.id]?.[s.id];
      row.push(price !== undefined ? price : '');
    });
    return row;
  });

  const totalsRow = ['Total (precio × cantidad)', '', ''];
  suppliers.forEach((s) => {
    const total = parts.reduce((sum, part) => {
      const price = priceMap[part.id]?.[s.id];
      const qty = part.quantity || 1;
      return price !== undefined ? sum + price * qty : sum;
    }, 0);
    totalsRow.push(total);
  });

  const sheetData = [header, ...rows, [], totalsRow];
  const ws = XLSX.utils.aoa_to_sheet(sheetData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Comparativo');
  XLSX.writeFile(wb, `comparativo-${slugify(title)}.xlsx`);
}

function exportPdf() {
  const { title, parts, suppliers } = state;
  const { priceMap } = buildMaps();

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: suppliers.length > 3 ? 'landscape' : 'portrait' });

  doc.setFontSize(14);
  doc.text(title, 14, 16);
  doc.setFontSize(9);
  doc.text(`Comparativo de cotizaciones - ${new Date().toLocaleDateString('es-CO')}`, 14, 22);

  const head = [['Repuesto', 'Cant.', ...suppliers.map((s) => s.company)]];
  const body = parts.map((part) => {
    const row = [part.name, String(part.quantity)];
    suppliers.forEach((s) => {
      const price = priceMap[part.id]?.[s.id];
      row.push(price !== undefined ? currency.format(price) : '—');
    });
    return row;
  });

  doc.autoTable({ head, body, startY: 28, styles: { fontSize: 8 } });
  doc.save(`comparativo-${slugify(title)}.pdf`);
}

function slugify(str) {
  return String(str)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

init();
