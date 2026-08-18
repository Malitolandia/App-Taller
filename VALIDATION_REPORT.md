# Informe de validación de APPTALLER

## Resultado general

La copia limpia fue validada como aplicación Flask unificada con backend remoto exclusivo. No depende de archivos XLSX locales para operar, no crea `data/` y no contiene un modo offline en Neveras.

## Pruebas ejecutadas

| Prueba | Resultado |
| --- | --- |
| `python3 -m compileall -q .` | Correcta |
| `node --check Neveras/app.js` | Correcta |
| Menú raíz `/` | HTTP 200 |
| Interfaz `/control/` | HTTP 200 |
| Interfaz `/neveras/` | HTTP 200 |
| Interfaz `/peritaje/` | HTTP 200 |
| `/api/health` sin credenciales | HTTP 503 JSON diagnóstico, comportamiento esperado |
| Lectura y alta en ControlTaller con Google Sheets simulado | Correcta |
| Lectura, venta y marcado de pago en Neveras con Google Sheets simulado | Correcta |
| Lectura y alta en Peritaje con Google Sheets simulado | Correcta |
| Exportación global XLSX | Correcta |
| Importación global XLSX | Correcta; 12 pestañas |
| Inicialización desde una hoja con una sola pestaña | Correcta; crea las 12 pestañas y conserva `Hoja 1` |
| Rangos de limpieza acotados al tamaño real | Correcta en el simulador |

La prueba remota simulada termina con:

```text
PASS clean remote CRUD + backup cycle
PASS schema bootstrap
```

## Qué debe verificarse después de subirlo

La conexión con la hoja real no puede certificarse desde esta copia sin utilizar las variables privadas de Vercel. Después del redeploy, abre `/api/health` en el dominio vigente. Debe devolver `ok: true`, `remote_connected: true` y `required_sheets_present: true`.

A continuación realiza una escritura real en cada módulo y confirma que la nueva fila aparece después de recargar la aplicación y directamente en Google Sheets. Si una operación falla, la respuesta JSON incluye la excepción concreta para identificar si el problema está en el ID, los permisos, el JSON de credenciales o la API.
