# Validación: pagos únicos, total pagado y balance mensual

## Cambios funcionales

- Las deudas con frecuencia `Único` y estado `Pagado` dejan de aparecer en la cuadrícula de compromisos activos.
- La deuda pagada permanece en `data.deudas`, conserva su registro en `Deudas Taller` y sus movimientos en `Pagos Deudas`.
- El resumen muestra `Falta por pagar`, `Total pagado`, `Pagado este mes`, `Faltante por reunir` y alertas de próximos/vencidos.
- `Total pagado` suma únicamente los registros de la hoja `Pagos Deudas`.
- `Pagado este mes` filtra los pagos por la fecha real del pago (`YYYY-MM`).
- El balance mensual agrupa únicamente pagos reales por mes y muestra operaciones y total pagado.
- El registro inferior se llama `Registro de pagos` y contiene exclusivamente movimientos de `Pagos Deudas`; los aportes de `Fondos Deudas` no se mezclan allí.
- Los fondos del bolsillo continúan visibles por separado en las tarjetas y se utilizan para validar la disponibilidad antes de pagar.

## Caso validado

Se creó una deuda única de 150, se aportaron 150 al bolsillo y se registró el pago total. El resultado fue:

- `deudas_activas`: la deuda dejó de aparecer.
- `deudas`: la deuda permaneció con estado `Pagado`.
- `pagos`: permaneció un registro de pago de 150.
- `pagado_total`: 150.
- `pagado_mes`: 150.
- `balance_mensual`: un período con una operación y 150 pagados.
- El registro visual inferior no incluyó el aporte al bolsillo.

## Regresión

Pasaron la prueba específica de balance, compilación de Python, sintaxis JavaScript y las pruebas existentes de Deudas del Taller, Nómina/préstamos, Inventario, filtro de stock, bootstrap de esquema y CRUD remoto con ciclo de respaldo XLSX.
