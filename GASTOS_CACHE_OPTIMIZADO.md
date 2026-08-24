# Gastos y caché optimizado

## Gastos

La ruta de Gastos muestra por defecto únicamente los registros de la fecha actual. El backend aplica hoy cuando no recibe filtros y usa solo la pestaña `Gastos`, por lo que no necesita cargar el libro completo.

El histórico se solicita de forma explícita con `historico=1`, mediante la acción **Ver todo**. También se conservan los filtros `desde` y `hasta` para consultar rangos concretos. La interfaz inicia con `desde` y `hasta` iguales a la fecha actual y ofrece una acción separada para volver al día de hoy.

## Política de caché

El backend mantiene caché segmentado por conjunto de pestañas durante diez minutos. Una lectura de una o varias pestañas puede reutilizar un snapshot fresco que ya contenga esas pestañas, incluso si fue obtenido por una carga superconjunta. Las lecturas concurrentes quedan protegidas por bloqueo para evitar batchGet duplicados durante un cache miss.

El caché se invalida inmediatamente después de escrituras confirmadas, importaciones y operaciones que cambian las pestañas. Después de guardar, la respuesta escrita se coloca directamente en el segmento correspondiente para evitar una lectura inmediata redundante.

En el frontend, las respuestas GET se reutilizan durante la sesión de la página. Cambiar de pestaña no vuelve a solicitar datos que ya fueron cargados. Las operaciones de crear, editar, eliminar, pagar, importar o ajustar inventario invalidan los segmentos afectados y fuerzan una lectura fresca solo cuando el cambio fue confirmado. La actualización manual sigue disponible para reflejar cambios realizados externamente en Google Sheets.

## Reducción de solicitudes

Las rutas de ControlTaller, Neveras y Peritaje usan scopes mínimos. Por ejemplo, Gastos consulta únicamente `Gastos`, Peritaje únicamente `Peritajes`, y las operaciones de Neveras que necesitan Inventario y Ventas comparten una sola carga parcial. El bootstrap inicial del esquema puede realizar una consulta de encabezados de todas las pestañas una vez por proceso; esto es necesario para verificar la estructura remota y no se repite mientras el proceso permanezca activo.

## Resultado funcional

La vista normal de Gastos es diaria y ligera. El histórico no se descarga por accidente al abrir la pestaña. Los datos recién modificados desde la aplicación aparecen inmediatamente después de la confirmación; los cambios hechos directamente en Google Sheets se reflejan mediante la actualización manual o cuando vence el TTL del caché remoto.

## Validación

Se verificaron el filtro diario predeterminado, los rangos históricos explícitos, la reutilización del caché, la invalidación tras escrituras, los scopes parciales, las tres aplicaciones integradas, la importación/exportación XLSX y la sintaxis Python/JavaScript.

> Nota: subir el paquete a GitHub y hacer redeploy en Vercel para que estas mejoras queden activas en producción.

