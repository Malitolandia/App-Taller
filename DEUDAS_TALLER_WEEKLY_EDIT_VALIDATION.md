# Validación: Deudas del Taller — semanal, edición y eliminación

## Alcance

Esta entrega amplía Deudas del Taller con la frecuencia `Semanal`, además de `Mensual` y `Unico`. La frecuencia semanal utiliza la primera fecha de vencimiento y avanza automáticamente siete días después de cada pago total del período.

También incorpora edición y eliminación desde la interfaz. La edición permite cambiar acreedor, concepto, monto, frecuencia, fecha o día de pago y observaciones, respetando el historial. La eliminación se confirma en la interfaz y solo se permite si la deuda no tiene fondos aportados ni pagos registrados.

## Reglas

- Una deuda semanal conserva su primera fecha y calcula el siguiente vencimiento con intervalos de siete días.
- El cambio de frecuencia se bloquea cuando la deuda ya tiene fondos o pagos históricos, para evitar inconsistencias en el calendario.
- El aumento de monto conserva los aportes existentes y recalcula el faltante por reunir.
- Las deudas con fondos o pagos no se eliminan; deben editarse o permanecer cerradas para conservar trazabilidad.
- Las deudas sin historial pueden editarse y eliminarse.
- Las confirmaciones y avisos se muestran antes y después de cada operación modificadora.

## Prueba ejecutada

`test_deudas_taller_semanal.py` validó:

1. Creación semanal con primera fecha.
2. Cálculo inicial del próximo vencimiento y período.
3. Aporte inicial al bolsillo.
4. Aumento del monto manteniendo fondos existentes.
5. Rechazo del cambio de frecuencia con historial.
6. Aporte restante y pago total.
7. Avance automático de siete días al siguiente período.
8. Rechazo de eliminación con fondos o pagos.
9. Edición de una deuda sin historial.
10. Eliminación de una deuda sin historial.
11. Presencia de frecuencia semanal y acciones de editar/eliminar en la interfaz.

Resultado: `PASS semanal + avance de 7 días + aumento + edición + eliminación segura + historial`.

La compilación de Python y la extracción/validación del JavaScript embebido también fueron exitosas. El cambio conserva las 17 pestañas remotas existentes y no requiere nuevas variables de entorno.
