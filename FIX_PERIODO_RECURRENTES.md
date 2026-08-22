# Corrección de períodos recurrentes

## Problema

Una obligación Recurrente pagada totalmente avanzaba inmediatamente al siguiente vencimiento y su nuevo monto aparecía en **Falta por pagar**. Esto mezclaba el período ya pagado con el próximo período y podía hacer parecer que el pago no había sido reconocido.

## Regla aplicada

**Falta por pagar** representa exclusivamente las obligaciones del período vigente. El siguiente ciclo recurrente se conserva, pero queda en estado `Programada` hasta su fecha de activación.

| Tipo de recurrente | Inicio del siguiente período |
|---|---|
| Mensual | Día 1 del mes correspondiente |
| Semanal | Día posterior al vencimiento del período anterior |

Mientras el período está programado, el backend lo excluye de `deudas_activas`, `faltante_recurrente`, `faltante_pagar` y del calendario de vencimientos. La interfaz lo muestra en **Próximo período — no suma a Falta por pagar**, con su valor y fecha de activación.

## Ejemplo

Si **LA MONA** tiene un arriendo mensual de $3.150.000 y se paga completamente el período de agosto:

| Momento | Estado | Falta por pagar |
|---|---|---:|
| Después de pagar agosto | Programada para septiembre | No incluye $3.150.000 |
| 1 de septiembre | Período vigente | Incluye $3.150.000 |

El pago de agosto permanece en **Pagos Deudas**, **Total pagado** y **Balance mensual**. No se elimina ni se duplica.

## Compatibilidad

Las Variables mantienen su comportamiento: al quedar en cero desaparecen de la vista activa y solo vuelven cuando se registra una nueva deuda. Las Recurrentes no requieren una nueva fila; se reutiliza el registro y se recalcula el período cuando llega su fecha de activación.

## Validación

Se ejecutaron correctamente las pruebas de deudas mensuales y semanales, separación Recurrente/Variable, exclusión de Variables pagadas, reactivación mensual el día 1, balance e historial, migración de esquema, nómina/préstamos, arnés remoto, rutas del dispatcher, compilación Python y sintaxis JavaScript inline.

La prueba específica usa un reloj simulado para verificar los dos estados: antes del día 1 la Recurrente está programada y no suma; el día 1 se reactiva con el monto completo y vuelve a sumar.

## Archivos principales modificados

- `ControlTaller/app.py`: cálculo del inicio del período, estado `Programada`, exclusión de recurrentes futuras y campo `deudas_programadas`.
- `ControlTaller/templates/index.html`: explicación del total y bloque visual para el próximo período.
- `test_deudas_falta_pagar_fix.py`, `test_deudas_taller.py`, `test_deudas_taller_semanal.py`, `test_deudas_tipos.py` y `test_deudas_summary_ui.py`: expectativas y cobertura actualizadas.
- `DEUDAS_RECURRENTES_VARIABLES.md`: documentación funcional actualizada.
