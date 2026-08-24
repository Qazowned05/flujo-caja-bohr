import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Button, HStack, Input, SimpleGrid, Stack, Td, Tr } from "@chakra-ui/react";
import { api, type Sucursal } from "../client/api";
import { active, confirmDelete, Cancel, DataTable, Editor, Empty, Field, Loading, PageTitle, Status } from "../components/common";
export function BranchesPage() {
  const queryClient = useQueryClient();
  const branches = useQuery({
    queryKey: ["sucursales"],
    queryFn: () => api.sucursales(true),
  });
  const [editing, setEditing] = useState<Sucursal>();
  const [form, setForm] = useState({ nombre: "", codigo: "" });
  const [search, setSearch] = useState("");
  const save = useMutation({
    mutationFn: () =>
      editing ? api.updateSucursal(editing.id, form) : api.createSucursal(form),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sucursales"] });
      setEditing(undefined);
      setForm({ nombre: "", codigo: "" });
    },
  });
  const remove = useMutation({
    mutationFn: api.deleteSucursal,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["sucursales"] }),
  });
  const visibleBranches = branches.data?.filter((item) =>
    `${item.nombre} ${item.codigo}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
  );
  return (
    <Stack spacing="6">
      <PageTitle
        title="Sucursales"
        description="Administra las sucursales disponibles."
      />
      <Editor
        title={editing ? "Editar sucursal" : "Nueva sucursal"}
        onSubmit={() => save.mutate()}
        loading={save.isPending}
        error={save.error}
      >
        <SimpleGrid columns={2} spacing="3">
          <Field label="Nombre" required>
            <Input
              value={form.nombre}
              onChange={(event) =>
                setForm({ ...form, nombre: event.target.value })
              }
            />
          </Field>
          <Field label="Código" required>
            <Input
              value={form.codigo}
              onChange={(event) =>
                setForm({ ...form, codigo: event.target.value })
              }
            />
          </Field>
        </SimpleGrid>
        <Cancel
          editing={Boolean(editing)}
          onClick={() => {
            setEditing(undefined);
            setForm({ nombre: "", codigo: "" });
          }}
        />
      </Editor>
      <Field label="Buscar">
        <Input
          placeholder="Nombre o código"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </Field>
      {branches.data && (
        <DataTable
          headers={["Nombre", "Código", "Estado", ""]}
          empty="No hay sucursales."
        >
          {visibleBranches?.map((item) => (
            <Tr key={item.id}>
              <Td>{item.nombre}</Td>
              <Td>{item.codigo}</Td>
              <Td>
                <Status active={item.is_active} />
              </Td>
              <Td>
                <HStack>
                  <Button
                    size="sm"
                    onClick={() => {
                      setEditing(item);
                      setForm({ nombre: item.nombre, codigo: item.codigo });
                    }}
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() =>
                      confirmDelete(item.nombre) && remove.mutate(item.id)
                    }
                  >
                    Inactivar
                  </Button>
                </HStack>
              </Td>
            </Tr>
          ))}
        </DataTable>
      )}
    </Stack>
  );
}





