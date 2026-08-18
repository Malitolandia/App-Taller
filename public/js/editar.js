// public/js/editar.js
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
let quoteImageData = '';
const removedPartIds = new Set();

function setQuoteImage(dataUrl) {
  quoteImageData = dataUrl || '';
  const thumb = document.getElementById('quote-image-thumb');
  const placeholder = document.getElementById('quote-image-placeholder');
  const remove = document.getElementById('quote-remove-image');
  if (!thumb || !placeholder || !remove) return;
  thumb.src = quoteImageData;
  thumb.style.display = quoteImageData ? 'block' : 'none';
  placeholder.style.display = quoteImageData ? 'none' : 'block';
  remove.style.display = quoteImageData ? 'inline-flex' : 'none';
}

function addPartRow(part = {}) {
  const row = document.createElement('div');
  row.className = 'card edit-part-row';
  row.dataset.partId = part.id || '';
  row.dataset.hasBids = part.hasBids ? 'true' : 'false';
  row.innerHTML = `
    <div class="row-between">
      <strong>${part.hasBids ? 'Repuesto con precios recibidos' : 'Repuesto'}</strong>
      <button type="button" class="btn-link remove-part" ${part.hasBids ? 'disabled title="No se puede eliminar: ya tiene precios"' : ''}>Quitar</button>
    </div>
    <div class="grid-2" style="margin-top:10px;">
      <label class="field"><span class="label">Nombre *</span>
        <input class="part-name" value="${escapeHtml(part.name || '')}" required /></label>
      <label class="field"><span class="label">Cantidad *</span>
        <input class="part-quantity" type="number" min="1" step="1" value="${escapeHtml(part.quantity || 1)}" required /></label>
      <label class="field"><span class="label">Código</span>
        <input class="part-code" value="${escapeHtml(part.code || '')}" /></label>
      <label class="field"><span class="label">Unidad</span>
        <input class="part-unit" value="${escapeHtml(part.unit || '')}" /></label>
    </div>
    <label class="field"><span class="label">Descripción</span>
      <textarea class="part-description" rows="2">${escapeHtml(part.description || '')}</textarea></label>
  `;
  row.querySelector('.remove-part').addEventListener('click', () => {
    if (row.dataset.partId) removedPartIds.add(row.dataset.partId);
    row.remove();
  });
  document.getElementById('parts-list').appendChild(row);
}

function renderForm() {
  quoteImageData = quoteData.image || '';
  app.innerHTML = `
    <div class="row-between" style="margin-bottom:14px;">
      <div>
        <p class="muted" style="margin:0;">Edición administrativa</p>
        <h1 style="margin:4px 0 0;">Editar cotización</h1>
      </div>
      <span class="badge ${quoteData.status === 'ACTIVE' ? 'badge-active' : 'badge-closed'}">
        ${quoteData.status === 'ACTIVE' ? 'Activa' : 'Cerrada'}
      </span>
    </div>
    <form id="edit-form">
      <div class="card">
        <label class="field"><span class="label">Título *</span>
          <input id="quote-title" value="${escapeHtml(quoteData.title)}" required /></label>
        <div class="field">
          <span class="label">Imagen principal</span>
          <div id="quote-image-placeholder" class="muted">Sin imagen</div>
          <img id="quote-image-thumb" alt="Vista previa" style="display:none; max-width:100%; max-height:220px; border-radius:8px;" />
          <div style="display:flex; gap:8px; margin-top:8px;">
            <label class="btn btn-secondary" for="quote-image-input">Seleccionar imagen</label>
            <button type="button" id="quote-remove-image" class="btn-link">Quitar imagen</button>
          </div>
          <input id="quote-image-input" type="file" accept="image/*" hidden />
        </div>
      </div>
      <div class="row-between" style="margin:18px 0 8px;">
        <h2 style="margin:0;">Repuestos</h2>
        <button type="button" id="add-part" class="btn btn-secondary">Agregar repuesto</button>
      </div>
      <div id="parts-list"></div>
      <div id="edit-error"></div>
      <button type="submit" id="save-edit" class="btn btn-primary" style="margin-top:16px;">Guardar cambios</button>
    </form>
  `;

  const partsList = document.getElementById('parts-list');
  (quoteData.parts || []).forEach(addPartRow);
  if (!quoteData.parts || quoteData.parts.length === 0) addPartRow();
  document.getElementById('add-part').addEventListener('click', () => addPartRow());
  document.getElementById('quote-remove-image').addEventListener('click', () => setQuoteImage(''));
  document.getElementById('quote-image-input').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const compressed = typeof compressImageFile === 'function'
        ? await compressImageFile(file)
        : await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });
      setQuoteImage(compressed);
    } catch (error) {
      document.getElementById('edit-error').innerHTML = `<div class="alert-error">${escapeHtml(error.message || 'No se pudo procesar la imagen.')}</div>`;
    } finally {
      event.target.value = '';
    }
  });
  setQuoteImage(quoteImageData);

  document.getElementById('edit-form').addEventListener('submit', saveChanges);
}

function collectParts() {
  return Array.from(document.querySelectorAll('.edit-part-row')).map((row) => ({
    id: row.dataset.partId || undefined,
    name: row.querySelector('.part-name').value.trim(),
    code: row.querySelector('.part-code').value.trim(),
    unit: row.querySelector('.part-unit').value.trim(),
    description: row.querySelector('.part-description').value.trim(),
    quantity: row.querySelector('.part-quantity').value.trim() || '1',
  })).filter((part) => part.name.length > 0);
}

async function saveChanges(event) {
  event.preventDefault();
  const errorBox = document.getElementById('edit-error');
  const button = document.getElementById('save-edit');
  errorBox.innerHTML = '';
  button.disabled = true;
  button.textContent = 'Guardando…';

  try {
    const response = await fetch(`/api/quote-edit?uuid=${encodeURIComponent(uuid)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        uuid,
        title: document.getElementById('quote-title').value.trim(),
        image: quoteImageData,
        parts: collectParts(),
        removedPartIds: Array.from(removedPartIds),
      }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'No se pudieron guardar los cambios.');
    }
    const blocked = Array.isArray(data.blocked) && data.blocked.length
      ? `\nNo se eliminaron porque ya tienen precios: ${data.blocked.join(', ')}.`
      : '';
    alert(`Cambios guardados correctamente.${blocked}`);
    window.location.href = '/admin.html';
  } catch (error) {
    errorBox.innerHTML = `<div class="alert-error">${escapeHtml(error.message || 'Error de conexión.')}</div>`;
    button.disabled = false;
    button.textContent = 'Guardar cambios';
  }
}

async function init() {
  if (!uuid) {
    app.innerHTML = '<div class="card alert-error">Enlace inválido: falta el identificador de la cotización.</div>';
    return;
  }
  try {
    const sessionResponse = await fetch('/api/session');
    const session = await sessionResponse.json();
    if (!session.authenticated) {
      window.location.href = `/admin-login.html?next=${encodeURIComponent(`/editar.html?uuid=${uuid}`)}`;
      return;
    }
    const response = await fetch(`/api/quote-edit?uuid=${encodeURIComponent(uuid)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Cotización no encontrada.');
    quoteData = data;
    renderForm();
  } catch (error) {
    app.innerHTML = `<div class="card alert-error">${escapeHtml(error.message || 'No se pudo cargar la cotización.')}</div>`;
  }
}

init();
