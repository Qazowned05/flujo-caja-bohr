# Guia Tecnica - Flujo de Caja BOHR

## 1. Alcance y produccion

Este repositorio contiene exclusivamente la aplicacion de BOHR. No mezclar cambios de Enfocado en esta rama o remoto.

| Recurso | Valor |
| --- | --- |
| Repositorio | `https://github.com/Qazowned05/flujo-caja-bohr.git` |
| Rama de produccion | `main` |
| Frontend | `https://flujo-caja-bohr.web.app` |
| API | `https://flujo-caja-bohr-api-1068017260711.us-central1.run.app/api/v1` |
| Proyecto GCP | `flujo-caja-bohr` |
| Servicio Cloud Run | `flujo-caja-bohr-api` |
| Job de migracion | `flujo-caja-bohr-migrate` |
| Base de datos | PostgreSQL 16 en VM privada `bohr-postgres` (`10.20.0.10`) |
| Modulo EGyP | Habilitado: `VITE_PROFIT_AND_LOSS_ENABLED=true` y `PROFIT_AND_LOSS_ENABLED=true` |

Los secretos no se guardan en Git. Cloud Run y el Job los reciben desde Secret Manager: `bohr-database-url` y `bohr-secret-key`.

## 2. Arquitectura

```text
Usuario -> Firebase Hosting (React/Vite) -> Cloud Run (FastAPI) -> PostgreSQL privada
                                              |
                                              +-> Cloud Run Job (Alembic)
```

- **Frontend:** React 18, TypeScript, Vite, Chakra UI, TanStack Query y TanStack Router.
- **Backend:** FastAPI, Pydantic Settings, SQLAlchemy 2 y Alembic.
- **Autenticacion:** JWT con inicio de sesion OAuth2 password flow.
- **Persistencia:** PostgreSQL; los modelos SQLAlchemy forman el esquema y Alembic registra los cambios.
- **Archivos Excel:** OpenPyXL para plantillas, importacion, validacion y reportes.
- **Infraestructura:** Cloud Run usa Direct VPC Egress hacia `bohr-db-vpc`, subred `bohr-db-us-central1` y tag `bohr-cloud-run`. La concurrencia es 10 y el maximo de instancias es 2.

## 3. Estructura del repositorio

```text
backend/
  app/
    core/                 # configuracion, DB y seguridad
    modules/              # modulos de negocio
      <modulo>/models.py  # tablas SQLAlchemy
      <modulo>/schemas.py # contratos Pydantic
      <modulo>/routes.py  # endpoints FastAPI
      shared/             # auditoria y mixins comunes
  alembic/versions/       # migraciones ordenadas
  tests/                  # pruebas pytest
  Dockerfile
frontend/
  src/client/             # API HTTP y tipos OpenAPI
  src/pages/              # paginas enrutadas
  src/components/         # componentes reutilizables
  src/hooks/              # consultas de catalogos
  .env.production         # URL API y banderas de build no secretas
  firebase.json
docs/
```

## 4. Modulos existentes

| Modulo | Responsabilidad |
| --- | --- |
| `auth` y `usuarios` | Login, JWT, usuarios, roles `admin` y `asesor`. |
| `cuentas_bancos` | Bancos, cuentas, moneda y saldo inicial. |
| `sucursales`, `vendedores` | Catalogos comerciales. |
| `categorias` | Actividad, concepto y tipo; define la tipificacion. |
| `transacciones` | Movimientos manuales, multiples, proyecciones, anulacion y hard delete de admin. |
| `imports` | Importacion Excel y plantillas con listas dependientes. |
| `reports` | Reportes, pendientes de tipificar y actualizacion masiva. |
| `flujo_caja` | Saldos, resumen, matriz y resultados operativos. |
| `divisas` | Tipos de cambio y conversiones para visualizacion. |
| `ganancias_perdidas` | EGyP: centros, rubros, reglas de distribucion, asientos e informes. |
| `shared` | `AuditLog`, acciones de auditoria y borrado logico compartido. |

## 5. Ejecucion local

Prerequisitos: Python 3.12+, Node.js 20+, npm, PostgreSQL y Git.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Crear backend/.env fuera de Git. No reutilizar secretos de produccion.
$env:PYTHONPATH = (Resolve-Path '.').Path
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend, en otra terminal
cd frontend
npm ci
npm run dev
```

Variables del backend: `ENVIRONMENT`, `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `BACKEND_CORS_ORIGINS` y `PROFIT_AND_LOSS_ENABLED`. La definicion esta en `backend/app/core/config.py`.

Variables de build frontend: `VITE_API_URL` y `VITE_PROFIT_AND_LOSS_ENABLED`. Nunca poner contrasenas, tokens o URLs de PostgreSQL en el frontend.

## 6. API, permisos y auditoria

- Health: `GET /api/v1/health`.
- OpenAPI: `GET /api/v1/openapi.json`.
- Login: `POST /api/v1/login/access-token`.
- El cliente HTTP comun esta en `frontend/src/client/api.ts` y agrega el bearer token automaticamente.
- Endpoints de lectura requieren usuario autenticado. Cambios administrativos usan `require_admin`.
- Crear, editar, anular, desactivar y borrar permanentemente deben registrar auditoria mediante `log_audit` cuando corresponda.
- Hard delete es solo para administradores. Devuelve HTTP 204; el cliente ya maneja respuestas exitosas sin JSON.

## 7. Agregar un modulo nuevo

Ejemplo: agregar el modulo `presupuestos`.

1. Crear `backend/app/modules/presupuestos/` con `models.py`, `schemas.py` y `routes.py`.
2. Definir la tabla en `models.py` usando `Base` y, si aplica, `SoftDeleteMixin`.
3. Definir entradas y salidas Pydantic en `schemas.py`. Usar `Field` para validar limites y textos.
4. Crear el `APIRouter` con prefijo claro, por ejemplo `/presupuestos`, y dependencias `get_current_user` o `require_admin`.
5. Importar el router en `backend/app/main.py` y registrarlo con `app.include_router(..., prefix="/api/v1")`.
6. Importar el modelo en `backend/alembic/env.py` para que `Base.metadata` lo conozca.
7. Generar y revisar una migracion:

```powershell
cd backend
alembic revision --autogenerate -m "create budgets"
alembic upgrade head
```

8. Crear pruebas en `backend/tests/test_presupuestos.py`: autorizacion, validaciones, casos correctos y auditoria.
9. Actualizar el cliente tipado y la UI:

```powershell
cd frontend
npm run generate-client
```

10. Agregar funciones HTTP en `src/client/api.ts`, una pagina en `src/pages/`, la ruta en `src/main.tsx` y navegacion en `src/components/layout/AppLayout.tsx` si corresponde.
11. Ejecutar pruebas y build antes de desplegar.

No ejecutar una migracion generada automaticamente sin leerla. Verificar nombres, indices, datos existentes y operaciones destructivas.

## 8. Cambiar un modulo existente

1. Identificar el contrato actual: ruta, schema, modelo, pruebas y consumidor frontend.
2. Mantener el cambio pequeno y compatible cuando existan datos en produccion.
3. Si cambia una tabla o enum, crear una migracion Alembic. Nunca modificar una migracion ya aplicada.
4. Si cambia un endpoint, actualizar pruebas, `schema.ts` con `npm run generate-client` y el cliente/pagina que lo consume.
5. Para formularios, no enviar `null` si el backend espera omitir un campo opcional. Ejemplo: una contrasena vacia no debe reemplazar la existente.
6. Para acciones sin cuerpo, como `DELETE` con HTTP 204, no intentar leer JSON de la respuesta.
7. Ejecutar las pruebas del modulo y el build frontend. Revisar `git diff --check` antes de commit.

## 9. Datos y migraciones

- Las migraciones viven en `backend/alembic/versions/` y deben tener revision unica.
- Secuencia segura: migracion local -> pruebas -> deploy backend -> actualizar/ejecutar Job de migracion -> smoke test.
- No conectarse a la VM ni ejecutar SQL manual para cambios de esquema rutinarios. Usar Alembic.
- Si se requiere revisar datos de produccion, usar solo cuentas autorizadas, consultas de solo lectura y no copiar datos sensibles fuera del entorno.

## 10. Pruebas y calidad

```powershell
cd backend
$env:PYTHONPATH = (Resolve-Path '.').Path
pytest
ruff check app tests

cd ..\frontend
npm run build
```

La suite historica puede contener pruebas con fechas fijas; una falla debe analizarse antes de ignorarla. Ejecutar como minimo el archivo de pruebas afectado por el cambio.

## 11. Despliegue de BOHR

Antes de desplegar: estar en este repositorio, tener `gcloud`, Firebase CLI y sesion iniciada; confirmar `git status`, pruebas y build. No desplegar cambios no revisados.

### Backend sin cambio de esquema

```powershell
cd backend
gcloud run deploy flujo-caja-bohr-api --source . --region us-central1 --project flujo-caja-bohr --quiet
```

### Backend con migracion

Desplegar la API primero, actualizar la imagen del Job y ejecutar Alembic. El Job ya tiene acceso a la VPC privada y secretos; no agregar Cloud SQL.

```powershell
cd backend
gcloud run deploy flujo-caja-bohr-api --source . --region us-central1 --project flujo-caja-bohr --quiet
$image = gcloud run services describe flujo-caja-bohr-api --region us-central1 --project flujo-caja-bohr --format="value(spec.template.spec.containers[0].image)"
gcloud run jobs update flujo-caja-bohr-migrate --image $image --region us-central1 --project flujo-caja-bohr --quiet
gcloud run jobs execute flujo-caja-bohr-migrate --region us-central1 --project flujo-caja-bohr --wait --quiet
```

### Frontend

`frontend/.env.production` ya contiene los valores correctos de BOHR. Para hacer explicita la configuracion durante un deploy:

```powershell
cd frontend
$env:VITE_API_URL = "https://flujo-caja-bohr-api-1068017260711.us-central1.run.app/api/v1"
$env:VITE_PROFIT_AND_LOSS_ENABLED = "true"
npm ci
npm run build
firebase deploy --only hosting --project flujo-caja-bohr
```

### Verificacion y rollback

```powershell
Invoke-WebRequest https://flujo-caja-bohr-api-1068017260711.us-central1.run.app/api/v1/health
Invoke-WebRequest https://flujo-caja-bohr.web.app
gcloud run revisions list --service flujo-caja-bohr-api --region us-central1 --project flujo-caja-bohr
```

Para volver una API a una revision anterior, identificar su nombre en la lista y ejecutar:

```powershell
gcloud run services update-traffic flujo-caja-bohr-api --to-revisions REVISION_ANTERIOR=100 --region us-central1 --project flujo-caja-bohr
```

Un rollback de codigo no revierte una migracion de base de datos. Preparar migracion inversa solo si es segura y necesaria.

## 12. Checklist de entrega

1. Pruebas del modulo y `npm run build` exitosos.
2. Migracion revisada y Job ejecutado si cambio el esquema.
3. Health, login y flujo modificado verificados en produccion.
4. `git diff --check`, commit descriptivo y `git push origin main`.
5. Confirmar que ninguna clave, `.env` local, archivo Excel de cliente o backup entro al commit.
