# Módulo de Préstamos y Descuentos de Nómina

## Alcance

Se añadió una pestaña independiente **Préstamos / Descuentos** dentro de **Control de Taller**. El módulo se integra con la nómina existente y conserva el historial de préstamos, abonos, pagos y saldos pendientes en Google Sheets.

La estructura añadida es funcional y reutiliza el lenguaje visual actual de Control de Taller. La referencia visual del usuario se empleó solamente para organizar la información en paneles y tarjetas, no para copiar el diseño.

## Funcionalidad

| Área | Comportamiento |
|---|---|
| Registro de préstamo | Selección de mecánico activo, fecha, monto, cuota sugerida y observaciones. |
| Liquidación | Muestra bruto pendiente antes de descuentos, descuentos aplicados y neto a pagar. |
| Aplicación de descuento | Permite seleccionar semana, mecánico y préstamo, usar la cuota sugerida o editar el monto del período. |
| Saldo pendiente | Calcula monto original menos abonos aplicados y muestra estado Pendiente o Pagado. |
| Historial | Conserva fecha, mecánico, semana, concepto, monto, préstamo asociado y observaciones. |
| Pago de nómina | Guarda bruto, descuentos y neto pagado en la hoja Pagos. |

## Reglas de seguridad

Los montos deben ser mayores que cero. La cuota sugerida no puede superar el monto original del préstamo. Un descuento asociado a un préstamo no puede superar su saldo pendiente ni el bruto disponible de la nómina para ese mecánico y semana. Un préstamo que ya tiene descuentos aplicados no puede eliminarse. Una cuota de un préstamo que ya está pagado no puede modificarse.

Antes de registrar un préstamo, aplicar un descuento o cerrar el pago de nómina se muestra una confirmación. Cada operación realiza una carga y un guardado del libro dentro de la misma operación lógica, respetando el adaptador remoto y la protección contra exceso de lecturas.

## Hojas de Google Sheets

Se añadieron dos pestañas a la estructura remota:

| Hoja | Columnas principales |
|---|---|
| `Prestamos` | ID, Fecha, Mecánico, Monto Original, Cuota Sugerida, Observaciones |
| `Descuentos Nomina` | ID, Fecha Aplicación, Mecánico, Semana, Monto, Concepto, Préstamo ID, Observaciones |

La hoja `Pagos` se amplió con `Total Descuentos` y `Neto Pagado`. En un archivo existente, el bootstrap amplía automáticamente los encabezados antiguos de `Pagos` cuando detecta la fila estándar anterior de siete columnas. Las doce pestañas anteriores se conservan y la estructura resultante pasa a catorce pestañas.

## Endpoints añadidos

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/control/api/prestamos/panel` | Devuelve préstamos, descuentos e información de nómina en una respuesta combinada. |
| `POST` | `/control/api/prestamo` | Registra un préstamo. |
| `PUT` | `/control/api/prestamo/<id>` | Actualiza la cuota sugerida de un préstamo pendiente. |
| `DELETE` | `/control/api/prestamo/<id>` | Elimina un préstamo sin abonos. |
| `POST` | `/control/api/nomina/descuento` | Aplica un descuento a una nómina y, opcionalmente, a un préstamo. |

La ruta existente `POST /control/api/nomina/pagar` ahora calcula y guarda `Total Descuentos` y `Neto Pagado`. Los descuentos históricos no se vuelven a restar si se registra un pago posterior de la misma semana; solamente se aplica la diferencia todavía pendiente.

## Validación ejecutada

Se ejecutaron las siguientes comprobaciones:

1. Compilación de `ControlTaller/app.py` y `storage.py`.
2. Bootstrap remoto con las hojas `Prestamos` y `Descuentos Nomina`.
3. Registro de un préstamo de 600 con cuota sugerida de 100.
4. Aplicación de un descuento de 100 y verificación de saldo restante de 500.
5. Rechazo de un descuento superior al saldo de nómina disponible.
6. Cálculo de bruto de 500, descuento de 100 y neto de 400.
7. Cierre de nómina con persistencia de bruto, descuentos y neto.
8. Verificación de que los descuentos no se aplican dos veces.
9. Verificación de la pestaña, formularios, KPIs, tablas y acciones del frontend.
10. Regresión completa de Control de Taller, Neveras, Peritaje, exportación e importación XLSX.

Resultado: **todas las pruebas pasaron**.

## Despliegue

Reemplazar el contenido del repositorio por el contenido del ZIP incremental y realizar un nuevo commit/redeploy en Vercel. No se requiere modificar las variables de entorno existentes. Al ejecutar `/api/health`, el sistema creará las dos nuevas pestañas y actualizará los encabezados de `Pagos` si todavía conserva el formato anterior.

El paquete no contiene credenciales, archivos XLSX locales, cachés de Python, archivos de depuración ni artefactos de pruebas.
