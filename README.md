# APPTALLER · Vene Autos

APPTALLER consolida los módulos de **Control de Taller**, **Control de Neveras** y **Peritaje Vehicular** en una única aplicación Flask apta para desplegarse en Vercel. El proyecto conserva los libros Excel como respaldo local de desarrollo, pero al configurar Google Sheets pasa a utilizar una única hoja de cálculo remota como almacenamiento compartido y persistente.

> La aplicación no incluye ninguna clave en el repositorio. La comunicación con Google se activa únicamente al configurar variables de entorno en el despliegue.

## Funcionalidades incluidas

| Área | Implementación |
| --- | --- |
| Navegación | Menú central con rutas `/control`, `/neveras` y `/peritaje` en el mismo dominio. |
| Persistencia | Adaptador híbrido: Google Sheets en producción cuando hay credenciales y XLSX local como modo de desarrollo/contingencia. |
| Datos iniciales | En la primera conexión a una hoja vacía, las pestañas de los tres Excel incluidos se cargan como semilla sin sobrescribir pestañas remotas ya existentes. |
| Respaldo global | La pantalla de inicio permite descargar `APPTALLER_respaldo.xlsx` con las pestañas de todos los módulos. |
| Restauración global | La pantalla de inicio permite subir un `.xlsx` o `.xlsm`; las pestañas presentes se restauran en la base remota o local. |
| Respaldo por módulo | Control de Taller, Neveras y Peritaje conservan su descarga individual de Excel. |
| Vercel | Punto de entrada `app.py`, dependencias en `requirements.txt` y configuración de función en `vercel.json`. |

## Arquitectura de datos

Las entidades se mantienen en una sola hoja de cálculo de Google Sheets, organizada por pestañas. La aplicación trata la primera fila de cada pestaña como encabezados, de forma compatible con los libros existentes.

| Módulo | Pestañas gestionadas |
| --- | --- |
| Control de Taller | `Mecanicos`, `Equipos`, `Trabajos`, `Gastos`, `Pagos`, `Herramientas` |
| Neveras | `Inventario`, `Ventas`, `Clientes` |
| Peritaje | `Peritajes` |

La cuenta de servicio debe tener acceso de **editor** solamente a esa hoja. Este diseño evita que los datos dependan del sistema de archivos efímero de una función de Vercel y permite consultar o editar la información desde Google Sheets cuando sea necesario.

## Configurar Google Sheets

La implementación usa una cuenta de servicio, que es la opción apropiada para un backend desplegado porque no requiere que un usuario inicie sesión para cada petición. Google documenta la habilitación de Sheets API y el uso de bibliotecas cliente para aplicaciones Python.[1]

| Paso | Acción necesaria |
| --- | --- |
| 1 | Crea una hoja de cálculo en Google Drive, por ejemplo `APPTALLER - Base de datos`. Copia el identificador de la URL situada entre `/d/` y `/edit`. |
| 2 | En Google Cloud Console crea o selecciona un proyecto, habilita **Google Sheets API** y crea una cuenta de servicio con una clave JSON. |
| 3 | Abre el archivo JSON, identifica el valor `client_email` y comparte la hoja de cálculo con ese correo como **Editor**. |
| 4 | Conserva el JSON fuera de GitHub. En Vercel crearás las variables descritas a continuación. |

Configura estas variables en los entornos **Production**, **Preview** y, si lo deseas, **Development** de Vercel. Las variables de entorno son valores externos al código que pueden diferir por entorno.[2]

| Variable | Valor |
| --- | --- |
| `GOOGLE_SHEETS_ID` | El identificador de la hoja creada en Google Drive. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | El contenido completo y válido, en una sola línea, del archivo JSON de la cuenta de servicio. |

Para probar con el archivo de credenciales solamente en tu computador, exporta sus valores antes de iniciar Flask. El archivo de clave no debe estar dentro del repositorio.

```bash
cd "APP TALLER"
export GOOGLE_SHEETS_ID="ID_DE_TU_HOJA"
export GOOGLE_SERVICE_ACCOUNT_FILE="/ruta/segura/google-service-account.json"
python3 app.py
```

Al abrir la aplicación por primera vez con una hoja nueva, se crearán y cargarán las pestañas de datos existentes. En los siguientes arranques se preservará el contenido remoto.

## Ejecución local

Instala las dependencias y arranca el punto de entrada unificado.

```bash
cd "APP TALLER"
python3 -m pip install -r requirements.txt
python3 app.py
```

Después abre `http://127.0.0.1:8000`. Sin las variables de Google, el sistema utiliza los Excel incluidos de forma local; este modo facilita pruebas sin afectar los datos de producción.

## Publicación en GitHub y Vercel

La aplicación cumple el patrón de Vercel para Flask: expone una instancia `app` en un archivo de entrada compatible. Vercel también recomienda utilizar el directorio `public/` para estáticos de funciones Flask; en este proyecto los estáticos se entregan desde cada módulo Flask por compatibilidad con las tres interfaces existentes.[3]

| Etapa | Acción |
| --- | --- |
| GitHub | Crea un repositorio privado o público, sube este directorio y confirma que `.env`, claves JSON y archivos temporales no aparezcan en el historial. |
| Vercel | Importa el repositorio, conserva el directorio raíz donde se encuentra `app.py` y deja que Vercel instale `requirements.txt`. |
| Variables | Crea `GOOGLE_SHEETS_ID` y `GOOGLE_SERVICE_ACCOUNT_JSON` en los entornos que vayas a desplegar. |
| Despliegue | Lanza el deploy y comprueba `/api/health`. Debe responder `{"ok": true, "backend": "google_sheets", ...}`. |
| Operación | Descarga un respaldo antes de una restauración. Al restaurar, confirma el aviso de la aplicación y luego comprueba los tres módulos. |

Vercel reconoce una instancia Flask llamada `app` en puntos de entrada como `app.py`, y permite configurar el tiempo máximo de la función mediante `vercel.json`.[3]

## Estrategias de respaldo

| Enfoque | Uso recomendado | Ventajas | Consideraciones |
| --- | --- | --- | --- |
| **Google Sheets + XLSX global** — implementado | Operación diaria del taller | Datos compartidos, consulta manual en Sheets y restauración completa desde la aplicación. | Requiere una cuenta de servicio y una única configuración inicial. |
| **Solo XLSX local** | Pruebas aisladas o contingencia local | No requiere credenciales ni conexión externa. | No es adecuado para Vercel porque el almacenamiento local de funciones no es persistente. |

La segunda estrategia permanece disponible de forma automática cuando no existen variables de Google, pero el despliegue de producción debe usar la primera.

## Validación realizada

Se han verificado de forma local los siguientes flujos: carga del menú, disponibilidad de los tres módulos, lectura de sus API, descarga del respaldo global XLSX y carga de ese mismo respaldo. La prueba de humo finalizó correctamente con las diez pestañas de datos restauradas.

## Seguridad y mantenimiento

No subas cuentas de servicio, archivos `.env` ni credenciales de Vercel al repositorio. La descarga de un respaldo contiene los datos operativos de los tres módulos, por lo que debe almacenarse en una ubicación controlada. Antes de cargar un archivo de respaldo, descarga la versión actual como punto de retorno.

## Referencias

[1] [Google Sheets API: Python quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)

[2] [Vercel: Environment Variables](https://vercel.com/docs/environment-variables)

[3] [Vercel: Deploy a Flask app](https://vercel.com/docs/frameworks/backend/flask)
