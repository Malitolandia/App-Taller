# Corrección del cobro parcial en Neveras

## Problema identificado

El cobro parcial rechazaba importes menores que el saldo de la primera venta pendiente. Por eso un abono como `$4,00` era rechazado cuando la primera venta tenía un saldo de `$6.000`, aunque el cliente tuviera una deuda total mayor.

La validación anterior imponía un mínimo por venta individual. Esa regla no corresponde a un abono global por cliente.

## Regla definitiva

El formulario de cobro acepta cualquier importe que cumpla:

```text
monto > 0
monto <= deuda total pendiente del cliente
```

El importe puede ser menor que una venta completa y puede escribirse como número o con coma decimal, por ejemplo `4,00` o `4.000,00`.

## Aplicación del abono

Los pagos se distribuyen cronológicamente entre las ventas pendientes del cliente:

1. Se calcula la deuda total pendiente.
2. Se rechazan los importes cero, negativos, no numéricos o superiores a la deuda total.
3. El abono se aplica a la primera venta pendiente.
4. Si sobra dinero después de cerrar esa venta, continúa con la siguiente.
5. Si el abono no cubre la venta, se conserva el saldo parcial en esa misma venta.
6. Las ventas completamente pagadas pasan a `SI`; las ventas con saldo conservan `NO` y muestran el abono acumulado.

Por ejemplo, con ventas pendientes de `$6.000` y `$10.000`, un abono de `$4.000` deja saldos de `$2.000` y `$10.000`. No se exige cubrir primero los `$6.000` completos.

## Persistencia y compatibilidad

La pestaña `Ventas` incorpora `Monto Abonado` al final del encabezado. La migración es no destructiva: las ventas antiguas sin esa columna se interpretan con abono cero y el encabezado se completa sin desplazar las columnas existentes.

Los cobros parciales se guardan en Google Sheets. El total pagado del cliente aumenta con cada abono y la deuda pendiente disminuye sin alterar existencias, precio, costo ni ganancia de la venta.

## Validación ejecutada

La prueba funcional cubre un abono menor que la primera venta, un abono complementario que cierra esa venta, un cobro total del saldo restante, el rechazo de sobrepagos, el rechazo de cero, la persistencia del abono y la actualización de la interfaz.

También se ejecutó la regresión del proyecto: ControlTaller, Neveras, Peritaje, persistencia remota simulada, esquema, inventario, ventas, stock, deudas, nómina, caché, importación/exportación y compilación Python. Todas las pruebas finalizaron correctamente.

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `Neveras/servidor.py` | Aceptación de abonos arbitrarios dentro del saldo total, distribución cronológica y normalización de montos con coma decimal. |
| `storage.py` | Encabezado y migración no destructiva de `Monto Abonado` en `Ventas`. |
| `test_cobro_deuda.py` | Cobertura de abonos menores que una venta, abonos acumulados, cobro total y validaciones. |

La corrección no modifica la lógica de cobro total existente ni elimina el historial de ventas.
