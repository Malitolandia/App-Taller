# Corrección de límite de Google Sheets

## Problema observado

Google Sheets respondió con `HTTP 429 RATE_LIMIT_EXCEEDED` para la métrica `ReadRequestsPerMinutePerUser`. La operación que falló intentaba leer el rango de la pestaña predeterminada `Hoja 1` hasta `ZZ`.

## Cambios aplicados

La aplicación ahora excluye `Hoja 1` y cualquier pestaña ajena al proyecto. Las lecturas de las doce pestañas se agrupan mediante `values.batchGet`, y los metadatos de las hojas se conservan en una caché breve. La inicialización del esquema está protegida con un bloqueo para que solicitudes concurrentes no repitan la creación y lectura de pestañas.

El adaptador usa reintentos con backoff para respuestas 429 y errores transitorios 5xx. Si ya existe una instantánea confirmada en memoria, una lectura limitada puede continuar utilizando esa instantánea en lugar de presentar un libro vacío. Después de una escritura o importación confirmada, la instantánea se actualiza con los valores que fueron enviados a Google Sheets.

Neveras dejó de consultar `/productos` y después `/datos` al arrancar, dejó de consultar `/lista-clientes` cada vez que se abre el modal de venta y dejó de ejecutar el sondeo automático cada 10 segundos. ControlTaller incorpora deduplicación de GET simultáneos durante el arranque para no cargar dos veces las pestañas `Mecanicos` y `Equipos`.

Cuando el límite de cuota todavía se alcanza y no existe una instantánea disponible, los endpoints responden `503` con un mensaje de espera, en lugar de convertir el límite temporal en un `500` genérico.

## Pruebas ejecutadas

| Prueba | Resultado |
| --- | --- |
| Compilación Python de todos los módulos | PASS |
| Sintaxis JavaScript de Neveras | PASS |
| Lectura sin `Hoja 1` y fallback ante 429 | PASS |
| CRUD de ControlTaller | PASS |
| Lectura, venta y marcado de pago en Neveras | PASS |
| Lectura y alta en Peritaje | PASS |
| Exportación XLSX de las 12 pestañas | PASS |
| Importación XLSX hacia las 12 pestañas | PASS |
| Arranque desde esquema incompleto, conservando `Hoja 1` | PASS |

## Verificación después del redeploy

1. Publicar el contenido del ZIP en la raíz del repositorio.
2. Ejecutar un nuevo deploy en Vercel conservando `GOOGLE_SHEETS_ID` y `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. Abrir `/api/health` una sola vez. Debe devolver HTTP 200, `ok: true`, `remote_connected: true` y las doce pestañas requeridas.
4. Esperar unos segundos si se acaba de producir un 429 antes de probar la carga.
5. Cargar un respaldo una sola vez y esperar la respuesta de confirmación.
6. Recargar el módulo que corresponda y comprobar una fila en Google Sheets.
7. No abrir varias pestañas del navegador ni refrescar repetidamente durante la primera prueba, porque la cuota de lectura es por ventana temporal y puede volver a agotarse aunque el código ya no lea `Hoja 1`.

La validación local usa un simulador completo de Google Sheets. La comprobación real depende de que Vercel conserve las variables de entorno y de que la cuenta de servicio tenga acceso de Editor al archivo indicado.
