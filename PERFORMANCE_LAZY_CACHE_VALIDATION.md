# Validación de rendimiento: carga diferida y caché segmentado

## Alcance

Esta entrega optimiza Control de Taller sin cambiar Google Sheets como almacenamiento principal. Las pestañas de Nómina y Deudas del Taller se cargan bajo demanda, únicamente cuando el usuario abre el panel correspondiente. Las lecturas se almacenan temporalmente en un caché de servidor por conjunto de pestañas y en un caché breve del navegador.

## Cambios realizados

`storage.py` conserva el caché completo para operaciones que lo necesitan y añade un caché segmentado por alcance. El alcance de Nómina utiliza las pestañas `Trabajos` y `Descuentos Nomina`. El panel de Préstamos utiliza `Trabajos`, `Prestamos` y `Descuentos Nomina`. El panel de Deudas utiliza `Deudas Taller`, `Fondos Deudas` y `Pagos Deudas`. Las operaciones de escritura invalidan el caché y lo vuelven a sembrar con la instantánea confirmada, evitando una lectura remota inmediata adicional.

El frontend utiliza un caché breve de ocho segundos para evitar solicitudes duplicadas al cambiar repetidamente entre las pestañas. Después de registrar un pago, préstamo, descuento, aporte o modificación de deuda, se invalida solamente el módulo afectado. Nómina y Deudas ya no se consultan durante el arranque inicial de Control de Taller.

## Métricas verificadas con simulador remoto

| Escenario | Lecturas solicitadas |
|---|---:|
| Carga completa de la aplicación | 17 pestañas |
| Apertura del panel de Nómina | 2 pestañas |
| Lectura repetida dentro del TTL | 0 llamadas adicionales |
| Escritura seguida de lectura del mismo alcance | 0 llamadas adicionales; se usa la instantánea confirmada |

La prueba confirmó que una carga segmentada solicita `Trabajos` y `Descuentos Nomina` en lugar de las 17 pestañas. El resultado fue `full_read_ranges: 17`, `scoped_read_ranges: 2`, `batchGet_calls_after_cache: 2` y `batchGet_calls_after_save_refresh: 2`.

Estas cifras miden solicitudes y comportamiento de caché en el simulador. La mejora de tiempo real en Vercel depende de la latencia de Google Sheets, el estado frío o caliente de la función y el volumen de datos. La arquitectura reduce el trabajo remoto y el procesamiento local, pero no se presenta como un tiempo fijo garantizado.

## Reglas de frescura

El caché de servidor tiene un TTL de diez segundos. El caché del navegador para paneles tiene un TTL de ocho segundos. Una escritura exitosa invalida el módulo correspondiente y actualiza el panel con la respuesta confirmada. Si Google Sheets responde con un límite temporal y existe una instantánea válida, el adaptador puede reutilizarla como fallback recuperable.

## Validación funcional

Pasaron las pruebas de caché y carga diferida, sintaxis Python, sintaxis JavaScript, Nómina y préstamos, Deudas del Taller y sus balances, frecuencia semanal, Inventario CRUD, filtro de productos con existencias, bootstrap del esquema remoto y regresión principal de Control de Taller, Neveras, Peritaje y respaldo XLSX.

## Despliegue

La entrega no requiere nuevas variables de entorno ni cambios en las hojas de Google Sheets. Se debe reemplazar el código del repositorio por el ZIP de esta entrega y realizar un nuevo commit y redeploy en Vercel.
