import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Button, HStack, Input, Select, SimpleGrid, Stack, Td, Tr } from "@chakra-ui/react";
import { api, type Sucursal, type Vendedor } from "../client/api";
import { active, confirmDelete, Cancel, DataTable, Editor, Empty, Field, Loading, PageTitle, Status } from "../components/common";
export function SellersPage() {
  const queryClient = useQueryClient();
  const sellers = useQuery({
    queryKey: ["vendedores"],
    queryFn: () => api.vendedores(true),
  });
  const branches = useQuery({
    queryKey: ["sucursales"],
    queryFn: () => api.sucursales(true),
  });
  const [editing, setEditing] = useState<Vendedor>();
  const [form, setForm] = useState({ nombre: "", codigo: "", sucursal_id: "" });
  const [search, setSearch] = useState("");
  const save = useMutation({
    mutationFn: () =>
      editing
        ? api.updateVendedor(editing.id, {
            ...form,
            sucursal_id: form.sucursal_id || null,
          })
        : api.createVendedor({
            ...form,
            sucursal_id: form.sucursal_id || null,
          }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["vendedores"] });
      setEditing(undefined);
      setForm({ nombre: "", codigo: "", sucursal_id: "" });
    },
  });
  const remove = useMutation({
    mutationFn: api.deleteVendedor,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["vendedores"] }),
  });
  const visibleSellers = sellers.data?.filter((item) =>
    `${item.nombre} ${item.codigo}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
  );
  return (
    <Stack spacing="6">
      <PageTitle
        title="Vendedores"
        description="Asigna opcionalmente cada vendedor a una sucursal activa."
      />
      <Editor
        title={editing ? "Editar vendedor" : "Nuevo vendedor"}
        onSubmit={() => save.mutate()}
        loading={save.isPending}
        error={save.error}
      >
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3">
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
          <Field label="Sucursal">
            <Select
              value={form.sucursal_id}
              onChange={(event) =>
                setForm({ ...form, sucursal_id: event.target.value })
              }
              placeholder="Sin sucursal"
            >
              {active(branches.data).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
            </Select>
          </Field>
        </SimpleGrid>
        <Cancel
          editing={Boolean(editing)}
          onClick={() => {
            setEditing(undefined);
            setForm({ nombre: "", codigo: "", sucursal_id: "" });
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
      {sellers.data && (
        <DataTable
          headers={["Nombre", "Código", "Sucursal", "Estado", ""]}
          empty="No hay vendedores."
        >
          {visibleSellers?.map((item) => (
            <Tr key={item.id}>
              <Td>{item.nombre}</Td>
              <Td>{item.codigo}</Td>
              <Td>
                {branches.data?.find((branch) => branch.id === item.sucursal_id)
                  ?.nombre ?? "Sin sucursal"}
              </Td>
              <Td>
                <Status active={item.is_active} />
              </Td>
              <Td>
                <HStack>
                  <Button
                    size="sm"
                    onClick={() => {
                      setEditing(item);
                      setForm({
                        nombre: item.nombre,
                        codigo: item.codigo,
                        sucursal_id: item.sucursal_id ?? "",
                      });
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





