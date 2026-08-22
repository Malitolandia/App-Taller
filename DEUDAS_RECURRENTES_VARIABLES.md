# Separación de Deudas del Taller: Recurrentes y Variables

## Objetivo

Deudas del Taller ahora distingue entre obligaciones **Recurrentes** y **Variables**. La separación se aplica en el registro web, el backend, los indicadores, la cuadrícula activa y la sincronización con Google Sheets.

## Reglas funcionales

| Tipo | Frecuencia | Regla de negocio |
|---|---|---|
| **Recurrente** | Mensual o semanal | Representa una obligación que vuelve a generarse. Cuando se paga el período actual, el sistema avanza al siguiente período, pero este queda programado y no se considera vigente hasta que comienza su ciclo. |
| **Variable** | Se guarda internamente como `Único` | Representa una deuda o saldo concreto de un proveedor o concepto. Puede pagarse parcialmente; cuando el saldo llega a cero, deja de aparecer en la cuadrícula activa y en el calendario. |

Las Variables pagadas no se borran. Permanecen en la pestaña **Deudas Taller** con estado `Pagado`, y sus movimientos permanecen en **Pagos Deudas** y **Fondos Deudas**. Para volver a registrar una obligación del mismo proveedor o concepto se crea una nueva deuda, con un nuevo ID.

## Indicadores

El panel devuelve y muestra tres saldos relacionados:

```text
faltante_recurrente = suma de saldos pendientes de obligaciones Recurrentes del período vigente
faltante_variable   = suma de saldos pendientes de obligaciones Variables activas
faltante_pagar      = faltante_recurrente + faltante_variable
```

Los saldos menores o iguales a $0,009 se consideran cero para evitar residuos de redondeo. Por ello, una Variable completamente pagada no aumenta **Falta por pagar**. Una Recurrente cuyo período siguiente todavía no ha comenzado tampoco aumenta el total.

Para una Recurrente mensual, el nuevo período comienza el día 1 del mes correspondiente. Para una Recurrente semanal, comienza el día posterior al vencimiento del período anterior. Hasta ese momento aparece en **Próximo período — no suma a Falta por pagar**, con su fecha de activación y su valor programado.

El indicador **Total pagado** y el **Balance mensual** continúan calculándose únicamente con registros de pagos efectivos. Los aportes al bolsillo no se mezclan con esos indicadores.

## Cambios en Google Sheets

La pestaña **Deudas Taller** conserva las diez columnas existentes y añade `Tipo` como columna número once, al final:

```text
ID | Fecha Registro | Acreedor | Concepto | Monto Total | Frecuencia |
Día Pago | Próximo Vencimiento | Estado | Observaciones | Tipo
```

No se crea una nueva pestaña. Al iniciar la aplicación, el bootstrap remoto actualiza solamente el encabezado de una hoja antigua que conserve las diez columnas conocidas. Los registros existentes no se desplazan ni se eliminan.

Para filas antiguas sin `Tipo`, el backend aplica compatibilidad automática: `Mensual` y `Semanal` se interpretan como **Recurrente**; las filas antiguas `Único` se interpretan como **Variable**. Los respaldos XLSX antiguos también se normalizan durante la carga y reciben el tipo inferido antes de sincronizarse.

## Uso desde la web

En el formulario de alta se selecciona **Recurrente** o **Variable**. Para Recurrente se elige `Mensual` o `Semanal`; para Variable se solicita una fecha de vencimiento y no se muestra el selector de frecuencia. El monto de una Variable se entiende como su saldo inicial.

La cuadrícula separa las tarjetas en los bloques **Recurrentes** y **Variables**. Una Variable pagada no aparece en esos bloques activos, pero puede consultarse en el registro histórico de pagos. Una Recurrente pagada se mueve temporalmente a **Próximo período**, no se puede pagar dos veces antes de su activación y reaparece en la cuadrícula activa al comenzar el ciclo. Las ediciones conservan las validaciones existentes y no permiten reducir una deuda por debajo de lo ya pagado en el período.

## Validación realizada

Se validaron los siguientes casos:

| Caso | Resultado |
|---|---|
| Variable creada con saldo pendiente | Aparece en Variables y suma al subtotal variable. |
| Variable pagada totalmente | Desaparece de activos, conserva el registro y deja de sumar al total. |
| Nueva Variable para el mismo proveedor | Se crea como registro independiente y vuelve a sumar al subtotal variable. |
| Recurrente mensual | Se mantiene fuera del total tras el pago hasta el día 1 del próximo período; luego se reactiva con su saldo completo. |
| Deuda antigua sin columna Tipo | Se migra el encabezado sin pérdida de datos y se infiere el tipo. |
| Recurrente semanal y mensual, con período siguiente programado | Regresión aprobada. |
| Pagos, bolsillos, calendario e historial | Regresión aprobada. |
| Neveras, Peritaje, Nómina, préstamos y respaldos XLSX | Regresión aprobada. |

La actualización es incremental y no requiere modificar manualmente las 17 pestañas existentes. Después de desplegar, se recomienda abrir el panel de Deudas del Taller y verificar que el encabezado `Tipo` esté al final de **Deudas Taller**.
