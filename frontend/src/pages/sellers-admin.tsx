import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, Button, Card, CardBody, HStack, Input, Select, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api, type Vendedor } from "../client/api";
import { active, confirmDelete, Cancel, Editor, Empty, ErrorBox, Field, Loading, PageTitle, Status } from "../components/common";
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
  const [openBranches, setOpenBranches] = useState<string[]>([]);
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
  const visibleSellers = (sellers.data ?? []).filter((item) =>
    `${item.nombre} ${item.codigo}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
  );
  const groups = [
    ...(branches.data ?? []).map((branch) => ({
      id: branch.id,
      name: branch.nombre,
      code: branch.codigo,
      active: branch.is_active,
      sellers: visibleSellers.filter((seller) => seller.sucursal_id === branch.id),
    })),
    {
      id: "without-branch",
      name: "Sin sucursal",
      code: "",
      active: true,
      sellers: visibleSellers.filter((seller) => !seller.sucursal_id),
    },
  ].filter((group) => !search || group.sellers.length > 0);
  const toggle = (id: string) =>
    setOpenBranches((items) =>
      items.includes(id) ? items.filter((item) => item !== id) : [...items, id],
    );
  const edit = (seller: Vendedor) => {
    setEditing(seller);
    setForm({
      nombre: seller.nombre,
      codigo: seller.codigo,
      sucursal_id: seller.sucursal_id ?? "",
    });
  };
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
      {(sellers.isLoading || branches.isLoading) && <Loading />}
      {(sellers.isError || branches.isError) && <ErrorBox error={sellers.error ?? branches.error} />}
      {!sellers.isLoading && !branches.isLoading && visibleSellers.length === 0 && (
        <Empty text="No hay vendedores." />
      )}
      {groups.length > 0 && (
        <Card>
          <CardBody>
            {groups.map((group) => {
              const isOpen = search ? true : openBranches.includes(group.id);
              return (
                <Box key={group.id} borderBottom="1px solid" borderColor="gray.100" py="3">
                  <HStack>
                    <Button
                      size="xs"
                      variant="ghost"
                      isDisabled={group.sellers.length === 0}
                      onClick={() => toggle(group.id)}
                    >
                      {isOpen ? "-" : "+"}
                    </Button>
                    <Text fontWeight="bold">Sucursal: {group.name}</Text>
                    {group.code && <Text color="gray.500" fontSize="sm">({group.code})</Text>}
                    {group.id !== "without-branch" && <Status active={group.active} />}
                  </HStack>
                  {isOpen && group.sellers.map((seller) => (
                    <HStack key={seller.id} ml={{ base: 3, md: 8 }} mt="3" justify="space-between">
                      <Box>
                        <Text>Vendedor: {seller.nombre} <Text as="span" color="gray.500">({seller.codigo})</Text><Status active={seller.is_active} /></Text>
                      </Box>
                      <HStack>
                        <Button size="xs" onClick={() => edit(seller)}>Editar</Button>
                        <Button
                          size="xs"
                          colorScheme="red"
                          variant="ghost"
                          onClick={() => confirmDelete(seller.nombre) && remove.mutate(seller.id)}
                        >
                          Inactivar
                        </Button>
                      </HStack>
                    </HStack>
                  ))}
                </Box>
              );
            })}
          </CardBody>
        </Card>
      )}
    </Stack>
  );
}





