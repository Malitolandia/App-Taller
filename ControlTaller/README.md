# VENE AUTOS · Control de Nómina y Gastos

Sistema local (Flask + Excel) para llevar la nómina semanal de los mecánicos
(pagada como % de la mano de obra, editable) y los gastos diarios del taller
(gasolina, repuestos, almuerzos, etc.).

## Instalación

### 1. Instalar Python (si no lo tienes)
https://www.python.org/downloads/ — marca "Add Python to PATH".

### 2. Instalar dependencias
```
pip install -r requirements.txt
```

### 3. Iniciar el servidor
```
python app.py
```
O simplemente haz doble clic en **Iniciar_ControlTaller.bat**.

### 4. Abrir en el navegador
http://localhost:5002

### 5. (Opcional) Crear acceso directo en el Escritorio
Haz doble clic en **Crear_Acceso_Directo.bat**. Esto crea un ícono
"Vene Autos - Nómina y Gastos" en tu Escritorio (con el logo de la empresa)
que abre el sistema directamente, sin tener que entrar a la carpeta.
Solo necesitas hacerlo una vez.

---

## Cómo funciona

### Mecánicos
- Registra cada mecánico con su **% de comisión sobre la mano de obra**
  (por defecto 50%, pero se puede editar en cualquier momento por mecánico,
  directamente desde su tarjeta).
- Puedes desactivar un mecánico sin borrar su historial.

### Trabajos / Nómina
- Cada vez que un mecánico hace un trabajo, regístralo con el **monto de
  mano de obra**. El sistema calcula automáticamente cuánto le corresponde
  al mecánico según su % (también editable en el momento del registro).
- El sistema agrupa los trabajos por **semana ISO** (Lunes a Domingo).
- En "Resumen de Nómina" ves, por semana, cuánto se le debe a cada mecánico.
  Al hacer clic en **Pagar semana**, todos los trabajos pendientes de esa
  semana para ese mecánico quedan marcados como pagados y se guarda un
  registro en el historial de pagos.

### Gastos
- Registra gastos diarios por categoría (Gasolina, Repuestos, Almuerzos,
  Herramientas, Servicios, Otros, o cualquier categoría nueva que escribas).
- Puedes filtrar por fecha y categoría, y ver el total del día y del mes
  en la pestaña **Resumen**.

### Excel
- Todo se guarda automáticamente en `data/taller_control.xlsx`, con 4 hojas:
  `Mecanicos`, `Trabajos`, `Gastos` y `Pagos` (historial de nómina pagada).
- Botón **Descargar Excel** en la barra superior para exportar el archivo
  completo en cualquier momento.

---

## Archivos del proyecto
```
taller_control/
├── app.py                        → Servidor Flask (lógica principal)
├── requirements.txt              → Dependencias
├── Iniciar_ControlTaller.bat     → Inicia el servidor
├── Crear_Acceso_Directo.bat      → Crea el ícono en el Escritorio (una sola vez)
├── templates/
│   └── index.html                → Interfaz web
├── static/
│   ├── logo.png                  → Logo de la empresa
│   └── icon.ico                  → Ícono para el acceso directo
└── data/
    └── taller_control.xlsx       → Base de datos Excel (se crea automáticamente)
```

**Nota:** este proyecto corre en el puerto **5002** para no chocar con el
Sistema de Peritaje (puerto 5001).
