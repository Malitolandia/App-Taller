# Validación: gestión del Inventario de Neveras

## Alcance

La pestaña **Inventario** ahora permite editar los datos del producto, modificar la existencia actual y eliminar productos que todavía no tienen ventas asociadas. Cada operación de escritura solicita confirmación mediante una alerta antes de enviarse a Google Sheets y muestra un aviso de resultado cuando termina o cuando se cancela.

| Acción | Resultado |
|---|---|
| Editar producto | Permite actualizar nombre, costo, precio de venta y stock mínimo. El nombre no se puede cambiar si existen ventas históricas. |
| Modificar existencias | Permite fijar la existencia actual como un número entero no negativo, conservando las unidades vendidas históricas. |
| Eliminar producto | Elimina la fila del inventario únicamente si el producto no tiene ventas históricas. Si las tiene, la operación se bloquea para no romper Ventas, Clientes o Deudas. |
| Nuevo producto | Conserva el alta existente y ahora solicita confirmación antes de guardar. |

## Protección de ventas históricas

Cuando se edita el costo o precio de un producto con ventas anteriores, el sistema congela en esas ventas el precio, total y ganancia que tenían antes de la edición. El nuevo precio queda disponible para las ventas futuras. De esta manera, cambiar el catálogo no reescribe la historia comercial.

## Endpoints añadidos

| Ruta | Método | Datos principales |
|---|---|---|
| `/neveras/api/editar-producto` | POST | `productoOriginal`, `producto`, `costo`, `precio`, `stockInicial`, `stockMin` |
| `/neveras/api/ajustar-existencias` | POST | `producto`, `stockActual` |
| `/neveras/api/eliminar-producto` | POST | `producto` |

Cada respuesta exitosa devuelve `ventas`, `inventario` y `clientes` para que el frontend actualice el estado completo sin una lectura adicional. Cada operación realiza una carga del libro y un guardado lógico en Google Sheets.

## Validaciones ejecutadas

| Prueba | Resultado |
|---|---|
| Crear, editar, ajustar y eliminar producto sin ventas | Correcta |
| Editar costo/precio de producto con ventas | Correcta; las ventas históricas conservaron precio 25, total 50 y ganancia 30 |
| Renombrar producto con ventas | Bloqueado con HTTP 409 |
| Eliminar producto con ventas | Bloqueado con HTTP 409 |
| Stock fraccionario | Rechazado con HTTP 400 |
| Botones y columna Acciones en la interfaz | Confirmados |
| Modal de edición y modal de existencias | Confirmados |
| Confirmaciones `confirm()` y avisos de cancelación/resultado | Confirmados en JavaScript |
| Sintaxis Python y JavaScript | Correcta |
| Regresión ControlTaller, Peritaje, Ventas, Deudas y respaldo XLSX | Correcta |

Pruebas utilizadas:

- `test_inventario_crud.py`
- `test_clean_remote.py`

Las pruebas usan el simulador remoto existente, sin credenciales reales ni modificaciones en la hoja de producción.

## Despliegue

Reemplaza el contenido del repositorio con el ZIP incremental, conserva las variables actuales de Vercel y realiza un nuevo commit/redeploy. No es necesario crear nuevas pestañas ni cambiar `GOOGLE_SHEETS_ID` o `GOOGLE_SERVICE_ACCOUNT_JSON`.
