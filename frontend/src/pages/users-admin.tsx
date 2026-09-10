import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Badge, Box, Button, Card, CardBody, HStack, Input, Select, SimpleGrid, Stack, Switch, Td, Text, Tr } from "@chakra-ui/react";
import { api, type User } from "../client/api";
import { active, confirmDelete, DataTable, Empty, ErrorBox, Field, Loading, PageTitle } from "../components/common";
export function UsersPage() {
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: api.users });
  const [editing, setEditing] = useState<User>();
  const [form, setForm] = useState({
    email: "",
    nombre: "",
    rol: "asesor" as "admin" | "asesor",
    password: "",
    is_active: true,
  });
  const save = useMutation({
    mutationFn: () =>
      editing
        ? api.updateUser(editing.id, {
            nombre: form.nombre,
            rol: form.rol,
            is_active: form.is_active,
            ...(form.password ? { password: form.password } : {}),
          })
        : api.createUser({
            email: form.email,
            nombre: form.nombre,
            rol: form.rol,
            password: form.password,
          }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      setEditing(undefined);
      setForm({
        email: "",
        nombre: "",
        rol: "asesor",
        password: "",
        is_active: true,
      });
    },
  });
  const edit = (user: User) => {
    setEditing(user);
    setForm({
      email: user.email,
      nombre: user.nombre,
      rol: user.rol,
      password: "",
      is_active: user.is_active,
    });
  };
  return (
    <Stack spacing="6">
      <PageTitle
        title="Usuarios"
        description="Crea usuarios, actualiza su rol, contraseña y estado."
      />
      <Card>
        <CardBody>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              save.mutate();
            }}
          >
            <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing="4">
              <Field label="Correo" required>
                <Input
                  type="email"
                  value={form.email}
                  disabled={Boolean(editing)}
                  onChange={(event) =>
                    setForm({ ...form, email: event.target.value })
                  }
                />
              </Field>
              <Field label="Nombre" required>
                <Input
                  value={form.nombre}
                  onChange={(event) =>
                    setForm({ ...form, nombre: event.target.value })
                  }
                />
              </Field>
              <Field label="Rol">
                <Select
                  value={form.rol}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      rol: event.target.value as "admin" | "asesor",
                    })
                  }
                >
                  <option value="asesor">Asesor</option>
                  <option value="admin">Administrador</option>
                </Select>
              </Field>
              <Field
                label={editing ? "Nueva contraseña (opcional)" : "Contraseña"}
                required={!editing}
              >
                <Input
                  type="password"
                  value={form.password}
                  onChange={(event) =>
                    setForm({ ...form, password: event.target.value })
                  }
                />
              </Field>
            </SimpleGrid>
            {editing && (
              <HStack mt="4">
                <Switch
                  isChecked={form.is_active}
                  onChange={(event) =>
                    setForm({ ...form, is_active: event.target.checked })
                  }
                />{" "}
                <Text>Usuario activo</Text>
              </HStack>
            )}
            <HStack mt="5">
              <Button
                type="submit"
                colorScheme="brand"
                isLoading={save.isPending}
              >
                {editing ? "Guardar cambios" : "Crear usuario"}
              </Button>
              {editing && (
                <Button
                  onClick={() => {
                    setEditing(undefined);
                    setForm({
                      email: "",
                      nombre: "",
                      rol: "asesor",
                      password: "",
                      is_active: true,
                    });
                  }}
                >
                  Cancelar
                </Button>
              )}
            </HStack>
            {save.isError && (
              <Box mt="3">
                <ErrorBox error={save.error} />
              </Box>
            )}
          </form>
        </CardBody>
      </Card>
      {users.isLoading && <Loading />}
      {users.isError && <ErrorBox error={users.error} />}
      {users.data && (
        <DataTable
          headers={["Nombre", "Correo", "Rol", "Estado", ""]}
          empty="No hay usuarios."
        >
          {users.data.map((user) => (
            <Tr key={user.id}>
              <Td>{user.nombre}</Td>
              <Td>{user.email}</Td>
              <Td>
                <Badge>{user.rol}</Badge>
              </Td>
              <Td>
                <Badge colorScheme={user.is_active ? "green" : "gray"}>
                  {user.is_active ? "Activo" : "Inactivo"}
                </Badge>
              </Td>
              <Td>
                <Button size="sm" onClick={() => edit(user)}>
                  Editar
                </Button>
              </Td>
            </Tr>
          ))}
        </DataTable>
      )}
    </Stack>
  );
}





