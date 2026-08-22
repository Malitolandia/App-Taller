# Corrección de «Falta por pagar»

## Diagnóstico

El indicador general de **Falta por pagar** se calculaba recorriendo la lista completa de deudas y excluyendo únicamente las que tuvieran estado textual `Pagado`. Las deudas únicas pagadas deben conservarse en el histórico, pero no forman parte de los compromisos activos del taller. Esa separación ya existía para la cuadrícula y el calendario mediante `deudas_activas`, pero el total general no la estaba utilizando.

La ubicación del cálculo era `ControlTaller/app.py`, dentro de `_deudas_panel()`.

## Ajuste aplicado

Se modificó únicamente el cálculo del total para que:

1. Use `deudas_activas`, que excluye las deudas de frecuencia **Único** con estado `Pagado`.
2. Sume solo saldos materialmente pendientes, superiores a `0.009`, evitando residuos de redondeo.
3. Mantenga las deudas **Mensuales** y **Semanales** después de pagar un período, porque esas deudas avanzan al siguiente período con un nuevo saldo pendiente.

El historial de deudas, los pagos, los aportes, el balance mensual, el calendario y las tarjetas individuales no fueron modificados.

## Validación realizada

Se ejecutó la prueba específica `test_deudas_falta_pagar_fix.py`, con estos casos:

| Caso | Resultado esperado | Resultado |
|---|---|---|
| Deuda única pagada | No aparece en `deudas_activas` ni en **Falta por pagar** | PASS |
| Deuda única pendiente | Se suma al indicador general | PASS |
| Deuda mensual pagada en el período | Avanza al siguiente período y conserva su nuevo saldo pendiente | PASS |
| Cálculo combinado | 80 de deuda única pendiente + 200 del siguiente período mensual = 280 | PASS |

También se ejecutó la regresión existente:

| Prueba | Resultado |
|---|---|
| `test_deudas_balance.py` | PASS |
| `test_deudas_taller.py` | PASS |
| `test_deudas_taller_semanal.py` | PASS |
| `test_nomina_prestamos.py` | PASS |
| `test_clean_remote.py` | PASS |
| Compilación Python del proyecto | PASS |
| Verificación sintáctica de `Neveras/app.js` | PASS |

## Archivos modificados o agregados

| Archivo | Tipo de cambio |
|---|---|
| `ControlTaller/app.py` | Cambio mínimo en el cálculo de `falta_pagar` |
| `test_deudas_falta_pagar_fix.py` | Nueva prueba específica del bug |
| `FIX_FALTA_POR_PAGAR.md` | Esta documentación |

La persistencia en Google Sheets, las 17 pestañas, la importación/exportación XLSX y las demás funcionalidades de las tres aplicaciones permanecen sin cambios.
