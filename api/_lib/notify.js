/**
 * Notificación opcional por correo cuando un proveedor envía precios.
 * Solo se activa si defines RESEND_API_KEY y ADMIN_EMAIL en las variables
 * de entorno. Si faltan, la función no hace nada (no rompe el flujo).
 *
 * Usa la API HTTP de Resend (https://resend.com) porque no requiere
 * ninguna librería adicional, solo fetch.
 */
async function notifyNewBid({ quoteTitle, quoteUuid, company, phone }) {
  const apiKey = process.env.RESEND_API_KEY;
  const toEmail = process.env.ADMIN_EMAIL;
  if (!apiKey || !toEmail) return; // notificaciones desactivadas

  const fromEmail = process.env.RESEND_FROM_EMAIL || 'onboarding@resend.dev';
  const siteUrl = process.env.SITE_URL || '';
  const resultsLink = siteUrl ? `${siteUrl}/results.html?uuid=${quoteUuid}` : '';

  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: fromEmail,
        to: toEmail,
        subject: `Nueva cotización recibida: ${quoteTitle}`,
        html: `
          <p>El proveedor <strong>${escapeHtml(company)}</strong> (${escapeHtml(phone)})
          acaba de enviar precios para la cotización "<strong>${escapeHtml(quoteTitle)}</strong>".</p>
          ${resultsLink ? `<p><a href="${resultsLink}">Ver resultados</a></p>` : ''}
        `,
      }),
    });
  } catch (err) {
    // No queremos que un fallo de correo tumbe el flujo principal.
    console.error('No se pudo enviar la notificación por correo:', err);
  }
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));
}

module.exports = { notifyNewBid };
