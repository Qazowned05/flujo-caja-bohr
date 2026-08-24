# Despliegue en GCP

La aplicacion usa `DATABASE_URL`; no depende de Docker Compose ni de una direccion local. Esto permite usar PostgreSQL de Cloud SQL sin modificar codigo.

## Cloud SQL

1. Crea una instancia PostgreSQL y la base `flujo_caja`.
2. Crea un usuario de aplicacion sin privilegios de superusuario y concédele acceso a esa base.
3. Guarda la URL de conexion y `SECRET_KEY` en Secret Manager.
4. Conecta el servicio Cloud Run a la instancia Cloud SQL con la opcion `--add-cloudsql-instances`.

Para el socket Unix que Cloud Run monta, la URL tiene este formato:

```
postgresql+psycopg://USUARIO:CONTRASENA@/flujo_caja?host=/cloudsql/PROYECTO:REGION:INSTANCIA
```

Si se usa una IP privada o publica en lugar del socket, usa la URL TCP normal y exige TLS cuando corresponda:

```
postgresql+psycopg://USUARIO:CONTRASENA@HOST:5432/flujo_caja?sslmode=require
```

## Cloud Run

La imagen actual se puede desplegar directamente. El comando de inicio aplica migraciones antes de levantar Uvicorn, por lo que para produccion se recomienda ejecutar `alembic upgrade head` como un Cloud Run Job separado y conceder a ese job la cuenta de servicio con acceso a Cloud SQL.

Configura estas variables de entorno en Cloud Run:

- `ENVIRONMENT=production`
- `DATABASE_URL` desde Secret Manager
- `SECRET_KEY` desde Secret Manager
- `BACKEND_CORS_ORIGINS` como lista JSON de los dominios del frontend

La cuenta de servicio de Cloud Run necesita el rol `Cloud SQL Client` para usar el socket de Cloud SQL.
