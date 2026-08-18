# Cotizador de Repuestos — HTML/CSS/JS + Vercel Functions + Google Sheets

Frontend 100% estático (HTML, CSS y JavaScript puro, sin frameworks ni build
step) + backend con **Vercel Serverless Functions** (Node.js) en `/api`, que
hablan con Google Sheets vía una Service Account. No hay base de datos.

## Estructura

```
public/                    Todo lo que ve el navegador (estático)
  index.html                Landing
  admin-login.html           Login del admin
  admin.html                 Panel: crear cotización + listado
  editar.html                Editar título/repuestos de una cotización
  cotizar.html               Página pública del proveedor (?uuid=...)
  results.html               Comparativo, ganador por repuesto, exportar, WhatsApp (?uuid=...)
  buscar.html                Buscador histórico de repuestos
  proveedores.html           Historial de desempeño por proveedor
  css/styles.css
  js/login.js, admin.js, editar.js, cotizar.js, results.js, buscar.js, proveedores.js

api/                        Backend (cada archivo = 1 función serverless)
  _lib/sheets.js              Auth + CRUD genérico sobre Google Sheets
  _lib/auth.js                Cookie de sesión admin (sha256 de ADMIN_PASSWORD)
  _lib/notify.js               Notificación por correo opcional (Resend)
  login.js / logout.js / session.js
  quotes.js                   GET listar (admin) / POST crear (admin)
  quote.js                    GET cotización + repuestos (público, ?uuid=)
  quote-edit.js                GET/POST editar título y repuestos (admin, ?uuid=)
  quote-status.js             POST cerrar/reabrir (admin)
  suppliers.js                POST registrar proveedor (público, valida teléfono duplicado)
  bids.js                     POST enviar precios (público) + dispara notificación opcional
  results.js                  GET comparativo completo, cantidades y ganadores (admin, ?uuid=)
  set-winner.js                POST marcar/quitar ganador de un repuesto (admin)
  part-catalog.js               GET nombres históricos de repuestos, para autocompletar (admin)
  search-parts.js               GET buscador histórico de repuestos (admin)
  supplier-stats.js             GET historial de desempeño por proveedor (admin)
```

## Funcionalidades

- Crear cotizaciones con **cantidad por repuesto** (el comparativo calcula precio × cantidad).
- **Editar** una cotización ya creada (título y repuestos) desde `/editar.html?uuid=...`.
  Un repuesto que ya recibió precios de algún proveedor no se puede borrar (para no dejar
  precios huérfanos), pero sí se puede seguir editando su nombre/código/cantidad.
- **Elegir ganador** por repuesto directamente en la tabla de resultados — arma
  automáticamente una "Lista de compra" agrupada por proveedor con el total a pagar a cada uno.
- **Catálogo con autocompletado**: al crear o editar una cotización, el campo de nombre del
  repuesto sugiere nombres ya usados antes (para evitar duplicados como "pastillas freno" /
  "pastillas de freno").
- **Historial de proveedores** (`/proveedores.html`): veces invitado, precios enviados, veces
  que tuvo el precio más bajo, veces elegido como ganador.
- **Botón de WhatsApp** en cada tarjeta de contacto de proveedor (abre wa.me con mensaje
  pre-armado).
- **Exportar a Excel / PDF** desde la página de resultados (se genera en el navegador, no
  necesita backend adicional).
- **Notificación por correo** (opcional) cuando un proveedor envía precios — ver más abajo.
- Buscador de repuestos histórico (`/buscar.html`) con precio más bajo histórico.

## Cambios en el Google Sheet

Estos cambios se aplican solos la primera vez que la app corre después de actualizar el
código — no necesitas tocar el Sheet a mano:

- La pestaña `Parts` ahora tiene una columna extra `quantity` al final.
- Se crea una pestaña nueva `Winners` (quote_uuid, part_id, supplier_id, chosen_at) para
  guardar qué proveedor elegiste como ganador de cada repuesto.
- Si ya tenías repuestos creados antes de este cambio, su cantidad queda vacía; la app la
  trata como `1` automáticamente hasta que la edites.

## Notificación por correo (opcional)

Si quieres que te llegue un correo cada vez que un proveedor envía precios, agrega estas
variables de entorno (si no las agregas, la app sigue funcionando igual, solo sin avisos):

```
RESEND_API_KEY=tu-api-key-de-resend.com
ADMIN_EMAIL=tu-correo@ejemplo.com
RESEND_FROM_EMAIL=onboarding@resend.dev   # opcional, o tu dominio verificado en Resend
SITE_URL=https://tu-proyecto.vercel.app   # opcional, para incluir el link directo al resultado
```

[resend.com](https://resend.com) tiene un plan gratis y no requiere tarjeta para empezar;
con la dirección `onboarding@resend.dev` puedes enviarte correos a ti mismo sin verificar
un dominio propio (para producción real con tu propio dominio, sí tendrías que verificarlo
en Resend).

## 1. Preparar Google Sheets (igual que siempre)

1. Google Cloud Console → crea/usa un proyecto → habilita **Google Sheets API**.
2. **Credenciales → Crear credenciales → Cuenta de servicio** → créala →
   pestaña **Claves → Agregar clave → JSON** → descarga el archivo.
3. Del JSON copia `client_email` y `private_key`.
4. Crea un Google Sheet (puede quedar vacío; las 5 pestañas y encabezados se
   crean solas la primera vez que la app llama a la API). La lectura se hace por nombre de
   encabezado, no por posición fija; por eso conserva datos aunque Excel haya cambiado el orden
   de las columnas. También reconoce encabezados equivalentes en español como `Cotización`,
   `Nombre`, `Cantidad`, `Teléfono` y `Precio`.
5. **Compartir** el Sheet con el `client_email` de la Service Account, rol
   **Editor**.
6. Copia el ID del Sheet desde la URL:
   `https://docs.google.com/spreadsheets/d/EL_ID_VA_AQUI/edit`

## 2. Completa las variables de entorno. Este proyecto usa nombres distintos a la versión anterior:

```bash
cp .env.example .env.local
```

Completa `GOOGLE_SHEETS_CLIENT_EMAIL`, `GOOGLE_SHEETS_PRIVATE_KEY`,
`SPREADSHEET_ID` y `ADMIN_PASSWORD`. En Vercel, crea esas mismas variables para **Production**
y vuelve a desplegar. No uses `GOOGLE_SHEETS_ID` ni `GOOGLE_SERVICE_ACCOUNT_JSON` de la aplicación
anterior: este proyecto no las lee.

## 3. Probar en local con Vercel CLI

Como el backend son funciones serverless de Vercel (no un servidor Express),
la forma correcta de probarlo en local —con el mismo comportamiento que en
producción— es con `vercel dev`:

```bash
npm install -g vercel      # si no lo tienes instalado
npm install                 # instala googleapis
vercel dev                  # levanta todo en http://localhost:3000
```

La primera vez te pedirá loguearte con tu cuenta de Vercel y "linkear" la
carpeta a un proyecto (puedes crear uno nuevo, ej. `cotizador-repuestos`).
`vercel dev` lee automáticamente las variables de `.env.local`.

Abre `http://localhost:3000/admin.html`, entra con `ADMIN_PASSWORD`, crea una
cotización y copia el enlace `/cotizar.html?uuid=...` para probarlo como
proveedor (puedes abrirlo en una ventana de incógnito).

> Si prefieres no instalar Vercel CLI globalmente: `npx vercel dev`.

## 4. Desplegar a Vercel

```bash
vercel          # despliegue de prueba (preview)
vercel --prod    # despliegue a producción
```

O conecta el repo de GitHub desde el dashboard de Vercel (Import Project).
En cualquiera de los dos casos, agrega las variables de entorno en
**Project Settings → Environment Variables**: `GOOGLE_SHEETS_CLIENT_EMAIL`,
`GOOGLE_SHEETS_PRIVATE_KEY`, `SPREADSHEET_ID` y `ADMIN_PASSWORD` (pega
`GOOGLE_SHEETS_PRIVATE_KEY` con los `\\n` literales; el adaptador los convierte a saltos de línea).

No hace falta configurar nada más: Vercel detecta automáticamente que
`public/` es el contenido estático y que cada archivo en `api/` es un
endpoint (`api/quotes.js` → `/api/quotes`, etc.).

## Notas de diseño

- **Sesión admin**: cookie `HttpOnly` con `sha256(ADMIN_PASSWORD)`. Cada
  función protegida (`quotes.js` GET/POST, `quote-status.js`, `results.js`)
  llama a `requireAuth()`; las páginas `admin.html` y `results.html`
  consultan `/api/session` al cargar y redirigen a `admin-login.html` si no
  hay sesión.
- **Anti-duplicados**: `suppliers.js` normaliza el teléfono (solo dígitos) y
  busca coincidencias dentro de la misma `quote_uuid` antes de guardar.
- **IDs**: `crypto.randomUUID()` generado siempre en el servidor (dentro de
  cada función de `/api`), nunca en el navegador.
- **Diagnóstico**: `GET /api/health` verifica acceso real a Google Sheets y devuelve el conteo de
  filas por pestaña. Si falla, devuelve el error desde la función serverless en lugar de declarar
  éxito solo porque existen variables.
- **Sin build step**: no hay bundler, ni TypeScript, ni React — todo es
  JS plano servido tal cual, más fácil de depurar y de modificar a mano.
