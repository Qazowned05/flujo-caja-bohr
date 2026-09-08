import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Badge, Box, Button, Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerOverlay, Flex, Heading, IconButton, Stack, Text, useDisclosure } from "@chakra-ui/react";
import { api, profitAndLossEnabled } from "../../client/api";
type NavItem = { to: string; label: string };
const cashFlowNav: NavItem[] = [
  { to: "/", label: "Resumen" },
  { to: "/transacciones", label: "Transacciones" },
  { to: "/movimiento-manual", label: "Nuevo movimiento manual" },
  { to: "/importar", label: "Importar masivo" },
  { to: "/reportes", label: "Reportes" },
];
const adminNav: NavItem[] = [
  { to: "/administracion/usuarios", label: "Usuarios" },
  { to: "/administracion/bancos", label: "Bancos y cuentas" },
  { to: "/administracion/sucursales", label: "Sucursales" },
  { to: "/administracion/vendedores", label: "Vendedores" },
  { to: "/administracion/tipificaciones", label: "Árbol de tipificaciones" },
  { to: "/administracion/divisas", label: "Divisas" },
];
const profitLossNav: NavItem[] = profitAndLossEnabled ? [
  { to: "/ganancias-perdidas", label: "Estado de ganancias y pérdidas" },
] : [];
const profitLossAdminNav: NavItem[] = profitAndLossEnabled ? [
  { to: "/administracion/ganancias-perdidas", label: "Configuración EGyP" },
  { to: "/administracion/ganancias-perdidas/operacion", label: "Operación EGyP" },
] : [];
function Navigation({ onClose }: { onClose?: () => void }) {
  const user = useQuery({ queryKey: ["me"], queryFn: api.me });
  const navigate = useNavigate();
  const logout = () => {
    localStorage.removeItem(api.tokenKey);
    void navigate({ to: "/login" });
  };
  const [openSections, setOpenSections] = useState({ cash: true, profit: true, admin: true });
  const group = (title: string, section: "cash" | "profit" | "admin", links: NavItem[]) => links.length ? <Box mb="2"><Button w="100%" mt="3" px="2" justifyContent="space-between" variant="ghost" color="whiteAlpha.600" _hover={{ bg: "whiteAlpha.100", color: "white" }} fontSize="xs" letterSpacing=".1em" rightIcon={<span>{openSections[section] ? "−" : "+"}</span>} onClick={() => setOpenSections({ ...openSections, [section]: !openSections[section] })}>{title}</Button>{openSections[section] && <Stack spacing="0" mt="1">{links.map((item) => <Button key={item.to} as={Link} to={item.to} onClick={onClose} justifyContent="flex-start" variant="ghost" color="whiteAlpha.800" _hover={{ bg: "whiteAlpha.200", color: "white" }} size="sm">{item.label}</Button>)}</Stack>}</Box> : null;
  const flowLinks = user.data?.rol === "asesor" ? [...cashFlowNav, { to: "/tipificaciones", label: "Guía de tipificaciones" }] : cashFlowNav;
  const profitLinks = user.data?.rol === "admin" ? [...profitLossNav, ...profitLossAdminNav] : profitLossNav;
  return (
    <Flex direction="column" h="100%" bg="#14231f" color="white" p="4">
      <Box mb="1" flexShrink="0">
        <Text fontSize="xs" letterSpacing=".18em" color="teal.200">
          CONTROL FINANCIERO
        </Text>
        <Heading size="md" mt="1">
          Flujo Caja
        </Heading>
      </Box>
      <Box flex="1" minH="0" overflowY="auto" pr="1" className="sidebar-menu-scroll">
        {group("FLUJO DE CAJA", "cash", flowLinks)}
        {group("GANANCIAS Y PÉRDIDAS", "profit", profitLinks)}
        {user.data?.rol === "admin" && group("ADMINISTRACIÓN", "admin", adminNav)}
      </Box>
      <Box flexShrink="0" borderTop="1px solid" borderColor="whiteAlpha.300" pt="4" mt="3">
        <Text fontSize="sm" fontWeight="semibold">
          {user.data?.nombre ?? "Cargando usuario"}
        </Text>
        <Text fontSize="xs" color="whiteAlpha.600">
          {user.data?.email}
        </Text>
        <Button
          mt="3"
          size="sm"
          variant="link"
          color="teal.200"
          onClick={logout}
        >
          Cerrar sesión
        </Button>
      </Box>
    </Flex>
  );
}

export function AppLayout() {
  const drawer = useDisclosure();
  const [sidebarHidden, setSidebarHidden] = useState(false);
  return (
    <Flex minH="100vh" overflowX="hidden">
      <Box
        display={{ base: "none", md: sidebarHidden ? "none" : "block" }}
        w="250px"
        position="fixed"
        insetY="0"
      >
        <Navigation />
      </Box>
      <Drawer isOpen={drawer.isOpen} placement="left" onClose={drawer.onClose}>
        <DrawerOverlay />
        <DrawerContent>
          <DrawerHeader p="0">
            <Box h="100vh">
              <Navigation onClose={drawer.onClose} />
            </Box>
          </DrawerHeader>
          <DrawerBody display="none" />
        </DrawerContent>
      </Drawer>
      <Box ml={{ base: 0, md: sidebarHidden ? 0 : "250px" }} flex="1" minW="0">
        <Flex
          h="68px"
          px={{ base: 4, md: 8 }}
          align="center"
          justify="space-between"
          bg="white"
          borderBottom="1px solid"
          borderColor="gray.200"
        >
          <IconButton
            aria-label="Abrir menú"
            display={{ base: "inline-flex", md: "none" }}
            icon={<span>Menú</span>}
            size="sm"
            onClick={drawer.onOpen}
          />
          <Button
            display={{ base: "none", md: "inline-flex" }}
            size="sm"
            variant="ghost"
            onClick={() => setSidebarHidden((hidden) => !hidden)}
          >
            {sidebarHidden ? "Mostrar menú" : "Ocultar menú"}
          </Button>
          <Box>
            <Text fontSize="sm" color="gray.500">
              Operación financiera
            </Text>
            <Text fontWeight="semibold">Panel de control</Text>
          </Box>
          <Badge colorScheme="green" variant="subtle">
            En línea
          </Badge>
        </Flex>
        <Box p={{ base: 4, md: 8 }} maxW="1500px" minW="0">
          <Outlet />
        </Box>
      </Box>
    </Flex>
  );
}
