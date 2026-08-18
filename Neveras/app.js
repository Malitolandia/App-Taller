/* app.js — Dashboard Neveras */
'use strict';

// ── DATOS EMBEBIDOS (fallback sin servidor) ───────────────────
const ORIG = {"ventas":[],"inventario":[],"clientes":[]};
let D = JSON.parse(JSON.stringify(ORIG));

const $ = id => document.getElementById(id);
const fmt = n => '$' + Number(n || 0).toLocaleString('es-CO');
let CH = {};

// ── NAVEGACIÓN POR TABS ───────────────────────────────────────
function tab(id, btn) {
  document.querySelectorAll('.sec').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  $(id).classList.add('active');
  btn.classList.add('active');
}

// ── RENDER DASHBOARD ──────────────────────────────────────────
function rDash() {
  const v  = D.ventas;
  const tV = v.reduce((s, r) => s + r.total, 0);
  const tC = v.filter(r => r.pago === 'SI').reduce((s, r) => s + r.total, 0);
  const tD = v.filter(r => r.pago === 'NO').reduce((s, r) => s + r.total, 0);
  const tG = v.reduce((s, r) => s + r.ganancia, 0);
  const nPag  = v.filter(r => r.pago === 'SI').length;
  const nPen  = v.filter(r => r.pago === 'NO').length;
  const tInv  = D.inventario.reduce((s, i) => s + (i.costo * Math.max(0, i.stockAct)), 0);
  const nAg   = D.inventario.filter(i => i.estado.includes('AGOTADO')).length;

  $('d-sub').textContent = v.length + ' transacciones · ' + D.clientes.length + ' clientes registrados';

  const kpis = [
    { l: 'Total Ventas',       v: fmt(tV), s: v.length + ' transacciones', i: '💰', c: 'var(--ac)' },
    { l: 'Total Cobrado',      v: fmt(tC), s: nPag + ' ventas pagadas',     i: '✅', c: 'var(--ac)' },
    { l: 'Deudas Pendientes',  v: fmt(tD), s: nPen + ' créditos',           i: '🔴', c: 'var(--rd)' },
    { l: 'Ganancia Total',     v: fmt(tG), s: ((tG / (tV || 1)) * 100).toFixed(1) + '% margen', i: '📈', c: 'var(--yw)' },
    { l: 'Valor Inventario',   v: fmt(tInv), s: D.inventario.length + ' productos', i: '📦', c: 'var(--bl)' },
    { l: 'Productos Agotados', v: nAg,     s: 'Requieren surtir',           i: '⚠️', c: 'var(--yw)' },
  ];

  $('kgrid').innerHTML = kpis.map(k =>
    `<div class="kcard" style="--kc:${k.c}">
       <div class="klabel">${k.l}</div>
       <div class="kval">${k.v}</div>
       <div class="ksub">${k.s}</div>
       <div class="kicon">${k.i}</div>
     </div>`).join('');

  // Gráfica: Top productos por ventas
  const prods = {};
  v.forEach(r => { prods[r.producto] = (prods[r.producto] || 0) + r.total; });
  const ps   = Object.entries(prods).sort((a, b) => b[1] - a[1]).slice(0, 7);
  const cols = ['#00e5a0','#3d8bff','#ffb800','#ff4f64','#a78bfa','#fb923c','#34d399'];
  if (CH.p) CH.p.destroy();
  CH.p = new Chart($('cProd'), {
    type: 'bar',
    data: { labels: ps.map(x => x[0]), datasets: [{ data: ps.map(x => x[1]), backgroundColor: cols, borderRadius: 6 }] },
    options: { plugins: { legend: { display: false } }, scales: {
      x: { ticks: { color: '#6b7590', font: { size: 11 } }, grid: { color: '#1e2330' } },
      y: { ticks: { color: '#6b7590', font: { size: 11 }, callback: v => '$' + v.toLocaleString() }, grid: { color: '#1e2330' } }
    }}
  });

  // Gráfica: Métodos de pago
  const mets = {};
  v.forEach(r => { mets[r.metodo] = (mets[r.metodo] || 0) + r.total; });
  if (CH.m) CH.m.destroy();
  CH.m = new Chart($('cMet'), {
    type: 'doughnut',
    data: { labels: Object.keys(mets), datasets: [{ data: Object.values(mets), backgroundColor: ['#00e5a0','#3d8bff','#ffb800'], borderWidth: 0, hoverOffset: 8 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#6b7590', font: { size: 12 }, padding: 12, boxWidth: 12 } } }, cutout: '68%', layout: { padding: 6 } }
  });

  // Gráfica: Ingresos vs Ganancia
  const ing = {}, gan = {};
  D.inventario.filter(i => i.vendidos > 0).forEach(i => {
    ing[i.producto] = i.vendidos * i.precio;
    gan[i.producto] = i.vendidos * i.ganUnit;
  });
  if (CH.ig) CH.ig.destroy();
  CH.ig = new Chart($('cIG'), {
    type: 'bar',
    data: { labels: Object.keys(ing), datasets: [
      { label: 'Ingresos',  data: Object.values(ing), backgroundColor: 'rgba(61,139,255,.7)',  borderRadius: 4 },
      { label: 'Ganancia',  data: Object.values(gan), backgroundColor: 'rgba(0,229,160,.7)',   borderRadius: 4 },
    ]},
    options: { plugins: { legend: { labels: { color: '#6b7590' } } }, scales: {
      x: { ticks: { color: '#6b7590', font: { size: 11 } }, grid: { color: '#1e2330' } },
      y: { ticks: { color: '#6b7590', font: { size: 11 }, callback: v => '$' + v.toLocaleString() }, grid: { color: '#1e2330' } }
    }}
  });
}

// ── FILTRO VENTAS ─────────────────────────────────────────────
let filtroVentas = { texto: '', soloDeudas: false };

function filtrarVentas(val) {
  filtroVentas.texto = val.trim();
  $('v-clear').style.display = filtroVentas.texto ? 'block' : 'none';
  rVentas();
}

function togglePendientes() {
  filtroVentas.soloDeudas = !filtroVentas.soloDeudas;
  const btn = $('btn-pendientes');
  btn.style.background  = filtroVentas.soloDeudas ? 'var(--rd)' : 'var(--s2)';
  btn.style.color       = filtroVentas.soloDeudas ? '#fff'      : 'var(--tm)';
  btn.style.borderColor = filtroVentas.soloDeudas ? 'var(--rd)' : 'var(--br)';
  rVentas();
}

function limpiarFiltroVentas() {
  filtroVentas = { texto: '', soloDeudas: false };
  $('v-buscar').value = '';
  $('v-clear').style.display = 'none';
  const btn = $('btn-pendientes');
  btn.style.background  = 'var(--s2)';
  btn.style.color       = 'var(--tm)';
  btn.style.borderColor = 'var(--br)';
  rVentas();
}

// ── RENDER VENTAS ─────────────────────────────────────────────
function rVentas() {
  const todos = D.ventas;

  // Aplicar filtros
  let v = todos;
  if (filtroVentas.texto) {
    const q = filtroVentas.texto.toUpperCase();
    v = v.filter(r => r.cliente.toUpperCase().includes(q));
  }
  if (filtroVentas.soloDeudas) {
    v = v.filter(r => r.pago === 'NO');
  }

  const hasFiltro  = filtroVentas.texto || filtroVentas.soloDeudas;
  const tTotal     = v.reduce((s, r) => s + r.total,   0);
  const tCobrado   = v.filter(r => r.pago === 'SI').reduce((s, r) => s + r.total, 0);
  const tPendiente = v.filter(r => r.pago === 'NO').reduce((s, r) => s + r.total, 0);

  $('v-sub').textContent = todos.length + ' transacciones · Total: ' + fmt(todos.reduce((s, r) => s + r.total, 0));
  $('v-cnt').textContent = (hasFiltro ? v.length + ' de ' + todos.length : v.length) + ' registros';

  // Resumen del filtro activo
  const info = $('v-filtro-info');
  if (hasFiltro) {
    info.style.display = 'block';
    info.innerHTML = v.length === 0
      ? `<span>Sin resultados para ese filtro</span>`
      : `Mostrando <strong style="color:var(--ac)">${v.length}</strong> venta${v.length !== 1 ? 's' : ''}
         &nbsp;·&nbsp; Total: <strong style="color:inherit">${fmt(tTotal)}</strong>
         &nbsp;·&nbsp; Cobrado: <strong style="color:var(--ac)">${fmt(tCobrado)}</strong>`
         + (tPendiente > 0
           ? `&nbsp;·&nbsp; Pendiente: <strong style="color:var(--rd)">${fmt(tPendiente)}</strong>`
           : '');
  } else {
    info.style.display = 'none';
  }

  $('tv').querySelector('tbody').innerHTML = v.map(r =>
    `<tr>
      <td style="color:var(--tm)">${r.num}</td>
      <td>${r.fecha}</td>
      <td>${r.hora || '—'}</td>
      <td style="font-weight:600">${r.cliente}</td>
      <td>${r.producto}</td>
      <td style="text-align:center">${r.cantidad}</td>
      <td>${fmt(r.precio)}</td>
      <td style="font-weight:600">${fmt(r.total)}</td>
      <td><span class="pill ${r.metodo==='Efectivo'?'pg':r.metodo==='Transferencia'?'pb':'pr'}">${r.metodo}</span></td>
      <td>${r.pago === 'NO'
            ? `<button class="pagar-btn" onclick="marcarPagado(${r.num})">💳 Cobrar</button>`
            : r.estado}</td>
      <td style="color:var(--ac)">${fmt(r.ganancia)}</td>
    </tr>`
  ).join('');
}

// ── RENDER INVENTARIO ─────────────────────────────────────────
function rInv() {
  const inv = D.inventario;
  $('i-sub').textContent = inv.length + ' productos · '
    + inv.filter(i => i.estado.includes('AGOTADO')).length + ' agotados · '
    + inv.filter(i => i.estado.includes('SURTIR')).length + ' por surtir';
  $('i-cnt').textContent = inv.length + ' productos';

  $('igrid').innerHTML = inv.map(i => {
    const pct = i.stockIni > 0 ? Math.max(0, (i.stockAct / i.stockIni) * 100) : 0;
    const cls = i.stockAct < 0 ? 'neg' : i.stockAct <= i.stockMin ? 'low' : 'ok';
    const cc  = i.estado.includes('AGOTADO') ? 'agot' : i.estado.includes('SURTIR') ? 'surt' : '';
    const bc  = cls === 'neg' ? 'var(--rd)' : cls === 'low' ? 'var(--yw)' : 'var(--ac)';
    return `<div class="iitem ${cc}">
      <div class="iname">${i.producto}</div>
      <div class="snum ${cls}">${i.stockAct}</div>
      <div class="ilabel">unidades</div>
      <div class="pbar"><div class="pfill" style="width:${pct}%;background:${bc}"></div></div>
      <div style="font-size:10px;color:var(--tm);margin-top:5px">${i.estado}</div>
    </div>`;
  }).join('');

  $('ti').querySelector('tbody').innerHTML = inv.map(i =>
    `<tr>
      <td style="font-weight:600">${i.producto}</td>
      <td>${i.costo ? fmt(i.costo) : '—'}</td>
      <td>${fmt(i.precio)}</td>
      <td style="color:var(--ac)">${fmt(i.ganUnit)}</td>
      <td>${i.stockIni}</td>
      <td>${i.vendidos}</td>
      <td style="font-weight:700;color:${i.stockAct < 0 ? 'var(--rd)' : i.stockAct <= i.stockMin ? 'var(--yw)' : 'var(--ac)'}">${i.stockAct}</td>
      <td>${i.estado}</td>
    </tr>`
  ).join('');
}

// ── RENDER DEUDAS ─────────────────────────────────────────────
function rDeudas() {
  const morosos = [...D.clientes].filter(c => c.deuda > 0).sort((a, b) => b.deuda - a.deuda);
  const td = morosos.reduce((s, c) => s + c.deuda, 0);
  $('deu-sub').textContent = morosos.length + ' clientes con deuda · Total: ' + fmt(td);
  $('dgrid').innerHTML = morosos.length === 0
    ? `<div style="color:var(--tm);font-size:14px;padding:12px">✅ No hay deudas pendientes</div>`
    : morosos.map(c =>
        `<div class="dcard debe">
          <div class="dcli">${c.cliente}</div>
          <div class="drow"><span>Total comprado</span><strong>${fmt(c.comprado)}</strong></div>
          <div class="drow"><span>Total pagado</span><strong style="color:var(--ac)">${fmt(c.pagado)}</strong></div>
          <div class="drow"><span>N° compras</span><strong>${c.compras}</strong></div>
          <div class="dtotal r">${fmt(c.deuda)}</div>
        </div>`
      ).join('');
}

// ── RENDER CLIENTES ───────────────────────────────────────────
function rClientes() {
  const cl = [...D.clientes].sort((a, b) => b.comprado - a.comprado);
  $('c-sub').textContent = cl.length + ' clientes · ' + fmt(cl.reduce((s, c) => s + c.comprado, 0)) + ' en ventas totales';
  $('c-cnt').textContent = cl.length + ' clientes';
  $('tc').querySelector('tbody').innerHTML = cl.map(c =>
    `<tr>
      <td style="font-weight:700">${c.cliente}</td>
      <td style="font-weight:600">${fmt(c.comprado)}</td>
      <td style="color:var(--ac)">${fmt(c.pagado)}</td>
      <td style="color:${c.deuda > 0 ? 'var(--rd)' : 'var(--tm)'};font-weight:${c.deuda > 0 ? '700' : '400'}">${c.deuda > 0 ? fmt(c.deuda) : '—'}</td>
      <td style="text-align:center">${c.compras}</td>
      <td><span class="pill ${c.deuda > 0 ? 'pr' : 'pg'}">${c.deuda > 0 ? '🔴 Debe' : '✅ Al día'}</span></td>
    </tr>`
  ).join('');
}

function renderAll() { rDash(); rVentas(); rInv(); rDeudas(); rClientes(); }

// ── INTEGRACIÓN CON SERVIDOR ──────────────────────────────────
const API = `${window.location.pathname.startsWith('/neveras') ? '/neveras' : ''}/api`;
let modoServidor = false;

function toast(msg, err = false) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  setTimeout(() => t.className = 'toast', 3000);
}

async function checkServidor() {
  try {
    const r = await fetch(API + '/productos', { signal: AbortSignal.timeout(1500), cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const loaded = await recargarDesdeServidor();
    if (!loaded) throw new Error('No se pudieron leer los datos remotos');
    modoServidor = true;
    $('srv-dot').className = 'srv-dot on';
    $('srv-txt').textContent = 'En línea';
    $('srv-txt').style.color = 'var(--ac)';
  } catch (err) {
    modoServidor = false;
    $('srv-dot').className = 'srv-dot';
    $('srv-txt').textContent = 'Sin servidor';
    $('srv-txt').style.color = '';
  }
}

async function recargarDesdeServidor() {
  try {
    const r    = await fetch(API + '/datos', { cache: 'no-store' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error || !Array.isArray(data.ventas) || !Array.isArray(data.inventario) || !Array.isArray(data.clientes)) return false;
    D.ventas     = data.ventas;
    D.inventario = data.inventario;
    D.clientes   = data.clientes;
    renderAll();
    return true;
  } catch { return false; }
}

// ── MODAL NUEVA VENTA ─────────────────────────────────────────
let itemsVenta = [];

function optionsProductosHTML(seleccionado) {
  let html = '<option value="">Seleccionar...</option>';
  D.inventario.forEach(i => {
    const sel = i.producto === seleccionado ? 'selected' : '';
    html += `<option value="${i.producto}" ${sel}>${i.producto} — $${i.precio.toLocaleString('es-CO')} (stock: ${i.stockAct})</option>`;
  });
  return html;
}

function renderItems() {
  $('m-items').innerHTML = itemsVenta.map((it, idx) => `
    <div style="display:grid;grid-template-columns:1fr 68px 88px 24px;gap:8px;align-items:end;margin-bottom:8px">
      <div>
        <label style="margin-bottom:3px">Producto</label>
        <select onchange="cambiarProductoItem(${idx}, this.value)">${optionsProductosHTML(it.producto)}</select>
      </div>
      <div>
        <label style="margin-bottom:3px">Cant.</label>
        <input type="number" min="1" value="${it.cantidad}" oninput="cambiarCantidadItem(${idx}, this.value)">
      </div>
      <div id="m-item-sub-${idx}" style="font-size:12px;color:var(--tm);text-align:right;padding-bottom:10px">${fmt(it.cantidad * it.precio)}</div>
      <button type="button" onclick="eliminarItem(${idx})" ${itemsVenta.length <= 1 ? 'disabled' : ''}
              style="background:none;border:none;color:var(--tm);cursor:${itemsVenta.length <= 1 ? 'default' : 'pointer'};font-size:14px;padding-bottom:9px;opacity:${itemsVenta.length <= 1 ? '.35' : '1'}">✕</button>
    </div>`
  ).join('');
  calcTotal();
}

function agregarItem() {
  itemsVenta.push({ producto: '', cantidad: 1, precio: 0, ganUnit: 0 });
  renderItems();
}

function eliminarItem(idx) {
  if (itemsVenta.length <= 1) return;
  itemsVenta.splice(idx, 1);
  renderItems();
}

function cambiarProductoItem(idx, valor) {
  const inv = D.inventario.find(i => i.producto === valor);
  itemsVenta[idx].producto = valor;
  itemsVenta[idx].precio   = inv ? inv.precio  : 0;
  itemsVenta[idx].ganUnit  = inv ? inv.ganUnit : 0;
  renderItems();
}

function cambiarCantidadItem(idx, valor) {
  itemsVenta[idx].cantidad = Math.max(0, parseInt(valor) || 0);
  const sub = $('m-item-sub-' + idx);
  if (sub) sub.textContent = fmt(itemsVenta[idx].cantidad * itemsVenta[idx].precio);
  calcTotal();
}

async function abrirModal() {
  // Reiniciar lista de productos de la venta
  itemsVenta = [{ producto: '', cantidad: 1, precio: 0, ganUnit: 0 }];
  renderItems();

  // Clientes desde Excel (pestaña Clientes, col A desde fila 2)
  const dl = $('lista-clientes');
  dl.innerHTML = '';
  try {
    if (modoServidor) {
      const r       = await fetch(API + '/lista-clientes', { cache: 'no-store' });
      const nombres = await r.json();
      if (Array.isArray(nombres)) {
        nombres.forEach(nombre => {
          const opt = document.createElement('option');
          opt.value = nombre;
          dl.appendChild(opt);
        });
      }
    } else {
      // Fallback offline: usar clientes ya cargados en memoria
      D.clientes.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.cliente;
        dl.appendChild(opt);
      });
    }
  } catch {
    // Fallback silencioso
    D.clientes.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.cliente;
      dl.appendChild(opt);
    });
  }

  $('m-cliente').value = '';
  $('overlay').classList.add('open');
  $('m-cliente').focus();
}

function cerrarModal() {
  $('overlay').classList.remove('open');
}

function checkPago() {
  const p = $('m-pago').value;
  $('m-metodo').value = p === 'SI' ? 'Efectivo' : 'Credito';
}

function calcTotal() {
  const total = itemsVenta.reduce((s, it) => s + (it.cantidad || 0) * (it.precio || 0), 0);
  $('m-total').textContent = fmt(total);
}

async function guardarVenta() {
  const cliente = $('m-cliente').value.trim().toUpperCase();
  const metodo  = $('m-metodo').value;
  const pago    = $('m-pago').value;

  if (!cliente) { toast('⚠️ Escribe el nombre del cliente', true); return; }

  const items = itemsVenta.filter(it => it.producto && it.cantidad > 0);
  if (items.length === 0)               { toast('⚠️ Agrega al menos un producto', true); return; }
  if (items.length !== itemsVenta.length) { toast('⚠️ Revisa los productos y cantidades', true); return; }

  if (modoServidor) {
    const btn = document.querySelector('.btn-save');
    btn.textContent = '⏳ Guardando...'; btn.disabled = true;
    try {
      const r    = await fetch(API + '/nueva-venta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cliente, items: items.map(it => ({ producto: it.producto, cantidad: it.cantidad })), metodo, pago })
      });
      const data = await r.json();
      if (data.ok) {
        D.ventas = data.ventas; D.inventario = data.inventario; D.clientes = data.clientes;
        renderAll(); cerrarModal(); toast(data.mensaje);
      } else {
        toast('Error: ' + data.error, true);
      }
    } catch { toast('No se pudo conectar al servidor', true); }
    btn.textContent = '💾 Guardar en la nube'; btn.disabled = false;
  } else {
    // Modo offline: solo en memoria (una fila por producto)
    let num    = Math.max(0, ...D.ventas.map(v => v.num));
    const hoy  = new Date().toISOString().substring(0, 10);
    const hora = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    let cli = D.clientes.find(c => c.cliente === cliente);
    if (!cli) { cli = { cliente, comprado: 0, pagado: 0, deuda: 0, compras: 0 }; D.clientes.push(cli); }

    items.forEach(it => {
      num++;
      const inv     = D.inventario.find(i => i.producto === it.producto);
      const precio  = inv ? inv.precio  : 0;
      const ganUnit = inv ? inv.ganUnit : 0;
      const total   = it.cantidad * precio;
      D.ventas.push({ num, fecha: hoy, hora, cliente, producto: it.producto, cantidad: it.cantidad, precio, total, metodo, pago,
        estado: pago === 'SI' ? '✅ PAGADO' : '🔴 PENDIENTE', ganancia: ganUnit * it.cantidad });
      if (inv) { inv.vendidos += it.cantidad; inv.stockAct -= it.cantidad; }
      cli.comprado += total; cli.compras++;
      if (pago === 'SI') cli.pagado += total; else cli.deuda += total;
    });

    renderAll(); cerrarModal();
    toast('⚠️ Guardado en memoria — inicia servidor.py para guardar en Excel');
  }
}

// ── MARCAR PAGADO ─────────────────────────────────────────────
async function marcarPagado(num) {
  if (!confirm(`¿Marcar venta #${num} como PAGADA?`)) return;
  if (modoServidor) {
    try {
      const r    = await fetch(API + '/marcar-pagado', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ num }), cache: 'no-store'
      });
      const data = await r.json();
      if (data.ok) { D.ventas = data.ventas; D.clientes = data.clientes; D.inventario = data.inventario; renderAll(); toast(data.mensaje); }
      else toast('Error: ' + data.error, true);
    } catch { toast('No se pudo conectar', true); }
  } else {
    const v = D.ventas.find(x => x.num === num);
    if (v) { v.pago = 'SI'; v.estado = '✅ PAGADO'; }
    const cli = D.clientes.find(c => c.cliente === v?.cliente);
    if (cli) { cli.deuda = Math.max(0, cli.deuda - (v?.total || 0)); cli.pagado += (v?.total || 0); }
    renderAll();
    toast('✅ Marcado como pagado (solo en memoria)');
  }
}

// ── CARGAR EXCEL MANUALMENTE ──────────────────────────────────
function cargarExcel(e) {
  const file = e.target.files[0]; if (!file) return;
  const btn  = document.querySelector('.upbtn.excel-btn');
  btn.textContent = '⏳ Leyendo...';
  const reader = new FileReader();
  reader.onload = function (ev) {
    try {
      const wb = XLSX.read(new Uint8Array(ev.target.result), { type: 'array', cellDates: true });
      const vs = wb.Sheets['Ventas'], is = wb.Sheets['Inventario'], cs = wb.Sheets['Clientes'];
      if (vs) {
        const rows = XLSX.utils.sheet_to_json(vs, { defval: '' });
        D.ventas = rows.filter(r => r['Producto']).map((r, i) => {
          let fecha = '';
          if (r['Fecha']) { const d = new Date(r['Fecha']); fecha = isNaN(d) ? String(r['Fecha']).substring(0, 10) : d.toISOString().substring(0, 10); }
          return {
            num:      r['N'] || r['#'] || i + 1,
            fecha,
            hora:     String(r['Hora'] || ''),
            cliente:  String(r['Cliente'] || ''),
            producto: String(r['Producto'] || ''),
            cantidad: Number(r['Cantidad']) || 0,
            precio:   Number(r['Precio Unit.']) || 0,
            total:    Number(r['Total']) || 0,
            metodo:   String(r['Método Pago'] || ''),
            pago:     String(r['Pagó']).trim().toUpperCase() === 'SI' ? 'SI' : 'NO',
            estado:   String(r['Estado Pago'] || ''),
            ganancia: Number(r['Ganancia']) || 0,
          };
        });
      }
      if (is) {
        const rows = XLSX.utils.sheet_to_json(is, { defval: '' });
        D.inventario = rows.filter(r => r['Producto']).map(r => ({
          producto: String(r['Producto']),
          costo:    Number(r['Costo']) || 0,
          precio:   Number(r['Precio Venta']) || 0,
          ganUnit:  Number(r['Ganancia Unit.']) || 0,
          stockIni: Number(r['Stock Inicial']) || 0,
          stockMin: Number(r['Stock Mín.']) || 0,
          vendidos: Number(r['Vendidos']) || 0,
          stockAct: Number(r['Stock Actual']) || 0,
          estado:   String(r['Estado'] || ''),
        }));
      }
      if (cs) {
        const rows = XLSX.utils.sheet_to_json(cs, { defval: '' });
        D.clientes = rows.filter(r => r['Cliente']).map(r => ({
          cliente:  String(r['Cliente']),
          comprado: Number(r['Total Comprado']) || 0,
          pagado:   Number(r['Total Pagado']) || 0,
          deuda:    Number(r['Deuda Pendiente']) || 0,
          compras:  Number(r['N° Compras']) || 0,
        }));
      }
      renderAll();
      btn.innerHTML = '✅ Actualizado!';
      setTimeout(() => { btn.innerHTML = '📂 Actualizar Excel'; }, 2500);
    } catch (err) {
      btn.innerHTML = '📂 Actualizar Excel';
      alert('Error al leer Excel: ' + err.message);
    }
    e.target.value = '';
  };
  reader.readAsArrayBuffer(file);
}

// ── INIT ──────────────────────────────────────────────────────
Chart.defaults.color        = '#6b7590';
Chart.defaults.borderColor  = '#1e2330';
Chart.defaults.font.family  = 'Space Grotesk';

$('fhoy').textContent = new Date().toLocaleDateString('es-CO', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
});

renderAll();
checkServidor();
setInterval(checkServidor, 10000);
