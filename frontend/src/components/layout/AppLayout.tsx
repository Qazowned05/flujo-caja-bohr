import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Badge, Box, Button, Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerOverlay, Flex, IconButton, Image, Stack, Text, useDisclosure } from "@chakra-ui/react";
import { api, profitAndLossEnabled } from "../../client/api";
import bohrLogo from "../../../../docs/LOGO BOHR PNG BLANCO (1).png";
type NavItem = { to: string; label: string };
const adminNav: NavItem[] = [
  { to: "/administracion/usuarios", label: "Usuarios" },
  { to: "/administracion/bancos", label: "Bancos y cuentas" },
  { to: "/administracion/sucursales", label: "Sucursales" },
  { to: "/administracion/vendedores", label: "Vendedores" },
  { to: "/administracion/tipificaciones", label: "Tipificaciones" },
  { to: "/administracion/divisas", label: "Divisas" },
];
const cashFlowNav: NavItem[] = [
  { to: "/", label: "Resumen" },
  { to: "/transacciones", label: "Transacciones" },
  { to: "/movimiento-manual", label: "Movimiento manual" },
  { to: "/importar", label: "Importar Excel" },
  { to: "/reportes", label: "Reportes" },
  { to: "/tipificaciones", label: "Referencia de tipificaciones" },
];
const profitLossNav: NavItem[] = profitAndLossEnabled ? [
  { to: "/ganancias-perdidas", label: "Estado de ganancias y pérdidas" },
] : [];
const profitLossAdminNav: NavItem[] = profitAndLossEnabled ? [
  { to: "/administracion/ganancias-perdidas", label: "Configuración EGyP" },
  { to: "/administracion/ganancias-perdidas/operacion", label: "Operación EGyP" },
  { to: "/administracion/ganancias-perdidas/registros", label: "Registros EGyP" },
  { to: "/administracion/ganancias-perdidas/reportes", label: "Reportes EGyP" },
] : [];
function Navigation({ onClose }: { onClose?: () => void }) {
  const user = useQuery({ queryKey: ["me"], queryFn: api.me });
  const navigate = useNavigate();
  const logout = () => {
    localStorage.removeItem(api.tokenKey);
    void navigate({ to: "/login" });
  };
  const [openSections, setOpenSections] = useState({ cash: false, profit: false, admin: false });
  const group = (title: string, section: "cash" | "profit" | "admin", links: NavItem[]) => links.length ? <Box mb="2"><Button w="100%" mt="3" px="2" justifyContent="space-between" variant="ghost" color="whiteAlpha.700" _hover={{ bg: "whiteAlpha.100", color: "white" }} fontSize="xs" letterSpacing=".1em" rightIcon={<span>{openSections[section] ? "−" : "+"}</span>} onClick={() => setOpenSections({ ...openSections, [section]: !openSections[section] })}>{title}</Button>{openSections[section] && <Stack spacing="0" mt="1">{links.map((item) => <Button key={item.to} as={Link} to={item.to} onClick={onClose} justifyContent="flex-start" variant="ghost" color="whiteAlpha.900" _hover={{ bg: "whiteAlpha.200", color: "white" }} size="sm">{item.label}</Button>)}</Stack>}</Box> : null;
  const profitLinks = user.data?.rol === "admin" ? [...profitLossNav, ...profitLossAdminNav] : profitLossNav;
  const administrationLinks = user.data?.rol === "admin" ? adminNav : [];
  return (
    <Flex direction="column" h="100%" bg="#0B2D63" color="white" p="4">
      <Box mb="5" flexShrink="0" display="flex" justifyContent="center">
        <Image src={bohrLogo} alt="BOHR" maxW="170px" maxH="72px" objectFit="contain" />
      </Box>
      <Box flex="1" minH="0" overflowY="auto" pr="1" className="sidebar-menu-scroll">
        {group("FLUJO DE CAJA", "cash", cashFlowNav)}
        {group("GANANCIAS Y PÉRDIDAS", "profit", profitLinks)}
        {group("ADMINISTRACIÓN", "admin", administrationLinks)}
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
          color="blue.200"
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
              Gestión financiera
            </Text>
            <Text fontWeight="semibold">BOHR</Text>
          </Box>
          <Badge colorScheme="blue" variant="subtle">
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
