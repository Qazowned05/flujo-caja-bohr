# Modulo de Ganancias y Perdidas BOHR

Fecha de implementacion: 2026-09-08

## Proposito

El modulo convierte el Estado de Ganancias y Perdidas (EGyP) que BOHR administraba en Excel en un reporte consultable, editable en su estructura y trazable hasta sus asientos de origen.

No reemplaza el modulo de flujo de caja:

- Flujo de caja: movimientos bancarios, cobros, pagos y proyecciones por fecha de caja.
- EGyP: ingresos, descuentos, costos y gastos contables por periodo y linea de negocio.

Los dos modulos usan la misma aplicacion, pero sus datos no se mezclan.

## Estado Local BOHR

La instancia local usa una base de datos separada:

- Base: `flujo_caja_bohr`.
- Configuracion: `backend/.env` mediante `DATABASE_URL`.
- Migracion actual: `20260908_0012`.
- No contiene movimientos ni datos de prueba de Enfocado.
- Se creo un administrador local BOHR para iniciar la operacion.

La estructura inicial se carga con:

```powershell
python -m scripts.seed_bohr_egyp
```

El script es idempotente: puede ejecutarse otra vez sin duplicar catalogos. Solo carga configuracion, nunca asientos financieros.

## Feature Flag

El modulo se controla por despliegue, no por multitenancy. Cada empresa tiene su propia base de datos y sus propias variables de entorno.

| Variable | Lugar | Funcion |
| --- | --- | --- |
| `PROFIT_AND_LOSS_ENABLED` | Backend | Habilita las rutas EGyP. Si es `false`, responden `404`. |
| `VITE_PROFIT_AND_LOSS_ENABLED` | Frontend | Muestra u oculta el reporte y la administracion en la navegacion. |

Para BOHR local ambas variables tienen valor `true`. Para una instancia de Enfocado pueden mantenerse en `false` sin cambiar el codigo.

## Modelo De Datos

### Centros de resultado

Representan las lineas de negocio o centros de costo que se ven como columnas en el EGyP.

Catalogo inicial BOHR:

- `200`: Administracion.
- `300`: Santa Natura.
- `310`: FQP.
- `340`: Abbott.
- `350`: Colichon.

Los centros tienen codigo, nombre, orden y estado activo. Se inactivan, no se eliminan fisicamente.

### Rubros de resultado

Forman un arbol editable que define como se presenta el reporte. Cada rubro tiene codigo, nombre, padre, orden y naturaleza.

Naturalezas disponibles:

- `INGRESO`
- `CONTRA_INGRESO`
- `COSTO_VENTA`
- `GASTO_OPERATIVO`
- `INGRESO_FINANCIERO`
- `GASTO_FINANCIERO`
- `IMPUESTO`

El catalogo inicial replica la estructura observada en el Excel: ingresos operacionales, ventas, reembolsos, descuentos, costos de venta, personal, administrativos y servicios, logistica, publicidad y marketing, gastos varios, detracciones, ingresos/gastos financieros e impuesto a la renta.

### Lotes y asientos

Cada importacion crea un lote. Cada fila valida crea un asiento con:

- Fecha contable.
- Descripcion y documento.
- Moneda.
- Debe y haber.
- Rubro y centro resueltos.
- Observaciones.
- Usuario, lote y numero de fila de origen.

El reporte no guarda totales editables. Los importes se calculan desde los asientos: `haber - debe`. Por tanto, un credito de ingreso aumenta la utilidad y un debito de gasto la reduce.

## Permisos Y Auditoria

| Operacion | Admin | Asesor |
| --- | --- | --- |
| Consultar resumen EGyP | Si | Si |
| Consultar asientos | Si | Si |
| Crear/editar/inactivar centros | Si | No |
| Crear/editar/inactivar rubros | Si | No |
| Descargar plantilla e importar | Si | No |

Las mutaciones de catalogos y la creacion de lotes se registran en `audit_logs`. Los catalogos utilizados no se borran; se inactivan para proteger el historial.

## Importacion Excel

Ruta de plantilla:

```text
GET /api/v1/ganancias-perdidas/plantilla.xlsx
```

Ruta de carga:

```text
POST /api/v1/ganancias-perdidas/importar.xlsx
```

El archivo debe ser `.xlsx`, tener una hoja llamada `Asientos` y estas cabeceras exactas, en este orden:

```text
fecha,descripcion,documento,moneda,debe,haber,centro_codigo,rubro_codigo,observaciones
```

Reglas principales:

- `fecha`, `descripcion` y moneda ISO son obligatorios.
- `debe` y `haber` no pueden ser negativos; por lo menos uno debe ser mayor que cero.
- `rubro_codigo` es obligatorio y debe existir en el catálogo activo.
- `centro_codigo` es obligatorio, excepto si hay una regla de distribución vigente para el rubro.
- Si cualquier fila falla, no se crea el lote ni se guarda ningun asiento.
- Los errores indican la fila del Excel.

La plantilla incluye hojas de solo consulta para tipificar correctamente los asientos:

- `Lineas de negocio`: códigos y nombres de las líneas activas.
- `Rubros`: códigos, nombres y naturalezas de los rubros activos.
- `Reglas distribucion`: repartos automáticos vigentes.
- `Guia de tipificacion`: reglas de llenado y ejemplos de debe/haber.

Las columnas `centro_codigo`, `rubro_codigo` y `moneda` en `Asientos` tienen listas desplegables. Las hojas guía no se importan como datos: se generan desde la configuración actual del sistema.

Ejemplo:

| fecha | descripcion | documento | moneda | debe | haber | centro_codigo | rubro_codigo |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 2026-06-30 | Planilla junio | PL-060001 | PEN | 12000 | 0 | 200 | PERSONAL |
| 2026-06-30 | Facturacion | F001-001 | PEN | 0 | 25000 | 310 | VENTAS_MERCADERIA |

## Interfaz

### Ganancias y perdidas

Ruta: `/ganancias-perdidas`

- Disponible para administradores y asesores.
- Filtra por fecha desde/hasta.
- Muestra ingresos netos, utilidad bruta, gastos operativos, utilidad operativa y utilidad neta.
- Presenta cada rubro y sus importes por linea de negocio, mas la columna total.

### Configuracion EGyP

Ruta: `/administracion/ganancias-perdidas`

- Solo administradores.
- Permite crear, editar e inactivar centros y rubros.
- Permite descargar la plantilla e importar asientos.

### Operacion EGyP

Ruta: `/administracion/ganancias-perdidas/operacion`

- Solo administradores.
- Crea, edita e inactiva reglas de distribución por rubro.
- Crea, edita y anula asientos manuales, registrando usuario y motivo de anulación.

## Reglas De Distribucion

Una regla distribuye un asiento sin centro informado entre dos o más líneas de negocio. Se configura por rubro, vigencia y porcentajes que deben sumar exactamente 100%.

Prioridad durante una carga:

1. Si la fila incluye `centro_codigo`, se respeta ese centro y no se ejecuta ninguna regla.
2. Sin centro explícito, se busca una regla vigente por rubro.
3. Si no existe regla, la importación se rechaza para que el asiento no quede sin asignación.

Cuando se aplica una regla, el sistema conserva un asiento origen no contabilizable y crea líneas derivadas por cada centro. Las líneas derivadas suman exactamente el debe/haber original y quedan vinculadas al origen para auditoría.

Ejemplo de los repartos observados en el Excel BOHR:

| Concepto | Santa Natura | FQP | Administración |
| --- | ---: | ---: | ---: |
| Alquiler + arbitrios Botica | 70% | 20% | 10% |
| Contabilidad | 40% | 20% | 40% |
| Planilla soporte administrativo | 30% | 30% | 40% |

## Endpoints

| Metodo | Ruta | Uso |
| --- | --- | --- |
| `GET/POST` | `/ganancias-perdidas/centros` | Listar y crear centros. |
| `PATCH/DELETE` | `/ganancias-perdidas/centros/{id}` | Editar e inactivar centro. |
| `GET/POST` | `/ganancias-perdidas/rubros` | Listar y crear rubros. |
| `PATCH/DELETE` | `/ganancias-perdidas/rubros/{id}` | Editar e inactivar rubro. |
| `GET` | `/ganancias-perdidas/plantilla.xlsx` | Descargar plantilla. |
| `POST` | `/ganancias-perdidas/importar.xlsx` | Importar asientos. |
| `GET` | `/ganancias-perdidas/asientos` | Consultar detalle trazable. |
| `POST` | `/ganancias-perdidas/asientos` | Crear asiento manual. |
| `PATCH` | `/ganancias-perdidas/asientos/{id}` | Editar asiento manual directo. |
| `PATCH` | `/ganancias-perdidas/asientos/{id}/anular` | Anular asiento y sus líneas derivadas. |
| `GET/POST` | `/ganancias-perdidas/reglas-distribucion` | Listar y crear reglas. |
| `PATCH/DELETE` | `/ganancias-perdidas/reglas-distribucion/{id}` | Editar e inactivar regla. |
| `GET` | `/ganancias-perdidas/resumen` | Consultar reporte por periodo. |

Todos los endpoints usan el prefijo `/api/v1`.

## Archivos Principales

| Archivo | Responsabilidad |
| --- | --- |
| `app/modules/ganancias_perdidas/models.py` | Entidades y naturalezas contables. |
| `app/modules/ganancias_perdidas/schemas.py` | Contratos API. |
| `app/modules/ganancias_perdidas/routes.py` | Permisos, CRUD, importacion y calculo. |
| `alembic/versions/20260908_0012_create_profit_and_loss.py` | Tablas y migracion. |
| `scripts/seed_bohr_egyp.py` | Catalogo inicial BOHR. |
| `frontend/src/pages/profit-loss.tsx` | Reporte contraíble y detalle trazable. |
| `frontend/src/pages/profit-loss-admin.tsx` | Administración de centros, rubros e importación guiada. |
| `frontend/src/pages/profit-loss-operations.tsx` | Reglas, importación histórica y asientos manuales. |

## Pendientes Del Siguiente Corte

La primera version no debe confundirse con una migracion completa de los libros Excel historicos. Aun faltan:

- Importacion de ventas, notas de credito, costos e inventario desde sus fuentes operativas.
- Validacion de junio, julio y agosto de 2026 contra los totales aprobados del Excel BOHR.

El siguiente trabajo recomendado es tipificar los asientos mediante la plantilla y cargar junio 2026 como periodo de validación, manteniendo el Excel como referencia de control.

## Simulacion Local Junio 2026

Para mostrar el funcionamiento sin declarar una carga contable oficial, se cargó una simulación consolidada con documento `DEMO-EGYP-062026`. Sus importes proceden de `EGYP COSTOS JUNIO MA` y su resultado neto es `-21,817.29`, igual al Excel de referencia.

La simulación no sustituye el proceso de importación de fuentes. Está marcada en observaciones como demo y se puede identificar en el detalle de asientos por su documento. El script `scripts/seed_bohr_junio_demo.py` no duplica la carga si se ejecuta más de una vez.
