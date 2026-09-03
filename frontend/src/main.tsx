import { ChakraProvider, extendTheme } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { createRootRoute, createRoute, createRouter, redirect } from "@tanstack/react-router";
import React from "react";
import ReactDOM from "react-dom/client";
import { AppLayout } from "./components/layout/AppLayout";
import { BanksPage } from "./pages/banks-admin";
import { BranchesPage } from "./pages/branches-admin";
import { CurrenciesPage } from "./pages/currencies-admin";
import { Dashboard } from "./pages/dashboard";
import { ImportPage } from "./pages/import";
import { Login } from "./pages/login";
import { ManualMovement } from "./pages/manual-movement";
import { Reports } from "./pages/reports";
import { SellersPage } from "./pages/sellers-admin";
import { TipificationsAdminPage } from "./pages/tipifications-admin";
import { TipificationsReferencePage } from "./pages/tipifications-reference";
import { Transactions } from "./pages/transactions";
import { UsersPage } from "./pages/users-admin";
import "./styles.css";
import { api } from "./client/api";

const protectedBeforeLoad = () => {
  const token = localStorage.getItem(api.tokenKey);
  if (!token) throw redirect({ to: "/login" });
  if (api.isTokenExpired(token)) {
    localStorage.removeItem(api.tokenKey);
    throw redirect({ to: "/login", search: { expired: "1" } });
  }
};
const adminBeforeLoad = async () => {
  protectedBeforeLoad();
  const user = await api.me();
  if (user.rol !== "admin") throw redirect({ to: "/" });
};
const rootRoute = createRootRoute();
const layoutRoute = createRoute({ getParentRoute: () => rootRoute, id: "app", component: AppLayout, beforeLoad: protectedBeforeLoad });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: "/login", component: Login });
const indexRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/", component: Dashboard });
const transactionsRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/transacciones", component: Transactions });
const manualRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/movimiento-manual", component: ManualMovement });
const importRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/importar", component: ImportPage });
const reportsRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/reportes", component: Reports });
const tipificationsReferenceRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/tipificaciones", component: TipificationsReferencePage });
const usersRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/administracion/usuarios", component: UsersPage, beforeLoad: adminBeforeLoad });
const banksRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/administracion/bancos", component: BanksPage, beforeLoad: adminBeforeLoad });
const branchesRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/administracion/sucursales", component: BranchesPage, beforeLoad: adminBeforeLoad });
const sellersRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/administracion/vendedores", component: SellersPage, beforeLoad: adminBeforeLoad });
const tipificationsRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/administracion/tipificaciones", component: TipificationsAdminPage, beforeLoad: adminBeforeLoad });
const currenciesRoute = createRoute({ getParentRoute: () => layoutRoute, path: "/administracion/divisas", component: CurrenciesPage, beforeLoad: adminBeforeLoad });
const router = createRouter({ routeTree: rootRoute.addChildren([loginRoute, layoutRoute.addChildren([indexRoute, transactionsRoute, manualRoute, importRoute, reportsRoute, tipificationsReferenceRoute, usersRoute, banksRoute, branchesRoute, sellersRoute, tipificationsRoute, currenciesRoute])]) });
declare module "@tanstack/react-router" { interface Register { router: typeof router } }

const theme = extendTheme({ fonts: { heading: "Inter, system-ui, sans-serif", body: "Inter, system-ui, sans-serif" }, colors: { brand: { 500: "#1d7a64", 600: "#176651" } } });
ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><ChakraProvider theme={theme}><QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider></ChakraProvider></React.StrictMode>);
