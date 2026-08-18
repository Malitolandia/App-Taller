const crypto = require('crypto');

const COOKIE_NAME = 'admin_session';

function expectedToken() {
  const password = process.env.ADMIN_PASSWORD || '';
  return crypto.createHash('sha256').update(password).digest('hex');
}

function parseCookies(req) {
  const header = req.headers.cookie || '';
  const cookies = {};
  header.split(';').forEach((part) => {
    const idx = part.indexOf('=');
    if (idx === -1) return;
    const key = part.slice(0, idx).trim();
    const val = part.slice(idx + 1).trim();
    if (key) cookies[key] = decodeURIComponent(val);
  });
  return cookies;
}

function isAuthenticated(req) {
  const cookies = parseCookies(req);
  const token = cookies[COOKIE_NAME];
  return Boolean(token) && token === expectedToken();
}

function setSessionCookie(res) {
  const token = expectedToken();
  const parts = [
    `${COOKIE_NAME}=${encodeURIComponent(token)}`,
    'Path=/',
    'HttpOnly',
    'SameSite=Lax',
    `Max-Age=${60 * 60 * 8}`,
  ];
  res.setHeader('Set-Cookie', parts.join('; '));
}

function clearSessionCookie(res) {
  res.setHeader(
    'Set-Cookie',
    `${COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`
  );
}

function requireAuth(req, res) {
  if (!isAuthenticated(req)) {
    res.status(401).json({ error: 'No autenticado' });
    return false;
  }
  return true;
}

module.exports = {
  isAuthenticated,
  setSessionCookie,
  clearSessionCookie,
  requireAuth,
};