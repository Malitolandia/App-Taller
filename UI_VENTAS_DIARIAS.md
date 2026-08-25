# Actualización visual y Ventas diarias

## Alcance

Se aplicó a **ControlTaller** y **Peritaje** la identidad visual que ya utilizaba **Control Neveras / Tienda**, sin modificar sus rutas, contratos API ni lógica de negocio. El menú principal ya utilizaba esta misma línea visual y se conserva como punto de entrada común.

| Elemento | Tratamiento aplicado |
|---|---|
| Fondo y superficies | Fondo oscuro `#0a0c10`, tarjetas `#111318` y superficies secundarias `#181c24` |
| Tipografía | `Space Grotesk` para la interfaz y `Bebas Neue` para títulos y valores destacados |
| Acentos | Verde para acciones principales, azul para información, amarillo para advertencias y rojo para pendientes o errores |
| Controles | Bordes oscuros, radios consistentes, estados de foco visibles y transiciones suaves |
| Tablas y tarjetas | Encabezados sobre superficie secundaria, divisores sutiles y estados con colores semánticos |
| Adaptación móvil | Menús, formularios y controles reorganizados para pantallas estrechas |

Las reglas se añadieron como una capa de tema al final de las plantillas existentes. Esto permite conservar las clases, eventos y fragmentos HTML que ya utiliza cada módulo.

## Ventas de Neveras

La pestaña **Ventas** ahora inicia siempre con la fecha local actual seleccionada. El calendario permite escoger otro día y actualizar la tabla sin realizar una nueva carga de Google Sheets: el filtrado se ejecuta sobre los datos que ya recibió la interfaz.

La tabla se ordena por fecha y hora en orden descendente. Por tanto, la primera fila visible corresponde a la venta más reciente del día seleccionado; en caso de empate se utiliza el número de venta como desempate descendente.

El botón **Hoy** restablece la fecha actual. El botón **Solo pendientes** y la búsqueda por cliente se aplican después del filtro de fecha. Si no existen ventas para el día seleccionado, se muestra un mensaje explícito y la tabla queda vacía.

| Comportamiento | Resultado |
|---|---|
| Entrada inicial | Fecha del día actual y título `Ventas del día` |
| Cambio de fecha | Muestra únicamente las ventas de la fecha seleccionada |
| Orden | Más reciente primero, usando fecha, hora y número de venta |
| Buscar cliente | Filtra las ventas del día seleccionado |
| Solo pendientes | Conserva únicamente ventas con saldo pendiente |
| Restablecer | `Hoy` vuelve a la fecha local actual; limpiar búsqueda conserva esa fecha |
| Indicadores | Total, cobrado y pendiente se calculan sobre las filas visibles |

## Validación realizada

La regresión completa disponible pasó correctamente, incluyendo persistencia remota simulada, cobro parcial, deudas, nómina, gastos, inventario, filtros de stock, caché, esquema, importación/exportación y rutas del dispatcher. También pasaron la prueba específica `test_ventas_diarias.py`, la compilación Python, la comprobación JavaScript de `Neveras/app.js` y la comprobación de JavaScript inline.

La revisión visual local confirmó que el menú, Neveras, ControlTaller y Peritaje cargan con el tema oscuro compartido. La pantalla local puede indicar que Google Sheets no está disponible cuando se usan credenciales de prueba; esto no afecta la validación del marcado, estilos ni comportamiento del filtro.

## Archivos principales modificados

- `ControlTaller/templates/index.html`: tema visual compartido.
- `Peritaje/templates/index.html`: tema visual compartido.
- `Neveras/dashboard_neveras.html`: calendario, botón Hoy y estructura del filtro.
- `Neveras/styles.css`: estilos de la barra de filtros y adaptación móvil.
- `Neveras/app.js`: fecha inicial, filtro diario y orden descendente.
- `test_ventas_diarias.py`: regresión estática de la funcionalidad.
