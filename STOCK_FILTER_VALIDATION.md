# Validación: productos con existencias en Nueva venta

## Cambio aplicado

En **Neveras → Nueva venta**, el selector de productos ahora muestra únicamente los productos cuyo campo `stockAct` sea mayor que cero. Los productos agotados, con existencia cero o negativa, no se ofrecen para seleccionar.

El filtro se aplica cada vez que se abre o se redibuja el formulario. Por lo tanto, después de una venta o de un ajuste de inventario, la lista se actualiza con el estado más reciente que ya tiene la interfaz.

## Protección adicional

La interfaz valida que la cantidad solicitada no supere la existencia disponible. Además, el endpoint `/neveras/api/nueva-venta` vuelve a comprobar el inventario usando el mismo libro cargado antes de escribir. Esta segunda validación evita vender productos agotados si el formulario llevaba abierto mientras otro usuario o proceso modificaba el stock.

Cuando se intenta vender un producto agotado o una cantidad superior a la disponible, el backend devuelve HTTP 409 con un mensaje de existencias insuficientes y no guarda ninguna fila de venta.

## Validaciones ejecutadas

| Prueba | Resultado |
|---|---|
| Producto con stock cero | Excluido del selector y venta rechazada |
| Producto con stock disponible | Visible y venta permitida dentro del límite |
| Venta que deja stock en cero | Correcta; el producto deja de estar disponible para ventas posteriores |
| Venta posterior sin stock | Rechazada con HTTP 409 |
| Varias líneas del mismo producto | Stock acumulado validado antes de guardar |
| Sintaxis Python | Correcta con `py_compile` |
| Sintaxis JavaScript | Correcta con `node --check` |
| Regresión general | Correcta en Control de Taller, Peritaje, Ventas, Deudas y respaldo XLSX |

Pruebas utilizadas:

- `test_stock_filter.py`
- `test_inventario_crud.py`
- `test_clean_remote.py`

Las pruebas utilizan el simulador remoto existente y no modifican la hoja de Google Sheets de producción.

## Despliegue

Reemplaza el contenido del repositorio con el ZIP incremental, conserva las variables actuales de Vercel y realiza un nuevo commit/redeploy. No es necesario modificar las pestañas ni las variables de Google Sheets.
