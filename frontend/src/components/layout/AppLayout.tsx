import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Badge, Box, Button, Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerOverlay, Flex, Heading, IconButton, Stack, Text, useDisclosure } from "@chakra-ui/react";
import { api } from "../../client/api";
const operationNav = [
  { to: "/", label: "Resumen" },
  { to: "/transacciones", label: "Transacciones" },
  { to: "/movimiento-manual", label: "Nuevo movimiento manual" },
  { to: "/importar", label: "Importar masivo" },
  { to: "/reportes", label: "Reportes" },
];
const advisorNav = [...operationNav, { to: "/tipificaciones", label: "Guía de tipificaciones" }];
const adminNav = [
  { to: "/administracion/usuarios", label: "Usuarios" },
  { to: "/administracion/bancos", label: "Bancos y cuentas" },
  { to: "/administracion/sucursales", label: "Sucursales" },
  { to: "/administracion/vendedores", label: "Vendedores" },
  { to: "/administracion/tipificaciones", label: "Árbol de tipificaciones" },
  { to: "/administracion/divisas", label: "Divisas" },
];
function Navigation({ onClose }: { onClose?: () => void }) {
  const user = useQuery({ queryKey: ["me"], queryFn: api.me });
  const navigate = useNavigate();
  const logout = () => {
    localStorage.removeItem(api.tokenKey);
    void navigate({ to: "/login" });
  };
  const group = (title: string, links: typeof operationNav) => (
    <>
      <Text
        mt="5"
        mb="1"
        fontSize="xs"
        letterSpacing=".12em"
        color="whiteAlpha.500"
      >
        {title}
      </Text>
      {links.map((item) => (
        <Button
          key={item.to}
          as={Link}
          to={item.to}
          onClick={onClose}
          justifyContent="flex-start"
          variant="ghost"
          color="whiteAlpha.800"
          _hover={{ bg: "whiteAlpha.200", color: "white" }}
          size="sm"
        >
          {item.label}
        </Button>
      ))}
    </>
  );
  return (
    <Flex direction="column" h="100%" bg="#14231f" color="white" p="4">
      <Box mb="4">
        <Text fontSize="xs" letterSpacing=".18em" color="teal.200">
          CONTROL FINANCIERO
        </Text>
        <Heading size="md" mt="1">
          Flujo Caja
        </Heading>
      </Box>
      <Stack spacing="1">
        {group("OPERACIÓN", user.data?.rol === "asesor" ? advisorNav : operationNav)}
        {user.data?.rol === "admin" && group("ADMINISTRACIÓN", adminNav)}
      </Stack>
      <Box mt="auto" borderTop="1px solid" borderColor="whiteAlpha.300" pt="4">
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

