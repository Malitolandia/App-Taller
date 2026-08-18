# Alta de productos en Neveras

## Alcance

Se añadió la posibilidad de crear productos desde la pestaña **Inventario** de Neveras. El formulario escribe directamente en la pestaña `Inventario` de Google Sheets mediante `POST /neveras/api/nuevo-producto`.

## Campos

| Campo | Validación |
| --- | --- |
| Nombre del producto | Obligatorio, máximo 120 caracteres en la interfaz y comparación duplicada sin distinguir mayúsculas/minúsculas |
| Costo unitario | Obligatorio, numérico y no negativo |
| Precio de venta | Obligatorio, numérico y no negativo |
| Stock inicial | Obligatorio, entero y no negativo |
| Stock mínimo | Obligatorio, entero y no negativo |

Al guardar, el backend calcula `Ganancia Unit.`, `Stock Actual`, `Estado`, `Costo Total Inv.` y `Ganancia x Producto`. La fila se agrega a `Inventario` y el backend exige la confirmación `updatedRange` de Google Sheets antes de responder correctamente.

## Compatibilidad

El cambio es aditivo. No se cambiaron las rutas de ventas, marcado de pagos, clientes, dashboard ni respaldo global. La respuesta del alta incluye el producto confirmado y la interfaz actualiza el inventario en memoria, evitando una lectura adicional inmediatamente después del guardado.

## Pruebas ejecutadas

| Prueba | Resultado |
| --- | --- |
| Sintaxis Python de backend y WSGI | Correcta |
| Sintaxis JavaScript de Neveras | Correcta |
| Alta de un producto nuevo | Correcta |
| Lectura del producto recién creado | Correcta |
| Venta usando el producto recién creado | Correcta; el stock bajó de 20 a 18 en la prueba |
| Rechazo de producto duplicado sin distinguir mayúsculas | Correcto, HTTP 409 |
| Rechazo de costo negativo/stock no entero | Correcto, HTTP 400 |
| CRUD previo de ControlTaller, ventas, pagos y Peritaje | Correcto en la prueba de regresión |
| Exportación e importación de respaldo | Correcta en la prueba de regresión |

## Uso en producción

Después del redeploy, abrir Neveras, entrar en **Inventario** y pulsar **+ Nuevo Producto**. Tras guardar, el nuevo registro debe aparecer en la tabla y en la pestaña `Inventario` de Google Sheets. Si Google Sheets responde con una limitación temporal de cuota, la interfaz mostrará el error y no creará un registro local falso.
