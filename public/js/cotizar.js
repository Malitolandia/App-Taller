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
const uuid = new URLSearchParams(window.location.search).get('uuid');

let quoteData = null;
let supplierId = null; // se llena al registrar/obtener proveedor

// ---------------------------------------------------------------------
// Renderizado de la imagen con modal de zoom
// ---------------------------------------------------------------------
function renderQuoteImage(image) {
  if (!image) return '';
  return `
    <div class="card" style="margin-bottom: 20px; text-align: center; cursor: pointer;" id="quote-image-card">
      <img src="${image}" alt="Imagen de la cotización" style="max-width: 100%; max-height: 300px; border-radius: 8px;" />
      <p class="muted" style="margin-top: 6px; font-size: 0.75rem;">Haz clic para ampliar</p>
    </div>
    <!-- Modal de zoom -->
    <div id="image-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; justify-content:center; align-items:center; cursor:pointer;">
      <img src="${image}" style="max-width:90%; max-height:90%; border-radius:12px; box-shadow:0 0 40px rgba(0,0,0,0.8);" />
    </div>
  `;
}

function setupImageZoom() {
  const card = document.getElementById('quote-image-card');
  const modal = document.getElementById('image-modal');
  if (card && modal) {
    card.addEventListener('click', () => { modal.style.display = 'flex'; });
    modal.addEventListener('click', () => { modal.style.display = 'none'; });
  }
}

// ---------------------------------------------------------------------
// Render de cabecera
// ---------------------------------------------------------------------
function renderHeader(title) {
  return `
    <div style="text-align:center; margin-bottom: 20px;">
      <p class="muted" style="text-transform:uppercase; letter-spacing:0.05em; font-weight:700; font-size:0.72rem;">
        Solicitud de cotización
      </p>
      <h1 style="margin-top:4px;">${escapeHtml(title)}</h1>
    </div>
  `;
}

// ---------------------------------------------------------------------
// Autocompletar empresa según teléfono
// ---------------------------------------------------------------------
let lookupTimeout = null;

function setupAutocomplete() {
  const phoneInput = document.getElementById('phone');
  const companyInput = document.getElementById('company');

  phoneInput.addEventListener('input', () => {
    clearTimeout(lookupTimeout);
    const phone = phoneInput.value.trim();
    if (phone.length < 7) return; // esperar al menos 7 dígitos
    lookupTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`/api/supplier-lookup?phone=${encodeURIComponent(phone)}`);
        const data = await res.json();
        if (data.found && data.company) {
          // Si el teléfono coincide, autocompletar empresa
          companyInput.value = data.company;
        } else {
          // Si no se encuentra, no borramos lo que el usuario haya escrito
        }
      } catch (e) {
        // silencioso
      }
    }, 400);
  });
}

// ---------------------------------------------------------------------
// Renderizado único: datos + precios
// ---------------------------------------------------------------------
function renderCombinedStep() {
  const imageHtml = renderQuoteImage(quoteData.image || '');
  const partsHtml = quoteData.parts
    .map(
      (part) => `
      <div class="part-row">
        <div class="part-with-image">
          <div class="part-fields">
            <p style="font-weight:700; margin:0;">${escapeHtml(part.name)}</p>
            ${
              part.code || part.unit
                ? `<p class="muted" style="margin:2px 0;">${part.code ? 'Código: ' + escapeHtml(part.code) : ''} ${
                    part.unit ? '· Unidad: ' + escapeHtml(part.unit) : ''
                  }</p>`
                : ''
            }
            <p class="muted" style="margin:2px 0; font-weight:700;">Cantidad solicitada: ${part.quantity || 1}</p>
            ${part.description ? `<p class="muted" style="margin:2px 0 8px;">${escapeHtml(part.description)}</p>` : ''}
          </div>
          ${
            part.image
              ? `<div class="part-image-box"><img class="image-thumb" src="${part.image}" alt="Foto de ${escapeHtml(part.name)}" /></div>`
              : ''
          }
        </div>
        <div style="margin-top:8px;">
          <input type="number" step="0.01" min="0" class="bid-price" data-part-id="${part.id}" placeholder="Precio unitario (COP)" />
        </div>
      </div>
    `
    )
    .join('');

  app.innerHTML = `
    ${renderHeader(quoteData.title)}
    ${imageHtml}
    <form id="combined-form" class="card">
      <h2>Datos de tu empresa</h2>
      <div class="field">
        <label class="label" for="company">Empresa *</label>
        <input id="company" type="text" required />
      </div>
      <div class="field">
        <label class="label" for="phone">Teléfono (WhatsApp) *</label>
        <input id="phone" type="tel" required />
      </div>

      <hr style="border-color: var(--br); margin: 20px 0;" />

      <h2>Ingresa tus precios</h2>
      <p class="subtitle">Completa el precio para cada repuesto (deja en blanco si no manejas alguno).</p>
      ${partsHtml}

      <div id="combined-error"></div>
      <button type="submit" id="combined-submit" class="btn btn-primary" style="margin-top:16px;">Enviar cotización</button>
    </form>
  `;

  setupImageZoom();
  setupAutocomplete();

  const form = document.getElementById('combined-form');
  const errorBox = document.getElementById('combined-error');
  const submitBtn = document.getElementById('combined-submit');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.innerHTML = '';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Enviando…';

    const company = document.getElementById('company').value.trim();
    const phone = document.getElementById('phone').value.trim();

    if (!company || !phone) {
      errorBox.innerHTML = '<div class="alert-error">Empresa y teléfono son obligatorios.</div>';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Enviar cotización';
      return;
    }

    // Paso 1: Registrar/obtener proveedor
    try {
      const regRes = await fetch('/api/suppliers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uuid, company, phone }),
      });
      const regData = await regRes.json();
      if (!regRes.ok) {
        errorBox.innerHTML = `<div class="alert-error">${escapeHtml(regData.error || 'Error al registrar')}</div>`;
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enviar cotización';
        return;
      }
      supplierId = regData.supplierId;

      // Paso 2: Recolectar precios
      const bids = Array.from(document.querySelectorAll('.bid-price'))
        .map((input) => ({
          partId: input.dataset.partId,
          price: input.value.trim(),
        }))
        .filter((b) => b.price.length > 0);

      // Enviar precios
      const bidRes = await fetch('/api/bids', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ supplierId, bids }),
      });
      const bidData = await bidRes.json();
      if (!bidRes.ok) {
        errorBox.innerHTML = `<div class="alert-error">${escapeHtml(bidData.error || 'Error al enviar precios')}</div>`;
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enviar cotización';
        return;
      }

      // Éxito
      app.innerHTML = `
        ${renderHeader(quoteData.title)}
        ${imageHtml}
        <div class="card text-center">
          <p style="font-size:1.8rem; margin:0;">✅</p>
          <h2 style="margin-top:8px;">¡Cotización enviada!</h2>
          <p class="subtitle" style="margin-top:4px;">Gracias por tu tiempo. El administrador revisará tu propuesta.</p>
        </div>
      `;
    } catch (err) {
      errorBox.innerHTML = '<div class="alert-error">Error de conexión. Intenta de nuevo.</div>';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Enviar cotización';
    }
  });
}

// ---------------------------------------------------------------------
// Inicialización
// ---------------------------------------------------------------------
async function init() {
  if (!uuid) {
    app.innerHTML = '<div class="card alert-error">Enlace inválido: falta el identificador de la cotización.</div>';
    return;
  }

  try {
    const res = await fetch(`/api/quote?uuid=${encodeURIComponent(uuid)}`);
    const data = await res.json();

    if (!res.ok) {
      app.innerHTML = `<div class="card text-center">${escapeHtml(data.error || 'Cotización no encontrada')}</div>`;
      return;
    }

    quoteData = data;

    if (data.status === 'CLOSED') {
      const imageHtml = renderQuoteImage(data.image || '');
      app.innerHTML = `
        ${renderHeader(data.title)}
        ${imageHtml}
        <div class="card text-center muted">
          Esta cotización ya fue cerrada por el administrador. Gracias por tu interés.
        </div>
      `;
      setupImageZoom();
      return;
    }

    if (!data.parts || data.parts.length === 0) {
      const imageHtml = renderQuoteImage(data.image || '');
      app.innerHTML = `
        ${renderHeader(data.title)}
        ${imageHtml}
        <div class="card text-center muted">
          Esta cotización aún no tiene repuestos cargados.
        </div>
      `;
      setupImageZoom();
      return;
    }

    renderCombinedStep();
  } catch {
    app.innerHTML = '<div class="card alert-error">Error de conexión. Intenta de nuevo más tarde.</div>';
  }
}

init();