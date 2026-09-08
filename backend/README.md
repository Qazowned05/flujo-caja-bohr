# Flujo de Caja

API y frontend para la gestión interna de flujo de caja.

## Inicio local

1. Configura `DATABASE_URL` y `SECRET_KEY` en `.env`. Para desarrollo local de BOHR se usa la base `flujo_caja_bohr`, separada de `flujo_caja`.
2. Ejecuta `alembic upgrade head` para crear las tablas.
3. Crea el primer administrador con `python -m scripts.create_admin admin@empresa.com "Nombre Admin" "contrasena-segura"`.
4. Carga datos de prueba con `python -m scripts.seed`.
5. Inicia la API con `uvicorn main:app --reload`.

La documentacion OpenAPI queda disponible en `http://localhost:8000/docs`.

## Frontend

El cliente está en `frontend/` y usa React, TypeScript, Vite, Chakra UI v2, TanStack Query y TanStack Router.

1. Inicia la API y configura la base de datos como se indica arriba.
2. Ejecuta `cd frontend`.
3. Instala dependencias con `npm install`.
4. Genera el contrato tipado con `npm run generate-client`.
5. Inicia Vite con `npm run dev`.

`npm run build` valida el frontend con TypeScript estricto y construye la distribución. Consulta `frontend/README.md` para variables de entorno y detalles.

## Migraciones

Ejecuta `alembic revision --autogenerate -m "descripcion"` para generar una migracion y
`alembic upgrade head` para aplicarla.

## Ganancias y perdidas

- La guia completa de arquitectura y operacion BOHR esta en `docs/MODULO_GANANCIAS_PERDIDAS_BOHR.md`.
- El modulo se habilita con `PROFIT_AND_LOSS_ENABLED=true` en el backend y `VITE_PROFIT_AND_LOSS_ENABLED=true` en el frontend.
- Con la bandera desactivada, sus rutas devuelven 404 y la navegacion no se muestra.
- Solo administradores pueden administrar lineas de negocio, rubros, mapeos e importaciones. Los asesores pueden consultar el reporte y los asientos.
- La plantilla se descarga en `GET /api/v1/ganancias-perdidas/plantilla.xlsx` y se carga en `POST /api/v1/ganancias-perdidas/importar.xlsx`.

## Docker y GCP

`docker compose up --build` levanta PostgreSQL y la API en contenedores. La API recibe una URL interna hacia el servicio `db`.

Para Cloud Run con Cloud SQL, configura `DATABASE_URL`, `SECRET_KEY` y las credenciales como secretos o variables de entorno del servicio. Consulta `docs/gcp.md` para la cadena de conexión mediante el socket de Cloud SQL.
