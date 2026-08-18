# Validación: cobro total y parcial desde Deudas

## Alcance

Se modificó únicamente el módulo **Neveras**. El botón de cobro fue retirado de la tabla **Ventas** y se incorporó en la parte inferior derecha de cada tarjeta de **Deudas**. El botón abre un formulario donde el monto aparece precargado con la deuda total del cliente, pero puede reducirse para registrar un cobro parcial.

## Reglas implementadas

| Caso | Comportamiento |
|---|---|
| Cobro total | Se marcan como pagadas todas las ventas pendientes del cliente cuando el monto solicitado cubre la deuda completa. |
| Cobro parcial | Se marcan ventas completas, en orden cronológico, hasta cubrir el monto indicado. No se divide una venta en dos. |
| Monto menor que la primera venta pendiente | Se rechaza el cobro y no se modifica Google Sheets, porque el sistema no fracciona ventas. |
| Monto cero, negativo o no numérico | Se rechaza con validación visible y no se modifica la base de datos. |
| Cliente sin deuda | Se rechaza y no se modifica la base de datos. |

## Cambios técnicos

El backend incorpora `POST /neveras/api/cobrar-cliente`, que recibe `{ "cliente": "NOMBRE", "monto": 75 }`. La operación carga el libro remoto, calcula los totales pendientes usando los valores de Ventas y el precio de Inventario cuando las fórmulas todavía no tienen valor cacheado, actualiza únicamente las columnas **Pagó** y **Estado Pago**, y realiza un solo guardado lógico. La respuesta devuelve `ventas`, `inventario` y `clientes` para actualizar la interfaz sin una lectura adicional.

El frontend incorpora el modal `cobro-overlay`, la función `abrirCobroDeuda(cliente, deudaTotal)` y la función `confirmarCobroDeuda()`. La tabla Ventas conserva el estado visual, pero ya no incluye la acción de cobro individual.

## Pruebas ejecutadas

| Prueba | Resultado |
|---|---|
| Compilación de `Neveras/servidor.py` | Correcta |
| Sintaxis de `Neveras/app.js` | Correcta |
| Cobro parcial de 75 sobre ventas 25 + 50 + 25 | Marcó las dos primeras ventas y dejó deuda 25 |
| Cobro total del saldo restante de 25 | Marcó la última venta y dejó deuda 0 |
| Monto cero | HTTP 400, sin cambios |
| Cliente sin deuda | HTTP 400, sin cambios |
| Ausencia de `pagar-btn` en Ventas | Confirmada |
| Botón/modal de cobro en Deudas | Confirmados |
| Regresión ControlTaller, Peritaje y respaldo XLSX | Correcta |

Pruebas automatizadas utilizadas:

- `test_cobro_deuda.py`
- `test_clean_remote.py`

El arnés utiliza el simulador remoto de Google Sheets y no contiene credenciales reales ni modifica la hoja de producción.

## Despliegue

Descomprime el ZIP sobre una copia del repositorio `Malitolandia/App-Taller`, conserva las variables de entorno actuales de Vercel y realiza un nuevo commit/redeploy. No es necesario crear otra hoja de Google Sheets ni cambiar las variables `GOOGLE_SHEETS_ID` o `GOOGLE_SERVICE_ACCOUNT_JSON`.
