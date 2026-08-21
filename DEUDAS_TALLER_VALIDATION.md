# Deudas del Taller — validación y uso

## Alcance

La pestaña **Deudas del Taller** registra obligaciones del taller con proveedores, arrendadores, personas u otras entidades. La fecha de registro se asigna automáticamente al crear la obligación. No se solicita ni se guarda una fecha de nacimiento de la deuda.

Cada obligación tiene acreedor, concepto, monto total, frecuencia (`Mensual` o `Único`), día o fecha de pago, observaciones y estado calculado.

## Hojas de Google Sheets

Se añaden tres pestañas al esquema remoto:

| Hoja | Propósito |
|---|---|
| `Deudas Taller` | Registro maestro de la obligación, calendario y estado actual. |
| `Fondos Deudas` | Historial de dinero apartado en cada bolsillo. |
| `Pagos Deudas` | Historial de pagos parciales o totales. |

Las hojas se crean automáticamente durante `/api/health`, exportación o la primera escritura después del redeploy. El esquema completo pasa de 14 a 17 pestañas.

## Reglas funcionales

Una deuda mensual conserva el monto de la cuota del período y avanza automáticamente al mes siguiente cuando se registra el pago total del período. Una deuda única pasa a `Pagado` cuando su saldo queda en cero.

El bolsillo es un registro interno del dinero apartado para una obligación. Un aporte no puede superar el faltante por reunir. Un pago no puede superar el saldo pendiente ni el dinero actualmente disponible en el bolsillo. El sistema admite pagos parciales y totales.

Los estados visibles son `Pendiente de reunir`, `Listo para pagar`, `Atrasado` y `Pagado`. El calendario muestra la fecha siguiente, saldo, dinero apartado, faltante y recordatorio: vencido, por pagar en siete días, listo para pagar o pendiente de reunir.

## Interfaz

La nueva pestaña está disponible en **Control de Taller → Deudas del Taller**. Incluye:

- Formulario de registro con opción de pago mensual o único.
- Indicadores de saldo por pagar, dinero en bolsillos, faltante y alertas.
- Tarjetas por acreedor con acciones **Aportar al bolsillo** y **Registrar pago**.
- Calendario de compromisos y recordatorios calculados con la fecha actual.
- Historial combinado de aportes y pagos.

Antes de registrar una deuda, aporte o pago se solicita confirmación. Los errores de monto, fecha, día mensual y fondos insuficientes se devuelven sin guardar cambios.

## Pruebas ejecutadas

`test_deudas_taller.py` validó:

1. Bootstrap de las tres pestañas nuevas y ausencia de `Fecha Nacimiento`.
2. Registro de deuda mensual.
3. Aporte parcial al bolsillo.
4. Pago parcial y actualización del saldo.
5. Nuevo aporte y pago total del período.
6. Avance automático al siguiente mes.
7. Registro y pago total de una deuda única.
8. Rechazo de aportes superiores al faltante.
9. Rechazo de pagos sin dinero en el bolsillo.
10. Presencia de pestaña, formularios, tarjetas, calendario y acciones en la interfaz.
11. Regresión remota de Control de Taller, Neveras, Peritaje y respaldo XLSX.

Resultado: `PASS deudas taller: mensual + parcial + total + único + calendario + bolsillo + validaciones`.

También se verificó la sintaxis con `python3 -m py_compile` y `node --check` del JavaScript embebido.
