# Avances de Desarrollo

Fecha: 2026-08-19

## Fases completadas

### Fase 0: Base tecnica

- API FastAPI modularizada bajo `app/`.
- Configuracion tipada por variables de entorno en `app/core/config.py`.
- Conexion SQLAlchemy para PostgreSQL y migraciones Alembic.
- `Dockerfile` y `docker-compose.yml` para desarrollo por contenedores.
- Documentacion OpenAPI disponible en `/docs`.
- Soporte de configuracion para GCP Cloud Run y Cloud SQL documentado en `docs/gcp.md`.

### Fase 1: Autenticacion y usuarios

- Autenticacion JWT mediante `POST /api/v1/login/access-token`.
- Endpoint de perfil `GET /api/v1/users/me`.
- Gestion de usuarios para administradores: listado, creacion y actualizacion.
- Roles `admin` y `asesor`.
- Administrador inicial creado localmente:
  - Email: `admin@flujo-caja.com`
  - La contrasena fue generada de forma segura y se entrego fuera de este archivo.
- El script `scripts/create_admin.py` valida ahora el email antes de crear usuarios.

### Fase 2: Catalogos maestros

- CRUD autenticado para bancos, cuentas bancarias, sucursales, vendedores y tipificaciones.
- La tipificacion mantiene la jerarquia Actividad -> Concepto -> Tipo.
- Las cuentas bancarias validan banco activo, moneda ISO de tres letras y unicidad por banco y numero de cuenta.
- Los vendedores pueden asociarse opcionalmente a una sucursal activa.
- Las dependencias jerarquicas deben estar activas al crear o editar registros.
- Los listados excluyen registros inactivos por defecto. Solo los administradores pueden solicitar `include_inactive=true`.
- Las eliminaciones son logicas y solo los administradores pueden ejecutarlas.

### Fase 3: Auditoria

- Tabla `audit_logs` con accion, usuario, tabla, registro, fecha y cambios JSON.
- Las mutaciones de catalogos registran `CREATE`, `UPDATE` o `SOFT_DELETE` dentro de la misma transaccion de base de datos.
- La gestion de usuarios tambien registra auditoria; las contrasenas nunca se guardan en texto ni dentro de los cambios auditados.

### Fase 4: Importacion de extractos CSV

- Plantilla unica descargable desde `GET /api/v1/imports/plantilla.csv` con las columnas `fecha,descripcion,n_operacion,monto,documento,observaciones`.
- Carga autenticada mediante `POST /api/v1/imports/csv`, con una cuenta bancaria activa seleccionada como destino.
- Validacion atomica del archivo: codificacion UTF-8, cabeceras y orden exactos, fecha ISO, numero de operacion, monto decimal finito distinto de cero y ausencia de filas vacias.
- Si hay errores de formato se rechaza todo el archivo con detalle de fila, sin crear movimientos ni lotes.
- Deduplicacion contra movimientos existentes y dentro del mismo archivo usando `(cuenta_bancaria_id, n_operacion)`.
- Cada carga valida crea un `ImportBatch`, incluso si todas sus filas ya eran duplicadas, para conservar trazabilidad.
- Los movimientos nuevos se crean como `IMPORTADO`, `PENDIENTE_TIPIFICAR` y con la moneda de la cuenta bancaria.
- La carga es transaccional: un conflicto concurrente revierte completamente el lote y retorna HTTP 409.
- Auditoria de la creacion de lotes y transacciones importadas.
- Consulta de lote en `GET /api/v1/imports/{batch_id}`. Los asesores solo pueden consultar sus propios lotes; los administradores pueden consultar cualquiera.

### Fase 5: Consulta y tipificacion de transacciones

- Listado paginado en `GET /api/v1/transacciones`, ordenado por fecha y con filtros por cuenta, banco, moneda, rango de fechas, estado, vendedor, sucursal y origen.
- Detalle autenticado en `GET /api/v1/transacciones/{id}`.
- Edicion parcial autenticada en `PATCH /api/v1/transacciones/{id}` para datos operativos y tipificacion.
- Validacion de sucursal y vendedor activos durante la edicion.
- Validacion estricta de la jerarquia Actividad -> Concepto -> Tipo; los tres niveles deben asignarse juntos o quitarse juntos.
- La tipificacion valida cambia automaticamente el estado a `TIPIFICADO`; un movimiento importado sin tipificacion queda en `PENDIENTE_TIPIFICAR`.
- No se permite cambiar desde este endpoint la cuenta, moneda, origen, lote de importacion ni estado manualmente.
- Se controla la unicidad del numero de operacion por cuenta durante una edicion.
- Cada edicion conserva `updated_by_id` y genera su correspondiente registro de auditoria.
- Migracion `20260819_0004` agrega indices para los filtros mas frecuentes.

### Fase 6: Proyecciones y materializacion

- Creacion autenticada de proyecciones mediante `POST /api/v1/transacciones/proyeccion`.
- Las proyecciones no tienen numero de operacion, heredan la moneda de una cuenta bancaria activa y se crean con `origen=PROYECCION` y `estado=PROYECTADO`.
- Las proyecciones aceptan datos operativos, sucursal, vendedor y una tipificacion jerarquica valida opcional.
- Materializacion mediante `PATCH /api/v1/transacciones/{id}/materializar`.
- La materializacion exige un numero de operacion unico dentro de la cuenta, conserva el origen `PROYECCION` para trazabilidad y fija `materializado=true` y `estado=CONFIRMADO`.
- La edicion general no puede asignar el numero de operacion de una proyeccion: solo se permite mediante materializacion.
- Se validan referencias activas, montos y jerarquia de tipificacion durante ambas operaciones.
- Creacion y materializacion registran auditoria dentro de la misma transaccion de base de datos.

### Fase 7: Flujo de caja multidivisa

- Endpoint autenticado de resumen: `GET /api/v1/flujo-caja/resumen`.
- Agregacion independiente por divisa y por cuenta bancaria; el sistema nunca suma monedas distintas.
- Cada grupo separa ingresos, egresos, neto y cantidad de movimientos reales de los proyectados.
- Las proyecciones materializadas se consideran movimientos reales aunque mantengan el origen `PROYECCION`.
- Filtros disponibles por periodo, banco, cuenta, moneda e inclusion de proyecciones.
- El resumen conserva cuentas bancarias inactivas para mantener la trazabilidad historica.
- La API de dashboard esta implementada. La interfaz React sigue pendiente porque el repositorio aun no contiene el frontend base definido en el plan.

### Fase 8: Reportes y actualizacion masiva

- Exportacion de transacciones pendientes en `GET /api/v1/reports/no-tipificados.csv`.
- El archivo usa UTF-8-SIG y las columnas fijas definidas en el plan, incluida la fuente determinista `codigo_banco | alias_cuenta`.
- Carga masiva en `POST /api/v1/reports/actualizacion-masiva` mediante CSV.
- El modo predeterminado es vista previa: valida cada fila y devuelve los cambios propuestos sin persistirlos.
- La aplicacion requiere reenviar el archivo con `confirmar=true` para escribir cambios.
- Una confirmacion con cualquier error se rechaza completamente; no se aplican actualizaciones parciales.
- La carga valida fechas, montos, fuente, transaccion, catalogos activos y jerarquia de tipificacion.
- La aplicacion actualiza la tipificacion, el estado, referencias operativas y datos editables, pero conserva cuenta, moneda, origen, lote de importacion y numero de operacion.
- Cada actualizacion confirmada genera auditoria dentro de la misma transaccion.

### Frontend inicial

- Creado `frontend/` con React, TypeScript, Vite, Chakra UI v2, TanStack Query y TanStack Router.
- Cliente tipado generado desde la especificacion OpenAPI mediante `openapi-typescript`.
- El comando `npm run generate-client` exporta el contrato actual de FastAPI y regenera `frontend/src/client/schema.ts`.
- Login funcional con token Bearer y proteccion de rutas.
- Shell responsive inspirado en el template full-stack de FastAPI: barra lateral, cabecera, navegacion movil y estados de carga/error.
- Vistas iniciales implementadas para dashboard multidivisa, transacciones, importacion CSV, reportes con vista previa/confirmacion y administracion.
- Las operaciones de administracion aun se muestran como indice de catalogos; los formularios CRUD visuales quedan para un siguiente corte.
- Instrucciones de uso en `frontend/README.md` y resumen de comandos en `README.md`.

### Fase 9: Administracion y operacion manual en frontend

- Contrato OpenAPI regenerado con `npm run generate-client` para incluir usuarios, catalogos, tipos de cambio y movimientos manuales.
- Cliente React extendido con wrapper autenticado tipado para todos los CRUD disponibles y `POST /transacciones/manual`.
- Los errores HTTP 422 de importacion que contienen `errores: [{fila, mensaje}]` ahora se presentan como mensajes por fila en la interfaz.
- Navegacion lateral agrupada por Operacion y Administracion, con rutas administrativas protegidas mediante consulta del perfil y rol `admin`.
- Pantallas funcionales para usuarios, bancos/cuentas, sucursales, vendedores, tipificaciones y divisas; las mutaciones invalidan sus consultas TanStack Query.
- Formulario de movimiento manual con cuentas activas y catalogos activos en cascada; importacion CSV con selector de cuenta por alias y moneda.
- El dashboard conserva sus totales separados por moneda; los tipos de cambio se documentan como referencia para operaciones entre cuentas.
- API extendida con `POST /api/v1/transacciones/manual` y CRUD administrativo de `tipos-cambio`; la configuracion de divisas no mezcla los totales del dashboard.
- Migracion `20260819_0005` aplicada para los tipos de cambio.
- `python -m scripts.seed` carga de forma idempotente bancos, cuentas, sucursales, vendedores, tipificaciones, un tipo de cambio USD/PEN y ocho movimientos de prueba.
- No se modifico Docker. La semilla ya fue ejecutada sobre la base local para que las nuevas pantallas puedan probarse de inmediato.

### Fase 10: Detalles finales de flujo de caja

- Cliente OpenAPI regenerado y capa React extendida para edición y anulación de transacciones, desglose de tipificaciones y creación de proyecciones.
- Transacciones filtra por cuenta bancaria activa, permite edición restringida de datos operativos/tipificación y muestra anulación confirmada solo para administradores.
- La anulación conserva el movimiento en la base de datos y en auditoría, pero lo excluye de los listados y cálculos de flujo por defecto.
- Dashboard sincroniza el selector de proyecciones entre resumen y desglose; incorpora matriz expandible por actividad, concepto y tipo, filtros de cuenta/divisa y aviso de conversiones sin tasa.
- Movimiento manual permite seleccionar entre movimiento real y proyección, usando el endpoint correspondiente y refrescando los datos de flujo.
- La matriz se muestra antes de los filtros y el resumen de resultados queda después de ellos, según el flujo de lectura solicitado.
- El layout restringe el desborde horizontal al contenedor de la matriz y ofrece un botón de escritorio para ocultar o mostrar la barra lateral.

### Fase 11: Refactorización de frontend y cierre visual

- `src/pages.tsx` fue reducido a un índice de reexports y las rutas de `main.tsx` importan sus páginas por funcionalidad desde `src/pages/`.
- Se incorporaron capas `components/layout`, `components/common`, `hooks` y `lib` para navegación, estados de interfaz, consultas de catálogos y utilitarios.
- El dashboard usa una barra compacta y responsive con selector único de período, cuenta, moneda de visualización e inclusión de proyecciones; resumen y matriz comparten sus parámetros de consulta.
- La matriz se presenta antes del resumen, mantiene su expansión jerárquica y colorea cero, valores positivos y negativos de manera consistente.
- La tabla de transacciones resuelve cada cuenta desde el catálogo activo y muestra alias más moneda, con el fallback histórico `Cuenta no disponible`.

### Fase 12: Navegación contextual del desglose

- `GET /api/v1/transacciones` admite filtros opcionales combinables por `actividad_id`, `concepto_id` y `tipo_id`, además del rango de fechas existente.
- El dashboard reemplaza los presets de período por un rango compacto de dos fechas, inicializado desde el primer día del mes hasta hoy.
- La matriz fija la jerarquía a la izquierda y el total a la derecha durante el desplazamiento horizontal; el total se ubica después de todas las fechas y los niveles jerárquicos tienen pesos visuales diferenciados.
- Las celdas diarias no nulas abren `/transacciones` con día, cuenta y niveles de tipificación aplicables. La vista muestra chips del desglose y permite reiniciar sus filtros.

### Fase 13: Saldos iniciales en cuentas y flujo

- Las cuentas bancarias admiten y muestran un saldo inicial decimal, positivo o negativo, como saldo de apertura del flujo de caja.
- La matriz de tipificaciones presenta filas no interactivas y diferenciadas para saldo inicial y saldo final por fecha, incluyendo los extremos del período en la columna total.

## Base local

- Base creada: `flujo_caja`.
- Migraciones aplicadas: `20260819_0001`, `20260819_0002`, `20260819_0003`, `20260819_0004` y `20260819_0005`.
- La configuracion local vive en `.env`, archivo excluido del control de versiones.
- Para aplicar nuevas migraciones: `alembic upgrade head`.
- Para iniciar la API: `uvicorn main:app --reload`.

## Verificaciones realizadas

- `ruff format .`
- `ruff check .`
- `alembic check`
- Prueba del login JWT, perfil de administrador y consulta autenticada de bancos.
- Validacion de configuracion de Docker Compose.
- `pytest`: 16 pruebas funcionales aprobadas, incluyendo importacion CSV, tipificacion, filtros, proyecciones, resumen multidivisa, exportacion de pendientes y actualizacion masiva con vista previa y confirmacion atomica.
- `npm run generate-client` y `npm run build` en `frontend/`: cliente OpenAPI regenerado y compilacion de produccion correcta.
- `npm run build` tras la Fase 9: compilacion TypeScript estricta y build Vite correctos (advertencia informativa de bundle mayor a 500 kB).
- `pytest`: 18 pruebas aprobadas tras agregar movimientos manuales y tipos de cambio.
- `pytest`: 22 pruebas aprobadas tras agregar anulación auditada, edición restringida y desglose jerárquico con conversión referencial.
- `npm run generate-client` y `npm run build` tras la Fase 10: compilación correcta; Vite mantiene solo su advertencia informativa de tamaño de bundle.
- `npm run build` tras la Fase 11: compilación TypeScript estricta y build Vite correctos; se mantiene la advertencia informativa de bundle mayor a 500 kB.
- Fase 12 verificada con `ruff format .`, `ruff check .`, `pytest` (23 aprobadas), `alembic check`, `npm run generate-client` y `npm run build`.
- Fase 13 verificada con `npm run generate-client` y `npm run build` en `frontend/`.

## Siguiente etapa

La Fase 9 permanece en espera por decision de producto. Los siguientes cortes de frontend pueden completar formularios CRUD de administracion y la edicion visual de transacciones.
