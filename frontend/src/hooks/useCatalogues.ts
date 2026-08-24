import { useQuery } from "@tanstack/react-query";
import { api } from "../client/api";

export function useCatalogues(includeInactive = false) {
  const actividades = useQuery({ queryKey: ["actividades", includeInactive], queryFn: () => api.actividades(includeInactive) });
  const conceptos = useQuery({ queryKey: ["conceptos", includeInactive], queryFn: () => api.conceptos(includeInactive) });
  const tipos = useQuery({ queryKey: ["tipos", includeInactive], queryFn: () => api.tipos(includeInactive) });
  const sucursales = useQuery({ queryKey: ["sucursales", includeInactive], queryFn: () => api.sucursales(includeInactive) });
  const vendedores = useQuery({ queryKey: ["vendedores", includeInactive], queryFn: () => api.vendedores(includeInactive) });
  const cuentas = useQuery({ queryKey: ["cuentas", includeInactive], queryFn: () => api.cuentas(includeInactive) });
  return { actividades, conceptos, tipos, sucursales, vendedores, cuentas, loading: actividades.isLoading || conceptos.isLoading || tipos.isLoading, error: actividades.error ?? conceptos.error ?? tipos.error };
}

