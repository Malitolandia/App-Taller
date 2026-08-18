# Publicación manual de APPTALLER

## 1. Subir el contenido a GitHub

El repositorio debe contener directamente `app.py`, `storage.py`, `api/`, `ControlTaller/`, `Neveras/`, `Peritaje/`, `requirements.txt` y `vercel.json`. No subas una carpeta adicional que envuelva todo el proyecto.

Antes de subirlo, confirma que no existan archivos `.env`, JSON de cuentas de servicio, archivos dentro de `ControlTaller/data/` o `Peritaje/data/`, cachés `__pycache__` ni respaldos operativos. El archivo `.gitignore` incluido ya excluye esos elementos.

Si vas a utilizar la interfaz web de GitHub, abre `https://github.com/Malitolandia/App-Taller`, selecciona **Add file → Upload files**, arrastra el contenido del directorio del proyecto y confirma el commit en la rama `main`.

Si prefieres una terminal local, una forma segura es clonar primero el repositorio existente, copiar dentro de él el contenido de este proyecto y crear un commit:

```bash
git clone https://github.com/Malitolandia/App-Taller.git
cd App-Taller
# Copia aquí el contenido de APPTALLER_corregido_google_sheets/, no la carpeta envolvente.
git add .
git commit -m "Corregir persistencia remota y despliegue unificado"
git push origin main
```

## 2. Redeploy en Vercel

Importa `Malitolandia/App-Taller` en Vercel. Usa como **Root Directory** la carpeta donde estén `app.py` y `vercel.json`; normalmente será la raíz del repositorio. No cambies el nombre de las variables de entorno.

Crea o conserva estas dos variables en **Production** y, si utilizas despliegues Preview, también en **Preview**:

| Variable | Valor |
| --- | --- |
| `GOOGLE_SHEETS_ID` | `13IWMulcPLCPkM0GZOSjSI5N-hMkUh2MXiHIb7vmDUEY` o el ID de la hoja que realmente utilizarás. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | El contenido completo del JSON de la cuenta de servicio, pegado como un único valor. No lo publiques en GitHub. |

La cuenta de servicio debe tener permiso **Editor** sobre la hoja de cálculo. Después de guardar las variables, ejecuta **Redeploy** utilizando el commit que contiene esta versión corregida.

## 3. Comprobación posterior al deploy

Sustituye `TU_URL_VERCEL` por la URL vigente del proyecto y abre:

```text
https://TU_URL_VERCEL/api/health
https://TU_URL_VERCEL/control/api/mecanicos
https://TU_URL_VERCEL/neveras/api/datos
https://TU_URL_VERCEL/peritaje/api/peritajes
```

La primera ruta debe devolver `ok: true`, `backend: "google_sheets"` y `remote_connected: true`. Las otras tres deben devolver JSON, aunque las listas estén inicialmente vacías.

A continuación registra una fila de prueba en Control de Taller, una venta de prueba en Neveras y un peritaje de prueba. Recarga cada módulo y confirma que el registro permanece. Finalmente revisa en Google Sheets las pestañas `Mecanicos`, `Ventas` y `Peritajes`.

## 4. Respaldo y restauración

Desde el menú principal descarga el archivo `APPTALLER_respaldo.xlsx` antes de una restauración. Para restaurar, selecciona un archivo `.xlsx` o `.xlsm` y confirma la operación. La ruta global es:

```text
https://TU_URL_VERCEL/api/db/export
```

La importación reemplaza el contenido de las pestañas incluidas en el respaldo y conserva la organización integrada en una sola hoja de cálculo con doce pestañas.

## 5. Si `/api/health` falla

Comprueba primero que `GOOGLE_SHEETS_ID` sea el ID situado entre `/d/` y `/edit` en la URL de Google Sheets, que el JSON sea válido y que `client_email` tenga acceso de editor a esa hoja. Luego vuelve a guardar las variables y ejecuta un redeploy; cambiar solo el código sin redeploy no actualiza las variables del despliegue anterior.
