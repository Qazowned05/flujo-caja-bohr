# Frontend de Flujo Caja

Aplicación React + TypeScript construida con Vite, Chakra UI v2, TanStack Query y TanStack Router.

## Requisitos

Node.js 20+ y Python con las dependencias de la API instaladas. El generador importa `app.main.app` para obtener el contrato OpenAPI.

## Inicio local

1. Copia `.env.example` como `.env` si necesitas cambiar la URL de API. Por defecto usa `http://localhost:8000/api/v1`.
2. Instala dependencias: `npm install`.
3. Genera los tipos del contrato: `npm run generate-client`.
4. Inicia el cliente: `npm run dev`.
5. Abre la dirección indicada por Vite, habitualmente `http://localhost:5173`.

El servidor de Vite también tiene un proxy opcional para `/api` hacia `http://localhost:8000`.

## Verificación

Ejecuta `npm run build` para comprobar TypeScript estricto y crear la distribución en `dist/`.

## Cliente API

`src/client/schema.ts` es generado por `openapi-typescript`; no debe editarse manualmente. `src/client/api.ts` ofrece la capa pequeña de llamadas autenticadas y toma el token Bearer de `localStorage`.

Después de añadir o cambiar endpoints del backend, ejecuta siempre `npm run generate-client` antes de compilar. La capa API usa esos esquemas para los payloads de catálogos, usuarios, divisas y movimientos manuales.

## Arquitectura

- `src/pages/` contiene los puntos de entrada por ruta: login, dashboard, transacciones, movimiento manual, importación, reportes y administración.
- `src/components/layout/` contiene el shell autenticado y la definición de navegación; `src/components/common/` agrupa estados reutilizables de carga, error y vacío.
- `src/hooks/useCatalogues.ts` concentra las consultas TanStack Query de cuentas, sucursales, vendedores y niveles de tipificación.
- `src/lib/` contiene formato de dinero/fechas/errores y descarga de archivos.
- `src/pages.tsx` queda como un índice pequeño de reexports para consumidores internos; las rutas se importan directamente desde sus módulos en `src/main.tsx`.

El dashboard mantiene el resumen y desglose con los mismos filtros de período, cuenta e inclusión de proyecciones. El período usa dos campos de fecha compactos, inicializados desde el primer día del mes actual hasta hoy.

## Operación

- `Resumen` permite incluir o excluir proyecciones de las consultas, filtrar por cuenta y visualizar la matriz expandible Actividad > Concepto > Tipo por día en PEN o USD. Incluye filas no interactivas de saldo inicial y final por fecha; las columnas de jerarquía y total permanecen visibles al desplazarse horizontalmente y una celda diaria no nula de actividad abre el desglose de sus movimientos.
- `Transacciones` filtra por cuenta activa, creador, fecha y tipificación desde la matriz. Permite filtrar las transacciones propias o, para administradores, las de cualquier usuario; muestra creador, sucursal, vendedor y tipificación. Además permite editar únicamente vendedor, sucursal, observaciones y tipificación, y los administradores pueden anular con confirmación. La anulación preserva la auditoría y excluye el movimiento del flujo.
- `Nuevo movimiento manual` registra un movimiento real en `POST /transacciones/manual` o una proyección en `POST /transacciones/proyeccion`. Los selectores sólo muestran cuentas y catálogos activos; actividad, concepto y tipo son selectores en cascada.
- `Importar CSV` solicita una cuenta activa por alias y moneda. Cuando la API rechaza el archivo con errores por fila, éstos se muestran en el mensaje de error.

## Administración

Las rutas bajo `/administracion/*` se validan tanto en la navegación como al cargar la ruta con el usuario autenticado y rol `admin`.

- Usuarios: alta y edición de nombre, rol, contraseña y estado activo.
- Bancos, cuentas, sucursales y vendedores: creación, edición e inactivación lógica con confirmación. Las cuentas admiten saldo inicial decimal, incluso negativo, como saldo de apertura para el flujo de caja.
- Tipificaciones: alta e inactivación del árbol Actividad > Concepto > Tipo.
- Divisas: alta, edición, activación e inactivación de tipos de cambio de referencia.
