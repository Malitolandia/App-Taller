const { google } = require('googleapis');

// Contrato canónico de datos. La columna quantity se mantiene al final de
// Parts para conservar compatibilidad con libros creados antes de ese campo.
const SHEETS = {
  Quotes: ['uuid', 'title', 'image', 'status', 'created_at'],
  Parts: ['id', 'quote_uuid', 'name', 'code', 'unit', 'description', 'image', 'quantity'],
  Suppliers: ['id', 'quote_uuid', 'company', 'phone', 'email', 'submitted_at'],
  Bids: ['id', 'supplier_id', 'part_id', 'price', 'notes'],
  Winners: ['quote_uuid', 'part_id', 'supplier_id', 'chosen_at'],
};

// Permite leer libros de Excel/Sheets cuyos encabezados tengan espacios,
// mayúsculas, acentos o nombres equivalentes en español.
const HEADER_ALIASES = {
  uuid: ['quoteid', 'cotizacionid', 'idcotizacion'],
  title: ['titulo', 'nombrecotizacion'],
  image: ['imagen', 'foto', 'fotourl', 'urlimagen'],
  status: ['estado'],
  created_at: ['createdat', 'fechacreacion', 'fechacotizacion'],
  id: ['codigoid'],
  quote_uuid: ['quote', 'quoteid', 'cotizacion', 'cotizacionid', 'idcotizacion'],
  name: ['nombre', 'nombrerepuesto', 'repuesto'],
  code: ['codigo', 'codigorepuesto'],
  unit: ['unidad'],
  description: ['descripcion', 'detalles'],
  quantity: ['cantidad', 'cant', 'cantidadsolicitada'],
  supplier_id: ['idproveedor', 'proveedorid'],
  company: ['empresa', 'proveedor', 'nombreempresa'],
  phone: ['telefono', 'celular', 'whatsapp'],
  email: ['correo', 'emailproveedor'],
  submitted_at: ['submittedat', 'fecharegistro', 'fechasolicitud'],
  price: ['precio', 'valor'],
  notes: ['nota', 'observaciones', 'comentarios'],
  part_id: ['idrepuesto', 'repuestoid'],
  chosen_at: ['chosenat', 'fechaseleccion', 'fechaganador'],
};

function normalizeHeader(value) {
  return String(value ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '');
}

function canonicalForHeader(sheetName, header) {
  const key = normalizeHeader(header);
  if (!key) return null;
  const columns = SHEETS[sheetName] || [];
  return columns.find((column) => {
    if (normalizeHeader(column) === key) return true;
    return (HEADER_ALIASES[column] || []).some((alias) => normalizeHeader(alias) === key);
  }) || null;
}

function getSpreadsheetId() {
  const id = String(process.env.SPREADSHEET_ID || '').trim();
  if (!id) throw new Error('Falta la variable de entorno SPREADSHEET_ID');
  return id;
}

let cachedClient = null;

function getClient() {
  if (cachedClient) return cachedClient;

  const clientEmail = process.env.GOOGLE_SHEETS_CLIENT_EMAIL;
  const rawKey = process.env.GOOGLE_SHEETS_PRIVATE_KEY;
  if (!clientEmail || !rawKey) {
    throw new Error(
      'Faltan GOOGLE_SHEETS_CLIENT_EMAIL o GOOGLE_SHEETS_PRIVATE_KEY'
    );
  }
  const privateKey = rawKey.replace(/\\n/g, '\n');

  const auth = new google.auth.GoogleAuth({
    credentials: { client_email: clientEmail, private_key: privateKey },
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });

  cachedClient = google.sheets({ version: 'v4', auth });
  return cachedClient;
}

function colLetter(index) {
  let n = index + 1;
  let result = '';
  while (n > 0) {
    const remainder = (n - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

async function getHeaderInfo(sheetName) {
  const columns = SHEETS[sheetName];
  if (!columns) throw new Error(`Hoja no definida: ${sheetName}`);
  const client = getClient();
  const res = await client.spreadsheets.values.get({
    spreadsheetId: getSpreadsheetId(),
    range: `${sheetName}!A1:ZZ1`,
  });
  const actualHeaders = (res.data.values && res.data.values[0] || [])
    .map((value) => String(value ?? '').trim());
  const headers = actualHeaders.some(Boolean) ? actualHeaders : [...columns];
  const canonicalIndexes = {};
  headers.forEach((header, index) => {
    const canonical = canonicalForHeader(sheetName, header);
    if (canonical && canonicalIndexes[canonical] === undefined) {
      canonicalIndexes[canonical] = index;
    }
  });

  // Si la hoja está vacía o tiene encabezados irreconocibles, conserva el
  // orden canónico como fallback para no descartar filas existentes.
  columns.forEach((column, index) => {
    if (canonicalIndexes[column] === undefined && !actualHeaders.some(Boolean)) {
      canonicalIndexes[column] = index;
    }
  });
  return { headers, canonicalIndexes };
}

function rowValues(sheetName, headers, data) {
  return headers.map((header) => {
    const canonical = canonicalForHeader(sheetName, header);
    if (canonical) return data[canonical] ?? '';
    return data[header] ?? '';
  });
}

/** Lee todas las filas alineando cada valor con el nombre real del encabezado. */
async function getRows(sheetName) {
  const client = getClient();
  const { headers, canonicalIndexes } = await getHeaderInfo(sheetName);
  const lastCol = colLetter(Math.max(headers.length, 1) - 1);

  const res = await client.spreadsheets.values.get({
    spreadsheetId: getSpreadsheetId(),
    range: `${sheetName}!A2:${lastCol}`,
  });

  const rows = res.data.values || [];
  const columns = SHEETS[sheetName];
  return rows
    .map((row, idx) => {
      const obj = { _row: idx + 2 };
      columns.forEach((column) => {
        const colIdx = canonicalIndexes[column];
        obj[column] = colIdx === undefined ? '' : (row[colIdx] ?? '');
      });
      return obj;
    })
    .filter((row) =>
      Object.entries(row).some(([key, value]) => key !== '_row' && value !== '' && value !== undefined)
    );
}

async function appendRow(sheetName, data) {
  return appendRows(sheetName, [data]);
}

async function appendRows(sheetName, dataRows) {
  if (!dataRows.length) return;
  const client = getClient();
  const { headers } = await getHeaderInfo(sheetName);
  const values = dataRows.map((data) => rowValues(sheetName, headers, data));

  await client.spreadsheets.values.append({
    spreadsheetId: getSpreadsheetId(),
    range: `${sheetName}!A:${colLetter(headers.length - 1)}`,
    valueInputOption: 'USER_ENTERED',
    insertDataOption: 'INSERT_ROWS',
    requestBody: { values },
  });
}

async function updateRow(sheetName, rowNumber, data) {
  const client = getClient();
  const { headers } = await getHeaderInfo(sheetName);
  const values = rowValues(sheetName, headers, data);

  await client.spreadsheets.values.update({
    spreadsheetId: getSpreadsheetId(),
    range: `${sheetName}!A${rowNumber}:${colLetter(headers.length - 1)}${rowNumber}`,
    valueInputOption: 'USER_ENTERED',
    requestBody: { values: [values] },
  });
}

async function getSheetIdByName(sheetName) {
  const client = getClient();
  const meta = await client.spreadsheets.get({ spreadsheetId: getSpreadsheetId() });
  const sheet = (meta.data.sheets || []).find((item) => item.properties.title === sheetName);
  return sheet ? sheet.properties.sheetId : null;
}

async function deleteRow(sheetName, rowNumber) {
  const client = getClient();
  const sheetId = await getSheetIdByName(sheetName);
  if (sheetId === null) throw new Error(`No se encontró la hoja ${sheetName}`);

  await client.spreadsheets.batchUpdate({
    spreadsheetId: getSpreadsheetId(),
    requestBody: {
      requests: [{
        deleteDimension: {
          range: { sheetId, dimension: 'ROWS', startIndex: rowNumber - 1, endIndex: rowNumber },
        },
      }],
    },
  });
}

let readyChecked = false;

/** Crea pestañas nuevas y agrega columnas faltantes sin reordenar las existentes. */
async function ensureReady() {
  if (readyChecked) return;
  const client = getClient();
  const spreadsheetId = getSpreadsheetId();

  const meta = await client.spreadsheets.get({ spreadsheetId });
  const existingTitles = new Set((meta.data.sheets || []).map((sheet) => sheet.properties.title));
  const missingSheets = Object.keys(SHEETS).filter((name) => !existingTitles.has(name));

  if (missingSheets.length > 0) {
    await client.spreadsheets.batchUpdate({
      spreadsheetId,
      requestBody: { requests: missingSheets.map((title) => ({ addSheet: { properties: { title } } })) },
    });
  }

  for (const name of Object.keys(SHEETS)) {
    const { headers: actualHeaders } = await getHeaderInfo(name);
    const hasHeader = actualHeaders.some(Boolean);
    const currentHeaders = hasHeader ? actualHeaders : [];
    const present = new Set(currentHeaders.map((header) => canonicalForHeader(name, header)).filter(Boolean));
    const missingColumns = SHEETS[name].filter((column) => !present.has(column));
    const nextHeaders = [...currentHeaders, ...missingColumns];
    const expectedHeaders = hasHeader ? nextHeaders : SHEETS[name];
    const lastCol = colLetter(expectedHeaders.length - 1);

    if (!hasHeader || missingColumns.length > 0) {
      await client.spreadsheets.values.update({
        spreadsheetId,
        range: `${name}!A1:${lastCol}1`,
        valueInputOption: 'USER_ENTERED',
        requestBody: { values: [expectedHeaders] },
      });
    }
  }

  readyChecked = true;
}

module.exports = {
  SHEETS,
  getRows,
  appendRow,
  appendRows,
  updateRow,
  deleteRow,
  ensureReady,
};
