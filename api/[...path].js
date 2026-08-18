// api/[...path].js
// Este archivo maneja TODAS las rutas /api/* (catch-all)

const crypto = require('crypto');
const { SHEETS, getRows, appendRow, appendRows, updateRow, deleteRow, ensureReady } = require('./_lib/sheets');
const { notifyNewBid } = require('./_lib/notify');
const { requireAuth, setSessionCookie, clearSessionCookie, isAuthenticated } = require('./_lib/auth');

// ============================================================
// Utilidades
// ============================================================
function normalize(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

function normalizePhone(phone) {
  return String(phone || '').replace(/\D/g, '');
}

function getQuery(url) {
  const q = url.indexOf('?');
  if (q === -1) return {};
  const params = new URLSearchParams(url.slice(q + 1));
  const obj = {};
  for (const [key, val] of params) obj[key] = val;
  return obj;
}

// ============================================================
// Manejador principal
// ============================================================
module.exports = async (req, res) => {
  console.log('📥 Request:', req.method, req.url);

  // Parsear body solo para POST
  let body = {};
  if (req.method === 'POST') {
    try {
      const chunks = [];
      for await (const chunk of req) {
        chunks.push(chunk);
      }
      const data = Buffer.concat(chunks).toString();
      body = data ? JSON.parse(data) : {};
    } catch (err) {
      console.error('❌ Error al parsear body:', err);
      res.status(400).json({ error: 'Body inválido' });
      return;
    }
  }

  try {
    const url = req.url.split('?')[0]; // Solo la ruta, sin query params
    const query = getQuery(req.url);
    const method = req.method;

    // Diagnóstico real: comprueba acceso, pestañas y filas usando el mismo
    // adaptador que utiliza el resto de las rutas, no solo las variables.
    if (url === '/api/health' && method === 'GET') {
      await ensureReady();
      const counts = {};
      for (const sheetName of Object.keys(SHEETS)) {
        counts[sheetName] = (await getRows(sheetName)).length;
      }
      res.status(200).json({
        ok: true,
        backend: 'google_sheets',
        spreadsheet_configured: Boolean(process.env.SPREADSHEET_ID),
        sheet_counts: counts,
      });
      return;
    }

    await ensureReady();
    console.log(`📍 Ruta: ${url}, Método: ${method}`);

    // ============================================================
    // RUTAS DE AUTENTICACIÓN (reales)
    // ============================================================

    // POST /api/login
    if (url === '/api/login' && method === 'POST') {
      const { password } = body;
      const expected = process.env.ADMIN_PASSWORD || '';
      if (!password || password !== expected) {
        res.status(401).json({ error: 'Contraseña incorrecta' });
        return;
      }
      setSessionCookie(res);
      res.status(200).json({ ok: true });
      return;
    }

    // POST /api/logout
    if (url === '/api/logout' && method === 'POST') {
      clearSessionCookie(res);
      res.status(200).json({ ok: true });
      return;
    }

    // GET /api/session
    if (url === '/api/session' && method === 'GET') {
      const authenticated = isAuthenticated(req);
      res.status(200).json({ authenticated });
      return;
    }

    // ============================================================
    // RUTAS PÚBLICAS (sin autenticación)
    // ============================================================

    // GET /api/quote (público)
    if (url === '/api/quote' && method === 'GET' && query.uuid) {
      const uuid = query.uuid;
      const [quotes, allParts] = await Promise.all([getRows('Quotes'), getRows('Parts')]);
      const quote = quotes.find(q => q.uuid === uuid);
      if (!quote) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }
      const parts = allParts
        .filter(p => p.quote_uuid === uuid)
        .map(p => ({
          id: p.id,
          name: p.name,
          code: p.code,
          unit: p.unit,
          description: p.description,
          quantity: Number(p.quantity) > 0 ? Number(p.quantity) : 1,
          image: p.image || '',
        }));
      res.status(200).json({
        uuid: quote.uuid,
        title: quote.title,
        image: quote.image || '',
        status: quote.status,
        parts,
      });
      return;
    }

    // GET /api/supplier-lookup (público)
    if (url === '/api/supplier-lookup' && method === 'GET') {
      const phone = query.phone || '';
      const normalized = normalizePhone(phone);
      if (!normalized || normalized.length < 7) {
        res.status(200).json({ found: false });
        return;
      }
      const suppliers = await getRows('Suppliers');
      const match = suppliers.find(s => normalizePhone(s.phone) === normalized);
      if (match) {
        res.status(200).json({
          found: true,
          company: match.company,
          phone: match.phone,
        });
      } else {
        res.status(200).json({ found: false });
      }
      return;
    }

    // POST /api/suppliers (público)
    if (url === '/api/suppliers' && method === 'POST') {
      const { uuid, company, phone } = body;
      const cleanCompany = (company || '').trim();
      const cleanPhone = (phone || '').trim();
      if (!uuid || !cleanCompany || !cleanPhone) {
        res.status(400).json({ error: 'Empresa y teléfono son obligatorios' });
        return;
      }
      const quotes = await getRows('Quotes');
      const quote = quotes.find(q => q.uuid === uuid);
      if (!quote) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }
      if (quote.status !== 'ACTIVE') {
        res.status(400).json({ error: 'Esta cotización ya fue cerrada' });
        return;
      }

      const suppliers = await getRows('Suppliers');
      const normalized = cleanPhone.replace(/\D/g, '');
      const existing = suppliers.find(
        s => s.quote_uuid === uuid && normalizePhone(s.phone) === normalized
      );

      let supplierId;
      if (existing) {
        supplierId = existing.id;
        if (existing.company !== cleanCompany) {
          const { _row, ...rest } = existing;
          await updateRow('Suppliers', _row, { ...rest, company: cleanCompany });
        }
      } else {
        supplierId = crypto.randomUUID();
        await appendRow('Suppliers', {
          id: supplierId,
          quote_uuid: uuid,
          company: cleanCompany,
          phone: cleanPhone,
          email: '',
          submitted_at: new Date().toISOString(),
        });
      }
      res.status(200).json({ supplierId });
      return;
    }

    // POST /api/bids (público)
    if (url === '/api/bids' && method === 'POST') {
      const { supplierId, bids } = body;
      if (!supplierId || !Array.isArray(bids)) {
        res.status(400).json({ error: 'Parámetros inválidos' });
        return;
      }
      const cleanBids = bids
        .map(b => ({
          id: crypto.randomUUID(),
          supplier_id: supplierId,
          part_id: b.partId,
          price: String(b.price ?? '').trim(),
          notes: '',
        }))
        .filter(b => b.part_id && b.price.length > 0 && !Number.isNaN(Number(b.price)));
      if (cleanBids.length > 0) {
        await appendRows('Bids', cleanBids);
      }
      res.status(201).json({ ok: true });

      if (cleanBids.length > 0) {
        try {
          const [suppliers, quotes] = await Promise.all([getRows('Suppliers'), getRows('Quotes')]);
          const supplier = suppliers.find(s => s.id === supplierId);
          if (supplier) {
            const quote = quotes.find(q => q.uuid === supplier.quote_uuid);
            await notifyNewBid({
              quoteTitle: quote ? quote.title : '',
              quoteUuid: supplier.quote_uuid,
              company: supplier.company,
              phone: supplier.phone,
            });
          }
        } catch (notifyErr) {
          console.error('Error enviando notificación:', notifyErr);
        }
      }
      return;
    }

    // ============================================================
    // RUTAS ADMINISTRATIVAS (requieren autenticación)
    // ============================================================

    // GET /api/quotes
    if (url === '/api/quotes' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      const quotes = await getRows('Quotes');
      quotes.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      res.status(200).json({ quotes });
      return;
    }

    // POST /api/quotes (crear)
    if (url === '/api/quotes' && method === 'POST') {
      if (!requireAuth(req, res)) return;
      const { title, parts, image } = body;
      const cleanTitle = (title || '').trim();
      const cleanImage = typeof image === 'string' ? image.slice(0, 45000) : '';
      if (!cleanTitle) {
        res.status(400).json({ error: 'El título es obligatorio' });
        return;
      }
      const cleanParts = (Array.isArray(parts) ? parts : [])
        .map(p => {
          const qty = Number(p.quantity);
          return {
            id: crypto.randomUUID(),
            name: (p.name || '').trim(),
            code: (p.code || '').trim(),
            unit: (p.unit || '').trim(),
            description: (p.description || '').trim(),
            quantity: Number.isFinite(qty) && qty > 0 ? String(qty) : '1',
            image: typeof p.image === 'string' ? p.image.slice(0, 45000) : '',
          };
        })
        .filter(p => p.name.length > 0);
      if (cleanParts.length === 0) {
        res.status(400).json({ error: 'Agrega al menos un repuesto' });
        return;
      }
      const uuid = crypto.randomUUID();
      await appendRow('Quotes', {
        uuid,
        title: cleanTitle,
        image: cleanImage,
        status: 'ACTIVE',
        created_at: new Date().toISOString(),
      });
      await appendRows(
        'Parts',
        cleanParts.map(p => ({ ...p, quote_uuid: uuid }))
      );
      res.status(201).json({ uuid });
      return;
    }

    // DELETE /api/quotes (eliminar)
    if (url === '/api/quotes' && method === 'DELETE') {
      if (!requireAuth(req, res)) return;
      const uuid = query.uuid;
      if (!uuid) {
        res.status(400).json({ error: 'Falta el parámetro uuid' });
        return;
      }

      const [quotes, parts, suppliers, bids, winners] = await Promise.all([
        getRows('Quotes'),
        getRows('Parts'),
        getRows('Suppliers'),
        getRows('Bids'),
        getRows('Winners'),
      ]);

      const quote = quotes.find(q => q.uuid === uuid);
      if (!quote) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }

      const supplierIds = suppliers.filter(s => s.quote_uuid === uuid).map(s => s.id);

      // Eliminar winners
      for (const w of winners.filter(w => w.quote_uuid === uuid)) {
        await deleteRow('Winners', w._row);
      }

      // Eliminar bids
      for (const b of bids.filter(b => supplierIds.includes(b.supplier_id))) {
        await deleteRow('Bids', b._row);
      }

      // Eliminar suppliers
      for (const s of suppliers.filter(s => s.quote_uuid === uuid)) {
        await deleteRow('Suppliers', s._row);
      }

      // Eliminar parts
      for (const p of parts.filter(p => p.quote_uuid === uuid)) {
        await deleteRow('Parts', p._row);
      }

      // Eliminar la cotización
      await deleteRow('Quotes', quote._row);

      res.status(200).json({ ok: true });
      return;
    }

    // GET /api/part-catalog
    if (url === '/api/part-catalog' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      const parts = await getRows('Parts');
      const seen = new Map();
      for (const p of parts) {
        const name = (p.name || '').trim();
        if (!name) continue;
        const key = name.toLowerCase();
        if (!seen.has(key)) {
          seen.set(key, { name, code: p.code || '', unit: p.unit || '' });
        }
      }
      const catalog = Array.from(seen.values()).sort((a, b) => a.name.localeCompare(b.name));
      res.status(200).json({ catalog });
      return;
    }

    // GET /api/search-parts
    if (url === '/api/search-parts' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      const q = normalize(query.q || '');
      if (q.length < 2) {
        res.status(200).json({ results: [], lowest: null });
        return;
      }
      const [quotes, parts, suppliers, bids] = await Promise.all([
        getRows('Quotes'),
        getRows('Parts'),
        getRows('Suppliers'),
        getRows('Bids'),
      ]);
      const quotesByUuid = new Map(quotes.map(qt => [qt.uuid, qt]));
      const suppliersById = new Map(suppliers.map(s => [s.id, s]));
      const bidsByPartId = new Map();
      bids.forEach(b => {
        const price = Number(b.price);
        if (Number.isNaN(price)) return;
        if (!bidsByPartId.has(b.part_id)) bidsByPartId.set(b.part_id, []);
        bidsByPartId.get(b.part_id).push({ ...b, price });
      });
      const matchedParts = parts.filter(
        p => normalize(p.name).includes(q) || normalize(p.code).includes(q)
      );
      let lowest = null;
      const results = matchedParts
        .map(part => {
          const quote = quotesByUuid.get(part.quote_uuid);
          const partBids = (bidsByPartId.get(part.id) || [])
            .map(b => {
              const supplier = suppliersById.get(b.supplier_id);
              const entry = {
                price: b.price,
                notes: b.notes,
                company: supplier ? supplier.company : 'Proveedor desconocido',
                phone: supplier ? supplier.phone : '',
              };
              if (!lowest || entry.price < lowest.price) {
                lowest = {
                  price: entry.price,
                  company: entry.company,
                  phone: entry.phone,
                  partName: part.name,
                  quoteTitle: quote ? quote.title : '',
                  date: quote ? quote.created_at : '',
                };
              }
              return entry;
            })
            .sort((a, b) => a.price - b.price);
          return {
            partId: part.id,
            name: part.name,
            code: part.code,
            unit: part.unit,
            description: part.description,
            quoteUuid: part.quote_uuid,
            quoteTitle: quote ? quote.title : '(cotización eliminada)',
            quoteStatus: quote ? quote.status : null,
            quoteDate: quote ? quote.created_at : null,
            bids: partBids,
          };
        })
        .sort((a, b) => (a.quoteDate < b.quoteDate ? 1 : -1));
      res.status(200).json({ results, lowest });
      return;
    }

    // GET /api/supplier-stats
    if (url === '/api/supplier-stats' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      const [suppliers, bids, parts, winners] = await Promise.all([
        getRows('Suppliers'),
        getRows('Bids'),
        getRows('Parts'),
        getRows('Winners'),
      ]);
      const groups = new Map();
      suppliers.forEach(s => {
        const key = normalizePhone(s.phone);
        if (!key) return;
        if (!groups.has(key)) {
          groups.set(key, {
            phone: s.phone,
            company: s.company,
            lastSubmittedAt: s.submitted_at,
            supplierIds: new Set(),
            quotesInvited: 0,
          });
        }
        const g = groups.get(key);
        g.supplierIds.add(s.id);
        g.quotesInvited += 1;
        if (!g.lastSubmittedAt || s.submitted_at > g.lastSubmittedAt) {
          g.lastSubmittedAt = s.submitted_at;
          g.company = s.company;
        }
      });
      const supplierIdToKey = new Map();
      suppliers.forEach(s => supplierIdToKey.set(s.id, normalizePhone(s.phone)));
      const bidsByPart = new Map();
      bids.forEach(b => {
        const price = Number(b.price);
        if (Number.isNaN(price)) return;
        if (!bidsByPart.has(b.part_id)) bidsByPart.set(b.part_id, []);
        bidsByPart.get(b.part_id).push({ ...b, price });
        const key = supplierIdToKey.get(b.supplier_id);
        const g = key && groups.get(key);
        if (g) g.bidsGiven = (g.bidsGiven || 0) + 1;
      });
      bidsByPart.forEach(partBids => {
        const lowest = Math.min(...partBids.map(b => b.price));
        const winnersOfPart = partBids.filter(b => b.price === lowest);
        winnersOfPart.forEach(b => {
          const key = supplierIdToKey.get(b.supplier_id);
          const g = key && groups.get(key);
          if (g) g.timesLowestPrice = (g.timesLowestPrice || 0) + 1;
        });
      });
      winners.forEach(w => {
        const key = supplierIdToKey.get(w.supplier_id);
        const g = key && groups.get(key);
        if (g) g.timesChosenWinner = (g.timesChosenWinner || 0) + 1;
      });
      const stats = Array.from(groups.values())
        .map(g => ({
          company: g.company,
          phone: g.phone,
          quotesInvited: g.quotesInvited,
          bidsGiven: g.bidsGiven || 0,
          timesLowestPrice: g.timesLowestPrice || 0,
          timesChosenWinner: g.timesChosenWinner || 0,
          lastSubmittedAt: g.lastSubmittedAt,
        }))
        .sort((a, b) => b.timesChosenWinner - a.timesChosenWinner || b.timesLowestPrice - a.timesLowestPrice);
      res.status(200).json({ stats });
      return;
    }

    // GET /api/results
    if (url === '/api/results' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      const uuid = query.uuid;
      if (!uuid) {
        res.status(400).json({ error: 'Falta el parámetro uuid' });
        return;
      }
      const [quotes, allParts, allSuppliers, allBids, allWinners] = await Promise.all([
        getRows('Quotes'),
        getRows('Parts'),
        getRows('Suppliers'),
        getRows('Bids'),
        getRows('Winners'),
      ]);
      const quote = quotes.find(q => q.uuid === uuid);
      if (!quote) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }
      const parts = allParts
        .filter(p => p.quote_uuid === uuid)
        .map(p => ({
          id: p.id,
          name: p.name,
          code: p.code,
          unit: p.unit,
          description: p.description,
          quantity: Number(p.quantity) > 0 ? Number(p.quantity) : 1,
          image: p.image || '',
        }));
      const suppliers = allSuppliers
        .filter(s => s.quote_uuid === uuid)
        .map(s => ({ id: s.id, company: s.company, phone: s.phone, email: s.email }));
      const supplierIds = new Set(suppliers.map(s => s.id));
      const bids = allBids
        .filter(b => supplierIds.has(b.supplier_id))
        .map(b => ({ supplierId: b.supplier_id, partId: b.part_id, price: Number(b.price), notes: b.notes }))
        .filter(b => !Number.isNaN(b.price));
      const winners = allWinners
        .filter(w => w.quote_uuid === uuid)
        .map(w => ({ partId: w.part_id, supplierId: w.supplier_id }));
      res.status(200).json({
        title: quote.title,
        status: quote.status,
        parts,
        suppliers,
        bids,
        winners,
      });
      return;
    }

    // GET /api/quote-edit
    if (url === '/api/quote-edit' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      const uuid = query.uuid;
      if (!uuid) {
        res.status(400).json({ error: 'Falta el parámetro uuid' });
        return;
      }
      const [quotes, allParts, allBids] = await Promise.all([
        getRows('Quotes'),
        getRows('Parts'),
        getRows('Bids'),
      ]);
      const quote = quotes.find(q => q.uuid === uuid);
      if (!quote) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }
      const bidPartIds = new Set(allBids.map(b => b.part_id));
      const parts = allParts
        .filter(p => p.quote_uuid === uuid)
        .map(p => ({
          id: p.id,
          name: p.name,
          code: p.code,
          unit: p.unit,
          description: p.description,
          quantity: Number(p.quantity) > 0 ? Number(p.quantity) : 1,
          image: p.image || '',
          hasBids: bidPartIds.has(p.id),
        }));
      res.status(200).json({
        uuid: quote.uuid,
        title: quote.title,
        image: quote.image || '',
        status: quote.status,
        parts,
      });
      return;
    }

    // POST /api/quote-edit
    if (url === '/api/quote-edit' && method === 'POST') {
      if (!requireAuth(req, res)) return;
      const uuid = query.uuid || body.uuid;
      if (!uuid) {
        res.status(400).json({ error: 'Falta el parámetro uuid' });
        return;
      }
      const { title, parts, removedPartIds, image } = body;
      const cleanTitle = (title || '').trim();
      const cleanImage = typeof image === 'string' ? image.slice(0, 45000) : '';
      if (!cleanTitle) {
        res.status(400).json({ error: 'El título es obligatorio' });
        return;
      }
      const [quotes, allParts, allBids] = await Promise.all([
        getRows('Quotes'),
        getRows('Parts'),
        getRows('Bids'),
      ]);
      const quote = quotes.find(q => q.uuid === uuid);
      if (!quote) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }

      let needsUpdate = false;
      const updateData = {};
      if (quote.title !== cleanTitle) {
        updateData.title = cleanTitle;
        needsUpdate = true;
      }
      if ((quote.image || '') !== cleanImage) {
        updateData.image = cleanImage;
        needsUpdate = true;
      }
      if (needsUpdate) {
        const { _row, ...rest } = quote;
        await updateRow('Quotes', _row, { ...rest, ...updateData });
      }

      const existingParts = allParts.filter(p => p.quote_uuid === uuid);
      const existingById = new Map(existingParts.map(p => [p.id, p]));
      const bidPartIds = new Set(allBids.map(b => b.part_id));
      const incoming = Array.isArray(parts) ? parts : [];
      const newRows = [];
      for (const p of incoming) {
        const name = (p.name || '').trim();
        if (!name) continue;
        const qty = Number(p.quantity);
        const cleanQty = Number.isFinite(qty) && qty > 0 ? String(qty) : '1';
        const existingForImage = p.id ? existingById.get(p.id) : null;
        const cleanImagePart = typeof p.image === 'string'
          ? p.image.slice(0, 45000)
          : (existingForImage ? existingForImage.image || '' : '');
        const cleanFields = {
          name,
          code: (p.code || '').trim(),
          unit: (p.unit || '').trim(),
          description: (p.description || '').trim(),
          quantity: cleanQty,
          image: cleanImagePart,
        };
        if (p.id && existingById.has(p.id)) {
          const existing = existingById.get(p.id);
          await updateRow('Parts', existing._row, {
            id: existing.id,
            quote_uuid: uuid,
            ...cleanFields,
          });
        } else {
          newRows.push({ id: crypto.randomUUID(), quote_uuid: uuid, ...cleanFields });
        }
      }
      if (newRows.length > 0) {
        await appendRows('Parts', newRows);
      }
      const blocked = [];
      const toRemove = (Array.isArray(removedPartIds) ? removedPartIds : [])
        .map(partId => existingById.get(partId))
        .filter(Boolean)
        .sort((a, b) => b._row - a._row);
      for (const existing of toRemove) {
        if (bidPartIds.has(existing.id)) {
          blocked.push(existing.name);
          continue;
        }
        await deleteRow('Parts', existing._row);
      }
      res.status(200).json({
        ok: true,
        blocked: blocked.length > 0 ? blocked : undefined,
      });
      return;
    }

    // POST /api/quote-status
    if (url === '/api/quote-status' && method === 'POST') {
      if (!requireAuth(req, res)) return;
      const { uuid, status } = body;
      if (!uuid || !['ACTIVE', 'CLOSED'].includes(status)) {
        res.status(400).json({ error: 'Parámetros inválidos' });
        return;
      }
      const quotes = await getRows('Quotes');
      const target = quotes.find(q => q.uuid === uuid);
      if (!target) {
        res.status(404).json({ error: 'Cotización no encontrada' });
        return;
      }
      const { _row, ...rest } = target;
      await updateRow('Quotes', _row, { ...rest, status });
      res.status(200).json({ ok: true });
      return;
    }

    // POST /api/set-winner
    if (url === '/api/set-winner' && method === 'POST') {
      if (!requireAuth(req, res)) return;
      const { quoteUuid, partId, supplierId } = body;
      if (!quoteUuid || !partId) {
        res.status(400).json({ error: 'Parámetros inválidos' });
        return;
      }
      const winners = await getRows('Winners');
      const existing = winners.find(w => w.quote_uuid === quoteUuid && w.part_id === partId);
      if (!supplierId) {
        if (existing) await deleteRow('Winners', existing._row);
        res.status(200).json({ ok: true });
        return;
      }
      if (existing) {
        await updateRow('Winners', existing._row, {
          quote_uuid: quoteUuid,
          part_id: partId,
          supplier_id: supplierId,
          chosen_at: new Date().toISOString(),
        });
      } else {
        await appendRow('Winners', {
          quote_uuid: quoteUuid,
          part_id: partId,
          supplier_id: supplierId,
          chosen_at: new Date().toISOString(),
        });
      }
      res.status(200).json({ ok: true });
      return;
    }

    // Si no coincide ninguna ruta
    console.log('❌ Ruta no encontrada:', url);
    res.status(404).json({ error: 'Not found' });

  } catch (err) {
    console.error('💥 Error en API:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
};