# Plan de Implementación — Sistema de Flujo de Caja

**Stack:** FastAPI (backend) + React/TypeScript (frontend) + PostgreSQL + Alembic
**Referencia estética/arquitectónica:** [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)

---

## 1. Resumen del proyecto

Aplicación interna para gestionar el flujo de caja de una empresa con múltiples cuentas bancarias en distintas divisas. El flujo central es:

1. Se sube un extracto bancario en CSV → se crean registros "crudos" (40% completos) deduplicados por número de operación.
2. Un administrativo completa cada registro con vendedor, sucursal, tipificación (actividad, concepto, tipo), documento y observaciones.
3. Paralelamente, se pueden crear registros de **proyección de gastos/ingresos** (sin número de operación) que luego se "editan" para convertirse en movimientos reales cuando ocurren.
4. Todo el sistema respeta **soft delete** y **auditoría** completa (quién creó/editó cada cosa y cuándo).
5. Se pueden generar reportes de registros no tipificados en CSV, completarlos offline y volver a subirlos para actualización masiva.

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.14.5, FastAPI, SQLModel (o SQLAlchemy 2.0 + Pydantic v2) |
| Migraciones | Alembic |
| Base de datos | PostgreSQL |
| Auth | JWT (OAuth2 password flow), passlib/bcrypt — igual que el template full-stack |
| Frontend | React + TypeScript + Vite, TanStack Query + TanStack Router, Chakra UI (misma base del template) |
| Cliente API | `openapi-ts` generado automáticamente desde el OpenAPI de FastAPI (igual que el template) |
| Contenedores | Docker + docker-compose (ya presentes en tu estructura) |
| Testing | Pytest (backend), Playwright o Vitest (frontend) |
| Procesamiento CSV | pandas o csv nativo + validación con Pydantic |
| Background jobs (opcional) | FastAPI BackgroundTasks o Celery si el volumen de importación crece |

---

## 3. Modelo de datos

### 3.1 Entidades principales

```
Usuario (usuarios)
├─ id, email, hashed_password, nombre, rol, is_active, is_superuser
└─ soft delete: is_active / deleted_at

Banco (cuentas_bancos)
├─ id, nombre, codigo, is_active, deleted_at
└─ 1—N con CuentaBancaria

CuentaBancaria (cuentas_bancos)
├─ id, banco_id (FK), alias, numero_cuenta, moneda (ISO 4217: PEN, USD, EUR...), is_active, deleted_at
└─ 1—N con Transaccion

Sucursal (sucursales)
├─ id, nombre, codigo, is_active, deleted_at

Vendedor (vendedores)
├─ id, nombre, codigo, sucursal_id (FK opcional o N—N si aplica), is_active, deleted_at

Tipificacion jerárquica (categorias)
├─ Actividad (nivel 1)
│   └─ id, nombre, is_active, deleted_at
├─ Concepto (nivel 2)
│   └─ id, actividad_id (FK), nombre, is_active, deleted_at
└─ Tipo (nivel 3)
    └─ id, concepto_id (FK), nombre, is_active, deleted_at

Transaccion (transacciones)
├─ id
├─ fecha
├─ descripcion
├─ n_operacion  (UNIQUE, índice — clave de deduplicación; nullable solo para proyecciones)
├─ monto
├─ moneda (heredada de cuenta_bancaria o explícita)
├─ documento (url/adjunto)
├─ sucursal_id (FK, nullable hasta completar)
├─ vendedor_id (FK, nullable hasta completar)
├─ observaciones
├─ actividad_id / concepto_id / tipo_id (FK, nullable hasta completar)
├─ cuenta_bancaria_id (FK)
├─ origen: enum [IMPORTADO, PROYECCION, MANUAL]
├─ estado: enum [PENDIENTE_TIPIFICAR, TIPIFICADO, PROYECTADO, CONFIRMADO]
├─ is_active, deleted_at
├─ created_by_id (FK usuario), created_at
└─ updated_by_id (FK usuario), updated_at

AuditLog (shared / core)
├─ id, tabla, registro_id, accion [CREATE/UPDATE/SOFT_DELETE], usuario_id, timestamp, cambios (JSON diff)

ImportBatch (imports)
├─ id, cuenta_bancaria_id, archivo_nombre, usuario_id, fecha_importacion
├─ total_filas, filas_nuevas, filas_duplicadas, filas_error
└─ 1—N con Transaccion (para trazabilidad de qué importación generó qué registros)
```

### 3.2 Reglas clave de datos

- **Deduplicación**: índice único sobre `(cuenta_bancaria_id, n_operacion)` — mismo número de operación en distinta cuenta no es duplicado.
- **Soft delete universal**: campo `is_active` (bool) + `deleted_at` (timestamp nullable) en todas las tablas maestras (Usuario, Banco, CuentaBancaria, Sucursal, Vendedor, Actividad, Concepto, Tipo). Las FKs en `Transaccion` **nunca se borran**, solo se desactiva el registro maestro; la transacción sigue mostrando el nombre histórico.
- **Multidivisa**: cada `CuentaBancaria` tiene una moneda fija. El dashboard general debe agregar por separado por moneda (nunca sumar PEN + USD directamente) y ofrecer conversión referencial opcional con tasa de cambio manual/API.
- **Jerarquía de tipificación**: Tipo pertenece a Concepto, Concepto pertenece a Actividad. El frontend debe filtrar en cascada (seleccionar actividad → conceptos disponibles → tipos disponibles).
- **Proyecciones**: registros con `origen = PROYECCION` y `n_operacion = NULL`. Al "materializarse" (editar con número de operación real, documento, etc.) cambian `estado` a `CONFIRMADO` y `origen` puede mantenerse como `PROYECCION` con un flag `materializado = true` para trazabilidad.
- **Auditoría**: middleware/dependency que registra `created_by_id` / `updated_by_id` automáticamente en cada escritura, más un log detallado en `AuditLog` para reconstrucción de historial.

---

## 4. Arquitectura de módulos (mapeo a tu estructura actual)

Tu estructura ya sigue un patrón modular tipo DDD-lite. Se mantiene y se completa así:

```
app/
├─ core/                    # config, seguridad, db session, settings (.env)
├─ modules/
│   ├─ auth/                # login, JWT, refresh, recuperación de password
│   ├─ usuarios/            # CRUD usuarios, roles, permisos
│   ├─ cuentas_bancos/       # Banco + CuentaBancaria (entidades y relación)
│   ├─ sucursales/           # CRUD sucursal
│   ├─ vendedores/           # CRUD vendedor
│   ├─ categorias/           # Actividad / Concepto / Tipo (jerarquía)
│   ├─ transacciones/        # CRUD transacción, filtros, edición, tipificación
│   ├─ imports/              # parseo CSV, deduplicación, batch tracking
│   ├─ flujo_caja/           # agregaciones, dashboard, filtros por fuente/divisa
│   ├─ reports/              # export CSV no tipificados, export general, reimportación masiva
│   └─ shared/               # AuditLog, mixins soft-delete, paginación, permisos comunes
├─ tests/
└─ scripts/
    ├─ create_admin.py
    └─ seed.py               # datos base: bancos comunes, actividades/conceptos/tipos iniciales
```

Cada módulo sigue el patrón del template full-stack: `models.py`, `schemas.py` (o `models.py` con SQLModel unificando ambos), `crud.py`, `routes.py`, `deps.py` si aplica.

### Roles y permisos (definido)

Dos roles, con privilegios casi idénticos — la diferencia es exclusivamente sobre usuarios y desactivación de entidades maestras:

| Acción | Admin | Asesor |
|---|:---:|:---:|
| Login, ver dashboard/flujo de caja | ✅ | ✅ |
| Subir CSV (plantilla), tipificar, editar transacciones | ✅ | ✅ |
| Crear proyecciones de gastos/ingresos y materializarlas | ✅ | ✅ |
| Descargar reporte de no tipificados / subir actualización masiva | ✅ | ✅ |
| Crear vendedores, sucursales, bancos, cuentas bancarias, tipificaciones | ✅ | ✅ |
| **Inactivar (soft delete) vendedores, sucursales, bancos, cuentas, tipificaciones** | ✅ | ❌ |
| **Crear / editar / inactivar usuarios del sistema** | ✅ | ❌ |
| Ver auditoría | ✅ | ✅ (opcional, evaluar si se limita) |

Nota: `Vendedor` **no es un usuario del sistema** — es un dato interno (catálogo) que el administrativo/asesor carga y asocia a las transacciones. No tiene login propio.

Implementación sugerida: enum `rol` en `Usuario` (`admin` / `asesor`) + dependency de FastAPI (`require_admin`) que protege únicamente los endpoints de gestión de usuarios y los `DELETE` (soft delete) de entidades maestras. El resto de endpoints solo requieren usuario autenticado activo.

---

## 5. Frontend (React)

Siguiendo el template full-stack (Vite + Chakra UI + TanStack Router/Query):

```
frontend/src/
├─ routes/
│   ├─ _layout/
│   │   ├─ dashboard.tsx            # flujo de caja general, filtros por cuenta/divisa
│   │   ├─ transacciones/
│   │   │   ├─ index.tsx            # tabla con filtros (banco, cuenta, divisa, estado, sucursal, vendedor)
│   │   │   └─ [id].tsx             # detalle/edición de registro
│   │   ├─ proyecciones/
│   │   ├─ importar.tsx             # subida de CSV con preview de duplicados
│   │   ├─ reportes.tsx             # descarga no-tipificados / carga masiva
│   │   ├─ administracion/
│   │   │   ├─ bancos.tsx
│   │   │   ├─ cuentas.tsx
│   │   │   ├─ sucursales.tsx
│   │   │   ├─ vendedores.tsx
│   │   │   ├─ tipificaciones.tsx   # gestor jerárquico actividad/concepto/tipo
│   │   │   └─ usuarios.tsx
│   │   └─ auditoria.tsx
│   └─ login.tsx
├─ components/
│   ├─ transacciones/TablaTransacciones.tsx
│   ├─ transacciones/FormularioTipificacion.tsx  # cascada actividad→concepto→tipo
│   ├─ imports/CsvUploader.tsx
│   ├─ dashboard/ResumenPorDivisa.tsx
│   └─ common/ (reutilizados del template: ConfirmationDialog, Pagination, etc.)
├─ client/                          # generado automáticamente con openapi-ts
└─ hooks/useAuth.ts, usePermissions.ts
```

**UX clave a resolver:**
- Formulario de tipificación con selects en cascada y opción de "crear nueva tipificación" inline (para admins).
- Tabla de transacciones con filtros combinables (banco, cuenta, divisa, rango de fecha, estado tipificación, vendedor, sucursal).
- Indicador visual claro de "% completado" por registro (pendiente vs tipificado).
- Pantalla de importación con resumen previo: N filas nuevas, N duplicadas (con detalle de cuáles), N con error de formato.
- Pantalla de reportes: botón "descargar no tipificados (CSV)" y "subir CSV actualizado" con preview de cambios antes de confirmar.

---

## 6. Endpoints principales (API)

```
POST   /api/v1/login/access-token
GET    /api/v1/users/me

# Maestros (todos con soft delete: DELETE = desactivar, no borrar)
CRUD   /api/v1/bancos
CRUD   /api/v1/cuentas-bancarias           (filtrable por banco)
CRUD   /api/v1/sucursales
CRUD   /api/v1/vendedores
CRUD   /api/v1/actividades
CRUD   /api/v1/conceptos                   (filtrable por actividad)
CRUD   /api/v1/tipos                       (filtrable por concepto)

# Transacciones
GET    /api/v1/transacciones               (filtros: cuenta, banco, divisa, fecha, estado, vendedor, sucursal)
GET    /api/v1/transacciones/{id}
PATCH  /api/v1/transacciones/{id}          (tipificar / editar)
POST   /api/v1/transacciones/proyeccion    (crear proyección manual)
PATCH  /api/v1/transacciones/{id}/materializar

# Importación
GET    /api/v1/imports/plantilla.csv       (descarga plantilla vacía de carga)
POST   /api/v1/imports/csv                 (multipart + cuenta_bancaria_id obligatorio)
GET    /api/v1/imports/{batch_id}          (resumen del batch: nuevas/duplicadas/errores)

# Reportes
GET    /api/v1/reports/no-tipificados.csv
POST   /api/v1/reports/actualizacion-masiva  (sube CSV, valida y aplica cambios)

# Flujo de caja / dashboard
GET    /api/v1/flujo-caja/resumen          (agregado por divisa, por cuenta, por periodo)

# Auditoría
GET    /api/v1/auditoria                   (filtrable por tabla, registro, usuario, fecha)
```

---

## 7. Formato CSV — plantilla única

Se descarta el mapeo por banco. En su lugar: **una sola plantilla estándar** que el administrativo/asesor descarga, y luego llena copiando y pegando manualmente los valores desde el extracto original de cada banco (que puede tener cualquier formato). Esto simplifica mucho el backend: no hay que parsear N formatos distintos, solo validar una estructura fija.

### 7.1 Plantilla de carga (extracto → sistema)

Columnas de la plantilla descargable (`GET /api/v1/imports/plantilla.csv`):

```
fecha, descripcion, n_operacion, monto, documento, observaciones
```

Solo los campos "crudos" que vienen del banco. **No** incluye sucursal/vendedor/tipificación (eso se completa después dentro del sistema, al 40%→100%).

### 7.2 Selección de destino al subir

En el formulario de carga, el usuario **selecciona explícitamente el Banco y la Cuenta Bancaria** a la que pertenece ese archivo (dropdown dependiente: banco → cuentas activas de ese banco). Ese `cuenta_bancaria_id` se aplica a **todas las filas del archivo** subido, y de ahí se hereda la moneda. Así el CSV en sí no necesita columna de banco/fuente — la fuente la define el contexto de la carga, no el archivo.

Flujo:
1. Usuario descarga la plantilla vacía (o reutiliza una ya guardada).
2. Copia/pega los datos del extracto original del banco en las columnas correspondientes.
3. Sube el archivo y selecciona **Banco → Cuenta Bancaria** de destino.
4. Backend valida formato, deduplica por `(cuenta_bancaria_id, n_operacion)`, crea `ImportBatch` + transacciones con `estado = PENDIENTE_TIPIFICAR`.
5. Se muestra resumen: filas nuevas, duplicadas (con detalle), filas con error de formato.

### 7.3 Plantilla de trabajo (descarga "no tipificados" / actualización masiva)

Columnas fijas (incluye ya la `fuente` como columna informativa, ya que aquí sí mezcla registros de varias cuentas/bancos):

```
fecha, descripcion, n_operacion, monto, documento, sucursal, vendedor,
observaciones, actividad, concepto, tipo, fuente
```

- `fuente` = alias de la cuenta bancaria (banco + cuenta), solo para que el usuario ubique el registro; **no editable**, se usa como referencia de matcheo junto con `n_operacion`.
- Al re-subir: matchear por `n_operacion` + `fuente`/cuenta, validar que actividad/concepto/tipo respeten la jerarquía existente (o crearlas si el usuario tiene permiso), validar que vendedor/sucursal existan y estén activos, y aplicar la actualización dejando rastro en `AuditLog`.
- Reporte de errores post-carga: filas no encontradas, jerarquías inválidas, vendedores/sucursales inexistentes/inactivos.

---

## 8. Fases de implementación

### Fase 0 — Setup (0.5–1 semana)
- Adaptar `docker-compose.yml`, `Dockerfile`, `.env.example`, `alembic.ini` ya existentes al nuevo modelo de datos.
- Definir `core/config.py` (settings), conexión DB, estructura base de `main.py` con routers modulares.
- Configurar frontend base (Vite + Chakra + TanStack Router/Query) y generación de cliente OpenAPI.

### Fase 1 — Auth y usuarios (0.5 semana)
- JWT login, roles, `create_admin.py` (ya existe, adaptar), gestión de usuarios y permisos.

### Fase 2 — Maestros con soft delete (1 semana)
- Bancos, Cuentas Bancarias, Sucursales, Vendedores, jerarquía Actividad/Concepto/Tipo.
- CRUD backend + pantallas de administración frontend + mixin genérico de soft delete y auditoría (`shared/`).

### Fase 3 — Auditoría transversal (0.5 semana, en paralelo con Fase 2)
- Middleware/dependency que capture `created_by`/`updated_by` y escriba en `AuditLog` en cada mutación.
- Pantalla de consulta de auditoría (admin).

### Fase 4 — Importación de extractos CSV (1–1.5 semanas)
- Parser configurable por banco, deduplicación por `n_operacion` + cuenta, creación de `ImportBatch`.
- Validaciones y reporte de resultado de importación (nuevas / duplicadas / errores).
- Frontend: uploader con preview.

### Fase 5 — Tipificación y edición de transacciones (1 semana)
- Endpoint de edición parcial (`PATCH`), formulario en cascada de tipificación.
- Tabla de transacciones con filtros avanzados (banco, cuenta, divisa, estado, vendedor, sucursal, rango fecha).

### Fase 6 — Proyecciones de gastos/ingresos (0.5–1 semana)
- Creación manual de registros sin `n_operacion`, endpoint de "materialización" (editar proyección → registro real con documento y número de operación).

### Fase 7 — Flujo de caja / dashboard general (1 semana)
- Agregaciones por divisa, por cuenta, por periodo; filtros por fuente bancaria.
- Gráficos (recharts, ya disponible en artifacts; en la app real usar librería de charts que decidas — recharts/visx).

### Fase 8 — Reportes y actualización masiva (0.5–1 semana)
- Export CSV de no tipificados.
- Import de CSV de actualización masiva con validación y preview de cambios antes de confirmar.

### Fase 9 — Pulido, permisos finos, tests, deploy (1–1.5 semanas)
- Tests backend (pytest) y frontend (Playwright), ajuste de permisos por rol, revisión de UX, despliegue con docker-compose.
---

## 9. Consideraciones técnicas adicionales

- **Índices de performance**: sobre `n_operacion`, `cuenta_bancaria_id`, `fecha`, `estado` (las tablas de transacciones crecerán rápido con importaciones periódicas).
- **Concurrencia en importación**: usar transacción de BD por batch; si falla a mitad, rollback completo del batch y reporte de error, no dejar importaciones parciales.
- **Multidivisa en dashboard**: nunca mostrar un solo total sumando divisas distintas; agrupar siempre por moneda, con tabs o columnas separadas.
- **Plantilla única, sin parser por banco**: al usar una sola plantilla estándar (sección 7), el backend valida un único esquema de columnas. La diversidad de formatos bancarios se resuelve fuera del sistema (copiar/pegar manual), lo que reduce complejidad de parseo pero depende de la disciplina del usuario al copiar los datos — vale la pena agregar validaciones fuertes de tipo de dato por columna (fecha válida, monto numérico, n_operacion no vacío salvo proyecciones) y mensajes de error claros por fila.
- **Migraciones**: cada fase de maestros/transacciones debe ir acompañada de su migración Alembic versionada, nunca editar migraciones ya aplicadas en producción.
- **Seed inicial** (`scripts/seed.py`): cargar bancos comunes, sucursales base, y una jerarquía inicial de actividades/conceptos/tipos para no arrancar en blanco.

---

## 10. Decisiones confirmadas

- ✅ Vendedor = catálogo interno, sin login propio.
- ✅ Roles: `admin` (todo, incluye gestión de usuarios e inactivación de maestros) y `asesor` (todo lo operativo, sin gestión de usuarios ni inactivaciones).
- ✅ CSV: una sola plantilla estándar, con banco/cuenta seleccionados en el formulario de carga (no un mapeo por banco).
