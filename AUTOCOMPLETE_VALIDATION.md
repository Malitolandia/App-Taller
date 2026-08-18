# Sugerencias de productos en Neveras

## Funcionalidad

El formulario **Nuevo Producto** de Neveras ahora utiliza un campo de texto con `datalist`. Al escribir, el navegador sugiere los productos que ya existen en la pestaña `Inventario`, utilizando el inventario que la aplicación ya cargó desde Google Sheets.

La sugerencia muestra el nombre del producto y una referencia de precio y stock cuando el navegador lo admite. El campo sigue siendo editable: si el nombre no existe, se puede escribir normalmente y el flujo de alta lo valida y lo guarda como producto nuevo.

## Diseño de bajo riesgo

La funcionalidad no añade llamadas a Google Sheets. La lista se reconstruye desde `D.inventario` cada vez que se renderiza la aplicación, por lo que se actualiza después de una carga inicial, una venta o la creación de un nuevo producto. No se modificaron los endpoints de ventas ni de pagos.

## Verificaciones

| Verificación | Resultado |
| --- | --- |
| La página `/neveras/` carga correctamente | HTTP 200 |
| Existe el botón `+ Nuevo Producto` | Correcto |
| El campo `p-nombre` referencia `lista-productos` | Correcto |
| La lista se actualiza desde `D.inventario` | Correcto por inspección de código |
| Se puede escribir un producto nuevo | Conservado; el campo no es `select` obligatorio |
| Alta de producto | Correcta |
| Lectura posterior en inventario | Correcta |
| Venta del producto recién creado | Correcta |
| Duplicado | Rechazado con HTTP 409 |
| Datos inválidos | Rechazados con HTTP 400 |
| Regresión de ControlTaller, Peritaje y respaldo | Correcta en la prueba remota existente |
