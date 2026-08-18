# VENE AUTOS · Sistema de Peritaje Vehicular

## Instalación

### 1. Instalar Python (si no lo tienes)
Descargar desde: https://www.python.org/downloads/

### 2. Instalar dependencias
Abre una terminal en esta carpeta y ejecuta:
```
pip install -r requirements.txt
```

### 3. Iniciar el servidor
```
python app.py
```

### 4. Abrir en el navegador
Ve a: **http://localhost:5000**

---

## Uso

### Nuevo Peritaje
1. Completa los datos del cliente y vehículo
2. Marca el estado de cada componente (Bueno / Regular / Malo / No aplica)
3. Agrega observaciones por ítem si deseas
4. Haz clic en **Guardar Peritaje** o **Guardar y Exportar PDF**

### Historial
- Consulta todos los peritajes guardados
- Busca por cliente, placa o marca
- Exporta cualquier peritaje en PDF

### Excel
- El botón **Descargar Excel** exporta todos los peritajes en formato .xlsx
- Los datos se guardan automáticamente en `data/peritajes.xlsx`

---

## Archivos del proyecto
```
veneautos/
├── app.py              → Servidor Flask (lógica principal)
├── requirements.txt    → Dependencias
├── templates/
│   └── index.html      → Interfaz web
├── static/
│   └── logo.png        → Logo de la empresa
└── data/
    └── peritajes.xlsx  → Base de datos Excel (se crea automáticamente)
```
