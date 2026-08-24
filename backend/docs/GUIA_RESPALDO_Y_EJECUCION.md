# Respaldo y Ejecución en Otra Computadora

## Qué guardar

Guarda la carpeta completa `FLUJO_CAJA`, incluyendo:

- `app/`, `alembic/`, `scripts/` y `tests/`: backend y migraciones.
- `frontend/`: código fuente del panel web.
- `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `alembic.ini` y los archivos Markdown.
- `.env`: configuración local y secretos. Guárdalo de forma privada, nunca en un repositorio público.
- Un respaldo de la base de datos. El código no contiene los usuarios, cuentas ni movimientos reales.

No es necesario copiar estos directorios porque se regeneran:

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `.pytest_cache/`

## Respaldar la base de datos

En la computadora actual, desde Git Bash, ejecuta:

```bash
export PGPASSWORD='TU_CONTRASENA_POSTGRES'
pg_dump -h localhost -U postgres -d flujo_caja -Fc -f flujo_caja_respaldo.dump
unset PGPASSWORD
```

Guarda `flujo_caja_respaldo.dump` junto con la carpeta del proyecto, pero no lo publiques.

Si `pg_dump` no está disponible en la consola, ejecútalo usando la ruta de instalación de PostgreSQL, por ejemplo:

```bash
"C:/Program Files/PostgreSQL/16/bin/pg_dump.exe" -h localhost -U postgres -d flujo_caja -Fc -f flujo_caja_respaldo.dump
```

## Preparar la nueva computadora

Instala estos requisitos:

- Python 3.12 o superior.
- Node.js 20 o superior.
- PostgreSQL 16 o superior.

Copia la carpeta del proyecto y el archivo `flujo_caja_respaldo.dump` a la nueva computadora.

### 1. Crear y restaurar la base

Abre Git Bash o PowerShell y crea la base vacía:

```bash
createdb -h localhost -U postgres flujo_caja
```

Restaura el respaldo:

```bash
export PGPASSWORD='TU_CONTRASENA_POSTGRES'
pg_restore -h localhost -U postgres -d flujo_caja --clean --if-exists flujo_caja_respaldo.dump
unset PGPASSWORD
```

Si la base ya existe y contiene información que no necesitas, puedes eliminarla y crearla de nuevo antes de restaurar:

```bash
dropdb -h localhost -U postgres flujo_caja
createdb -h localhost -U postgres flujo_caja
```

## Configurar el backend

En la raíz de `FLUJO_CAJA`, crea o ajusta `.env` a partir de `.env.example`:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://postgres:TU_CONTRASENA_POSTGRES@localhost:5432/flujo_caja
SECRET_KEY=usa-una-clave-larga-y-privada
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
```

Instala dependencias y aplica cualquier migración pendiente:

```bash
python -m pip install -e ".[dev]"
python -m alembic upgrade head
```

Inicia la API:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Comprueba:

- API: `http://localhost:8000/api/v1/health`
- Documentación: `http://localhost:8000/docs`

No ejecutes `python -m scripts.seed` después de restaurar una base real, salvo que quieras agregar los datos de demostración.

## Configurar el frontend

Abre otra terminal y entra al directorio `frontend`:

```bash
cd frontend
```

Crea `frontend/.env` desde `frontend/.env.example` si deseas definir explícitamente la URL:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

Instala dependencias, actualiza los tipos OpenAPI e inicia Vite:

```bash
npm install
npm run generate-client
npm run dev
```

Abre `http://localhost:5173` e inicia sesión con las credenciales que existan en la base restaurada.

## Usarlo desde otra computadora en la misma red

En la computadora que ejecuta el proyecto, identifica su IP local, por ejemplo `192.168.1.50`.

En el `.env` del backend, permite el origen del frontend remoto:

```env
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://192.168.1.50:5173"]
```

Inicia backend y frontend escuchando en la red:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

En la otra computadora abre `http://192.168.1.50:5173`. También debes permitir los puertos `5173` y `8000` en el firewall de Windows si se bloquean.

## Respaldo periódico recomendado

Antes de cambios importantes, guarda:

1. Una copia de la carpeta del proyecto sin dependencias regenerables.
2. Un archivo `pg_dump` con fecha, por ejemplo `flujo_caja_2026-08-19.dump`.
3. Una copia segura del `.env` por separado.

El respaldo de base de datos es el elemento crítico: contiene movimientos, auditoría, usuarios y configuraciones creadas desde el panel.
