# Validación del resumen de Deudas del Taller

## Cambio funcional

Se eliminó del resumen superior el indicador general `Faltante por reunir`. Ese valor ya no se presenta como una métrica global porque corresponde a la necesidad de fondos de cada obligación individual.

El resumen superior conserva `Falta por pagar`, que se calcula con los saldos pendientes reales de las deudas activas. También conserva `Total pagado`, `Pagado este mes` y `Próximos / atrasados`, todos basados en pagos efectivos y estados de vencimiento.

## Presentación por deuda

Cada tarjeta de la cuadrícula continúa mostrando `Saldo por pagar`, `En bolsillo` y `Falta reunir`. Así se puede identificar exactamente cuánto dinero falta reunir para una deuda concreta sin mezclarlo con el total general del taller.

Los aportes al bolsillo no se contabilizan como pagos. El total pagado y el balance mensual siguen obteniéndose exclusivamente de la hoja `Pagos Deudas`.

## Validación ejecutada

La prueba de interfaz confirmó que no existe el elemento general `dtFaltante` ni una actualización JavaScript asociada. Confirmó también que `dtComprometido` continúa mostrando `totals.faltante_pagar` y que las tarjetas conservan `d.faltante_reunir`.

Además, pasaron compilación Python, sintaxis JavaScript, balance de Deudas del Taller y regresión remota principal.
