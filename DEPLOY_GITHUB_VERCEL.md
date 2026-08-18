# Despliegue limpio de APPTALLER en GitHub y Vercel

Esta versión utiliza **solo Google Sheets como almacenamiento operativo**. No necesita archivos Excel locales, carpetas `data/`, servidores independientes ni variables de credenciales en archivo.

## 1. Subir el contenido correcto a GitHub

El repositorio debe tener esta estructura en su raíz:

```text
app.py
storage.py
requirements.txt
vercel.json
api/index.py
ControlTaller/
Neveras/
Peritaje/
menu.html
```

Sube el contenido de `APPTALLER_GOOGLE_SHEETS_CLEAN`, no una carpeta contenedora adicional. Antes de confirmar el commit, verifica que no aparezcan `.env`, archivos JSON de cuentas de servicio, `*.xlsx`, `data/`, `__pycache__` ni ZIP con información operativa.

Si utilizas la interfaz web de GitHub, entra en `https://github.com/Malitolandia/App-Taller`, selecciona **Add file → Upload files**, arrastra el contenido del directorio limpio y confirma el commit en `main`.

## 2. Configurar las variables en Vercel

En **Project Settings → Environment Variables**, crea estas dos variables y actívalas para **Production** y **Preview**:

| Nombre | Valor |
| --- | --- |
| `GOOGLE_SHEETS_ID` | ID de la hoja tomado de `https://docs.google.com/spreadsheets/d/ID/edit`. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON completo de la cuenta de servicio, pegado como un único valor. |

El correo `client_email` del JSON debe tener acceso de **Editor** a la hoja de cálculo. No uses el ID de una pestaña (`gid`) como `GOOGLE_SHEETS_ID`, no subas el JSON a GitHub y no lo escribas en un archivo del proyecto.

## 3. Redeploy limpio

Después de actualizar GitHub, ejecuta un nuevo deploy en Vercel. En los detalles del deployment confirma que el commit desplegado contiene el `storage.py` y el `api/index.py` de esta versión.

No es suficiente con guardar variables: Vercel debe reconstruir el deployment para que las modificaciones de código y variables queden activas.

## 4. Verificar salud

Abre:

```text
https://TU-DOMINIO.vercel.app/api/health
```

La respuesta esperada contiene:

```json
{
  "ok": true,
  "backend": "google_sheets",
  "remote_connected": true,
  "required_sheets_present": true
}
```

La primera consulta prepara de forma idempotente las pestañas que falten. Deben existir estas doce pestañas:

```text
Mecanicos, Equipos, Trabajos, Gastos, Pagos, Herramientas,
Ventas, Inventario, Clientes, Deudas, Dashboard, Peritajes
```

Una pestaña adicional como `Hoja 1` puede permanecer en el archivo sin afectar a los módulos.

## 5. Pruebas funcionales

Realiza una prueba aislada en cada módulo y revisa tanto la interfaz como Google Sheets:

| Orden | Prueba | Confirmación esperada |
| --- | --- | --- |
| 1 | `GET /control/api/mecanicos` | Devuelve JSON y no genera 500. |
| 2 | Alta de mecánico | Aparece en la interfaz y en `Mecanicos`. |
| 3 | `GET /neveras/api/datos` | Devuelve `inventario`, `ventas` y `clientes`. |
| 4 | Registrar venta y marcar pago | Cambian `Ventas`, `Inventario` y `Clientes`. |
| 5 | `GET /peritaje/api/peritajes` | Devuelve los registros de `Peritajes`. |
| 6 | Registrar peritaje | Aparece una nueva fila en `Peritajes`. |
| 7 | Descargar respaldo | Descarga `APPTALLER_respaldo.xlsx`. |

Si una operación falla, la respuesta JSON muestra el tipo y texto de la excepción. Ese texto permite diferenciar una denegación de Google, un ID incorrecto, un rango inválido o un error del código.

## 6. Interpretación de errores

| Síntoma | Causa más probable | Acción |
| --- | --- | --- |
| `/api/health` devuelve 503 y falta `GOOGLE_SHEETS_ID` | Variable ausente o creada en otro entorno | Crear la variable en Production/Preview y hacer redeploy. |
| Error de JSON inválido | Se pegó un JSON incompleto o con comillas alteradas | Copiar el JSON completo en una sola variable. |
| `Requested entity was not found` | ID incorrecto o cuenta sin acceso | Revisar el ID y compartir la hoja con `client_email`. |
| `The caller does not have permission` | La cuenta no tiene rol Editor | Compartir la hoja con permisos Editor. |
| `/api/health` funciona pero el frontend usa datos antiguos | Se está abriendo otro deployment o dominio | Comprobar el commit desplegado y abrir el dominio vigente. |
| Un POST devuelve 500 con `updatedRange` ausente | Google rechazó la actualización | Revisar el JSON devuelto y los logs del deployment. |

## 7. Backup y restauración

Descarga primero el backup actual en `/api/db/export`. Para restaurar, usa la opción de carga del menú y selecciona un `.xlsx` confiable. La importación reemplaza el contenido de las pestañas presentes en el archivo; no la ejecutes sin conservar una copia de retorno.

## 8. Checklist final

Antes de considerar terminado el despliegue, confirma que el dominio abre el menú, `/api/health` devuelve `ok: true`, las doce pestañas existen, una escritura de cada módulo aparece en Google Sheets después de recargar, el respaldo se descarga y el repositorio no contiene secretos ni bases locales.


## 9. Nota importante sobre el límite 429

Google Sheets aplica una cuota de lecturas por ventana temporal. La versión actual excluye `Hoja 1`, agrupa las lecturas, evita el polling de Neveras y reutiliza una instantánea confirmada. Aun así, después de un 429 existente conviene esperar unos segundos antes de repetir la prueba.

Tras el redeploy, verifica en este orden:

1. Abre `/api/health` una sola vez.
2. Si responde `503` indicando cuota temporal, espera y no recargues repetidamente.
3. Cuando responda `200` con `ok: true`, abre un solo módulo.
4. Ejecuta una sola carga de respaldo y espera la confirmación.
5. Comprueba el resultado en la pestaña correspondiente de Google Sheets.

Un `503` con `retry_after_seconds` indica una limitación temporal de Google, no una pérdida de datos. Un `500` distinto debe revisarse con el JSON devuelto por el endpoint; el backend ya devuelve el tipo de excepción y el mensaje para facilitar el diagnóstico.

La versión actual no requiere ningún archivo XLSX local, carpeta `data/`, servidor independiente ni credencial guardada en disco. Solo necesita `GOOGLE_SHEETS_ID` y `GOOGLE_SERVICE_ACCOUNT_JSON` en Vercel, y la cuenta de servicio debe tener permiso de Editor sobre la hoja.
