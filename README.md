# APPTALLER — Vercel + Google Sheets

APPTALLER integra **Control de Taller**, **Neveras** y **Peritaje** en una sola aplicación Flask desplegable en Vercel. La versión de este directorio está diseñada para producción remota: **Google Sheets es la única base de datos operativa** y el sistema de archivos de Vercel no se utiliza para persistir registros.

> Los archivos XLSX solo se generan temporalmente en memoria para descargar o restaurar respaldos. No se usan como base de datos, no se crean carpetas `data/` y no se incluyen plantillas Excel operativas en el despliegue.

## Funcionalidades

| Función | Implementación |
| --- | --- |
| Aplicación integrada | Menú raíz y módulos montados en `/control`, `/neveras` y `/peritaje`. |
| Persistencia | Google Sheets API v4, una sola hoja de cálculo con pestañas compartidas. |
| Lecturas normales | Cada petición descarga una instantánea remota en memoria mediante `values.batchGet`. |
| Escrituras normales | `RemoteWorkbook.save()` sincroniza solamente las pestañas modificadas y confirma la respuesta de Google Sheets. |
| Backup | `/api/db/export` produce un XLSX global en memoria con todas las pestañas. |
| Restauración | `/api/db/import` carga un XLSX y reemplaza las pestañas recibidas en Google Sheets. |
| Diagnóstico | `/api/health` verifica credenciales, acceso y presencia de las doce pestañas requeridas. |

## Pestañas de Google Sheets

La aplicación utiliza una sola hoja de cálculo. En la primera operación remota crea las pestañas que falten, conserva los datos existentes y prepara una cuadrícula mínima de 100 columnas para soportar campos extendidos de Peritaje.

| Módulo | Pestañas |
| --- | --- |
| Control de Taller | `Mecanicos`, `Equipos`, `Trabajos`, `Gastos`, `Pagos`, `Herramientas` |
| Neveras | `Ventas`, `Inventario`, `Clientes`, `Deudas`, `Dashboard` |
| Peritaje | `Peritajes` |

Una pestaña adicional como `Hoja 1` puede permanecer en el archivo de Google Sheets sin afectar la aplicación. No se utiliza para las operaciones de los módulos.

## Variables de entorno de Vercel

Configura exactamente estas dos variables en **Production** y, si vas a probar Preview Deployments, también en **Preview**.

| Variable | Valor |
| --- | --- |
| `GOOGLE_SHEETS_ID` | El identificador entre `/d/` y `/edit` en la URL de Google Sheets. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | El contenido completo del JSON de la cuenta de servicio, pegado como valor de la variable. |

La hoja debe compartirse con el `client_email` de la cuenta de servicio con permisos de **Editor**. No subas el JSON a GitHub y no lo escribas en ningún archivo del proyecto.

## Verificación posterior al deploy

Después de publicar el proyecto, abre:

```text
https://TU-DOMINIO.vercel.app/api/health
```

La respuesta correcta debe incluir `"ok": true`, `"backend": "google_sheets"`, `"remote_connected": true`, `"required_sheets_present": true` y las doce pestañas en `sheet_titles`. Si devuelve `503`, el campo `error` indica si el problema es una variable ausente, JSON inválido, permisos de la cuenta de servicio o un identificador de hoja incorrecto.

La comprobación funcional debe hacerse en este orden: cargar `/control`, registrar un mecánico y recargar; cargar `/neveras`, crear una venta y marcarla como pagada; cargar `/peritaje`, registrar un peritaje y recargar. Cada resultado debe aparecer en la interfaz y en la pestaña correspondiente de Google Sheets.

## Respaldo y restauración

El respaldo global se descarga desde la pantalla principal o mediante:

```text
GET /api/db/export
```

La restauración se realiza mediante `POST /api/db/import` usando un campo multipart llamado `file`. Descarga siempre un respaldo actual antes de restaurar otro archivo. La restauración es una operación destructiva sobre las pestañas que vienen en el XLSX, por lo que debe ejecutarse únicamente con un archivo confiable.

## Estructura de despliegue

El punto de entrada es `api/index.py`, que importa la aplicación unificada de `app.py`. `vercel.json` envía todas las rutas al adaptador WSGI. Las dependencias de producción están centralizadas en el `requirements.txt` raíz; no hay `package.json`, scripts Windows, servidores independientes, carpetas `data/` ni plantillas Excel operativas.

La corrección principal elimina la creación y lectura de XLSX local desde los módulos. También elimina la migración de encabezados en cada petición de Control de Taller, que podía reescribir la hoja completa innecesariamente. El adaptador remoto ahora prepara las pestañas de forma explícita, lee por lotes, evita rangos abiertos a `ZZ`, amplía la cuadrícula para Peritaje y confirma cada actualización.

## Publicación manual en GitHub

Desde una copia local del contenido de este directorio, sube el contenido al repositorio `Malitolandia/App-Taller`. El directorio raíz del repositorio debe contener `app.py`, `storage.py`, `requirements.txt`, `vercel.json`, `api/index.py` y las carpetas de los tres módulos. No subas credenciales, archivos `.env`, respaldos con datos reales ni cachés.

En Vercel importa el repositorio, selecciona el directorio raíz, conserva las variables de entorno y realiza un nuevo deploy. El despliegue anterior no se puede considerar validado si apunta a una copia diferente del repositorio o si las variables fueron creadas únicamente en otro entorno.

## Pruebas reproducibles

La prueba `test_clean_remote.py`, ubicada fuera del paquete de despliegue, usa un simulador explícito de Google Sheets y comprueba salud, lectura y alta de mecánicos, lectura y escritura de Neveras, marcado de pago, lectura y alta de Peritaje, exportación XLSX e importación global. El resultado esperado termina con:

```text
PASS clean remote CRUD + backup cycle
```

La prueba no sustituye la verificación en Vercel: el último paso siempre es consultar `/api/health` en el dominio desplegado y realizar una escritura de prueba con la hoja real.

## Seguridad

Mantén el JSON de la cuenta de servicio únicamente en las variables de entorno de Vercel. Comparte la hoja solo con la cuenta de servicio que usa la aplicación y conserva los XLSX descargados en una ubicación controlada, porque contienen la información de los tres módulos.

## Referencias

[1] [Google Sheets API: Python quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)

[2] [Vercel: Environment Variables](https://vercel.com/docs/environment-variables)

[3] [Vercel: Deploy a Flask app](https://vercel.com/docs/frameworks/backend/flask)
