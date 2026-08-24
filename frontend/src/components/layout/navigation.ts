export const operationNav = [
  { to: "/", label: "Resumen" },
  { to: "/transacciones", label: "Transacciones" },
  { to: "/movimiento-manual", label: "Nuevo movimiento manual" },
  { to: "/importar", label: "Importar CSV" },
  { to: "/reportes", label: "Reportes" },
] as const;

export const adminNav = [
  { to: "/administracion/usuarios", label: "Usuarios" },
  { to: "/administracion/bancos", label: "Bancos y cuentas" },
  { to: "/administracion/sucursales", label: "Sucursales" },
  { to: "/administracion/vendedores", label: "Vendedores" },
  { to: "/administracion/tipificaciones", label: "Arbol de tipificaciones" },
  { to: "/administracion/divisas", label: "Divisas" },
] as const;
