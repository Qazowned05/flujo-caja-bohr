# Operacion, Actualizaciones, Escalado y GitHub

Esta guia explica como operar el ambiente ya publicado en GCP y como preparar despliegues futuros. Complementa `GUIA_DESPLIEGUE_GCP.md`.

## 1. Regla principal: una imagen no cambia sola

Cloud Run no ejecuta los archivos de tu computadora. Ejecuta una imagen Docker inmutable almacenada en Artifact Registry.

Por eso, cuando cambia codigo del backend, el flujo siempre es:

1. Cambiar y probar codigo localmente.
2. Construir una nueva imagen con una etiqueta nueva.
3. Ejecutar migraciones si el cambio incluye una migracion Alembic.
4. Desplegar la nueva imagen a `flujo-caja-api`.
5. Verificar la aplicacion publicada.

Un cambio local no llega a produccion hasta completar ese flujo o hasta que un pipeline CI/CD lo haga por ti.

## 2. Variables para operaciones manuales

Abre PowerShell y define estas variables al inicio de cada sesion nueva:

```powershell
$PROJECT_ID = "flujo-caja-enfocadosac"
$REGION = "us-central1"
$DB_INSTANCE = "flujo-caja-db"
$DB_NAME = "flujo_caja"
$REPOSITORY = "flujo-caja-images"
$API_SERVICE = "flujo-caja-api"
$CONNECTION_NAME = "flujo-caja-enfocadosac:us-central1:flujo-caja-db"
$SERVICE_ACCOUNT = "flujo-caja-run@$PROJECT_ID.iam.gserviceaccount.com"
```

La imagen debe tener una etiqueta nueva en cada despliegue. Usa una version semantica, por ejemplo `1.0.2`, o el identificador corto del commit Git.

```powershell
$VERSION = "1.0.2"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:$VERSION"
```

## 3. Antes de cualquier despliegue

### Cambios de backend

Desde `backend`:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m pytest
```

Corrige los errores antes de continuar. No uses la base de produccion para pruebas locales.

### Cambios de frontend

Desde `frontend`:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\frontend
npm ci
npm run build
```

El frontend debe construirse con la URL publica real de la API:

```powershell
$env:VITE_API_URL = "https://flujo-caja-api-357419791119.us-central1.run.app/api/v1"
npm run build
```

`VITE_API_URL` se incorpora al archivo JavaScript durante la compilacion. Si cambia la URL de Cloud Run, debes reconstruir y volver a publicar el frontend.

### Respaldo previo a cambios de base de datos

Antes de aplicar una migracion con datos reales:

1. Abre Cloud SQL > `flujo-caja-db` > Exportar.
2. Exporta `flujo_caja` a un bucket privado de Cloud Storage.
3. Confirma que el archivo de respaldo exista y tenga la fecha correcta.
4. Solo entonces ejecuta la migracion.

No ejecutes migraciones destructivas como eliminar columnas o tablas sin un plan de respaldo y recuperacion probado.

## 4. Actualizar solo el frontend

Usa este flujo si solo se modificaron archivos dentro de `frontend/` y no cambio el contrato de la API.

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\frontend
$env:VITE_API_URL = "https://flujo-caja-api-357419791119.us-central1.run.app/api/v1"
npm ci
npm run build
firebase deploy --only hosting
```

Firebase Hosting publica el contenido de `frontend/dist/`. Verifica la URL `https://flujo-caja-enfocadosac.web.app` con una recarga completa (`Ctrl + F5`).

## 5. Actualizar backend sin migracion

Usa este flujo si cambias rutas, logica, validaciones, reportes o dependencias, pero no modificas modelos ni agregas archivos en `alembic/versions/`.

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
$VERSION = "1.0.2"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:$VERSION"

gcloud builds submit --tag $IMAGE .

gcloud run deploy $API_SERVICE `
  --image $IMAGE `
  --region $REGION `
  --port 8000
```

Cloud Run conserva las configuraciones ya creadas: secretos, Cloud SQL, cuenta de servicio, CORS y permisos. No vuelvas a escribir contraseñas en comandos de despliegue.

Verifica la API:

```powershell
$API_URL = gcloud run services describe $API_SERVICE --region $REGION --format="value(status.url)"
Invoke-WebRequest "$API_URL/docs" -UseBasicParsing
```

## 6. Actualizar backend con migracion

Usa este flujo si agregaste o modificaste una migracion en `backend/alembic/versions/`.

### 6.1 Crear la migracion local

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "descripcion-corta"
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m pytest
```

Revisa manualmente el archivo generado antes de subirlo. `--autogenerate` no comprende todos los cambios de datos, indices o restricciones.

### 6.2 Construir, migrar y desplegar

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI\backend
$VERSION = "1.0.3"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:$VERSION"

gcloud builds submit --tag $IMAGE .

gcloud run jobs update flujo-caja-migrate --image $IMAGE --region $REGION
gcloud run jobs execute flujo-caja-migrate --region $REGION --wait

gcloud run deploy $API_SERVICE `
  --image $IMAGE `
  --region $REGION `
  --port 8000
```

Si el Job falla, no despliegues la imagen al servicio. Consulta sus logs:

```powershell
gcloud run jobs logs read flujo-caja-migrate --region $REGION --limit 100
```

## 7. Cambiar configuracion o secretos

### CORS

El backend espera `BACKEND_CORS_ORIGINS` como una lista JSON. Para evitar problemas de comillas en PowerShell, crea un archivo temporal:

```powershell
@'
ENVIRONMENT: production
BACKEND_CORS_ORIGINS: '["https://flujo-caja-enfocadosac.web.app","https://flujo-caja-enfocadosac.firebaseapp.com"]'
'@ | Set-Content -Encoding ascii .\cloud-run-env.yaml

gcloud run services update $API_SERVICE --region $REGION --env-vars-file .\cloud-run-env.yaml
Remove-Item -LiteralPath .\cloud-run-env.yaml
```

### Rotar un secreto

Nunca edites ni publiques un secreto en Git. En Secret Manager:

1. Abre el secreto existente.
2. Pulsa `Agregar nueva version`.
3. Pega el nuevo valor.
4. Despliega una nueva revision de Cloud Run para que use `latest`.
5. Verifica login y conexion a base de datos.

Para `SECRET_KEY`, planifica la rotacion: al cambiarla se invalidan los tokens de sesion existentes.

Para `DATABASE_URL`, prueba primero la nueva conexion con el Job `flujo-caja-migrate`.

## 8. Reversion segura

### Backend

Cloud Run conserva revisiones anteriores. En Cloud Console:

1. Cloud Run > `flujo-caja-api` > Revisiones.
2. Identifica la ultima revision estable.
3. En `Administrar trafico`, envia 100% del trafico a esa revision.

Tambien puedes desplegar de nuevo una imagen anterior conocida:

```powershell
$IMAGE_ANTERIOR = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/flujo-caja-api:1.0.2"
gcloud run deploy $API_SERVICE --image $IMAGE_ANTERIOR --region $REGION --port 8000
```

No reviertas una migracion de base de datos automaticamente. Si una migracion ya cambio datos, revisa el respaldo y crea una migracion correctiva hacia adelante. Usa `alembic downgrade` en produccion solo si fue probado contra una copia de produccion.

### Frontend

Firebase Hosting mantiene historial de versiones. En Firebase Console > Hosting > Historial de versiones, selecciona una version estable y usa `Revertir`.

## 9. Escalar sin agotar Cloud SQL

Cloud Run escala automaticamente segun solicitudes. Cada instancia de la API crea conexiones a PostgreSQL, por lo que no debes subir el maximo de instancias sin revisar Cloud SQL.

Configuracion inicial prudente:

```powershell
gcloud run services update $API_SERVICE `
  --region $REGION `
  --min 1 `
  --max 3 `
  --concurrency 40 `
  --cpu 1 `
  --memory 512Mi
```

- `--min 1`: reduce el retraso del primer usuario, pero tiene costo permanente.
- `--max 3`: limita inicialmente conexiones simultaneas a Cloud SQL.
- `--concurrency 40`: permite varias solicitudes por instancia. Ajusta segun las metricas.
- `--cpu 1` y `--memory 512Mi`: punto inicial. Los reportes Excel mas grandes pueden requerir mas memoria.

Para aumentar capacidad, procede en este orden:

1. Revisa latencia, errores 5xx, uso de CPU y memoria en Cloud Run > Metricas.
2. Revisa conexiones, CPU, memoria y almacenamiento en Cloud SQL > Metricas.
3. Aumenta primero el tamano de Cloud SQL si las conexiones o CPU de base llegan al limite.
4. Luego incrementa `--max` gradualmente, por ejemplo de 3 a 5.
5. Ejecuta pruebas de carga antes de subir limites en produccion.

Para una base de datos critica:

- Habilita copias de seguridad automatizadas y recuperacion a un punto en el tiempo.
- Configura alertas de uso de CPU, espacio y conexiones.
- Evalua alta disponibilidad regional cuando el presupuesto y el impacto operativo lo justifiquen.
- Considera una replica de lectura solo si los reportes pesados afectan la operacion diaria.

## 10. Observabilidad, costos y mantenimiento

Configura en Cloud Monitoring:

- Alerta por errores 5xx de Cloud Run.
- Alerta por latencia alta de Cloud Run.
- Alerta por CPU, memoria, conexiones y espacio de Cloud SQL.
- Presupuesto y alertas de facturacion del proyecto.

Comandos utiles:

```powershell
gcloud run services logs read $API_SERVICE --region $REGION --limit 100
gcloud run jobs logs read flujo-caja-migrate --region $REGION --limit 100
gcloud run revisions list --service $API_SERVICE --region $REGION
```

Revisa mensualmente:

1. Usuarios administradores activos.
2. Uso y costo de Cloud SQL, Cloud Run, Artifact Registry y Cloud Storage.
3. Imagenes antiguas de Artifact Registry. Conserva las necesarias para reversion y elimina las obsoletas segun una politica definida.
4. Estado de respaldos y una prueba de restauracion.
5. Dependencias de Python y npm con actualizaciones de seguridad.

## 11. Preparar el proyecto para GitHub

Actualmente esta carpeta no es un repositorio Git. GitHub no recibe cambios automaticamente: primero debes inicializar Git, crear un repositorio remoto y hacer `push`.

### 11.1 Antes del primer commit

No subas secretos ni dependencias regenerables. Comprueba que estos archivos no se incluyan:

- `backend/.env`
- `frontend/.env`
- `backend/venv/` y `backend/.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- respaldos de bases de datos
- `firebase-debug.log`

Mantiene en Git estos archivos de despliegue:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/alembic/`
- `backend/docs/`
- `frontend/firebase.json`
- `frontend/.firebaserc`
- `frontend/package-lock.json`

### 11.2 Crear el repositorio local

Desde la raiz del proyecto:

```powershell
cd C:\Users\user\Desktop\FLUJ_CAJA_FASTAPI

Revisa cuidadosamente `git status` antes de agregar archivos. Si aparece un secreto, agrega su patron a un `.gitignore` en la raiz antes de continuar.

### 11.3 Crear el repositorio remoto

1. En <https://github.com/new>, crea un repositorio privado, por ejemplo `flujo-caja`.
2. No inicialices README, `.gitignore` ni licencia desde GitHub, porque el proyecto ya existe localmente.
3. Copia la URL HTTPS del repositorio.

Conecta y publica el codigo:

```powershell
git remote add origin https://github.com/TU_ORGANIZACION/flujo-caja.git
git push -u origin main
```

Antes de cada `git push`, ejecuta `git status` y revisa los archivos que se van a subir.

## 12. Como se refleja GitHub en produccion

Si solo subes codigo a GitHub, produccion no cambia. Para que un cambio llegue automaticamente necesitas un workflow de GitHub Actions.

Flujo recomendado:

1. Cada cambio se desarrolla en una rama, por ejemplo `feature/reportes`.
2. Se abre un Pull Request hacia `main`.
3. GitHub Actions ejecuta pruebas y compilacion.
4. Un revisor aprueba el Pull Request.
5. Al hacer merge a `main`, GitHub Actions construye la imagen, ejecuta migraciones si existen, despliega Cloud Run y publica el frontend.

Nunca publiques directamente desde una rama de prueba hacia produccion.

## 13. CI/CD seguro con GitHub Actions

Usa Workload Identity Federation (WIF). No guardes una clave JSON de una cuenta de servicio en GitHub Secrets.

### 13.1 Recursos necesarios en GCP

Crea una cuenta de servicio exclusiva para despliegues, separada de `flujo-caja-run`:

```powershell
gcloud iam service-accounts create flujo-caja-github --display-name "GitHub Actions deployer"
$GITHUB_DEPLOYER = "flujo-caja-github@$PROJECT_ID.iam.gserviceaccount.com"
```

Asigna los roles minimos necesarios. Revisa y reduce permisos antes de usar produccion:

```powershell
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:$GITHUB_DEPLOYER" --role "roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:$GITHUB_DEPLOYER" --role "roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:$GITHUB_DEPLOYER" --role "roles/cloudbuild.builds.editor"
gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT --member "serviceAccount:$GITHUB_DEPLOYER" --role "roles/iam.serviceAccountUser"
```

Para configurar WIF, sigue la documentacion oficial de Google: <https://github.com/google-github-actions/auth#setting-up-workload-identity-federation>. Al finalizar tendras dos valores sin secretos:

- `WORKLOAD_IDENTITY_PROVIDER`: recurso completo del proveedor WIF.
- `GCP_SERVICE_ACCOUNT`: `flujo-caja-github@flujo-caja-enfocadosac.iam.gserviceaccount.com`.

Guarda ambos como GitHub Actions variables o secrets del repositorio. Aunque no son contraseñas, usar GitHub Secrets evita errores de configuracion.

### 13.2 Variables GitHub necesarias

En GitHub > Settings > Secrets and variables > Actions, crea:

| Nombre | Tipo | Valor |
| --- | --- | --- |
| `GCP_PROJECT_ID` | Variable | `flujo-caja-enfocadosac` |
| `GCP_REGION` | Variable | `us-central1` |
| `GCP_WIF_PROVIDER` | Secret | Recurso WIF completo. |
| `GCP_DEPLOYER_SERVICE_ACCOUNT` | Secret | Cuenta `flujo-caja-github@...`. |
| `VITE_API_URL` | Variable | URL Cloud Run seguida de `/api/v1`. |

No guardes `DATABASE_URL`, contrasenas ni `SECRET_KEY` en GitHub. Cloud Run ya las obtiene desde Secret Manager.

### 13.3 Flujo de backend que debe automatizarse

Cuando haya cambios en `backend/**` y se haga merge a `main`, el workflow debe:

1. Autenticarse con `google-github-actions/auth` usando WIF.
2. Ejecutar Ruff y Pytest.
3. Construir la imagen con una etiqueta igual al SHA corto del commit.
4. Actualizar el Job `flujo-caja-migrate` a esa imagen.
5. Ejecutar y esperar el Job de migraciones.
6. Desplegar la misma imagen en `flujo-caja-api` solo si el Job tuvo exito.
7. Comprobar que `/docs` responda correctamente.

### 13.4 Flujo de frontend que debe automatizarse

Cuando haya cambios en `frontend/**` y se haga merge a `main`, el workflow debe:

1. Ejecutar `npm ci`.
2. Definir `VITE_API_URL` desde la variable de GitHub.
3. Ejecutar `npm run build`.
4. Publicar `dist/` mediante `firebase deploy --only hosting` con credenciales federadas.
5. Ejecutar una comprobacion HTTP a la URL de Firebase Hosting.

Protege el ambiente `production` en GitHub. Configura revisores obligatorios para que el workflow espere aprobacion antes de ejecutar migraciones o desplegar.

## 14. Lista de verificacion para cada cambio

- [ ] El cambio fue probado localmente.
- [ ] Las pruebas y compilacion terminaron correctamente.
- [ ] No hay secretos en el diff ni en `git status`.
- [ ] Se tomo respaldo antes de migraciones riesgosas.
- [ ] La imagen tiene una etiqueta nueva e identificable.
- [ ] El Job de migraciones termino correctamente, si aplica.
- [ ] La API responde y se puede iniciar sesion.
- [ ] El frontend publicado apunta a la URL correcta de API.
- [ ] Se revisaron logs y metricas despues del despliegue.
- [ ] Existe una imagen o revision anterior conocida para reversion.
