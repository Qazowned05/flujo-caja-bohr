# Guia Completa de Despliegue en GCP

Esta guia publica el proyecto en produccion con esta arquitectura:

- API FastAPI: Cloud Run.
- Base de datos PostgreSQL: Cloud SQL.
- Secretos: Secret Manager.
- Frontend React/Vite: Firebase Hosting.
- Imagenes Docker: Artifact Registry.
- Migraciones: Cloud Run Job, ejecutado antes de cada despliegue del backend.

No se necesita modificar el codigo para usar Cloud SQL. El backend ya utiliza `DATABASE_URL`.

## 0. Antes de empezar

### Datos que debes definir

Reemplaza estos valores en todos los comandos:

| Variable | Ejemplo | Descripcion |
| --- | --- | --- |
| `PROJECT_ID` | `flujo-caja-prod-123456` | ID del proyecto GCP, no el nombre visible. |
| `REGION` | `us-central1` | Region para Cloud Run, Cloud SQL y Artifact Registry. |
| `DB_INSTANCE` | `flujo-caja-db` | Nombre de la instancia Cloud SQL. |
| `DB_NAME` | `flujo_caja` | Nombre de la base de datos. |
| `DB_USER` | `flujo_caja_app` | Usuario exclusivo de la aplicacion. |
| `API_SERVICE` | `flujo-caja-api` | Nombre del servicio Cloud Run. |

Usa una sola region para todos los recursos. Esto reduce latencia y costos de trafico entre Cloud Run y Cloud SQL.

### Requisitos locales

1. Una cuenta Google con permisos de propietario o, como minimo, permisos para Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Cloud Build e IAM.
2. Facturacion habilitada en el proyecto GCP.
3. Google Cloud CLI instalado: <https://cloud.google.com/sdk/docs/install>.
4. Node.js 20 o superior instalado para publicar el frontend.
5. El backend debe tener sus pruebas locales correctas antes del despliegue.

Comprueba las herramientas en PowerShell:

```powershell
gcloud version
node --version
npm --version
```

### Proteccion de secretos

No subas ni compartas estos archivos:

- `backend/.env`
- `frontend/.env`
- respaldos `.sql` o `.dump`

El archivo `backend/.dockerignore` ya excluye `.env`, entornos virtuales, pruebas y caches para que no se copien en la imagen de produccion.

Usa una contraseña nueva para Cloud SQL y una clave JWT nueva para `SECRET_KEY`. No reutilices secretos locales.

## 1. Crear y configurar el proyecto GCP

1. Entra en <https://console.cloud.google.com/>.
2. Crea un proyecto nuevo o selecciona el proyecto destinado a produccion.
3. Habilita la facturacion en `Facturacion`.
4. Abre PowerShell y autentica Google Cloud CLI:

```powershell
gcloud auth login
gcloud auth application-default login
```

Define las variables de la sesion. Cambia solo la primera linea por tu proyecto:

```powershell
$PROJECT_ID = "REEMPLAZAR-PROJECT-ID"
$REGION = "us-central1"
$DB_INSTANCE = "flujo-caja-db"
$DB_NAME = "flujo_caja"
$DB_USER = "flujo_caja_app"
$API_SERVICE = "flujo-caja-api"
$REPOSITORY = "flujo-caja-images"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:1.0.0"

gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
```

Confirma que seleccionaste el proyecto correcto antes de continuar:

```powershell
gcloud config get-value project
```

Habilita las APIs necesarias. Espera a que el comando termine sin errores:

```powershell
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com iamcredentials.googleapis.com
```

## 2. Crear Cloud SQL PostgreSQL

Usa Cloud Console para evitar errores de configuracion inicial:

1. Abre `Cloud SQL` y selecciona `Crear instancia`.
2. Selecciona `PostgreSQL`.
3. Selecciona PostgreSQL 16.
4. Usa el ID `flujo-caja-db`.
5. Selecciona la region definida en `$REGION`.
6. Para una primera demostracion, elige una configuracion pequena. Para produccion real, elige capacidad segun cantidad de usuarios y activa alta disponibilidad si el presupuesto lo permite.
7. Crea la instancia y espera hasta que muestre estado `En ejecucion`.

Una vez creada, genera la base y el usuario de aplicacion desde PowerShell:

```powershell
gcloud sql databases create $DB_NAME --instance $DB_INSTANCE
gcloud sql users create $DB_USER --instance $DB_INSTANCE --password "REEMPLAZAR-CON-UNA-CONTRASENA-LARGA"
```

Guarda la contraseña en un gestor de contraseñas. No la escribas en Git, archivos `.env` de produccion ni capturas de pantalla.

Obtiene el nombre de conexion que necesita Cloud Run:

```powershell
$CONNECTION_NAME = gcloud sql instances describe $DB_INSTANCE --format="value(connectionName)"
$CONNECTION_NAME
```

El resultado debe tener este formato:

```text
PROJECT_ID:REGION:DB_INSTANCE
```

## 3. Crear secretos en Secret Manager

Se requieren dos secretos:

| Secreto | Contenido |
| --- | --- |
| `flujo-caja-database-url` | URL de conexion de SQLAlchemy para Cloud SQL. |
| `flujo-caja-secret-key` | Clave privada larga para firmar tokens JWT. |

### 3.1 Crear `DATABASE_URL`

La URL para el socket Unix de Cloud SQL es:

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@/flujo_caja?host=/cloudsql/PROJECT_ID:REGION:DB_INSTANCE
```

Ejemplo de estructura, sin usar estos datos literalmente:

```text
postgresql+psycopg://flujo_caja_app:CONTRASENA_CODIFICADA@/flujo_caja?host=/cloudsql/mi-proyecto:us-central1:flujo-caja-db
```

Si la contraseña contiene `@`, `:`, `/`, `?`, `#`, `%` o espacios, codificala antes de incluirla en la URL. Por ejemplo, `Clave@2026` debe escribirse como `Clave%402026`.

En Cloud Console:

1. Abre `Seguridad > Secret Manager`.
2. Pulsa `Crear secreto`.
3. Nombre: `flujo-caja-database-url`.
4. Pega la URL completa.
5. Pulsa `Crear secreto`.

### 3.2 Crear `SECRET_KEY`

Genera una clave aleatoria desde el entorno virtual del backend:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

En Secret Manager, crea otro secreto:

1. Nombre: `flujo-caja-secret-key`.
2. Valor: la clave generada.
3. Pulsa `Crear secreto`.

## 4. Crear la cuenta de servicio de Cloud Run

Cloud Run no debe usar tu cuenta personal para acceder a la base ni a secretos.

```powershell
gcloud iam service-accounts create flujo-caja-run --display-name "Flujo Caja Cloud Run"
$SERVICE_ACCOUNT = "flujo-caja-run@$PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:$SERVICE_ACCOUNT" --role "roles/cloudsql.client"
gcloud secrets add-iam-policy-binding flujo-caja-database-url --member "serviceAccount:$SERVICE_ACCOUNT" --role "roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding flujo-caja-secret-key --member "serviceAccount:$SERVICE_ACCOUNT" --role "roles/secretmanager.secretAccessor"
```

Verifica que exista:

```powershell
gcloud iam service-accounts describe $SERVICE_ACCOUNT
```

## 5. Crear Artifact Registry y construir la imagen

Desde el directorio `backend`, crea el repositorio Docker:

```powershell
gcloud artifacts repositories create $REPOSITORY --repository-format docker --location $REGION --description "Imagenes de Flujo de Caja"
```

Si indica que ya existe, continua con el siguiente paso.

Construye la imagen. Este comando envia el contenido del directorio actual, por eso debes ejecutarlo desde `backend`:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
gcloud builds submit --tag $IMAGE .
```

Verifica que la imagen exista:

```powershell
gcloud artifacts docker images list "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY"
```

## 6. Ejecutar migraciones con un Cloud Run Job

Nunca dependas de que cada instancia web ejecute migraciones al arrancar. Ejecuta el Job antes del servicio web y antes de cada despliegue que incluya migraciones Alembic.

Crea el Job una sola vez:

```powershell
gcloud run jobs create flujo-caja-migrate `
  --image $IMAGE `
  --region $REGION `
  --service-account $SERVICE_ACCOUNT `
  --set-cloudsql-instances $CONNECTION_NAME `
  --set-secrets "DATABASE_URL=flujo-caja-database-url:latest,SECRET_KEY=flujo-caja-secret-key:latest" `
  --set-env-vars "ENVIRONMENT=production" `
  --command alembic `
  --args="upgrade,head"
```

Ejecutalo y espera su resultado:

```powershell
gcloud run jobs execute flujo-caja-migrate --region $REGION --wait
```

Si falla, consulta los logs antes de desplegar la API:

```powershell
gcloud run jobs executions list --job flujo-caja-migrate --region $REGION
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=flujo-caja-migrate" --limit 50
```

## 7. Desplegar la API en Cloud Run

El `Dockerfile` del proyecto escucha en el puerto 8000. Por eso `--port 8000` es obligatorio en este proyecto.

El valor de CORS se ajusta despues de obtener la URL del frontend. Por ahora se deja vacio; el frontend todavia no podra consumir la API hasta completar el paso 9.

```powershell
gcloud run deploy $API_SERVICE `
  --image $IMAGE `
  --region $REGION `
  --port 8000 `
  --service-account $SERVICE_ACCOUNT `
  --set-cloudsql-instances $CONNECTION_NAME `
  --set-secrets "DATABASE_URL=flujo-caja-database-url:latest,SECRET_KEY=flujo-caja-secret-key:latest" `
  --set-env-vars "ENVIRONMENT=production,BACKEND_CORS_ORIGINS=[]" `
  --allow-unauthenticated
```

Obtiene la URL de la API y guardala:

```powershell
$API_URL = gcloud run services describe $API_SERVICE --region $REGION --format="value(status.url)"
$API_URL
```

Verifica la API en el navegador:

```text
https://URL-DE-LA-API/docs
```

Tambien puedes comprobarla desde PowerShell:

```powershell
Invoke-WebRequest "$API_URL/docs" -UseBasicParsing
```

Debe devolver estado `200`. Si devuelve `500`, revisa los logs:

```powershell
gcloud run services logs read $API_SERVICE --region $REGION --limit 100
```

## 8. Publicar el frontend con Firebase Hosting

Firebase Hosting soporta rutas de aplicaciones de una sola pagina, como las rutas de React de este proyecto.

Instala e inicia sesion en Firebase CLI:

```powershell
npm install -g firebase-tools
firebase login
```

Si el proyecto todavia no esta asociado a Firebase, abre <https://console.firebase.google.com/>, pulsa `Crear un proyecto` y, al final de la pantalla, selecciona `Agregar Firebase al proyecto de Google Cloud`. Busca y elige `$PROJECT_ID`, acepta los Terminos de Firebase cuando se solicite y completa el asistente. Este paso solo asocia Firebase al proyecto existente; no crea otro proyecto ni modifica Cloud Run o Cloud SQL.

En el directorio del frontend ejecuta el asistente solo la primera vez:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\frontend
firebase init hosting
```

Responde exactamente:

1. `Use an existing project`.
2. Selecciona el mismo proyecto `$PROJECT_ID`.
3. Public directory: `dist`.
4. Configure as a single-page app: `Yes`.
5. Set up automatic builds and deploys with GitHub: `No` por ahora.
6. Si pregunta si debe sobrescribir `dist/index.html`, responde `No`.

Firebase creara `firebase.json` y `.firebaserc` en `frontend`. Conserva ambos archivos en el repositorio.

Compila el frontend con la URL real de Cloud Run. `VITE_API_URL` se integra durante la compilacion, por lo que debes definirla antes de cada `npm run build` de produccion:

```powershell
$env:VITE_API_URL = "$API_URL/api/v1"
npm ci
npm run build
firebase deploy --only hosting
```

Al finalizar, Firebase mostrara una URL parecida a:

```text
https://PROJECT_ID.web.app
```

Guardala como valor de `$FRONTEND_URL`:

```powershell
$FRONTEND_URL = "https://PROJECT_ID.web.app"
```

## 9. Configurar CORS definitivo

Actualiza Cloud Run con las URLs reales de Firebase. Incluye ambas URLs por defecto de Firebase para evitar bloqueos si se usa cualquiera de las dos:

```powershell
@'
ENVIRONMENT: production
BACKEND_CORS_ORIGINS: '["https://PROJECT_ID.web.app","https://PROJECT_ID.firebaseapp.com"]'
'@ | Set-Content -Encoding ascii .\cloud-run-env.yaml

gcloud run services update $API_SERVICE `
  --region $REGION `
  --env-vars-file .\cloud-run-env.yaml
```

Si agregas un dominio propio, actualiza CORS para incluirlo:

```powershell
@'
ENVIRONMENT: production
BACKEND_CORS_ORIGINS: '["https://PROJECT_ID.web.app","https://PROJECT_ID.firebaseapp.com","https://app.tudominio.com"]'
'@ | Set-Content -Encoding ascii .\cloud-run-env.yaml

gcloud run services update $API_SERVICE `
  --region $REGION `
  --env-vars-file .\cloud-run-env.yaml
```

Abre el frontend publicado, inicia sesion y prueba como minimo:

1. Inicio de sesion.
2. Consulta de dashboard.
3. Creacion de un movimiento manual.
4. Descarga del Excel de pendientes.
5. Carga y vista previa del Excel de actualizacion masiva.

Si el navegador muestra un error CORS, confirma que el dominio abierto coincide exactamente, incluido `https://`, con uno de los valores de `BACKEND_CORS_ORIGINS`.

## 10. Despliegues posteriores

### Cambio solo de frontend

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\frontend
$env:VITE_API_URL = "https://URL-DE-LA-API/api/v1"
npm ci
npm run build
firebase deploy --only hosting
```

### Cambio de backend sin migracion

Usa una etiqueta nueva para cada imagen. Ejemplo `1.0.1`:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:1.0.1"
gcloud builds submit --tag $IMAGE .
gcloud run deploy $API_SERVICE --image $IMAGE --region $REGION --port 8000
```

### Cambio de backend con migracion

Primero construye la nueva imagen. Luego actualiza y ejecuta el Job. Solo despues despliega el servicio:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:1.0.2"
gcloud builds submit --tag $IMAGE .

gcloud run jobs update flujo-caja-migrate --image $IMAGE --region $REGION
gcloud run jobs execute flujo-caja-migrate --region $REGION --wait

gcloud run deploy $API_SERVICE --image $IMAGE --region $REGION --port 8000
```

No despliegues la nueva API si el Job de migracion falla.

## 11. Respaldo y recuperacion de la base

Antes de cambios importantes, crea una exportacion de Cloud SQL:

1. En Cloud Console abre `Cloud SQL > flujo-caja-db > Exportar`.
2. Exporta la base `flujo_caja` a un bucket privado de Cloud Storage.
3. Espera la finalizacion de la operacion y confirma que el archivo exista en el bucket.

Para recuperar, crea primero una exportacion del estado actual. Luego usa `Cloud SQL > Importar` y selecciona el respaldo aprobado. Ejecuta las migraciones despues de restaurar para asegurar que el esquema quede en la revision esperada.

## 12. Diagnostico rapido

| Sintoma | Revision |
| --- | --- |
| Cloud Run devuelve 500 | Logs del servicio; verifica `DATABASE_URL`, secreto y rol `Cloud SQL Client`. |
| Job de migracion falla | Logs del Job; verifica nombre de conexion, secretos y estado de Cloud SQL. |
| Frontend muestra error CORS | Revisa `BACKEND_CORS_ORIGINS` y la URL exacta del navegador. |
| Frontend no encuentra la API | Reconstruye usando `VITE_API_URL=https://URL-API/api/v1`. |
| Login falla tras despliegue | Confirma que `SECRET_KEY` no haya cambiado accidentalmente; cambiarla invalida tokens existentes. |
| Cloud Run no inicia | Confirma que el despliegue use `--port 8000`, porque el Dockerfile escucha en ese puerto. |
| No se ven tablas o columnas nuevas | Ejecuta el Job `flujo-caja-migrate` y confirma que termine correctamente. |

## 13. Lista final de produccion

- [ ] Facturacion habilitada.
- [ ] Cloud SQL creado en la misma region que Cloud Run.
- [ ] Base y usuario de aplicacion creados.
- [ ] Secretos creados en Secret Manager.
- [ ] Cuenta de servicio con `Cloud SQL Client` y acceso a secretos.
- [ ] Job de migraciones ejecutado correctamente.
- [ ] API publicada y `/docs` responde 200.
- [ ] Frontend compilado con `VITE_API_URL` de Cloud Run.
- [ ] Firebase Hosting publicado.
- [ ] CORS configurado con las URLs reales del frontend.
- [ ] Inicio de sesion y flujos principales probados desde la URL publica.
- [ ] Respaldo inicial de Cloud SQL realizado.
