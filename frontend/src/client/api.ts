import type { components, paths } from "./schema";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const tokenKey = "flujo-caja-token";
export const profitAndLossEnabled = import.meta.env.VITE_PROFIT_AND_LOSS_ENABLED === "true";

const isTokenExpired = (token: string) => {
  try {
    const payload = token.split(".")[1];
    if (!payload) return true;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), "="))) as {
      exp?: number;
    };
    return typeof decoded.exp !== "number" || decoded.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
};

const expireSession = () => {
  localStorage.removeItem(tokenKey);
  if (window.location.pathname !== "/login") {
    window.location.assign("/login?expired=1");
  }
};

type Schema = components["schemas"];
type JsonResponse<
  P extends keyof paths,
  M extends keyof paths[P],
> = paths[P][M] extends {
  responses: {
    200?: { content: { "application/json": infer R } };
    201?: { content: { "application/json": infer R } };
  };
}
  ? R
  : never;

export type User = Schema["UserRead"];
export type Summary = JsonResponse<"/api/v1/flujo-caja/resumen", "get">;
export type TransactionList = JsonResponse<"/api/v1/transacciones", "get">;
export type ImportResult = JsonResponse<"/api/v1/imports/excel", "post">;
export type BulkResult = JsonResponse<
  "/api/v1/reports/actualizacion-masiva",
  "post"
>;
export type Banco = Schema["BancoRead"];
export type Cuenta = Schema["CuentaBancariaRead"];
export type Sucursal = Schema["SucursalRead"];
export type Vendedor = Schema["VendedorRead"];
export type Actividad = Schema["ActividadRead"];
export type Concepto = Schema["ConceptoRead"];
export type Tipo = Schema["TipoRead"];
export type TipoCambio = Schema["TipoCambioRead"];
export type ManualInput = Schema["TransaccionManualCreate"];
export type MultipleInput = Schema["TransaccionMultipleCreate"];
export type ProjectionInput = Schema["TransaccionProyeccionCreate"];
export type MaterializeInput = Schema["TransaccionMaterializar"];
export type TransactionUpdate = Schema["TransaccionUpdate"];
export type Transaction = Schema["TransaccionRead"];
export type CentroResultado = Schema["CentroResultadoRead"];
export type RubroResultado = Schema["RubroResultadoRead"];
export type ReglaDistribucion = Schema["ReglaDistribucionRead"];
export type AsientoResultado = Schema["AsientoResultadoRead"];
export type EgypSummary = JsonResponse<"/api/v1/ganancias-perdidas/resumen", "get">;
export type EgypImportResult = JsonResponse<"/api/v1/ganancias-perdidas/importar.xlsx", "post">;
export type TipificationBreakdown = JsonResponse<
  "/api/v1/flujo-caja/desglose-tipificaciones",
  "get"
>;

type RowError = { fila: number; mensaje: string };

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly rowErrors: RowError[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const endpoint = (path: string) => `${API_URL}${path.replace("/api/v1", "")}`;
const isRowErrors = (value: unknown): value is { errores: RowError[] } =>
  typeof value === "object" &&
  value !== null &&
  "errores" in value &&
  Array.isArray(value.errores) &&
  value.errores.every(
    (error) =>
      typeof error === "object" &&
      error !== null &&
      "fila" in error &&
      "mensaje" in error,
  );

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(tokenKey);
  const response = await fetch(endpoint(path), {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    if (response.status === 401 && token) expireSession();
    const data: unknown = await response.json().catch(() => null);
    const rowErrors = response.status === 422
      ? isRowErrors(data)
        ? data.errores
        : typeof data === "object" && data !== null && "detail" in data && isRowErrors(data.detail)
          ? data.detail.errores
          : []
      : [];
    const message = rowErrors.length
      ? rowErrors
          .map((error) => `Fila ${error.fila}: ${error.mensaje}`)
          .join(". ")
      : typeof data === "object" && data !== null && "detail" in data
        ? typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail
                .map((item) =>
                  typeof item === "object" && item !== null && "msg" in item
                    ? String(item.msg)
                    : "Datos inválidos.",
                )
                .join(". ")
            : "Datos inválidos."
        : `Error ${response.status}`;
    throw new ApiError(response.status, message, rowErrors);
  }
  return response.json() as Promise<T>;
}

const json = <T>(path: string, method: "POST" | "PATCH", body: T) =>
  request<unknown>(path, {
    method,
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
  });

export const api = {
  tokenKey,
  isTokenExpired,
  login: (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    return request<Schema["Token"]>("/api/v1/login/access-token", {
      method: "POST",
      body: form,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  me: () => request<User>("/api/v1/users/me"),
  users: () => request<User[]>("/api/v1/users"),
  createUser: (body: Schema["UserCreate"]) =>
    json("/api/v1/users", "POST", body) as Promise<User>,
  updateUser: (id: string, body: Schema["UserUpdate"]) =>
    json(`/api/v1/users/${id}`, "PATCH", body) as Promise<User>,
  bancos: (includeInactive = false) =>
    request<Banco[]>(
      `/api/v1/bancos${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  cuentas: (includeInactive = false) =>
    request<Cuenta[]>(
      `/api/v1/cuentas-bancarias${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  sucursales: (includeInactive = false) =>
    request<Sucursal[]>(
      `/api/v1/sucursales${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  vendedores: (includeInactive = false) =>
    request<Vendedor[]>(
      `/api/v1/vendedores${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  actividades: (includeInactive = false) =>
    request<Actividad[]>(
      `/api/v1/actividades${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  conceptos: (includeInactive = false) =>
    request<Concepto[]>(
      `/api/v1/conceptos${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  tipos: (includeInactive = false) =>
    request<Tipo[]>(
      `/api/v1/tipos${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  tiposCambio: (includeInactive = false) =>
    request<TipoCambio[]>(
      `/api/v1/divisas/tipos-cambio${includeInactive ? "?include_inactive=true" : ""}`,
    ),
  createBanco: (body: Schema["BancoCreate"]) =>
    json("/api/v1/bancos", "POST", body),
  updateBanco: (id: string, body: Schema["BancoUpdate"]) =>
    json(`/api/v1/bancos/${id}`, "PATCH", body),
  deleteBanco: (id: string) =>
    request<unknown>(`/api/v1/bancos/${id}`, { method: "DELETE" }),
  createCuenta: (body: Schema["CuentaBancariaCreate"]) =>
    json("/api/v1/cuentas-bancarias", "POST", body),
  updateCuenta: (id: string, body: Schema["CuentaBancariaUpdate"]) =>
    json(`/api/v1/cuentas-bancarias/${id}`, "PATCH", body),
  deleteCuenta: (id: string) =>
    request<unknown>(`/api/v1/cuentas-bancarias/${id}`, { method: "DELETE" }),
  createSucursal: (body: Schema["SucursalCreate"]) =>
    json("/api/v1/sucursales", "POST", body),
  updateSucursal: (id: string, body: Schema["SucursalUpdate"]) =>
    json(`/api/v1/sucursales/${id}`, "PATCH", body),
  deleteSucursal: (id: string) =>
    request<unknown>(`/api/v1/sucursales/${id}`, { method: "DELETE" }),
  createVendedor: (body: Schema["VendedorCreate"]) =>
    json("/api/v1/vendedores", "POST", body),
  updateVendedor: (id: string, body: Schema["VendedorUpdate"]) =>
    json(`/api/v1/vendedores/${id}`, "PATCH", body),
  deleteVendedor: (id: string) =>
    request<unknown>(`/api/v1/vendedores/${id}`, { method: "DELETE" }),
  createActividad: (body: Schema["ActividadCreate"]) =>
    json("/api/v1/actividades", "POST", body),
  updateActividad: (id: string, body: Schema["ActividadUpdate"]) =>
    json(`/api/v1/actividades/${id}`, "PATCH", body),
  deleteActividad: (id: string) =>
    request<unknown>(`/api/v1/actividades/${id}`, { method: "DELETE" }),
  createConcepto: (body: Schema["ConceptoCreate"]) =>
    json("/api/v1/conceptos", "POST", body),
  updateConcepto: (id: string, body: Schema["ConceptoUpdate"]) =>
    json(`/api/v1/conceptos/${id}`, "PATCH", body),
  deleteConcepto: (id: string) =>
    request<unknown>(`/api/v1/conceptos/${id}`, { method: "DELETE" }),
  createTipo: (body: Schema["TipoCreate"]) =>
    json("/api/v1/tipos", "POST", body),
  updateTipo: (id: string, body: Schema["TipoUpdate"]) =>
    json(`/api/v1/tipos/${id}`, "PATCH", body),
  deleteTipo: (id: string) =>
    request<unknown>(`/api/v1/tipos/${id}`, { method: "DELETE" }),
  createTipoCambio: (body: Schema["TipoCambioCreate"]) =>
    json("/api/v1/divisas/tipos-cambio", "POST", body),
  updateTipoCambio: (id: string, body: Schema["TipoCambioUpdate"]) =>
    json(`/api/v1/divisas/tipos-cambio/${id}`, "PATCH", body),
  deleteTipoCambio: (id: string) =>
    request<unknown>(`/api/v1/divisas/tipos-cambio/${id}`, {
      method: "DELETE",
    }),
  createManual: (body: ManualInput) =>
    json("/api/v1/transacciones/manual", "POST", body),
  createMultiple: (body: MultipleInput) =>
    json("/api/v1/transacciones/multiple", "POST", body) as Promise<Transaction>,
  createProjection: (body: ProjectionInput) =>
    json(
      "/api/v1/transacciones/proyeccion",
      "POST",
      body,
    ) as Promise<Transaction>,
  materializeProjection: (id: string, body: MaterializeInput) =>
    json(`/api/v1/transacciones/${id}/materializar`, "PATCH", body) as Promise<Transaction>,
  updateTransaction: (id: string, body: TransactionUpdate) =>
    json(`/api/v1/transacciones/${id}`, "PATCH", body) as Promise<Transaction>,
  updateMultipleOperations: (id: string, operaciones: string[]) =>
    json(`/api/v1/transacciones/${id}/operaciones`, "PATCH", { operaciones }) as Promise<Transaction>,
  cancelTransaction: (id: string) =>
    request<Transaction>(`/api/v1/transacciones/${id}/anular`, {
      method: "PATCH",
    }),
  deleteTransaction: (id: string) =>
    request<void>(`/api/v1/transacciones/${id}`, { method: "DELETE" }),
  summary: (params: URLSearchParams) =>
    request<Summary>(`/api/v1/flujo-caja/resumen?${params}`),
  tipificationBreakdown: (params: URLSearchParams) =>
    request<TipificationBreakdown>(
      `/api/v1/flujo-caja/desglose-tipificaciones?${params}`,
    ),
  transactions: (params: URLSearchParams) =>
    request<TransactionList>(`/api/v1/transacciones?${params}`),
  importBulk: (accountId: string, file: File, type: "REAL" | "PROYECCION" = "REAL") => {
    const form = new FormData();
    form.append("cuenta_bancaria_id", accountId);
    form.append("archivo", file);
    form.append("tipo_importacion", type);
    return request<ImportResult>("/api/v1/imports/excel", {
      method: "POST",
      body: form,
    });
  },
  bulkUpdate: (file: File, confirm: boolean) => {
    const form = new FormData();
    form.append("archivo", file);
    form.append("confirmar", String(confirm));
    return request<BulkResult>("/api/v1/reports/actualizacion-masiva", {
      method: "POST",
      body: form,
    });
  },
  download: async (path: string) => {
    const token = localStorage.getItem(tokenKey);
    const response = await fetch(endpoint(path), {
      headers: {
        Authorization: `Bearer ${token ?? ""}`,
      },
    });
    if (response.status === 401 && token) expireSession();
    if (!response.ok)
      throw new ApiError(response.status, `Error ${response.status}`);
    return response.blob();
  },
  egypCentros: (includeInactive = false) => request<CentroResultado[]>(
    `/api/v1/ganancias-perdidas/centros${includeInactive ? "?include_inactive=true" : ""}`,
  ),
  egypRubros: (includeInactive = false) => request<RubroResultado[]>(
    `/api/v1/ganancias-perdidas/rubros${includeInactive ? "?include_inactive=true" : ""}`,
  ),
  createEgypCentro: (body: Schema["CentroResultadoCreate"]) => json("/api/v1/ganancias-perdidas/centros", "POST", body),
  updateEgypCentro: (id: string, body: Schema["CentroResultadoUpdate"]) => json(`/api/v1/ganancias-perdidas/centros/${id}`, "PATCH", body),
  deleteEgypCentro: (id: string) => request<unknown>(`/api/v1/ganancias-perdidas/centros/${id}`, { method: "DELETE" }),
  createEgypRubro: (body: Schema["RubroResultadoCreate"]) => json("/api/v1/ganancias-perdidas/rubros", "POST", body),
  updateEgypRubro: (id: string, body: Schema["RubroResultadoUpdate"]) => json(`/api/v1/ganancias-perdidas/rubros/${id}`, "PATCH", body),
  deleteEgypRubro: (id: string) => request<unknown>(`/api/v1/ganancias-perdidas/rubros/${id}`, { method: "DELETE" }),
  egypReglas: (includeInactive = false) => request<ReglaDistribucion[]>(
    `/api/v1/ganancias-perdidas/reglas-distribucion${includeInactive ? "?include_inactive=true" : ""}`,
  ),
  createEgypRegla: (body: Schema["ReglaDistribucionCreate"]) => json("/api/v1/ganancias-perdidas/reglas-distribucion", "POST", body),
  updateEgypRegla: (id: string, body: Schema["ReglaDistribucionCreate"]) => json(`/api/v1/ganancias-perdidas/reglas-distribucion/${id}`, "PATCH", body),
  deleteEgypRegla: (id: string) => request<unknown>(`/api/v1/ganancias-perdidas/reglas-distribucion/${id}`, { method: "DELETE" }),
  egypSummary: (params: URLSearchParams) => request<EgypSummary>(`/api/v1/ganancias-perdidas/resumen?${params}`),
  egypEntries: (params: URLSearchParams) => request<AsientoResultado[]>(`/api/v1/ganancias-perdidas/asientos?${params}`),
  createEgypEntry: (body: Schema["AsientoResultadoCreate"]) => json("/api/v1/ganancias-perdidas/asientos", "POST", body) as Promise<AsientoResultado>,
  updateEgypEntry: (id: string, body: Schema["AsientoResultadoUpdate"]) => json(`/api/v1/ganancias-perdidas/asientos/${id}`, "PATCH", body) as Promise<AsientoResultado>,
  cancelEgypEntry: (id: string, motivo: string) => json(`/api/v1/ganancias-perdidas/asientos/${id}/anular`, "PATCH", { motivo }) as Promise<AsientoResultado>,
  importEgyp: (file: File) => {
    const form = new FormData();
    form.append("archivo", file);
    return request<EgypImportResult>("/api/v1/ganancias-perdidas/importar.xlsx", { method: "POST", body: form });
  },
};
