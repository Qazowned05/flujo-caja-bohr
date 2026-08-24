import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Button, HStack, Input, SimpleGrid, Stack, Switch, Td, Tr } from "@chakra-ui/react";
import { api, type TipoCambio } from "../client/api";
import { active, confirmDelete, Cancel, DataTable, Editor, Empty, Field, Loading, PageTitle, Status } from "../components/common";
import { today } from "../lib/format";
export function CurrenciesPage() {
  const queryClient = useQueryClient();
  const rates = useQuery({
    queryKey: ["tipos-cambio"],
    queryFn: () => api.tiposCambio(true),
  });
  const [editing, setEditing] = useState<TipoCambio>();
  const [form, setForm] = useState({
    moneda_origen: "USD",
    moneda_destino: "PEN",
    tasa: "",
    fecha_vigencia: today(),
    is_active: true,
  });
  const save = useMutation({
    mutationFn: () =>
      editing
        ? api.updateTipoCambio(editing.id, form)
        : api.createTipoCambio({
            moneda_origen: form.moneda_origen,
            moneda_destino: form.moneda_destino,
            tasa: form.tasa,
            fecha_vigencia: form.fecha_vigencia,
          }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tipos-cambio"] });
      setEditing(undefined);
      setForm({
        moneda_origen: "USD",
        moneda_destino: "PEN",
        tasa: "",
        fecha_vigencia: today(),
        is_active: true,
      });
    },
  });
  const remove = useMutation({
    mutationFn: api.deleteTipoCambio,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["tipos-cambio"] }),
  });
  return (
    <Stack spacing="6">
      <PageTitle
        title="Divisas"
        description="El tipo de cambio es una referencia para operaciones entre cuentas. El dashboard mantiene los totales separados por divisa."
      />
      <Editor
        title={editing ? "Editar tipo de cambio" : "Nuevo tipo de cambio"}
        onSubmit={() => save.mutate()}
        loading={save.isPending}
        error={save.error}
      >
        <SimpleGrid columns={{ base: 1, md: 5 }} spacing="3">
          <Field label="Origen" required>
            <Input
              maxLength={3}
              value={form.moneda_origen}
              onChange={(event) =>
                setForm({
                  ...form,
                  moneda_origen: event.target.value.toUpperCase(),
                })
              }
            />
          </Field>
          <Field label="Destino" required>
            <Input
              maxLength={3}
              value={form.moneda_destino}
              onChange={(event) =>
                setForm({
                  ...form,
                  moneda_destino: event.target.value.toUpperCase(),
                })
              }
            />
          </Field>
          <Field label="Tasa" required>
            <Input
              type="number"
              step="0.000001"
              value={form.tasa}
              onChange={(event) =>
                setForm({ ...form, tasa: event.target.value })
              }
            />
          </Field>
          <Field label="Fecha vigencia" required>
            <Input
              type="date"
              value={form.fecha_vigencia}
              onChange={(event) =>
                setForm({ ...form, fecha_vigencia: event.target.value })
              }
            />
          </Field>
          {editing && (
            <Field label="Activo">
              <Switch
                mt="2"
                isChecked={form.is_active}
                onChange={(event) =>
                  setForm({ ...form, is_active: event.target.checked })
                }
              />
            </Field>
          )}
        </SimpleGrid>
        <Cancel
          editing={Boolean(editing)}
          onClick={() => {
            setEditing(undefined);
            setForm({
              moneda_origen: "USD",
              moneda_destino: "PEN",
              tasa: "",
              fecha_vigencia: today(),
              is_active: true,
            });
          }}
        />
      </Editor>
      {rates.data && (
        <DataTable
          headers={["Origen", "Destino", "Tasa", "Vigencia", "Estado", ""]}
          empty="No hay tipos de cambio."
        >
          {rates.data.map((item) => (
            <Tr key={item.id}>
              <Td>{item.moneda_origen}</Td>
              <Td>{item.moneda_destino}</Td>
              <Td>{item.tasa}</Td>
              <Td>{item.fecha_vigencia}</Td>
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
                        moneda_origen: item.moneda_origen,
                        moneda_destino: item.moneda_destino,
                        tasa: item.tasa,
                        fecha_vigencia: item.fecha_vigencia,
                        is_active: item.is_active,
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
                      confirmDelete(
                        `${item.moneda_origen}/${item.moneda_destino}`,
                      ) && remove.mutate(item.id)
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





