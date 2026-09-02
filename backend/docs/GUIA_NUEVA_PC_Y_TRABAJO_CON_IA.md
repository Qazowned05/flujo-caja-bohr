# Continuidad en otra PC y trabajo con IA

Esta guía permite retomar el proyecto desde otra computadora sin recrear la infraestructura de producción. Complementa `GUIA_OPERACION_ESCALADO_Y_GITHUB.md`, que contiene el detalle de operación y despliegue.

## 1. Estado actual de producción

| Recurso | Valor |
| --- | --- |
| Proyecto GCP | `flujo-caja-enfocadosac` |
| Región | `us-central1` |
| API Cloud Run | `flujo-caja-api` |
| URL API | `https://flujo-caja-api-357419791119.us-central1.run.app/api/v1` |
| Job de migraciones | `flujo-caja-migrate` |
| Cloud SQL | `flujo-caja-enfocadosac:us-central1:flujo-caja-db` |
| Base de datos | `flujo_caja` |
| Artifact Registry | `flujo-caja-images` |
| Firebase Hosting | `https://flujo-caja-enfocadosac.web.app` |
| Repositorio GitHub | `https://github.com/Qazowned05/flujo-caja-enfocado-sac` |
| Última imagen desplegada | `1.0.23` |
| Última revisión Cloud Run | `flujo-caja-api-00025-cfv` |

No crees otra instancia de Cloud SQL, otro servicio Cloud Run ni otros secretos: los recursos anteriores ya existen y deben reutilizarse.

## 2. Repositorio GitHub

El repositorio remoto ya existe en `https://github.com/Qazowned05/flujo-caja-enfocado-sac`. GitHub es la fuente de código para todas las computadoras y subir código no modifica producción por sí solo.

Para comprobar que la copia local está vinculada y actualizada:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI
git remote -v
git pull --ff-only origin main
git status
```

Antes de crear un commit, revisa que `git status` no incluya `.env`, contraseñas, respaldos `.dump`, `.sql`, `node_modules` ni `venv`.

## 3. Programas requeridos en la nueva PC

Instala y verifica lo siguiente:

| Herramienta | Uso | Comprobación |
| --- | --- | --- |
| Git | Obtener y versionar el código | `git --version` |
| Python 3.12 o superior | Backend FastAPI | `py --version` |
| Node.js 20 o superior | Frontend React/Vite | `node --version` |
| Google Cloud CLI | Cloud Run, Cloud Build y Cloud SQL | `gcloud version` |
| Firebase CLI | Firebase Hosting | `firebase --version` |
| Cliente de IA, por ejemplo OpenCode | Delegar cambios de código | Sigue su instalador oficial |

Instala Firebase CLI con Node.js si aún no está disponible:

```powershell
npm install -g firebase-tools
```

## 4. Descargar y preparar el proyecto

En la nueva PC:

```powershell
cd $HOME\Desktop
git clone https://github.com/Qazowned05/flujo-caja-enfocado-sac.git FLUJ_CAJA_FASTAPI
cd FLUJ_CAJA_FASTAPI
```

### Backend

```powershell
cd backend
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Para desarrollo local, crea `backend/.env` solo con credenciales locales. Nunca copies ni descargues el `DATABASE_URL` ni `SECRET_KEY` de producción a este archivo.

Ejemplo local:

```dotenv
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://postgres:TU_CLAVE_LOCAL@localhost:5432/flujo_caja
SECRET_KEY=una-clave-local-larga-y-distinta
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
```

### Frontend

```powershell
cd ..\frontend
npm ci
```

`frontend/.env` debe apuntar al backend local durante desarrollo:

```dotenv
VITE_API_URL=http://localhost:8000/api/v1
```

El archivo `frontend/.env.production` ya contiene la URL pública de producción. No lo reemplaces por una URL local.

## 5. Recuperar acceso a GCP y Firebase

Inicia sesión con la misma cuenta Google que tenga permisos sobre el proyecto:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project flujo-caja-enfocadosac
gcloud config set run/region us-central1
gcloud auth list
gcloud config get-value project

firebase login
firebase projects:list
```

La cuenta necesita permisos para Cloud Run, Cloud Build, Artifact Registry, Secret Manager y Cloud SQL. Si `gcloud` responde `PERMISSION_DENIED`, un administrador del proyecto debe conceder los roles necesarios; no intentes resolverlo creando recursos paralelos.

Comprueba que ves los recursos existentes:

```powershell
gcloud run services describe flujo-caja-api --region us-central1
gcloud run jobs describe flujo-caja-migrate --region us-central1
gcloud sql instances describe flujo-caja-db
```

## 6. Ejecutar localmente y validar

Abre dos terminales PowerShell.

Terminal 1, backend:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Terminal 2, frontend:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\frontend
npm run dev
```

Antes de delegar o desplegar cambios, ejecuta:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe scripts/export_openapi.py

cd ..\frontend
npx openapi-typescript openapi.json -o src/client/schema.ts
npm run build
```

Si cambió una ruta, schema o respuesta del backend, siempre exporta OpenAPI y regenera `frontend/src/client/schema.ts` antes de compilar el frontend.

### Importación masiva Excel

La pantalla **Importar masivo** trabaja exclusivamente con archivos `.xlsx`. Descarga primero la plantilla desde la misma pantalla y completa solo la hoja `Movimientos`.

- Para movimientos reales, usa las columnas de la hoja `Movimientos`, incluido `n_operacion`.
- Para proyecciones, selecciona `Proyecciones`; la plantilla usa las columnas aplicables y exige `actividad`, `concepto` y `tipo`.
- Para un movimiento múltiple, escribe dos o más números de operación separados por comas en una sola celda de `n_operacion`.
- Las hojas `Tipificaciones`, `Sucursales` y `Vendedores` son catálogos de referencia para copiar valores. No se procesan como movimientos.
- Excel puede contener fechas y montos como valores de celda normales; el sistema también admite las fechas indicadas en la plantilla.

La API correspondiente es `GET /api/v1/imports/plantilla.xlsx` para descargar la plantilla y `POST /api/v1/imports/excel` para procesarla. Ambas requieren una sesión autenticada en la aplicación.

## 7. Flujo recomendado con IA

1. Abre la carpeta raíz `FLUJ_CAJA_FASTAPI` en tu cliente de IA.
2. Indica el objetivo de forma concreta, por ejemplo: `Agrega un filtro por banco en transacciones y prueba backend y frontend.`
3. Pide explícitamente que revise primero el código existente, agregue pruebas y no cambie secretos ni infraestructura sin autorización.
4. Revisa los archivos modificados y ejecuta las validaciones de la sección 6.
5. Prueba el cambio localmente antes de autorizar un despliegue.
6. Confirma que no se hayan añadido secretos:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI
git status
git diff --check
```

7. Crea una rama por cambio y publícala:

```powershell
git checkout -b feature/nombre-corto
git add .
git commit -m "Describe el cambio"
git push -u origin feature/nombre-corto
```

No delegues a una IA acciones destructivas contra Cloud SQL, como `DROP`, `TRUNCATE`, `DELETE` sin filtro, ni rotación de secretos, salvo que indiques exactamente qué debe ocurrir y exista un respaldo.

## 8. Desplegar cambios manualmente

Define estas variables en cada nueva sesión PowerShell:

```powershell
$PROJECT_ID = "flujo-caja-enfocadosac"
$REGION = "us-central1"
$REPOSITORY = "flujo-caja-images"
$API_SERVICE = "flujo-caja-api"
$VERSION = "1.0.24"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:$VERSION"
```

Usa una etiqueta nueva en cada despliegue; no reutilices una versión anterior.

### Solo frontend

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\frontend
npm ci
npm run build
firebase deploy --only hosting
```

### Backend sin migración

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
gcloud builds submit --tag $IMAGE .
gcloud run deploy $API_SERVICE --image $IMAGE --region $REGION --port 8000
```

### Backend con migración Alembic

Haz un respaldo de Cloud SQL antes de migraciones que puedan afectar datos. Luego:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
gcloud builds submit --tag $IMAGE .
gcloud run jobs update flujo-caja-migrate --image $IMAGE --region $REGION
gcloud run jobs execute flujo-caja-migrate --region $REGION --wait
gcloud run deploy $API_SERVICE --image $IMAGE --region $REGION --port 8000
```

Si el Job falla, no despliegues la imagen al servicio. Consulta la ejecución:

```powershell
gcloud run jobs executions list --job flujo-caja-migrate --region us-central1 --limit 5
```

Si hubo cambios en backend y frontend, despliega primero la API y después Firebase Hosting.

## 9. Verificación posterior

```powershell
Invoke-WebRequest "https://flujo-caja-api-357419791119.us-central1.run.app/api/v1/health" -UseBasicParsing
```

La respuesta esperada es:

```json
{"status":"ok"}
```

Después abre `https://flujo-caja-enfocadosac.web.app`, inicia sesión y prueba la pantalla afectada. Ante una regresión, revierte el frontend desde Firebase Hosting o envía el tráfico de Cloud Run a una revisión estable. No reviertas migraciones de producción sin probar la recuperación en una copia de la base.
