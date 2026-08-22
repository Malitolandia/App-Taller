# Indicadores definitivos de Deudas del Taller

## Criterio general

La pantalla muestra el importe pendiente actual de las obligaciones y, por separado, los pagos que ya se realizaron. La clasificación visible es **Gastos fijos** y **Únicos**. Internamente, los gastos fijos conservan el tipo `Recurrente` y los únicos/proveedores conservan el tipo `Variable`, para mantener compatibilidad con Google Sheets y con el historial existente.

| Indicador visible | Campo backend | Qué representa |
|---|---|---|
| **Total por pagar** | `totales.faltante_pagar` | Suma de los saldos pendientes de Gastos fijos y Únicos activos. |
| **Gastos fijos por pagar** | `totales.faltante_recurrente` | Suma de los saldos de obligaciones mensuales o semanales. Al pagar un ciclo, el siguiente ciclo se renueva inmediatamente, según la lógica estable anterior. |
| **Únicos por pagar** | `totales.faltante_variable` | Suma de deudas concretas activas, como proveedores o conceptos extraordinarios. Cuando llegan a cero desaparecen de activos. |
| **Total pagado** | `totales.pagado_total` | Suma histórica de todos los pagos registrados. |
| **Pagado este mes** | `totales.pagado_mes` | Pagos registrados en el mes calendario actual. |
| **Próximos / atrasados** | `totales.proximos` / `totales.atrasados` | Conteo de obligaciones activas próximas a vencer o vencidas. |

La fórmula principal es:

```text
Total por pagar = Gastos fijos por pagar + Únicos por pagar
```

Los aportes a **Fondos Deudas** no se suman a Total pagado. Se muestran dentro de cada obligación como dinero disponible en bolsillo y reducen el faltante por reunir, pero no constituyen un pago al acreedor.

## Comportamiento de cada categoría

Los **Gastos fijos** representan obligaciones que se repiten, como arriendo, vigilancia o internet. Cuando se registra el pago total del período, el sistema conserva el registro histórico y calcula el siguiente vencimiento; como esta es la solución estable solicitada, el nuevo ciclo aparece inmediatamente como saldo del gasto fijo.

Los **Únicos** representan deudas concretas de proveedores o conceptos puntuales. Admiten pagos parciales y totales. Al quedar con saldo cero, desaparecen de la cuadrícula activa y dejan de sumar a Total por pagar, sin borrar el registro original, los fondos ni los pagos. Una nueva obligación se registra como un nuevo movimiento.

## Ejemplo

Si existen $3.150.000 pendientes de un gasto fijo, $7.864.500 en Únicos y se han pagado $4.892.000, el panel muestra:

| Tarjeta | Valor |
|---|---:|
| Total por pagar | $11.014.500 |
| Gastos fijos por pagar | $3.150.000 |
| Únicos por pagar | $7.864.500 |
| Total pagado | $4.892.000 |

El Total por pagar no se obtiene sumando pagos históricos. Los pagos solo alimentan Total pagado y Pagado este mes.

## Validación

La versión fue comparada con el paquete estable anterior, se revirtió la lógica de períodos programados, se actualizaron las etiquetas visibles y se ejecutaron las pruebas de deudas mensuales y semanales, separación de tipos, pagos, historial, balance, migración de esquema, nómina/préstamos, arnés remoto, dispatcher, compilación Python y sintaxis JavaScript inline. Todas fueron aprobadas.
