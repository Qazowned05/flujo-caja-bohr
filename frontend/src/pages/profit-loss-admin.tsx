import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  HStack,
  Input,
  Select,
  SimpleGrid,
  Stack,
  Td,
  Tr,
} from "@chakra-ui/react";
import { api, type CentroResultado, type RubroResultado } from "../client/api";
import {
  confirmDelete,
  DataTable,
  Editor,
  Field,
  PageTitle,
  Status,
  TablePagination,
} from "../components/common";

type Naturaleza = NonNullable<RubroResultado["naturaleza"]>;
const refreshKeys = ["egyp-centros", "egyp-rubros"];
const emptyCenter = { codigo: "", nombre: "", orden: "0" };
const emptyRubro: {
  codigo: string;
  nombre: string;
  naturaleza: Naturaleza;
  padre_id: string;
  orden: string;
} = { codigo: "", nombre: "", naturaleza: "INGRESO", padre_id: "", orden: "0" };

export function ProfitLossAdminPage() {
  const queryClient = useQueryClient();
  const centers = useQuery({
    queryKey: ["egyp-centros"],
    queryFn: () => api.egypCentros(true),
  });
  const rubros = useQuery({
    queryKey: ["egyp-rubros"],
    queryFn: () => api.egypRubros(true),
  });
  const [center, setCenter] = useState(emptyCenter);
  const [rubro, setRubro] = useState(emptyRubro);
  const [editingCenter, setEditingCenter] = useState<CentroResultado>();
  const [editingRubro, setEditingRubro] = useState<RubroResultado>();
  const [rubroPage, setRubroPage] = useState(1);
  const refresh = () =>
    refreshKeys.forEach(
      (key) => void queryClient.invalidateQueries({ queryKey: [key] }),
    );
  const saveCenter = useMutation({
    mutationFn: () =>
      editingCenter
        ? api.updateEgypCentro(editingCenter.id, {
            ...center,
            orden: Number(center.orden),
          })
        : api.createEgypCentro({ ...center, orden: Number(center.orden) }),
    onSuccess: () => {
      refresh();
      setCenter(emptyCenter);
      setEditingCenter(undefined);
    },
  });
  const saveRubro = useMutation({
    mutationFn: () => {
      const body = {
        ...rubro,
        padre_id: rubro.padre_id || null,
        orden: Number(rubro.orden),
      };
      return editingRubro
        ? api.updateEgypRubro(editingRubro.id, body)
        : api.createEgypRubro(body);
    },
    onSuccess: () => {
      refresh();
      setRubro(emptyRubro);
      setEditingRubro(undefined);
      setRubroPage(1);
    },
  });
  const rubroPageSize = 10;
  const rubroItems = rubros.data ?? [];
  const safeRubroPage = Math.min(
    rubroPage,
    Math.max(1, Math.ceil(rubroItems.length / rubroPageSize)),
  );
  const visibleRubros = rubroItems.slice(
    (safeRubroPage - 1) * rubroPageSize,
    safeRubroPage * rubroPageSize,
  );
  return (
    <Stack spacing="6">
      <PageTitle
        title="Configuración EGyP"
        description="Define y mantiene las líneas de negocio y los rubros que se usan en la operación."
      />
      <Editor
        title={
          editingCenter ? "Editar línea de negocio" : "Nueva línea de negocio"
        }
        onSubmit={() => saveCenter.mutate()}
        loading={saveCenter.isPending}
        error={saveCenter.error}
      >
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3">
          <Field label="Código" required>
            <Input
              value={center.codigo}
              onChange={(event) =>
                setCenter({ ...center, codigo: event.target.value })
              }
            />
          </Field>
          <Field label="Nombre" required>
            <Input
              value={center.nombre}
              onChange={(event) =>
                setCenter({ ...center, nombre: event.target.value })
              }
            />
          </Field>
          <Field label="Orden">
            <Input
              type="number"
              value={center.orden}
              onChange={(event) =>
                setCenter({ ...center, orden: event.target.value })
              }
            />
          </Field>
        </SimpleGrid>
      </Editor>
      {centers.data && (
        <DataTable
          headers={["Código", "Línea de negocio", "Estado", ""]}
          empty="No hay líneas de negocio."
        >
          {centers.data.map((item) => (
            <Tr key={item.id}>
              <Td>{item.codigo}</Td>
              <Td>{item.nombre}</Td>
              <Td>
                <Status active={item.is_active} />
              </Td>
              <Td>
                <HStack>
                  <Button
                    size="sm"
                    onClick={() => {
                      setEditingCenter(item);
                      setCenter({
                        codigo: item.codigo,
                        nombre: item.nombre,
                        orden: String(item.orden),
                      });
                    }}
                  >
                    Editar
                  </Button>
                  {item.is_active && (
                    <Button
                      size="sm"
                      variant="ghost"
                      colorScheme="red"
                      onClick={() =>
                        confirmDelete(item.nombre) &&
                        api.deleteEgypCentro(item.id).then(refresh)
                      }
                    >
                      Inactivar
                    </Button>
                  )}
                </HStack>
              </Td>
            </Tr>
          ))}
        </DataTable>
      )}
      <Editor
        title={editingRubro ? "Editar rubro" : "Nuevo rubro"}
        onSubmit={() => saveRubro.mutate()}
        loading={saveRubro.isPending}
        error={saveRubro.error}
      >
        <SimpleGrid columns={{ base: 1, md: 5 }} spacing="3">
          <Field label="Código" required>
            <Input
              value={rubro.codigo}
              onChange={(event) =>
                setRubro({ ...rubro, codigo: event.target.value })
              }
            />
          </Field>
          <Field label="Nombre" required>
            <Input
              value={rubro.nombre}
              onChange={(event) =>
                setRubro({ ...rubro, nombre: event.target.value })
              }
            />
          </Field>
          <Field label="Naturaleza" required>
            <Select
              value={rubro.naturaleza}
              onChange={(event) =>
                setRubro({
                  ...rubro,
                  naturaleza: event.target.value as Naturaleza,
                })
              }
            >
              {[
                "INGRESO",
                "CONTRA_INGRESO",
                "COSTO_VENTA",
                "GASTO_OPERATIVO",
                "INGRESO_FINANCIERO",
                "GASTO_FINANCIERO",
                "IMPUESTO",
              ].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </Select>
          </Field>
          <Field label="Rubro padre">
            <Select
              value={rubro.padre_id}
              onChange={(event) =>
                setRubro({ ...rubro, padre_id: event.target.value })
              }
            >
              <option value="">Sin padre: rubro principal</option>
              {rubros.data
                ?.filter(
                  (item) => item.is_active && item.id !== editingRubro?.id,
                )
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="Orden">
            <Input
              type="number"
              value={rubro.orden}
              onChange={(event) =>
                setRubro({ ...rubro, orden: event.target.value })
              }
            />
          </Field>
        </SimpleGrid>
      </Editor>
      {rubros.data && (
        <>
          <DataTable
            headers={["Código", "Rubro", "Naturaleza", "Estado", ""]}
            empty="No hay rubros."
          >
            {visibleRubros.map((item) => (
              <Tr key={item.id}>
                <Td>{item.codigo}</Td>
                <Td>{item.nombre}</Td>
                <Td>{item.naturaleza}</Td>
                <Td>
                  <Status active={item.is_active} />
                </Td>
                <Td>
                  <HStack>
                    <Button
                      size="sm"
                      onClick={() => {
                        setEditingRubro(item);
                        setRubro({
                          codigo: item.codigo,
                          nombre: item.nombre,
                          naturaleza: item.naturaleza,
                          padre_id: item.padre_id ?? "",
                          orden: String(item.orden),
                        });
                      }}
                    >
                      Editar
                    </Button>
                    {item.is_active && (
                      <Button
                        size="sm"
                        variant="ghost"
                        colorScheme="red"
                        onClick={() =>
                          confirmDelete(item.nombre) &&
                          api.deleteEgypRubro(item.id).then(refresh)
                        }
                      >
                        Inactivar
                      </Button>
                    )}
                  </HStack>
                </Td>
              </Tr>
            ))}
          </DataTable>
          <TablePagination
            total={rubroItems.length}
            page={safeRubroPage}
            pageSize={rubroPageSize}
            onPageChange={setRubroPage}
          />
        </>
      )}
    </Stack>
  );
}
