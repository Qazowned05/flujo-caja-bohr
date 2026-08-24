import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Alert, AlertIcon, Button, Card, CardBody, Flex, Heading, Input, Stack, Text } from "@chakra-ui/react";
import { api } from "../client/api";
import { active, confirmDelete, ErrorBox, Field } from "../components/common";
export function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api.login(email, password),
    onSuccess: (result) => {
      localStorage.setItem(api.tokenKey, result.access_token);
      void navigate({ to: "/" });
    },
  });
  const sessionExpired = new URLSearchParams(window.location.search).get("expired") === "1";
  return (
    <Flex minH="100vh" bg="#10211d" align="center" justify="center" p="5">
      <Card w="full" maxW="440px" shadow="2xl">
        <CardBody p={{ base: 7, md: 10 }}>
          <Text
            color="brand.600"
            fontSize="xs"
            fontWeight="bold"
            letterSpacing=".16em"
          >
            CONTROL FINANCIERO
          </Text>
          <Heading mt="3" size="lg">
            Bienvenido de vuelta
          </Heading>
           <Text color="gray.500" mt="2" mb="8">
             Accede a la operación de Flujo Caja.
           </Text>
           {sessionExpired && <Alert status="warning" mb="6" borderRadius="md">
             <AlertIcon />
             Tu sesión expiró. Ingresa nuevamente para continuar.
           </Alert>}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              login.mutate();
            }}
          >
            <Stack spacing="5">
              <Field label="Correo electrónico">
                <Input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </Field>
              <Field label="Contraseña">
                <Input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </Field>
              {login.isError && <ErrorBox error={login.error} />}
              <Button
                type="submit"
                colorScheme="brand"
                isLoading={login.isPending}
              >
                Ingresar al panel
              </Button>
            </Stack>
          </form>
        </CardBody>
      </Card>
    </Flex>
  );
}





