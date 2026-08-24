import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Box, Button, Card, CardBody, HStack, Input, Select, SimpleGrid, Stack, Switch, Td, Text, Tr } from "@chakra-ui/react";
import { api, type TipoCambio } from "../client/api";
import { active, confirmDelete, Cancel, CatalogueSelect, DataTable, Editor, Empty, ErrorBox, Field, Loading, PageTitle, Status } from "../components/common";
import { useCatalogues } from "../hooks/useCatalogues";
import { today } from "../lib/format";
export function TipificationsPage() {
  const queryClient = useQueryClient();
  const catalogues = useCatalogues(true);
  const [kind, setKind] = useState<"actividad" | "concepto" | "tipo">(
    "actividad",
  );
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [openActivities, setOpenActivities] = useState<string[]>([]);
  const [openConcepts, setOpenConcepts] = useState<string[]>([]);
  const refresh = () => {
    ["actividades", "conceptos", "tipos"].forEach(
      (key) => void queryClient.invalidateQueries({ queryKey: [key] }),
    );
  };
  const save = useMutation({
    mutationFn: () =>
      kind === "actividad"
        ? api.createActividad({ nombre: name, orden: 0 })
        : kind === "concepto"
          ? api.createConcepto({
              nombre: name,
              actividad_id: parent,
              incluye_flujo_bruto_operativo: false,
              incluye_flujo_neto_operativo: false,
            })
          : api.createTipo({ nombre: name, concepto_id: parent }),
    onSuccess: () => {
      refresh();
      setName("");
      setParent("");
    },
  });
  const remove = useMutation({
    mutationFn: ({
      type,
      id,
    }: {
      type: "actividad" | "concepto" | "tipo";
      id: string;
    }) =>
      type === "actividad"
        ? api.deleteActividad(id)
        : type === "concepto"
          ? api.deleteConcepto(id)
          : api.deleteTipo(id),
    onSuccess: refresh,
  });
  const updateConcept = useMutation({
    mutationFn: ({ id, field, value }: { id: string; field: "incluye_flujo_bruto_operativo" | "incluye_flujo_neto_operativo"; value: boolean }) =>
      api.updateConcepto(id, { [field]: value }),
    onSuccess: refresh,
  });
  const updateActivity = useMutation({
    mutationFn: ({ id, orden }: { id: string; orden: number }) => api.updateActividad(id, { orden }),
    onSuccess: refresh,
  });
  const activities = catalogues.actividades.data ?? [];
  const concepts = catalogues.conceptos.data ?? [];
  const types = catalogues.tipos.data ?? [];
  const toggle = (set: React.Dispatch<React.SetStateAction<string[]>>, id: string) =>
    set((items) => (items.includes(id) ? items.filter((item) => item !== id) : [...items, id]));
  return (
    <Stack spacing="6">
      <PageTitle
        title="Árbol de tipificaciones"
        description="Jerarquía obligatoria: Actividad > Concepto > Tipo."
      />
      <Editor
        title={`Nueva ${kind}`}
        onSubmit={() => save.mutate()}
        loading={save.isPending}
        error={save.error}
      >
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3">
          <Field label="Nivel">
            <Select
              value={kind}
              onChange={(event) => {
                setKind(
                  event.target.value as "actividad" | "concepto" | "tipo",
                );
                setParent("");
              }}
            >
              <option value="actividad">Actividad</option>
              <option value="concepto">Concepto</option>
              <option value="tipo">Tipo</option>
            </Select>
          </Field>
          <Field
            label={
              kind === "actividad"
                ? "Nombre"
                : kind === "concepto"
                  ? "Actividad padre"
                  : "Concepto padre"
            }
            required
          >
            {kind === "actividad" ? (
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            ) : (
              <Select
                value={parent}
                onChange={(event) => setParent(event.target.value)}
                placeholder="Selecciona padre"
              >
                {(kind === "concepto"
                  ? active(activities)
                  : active(concepts)
                ).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {kind !== "actividad" && (
            <Field label="Nombre" required>
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </Field>
          )}
        </SimpleGrid>
      </Editor>
      <Card>
        <CardBody>
          {catalogues.loading && <Loading />}
          {catalogues.error && <ErrorBox error={catalogues.error} />}
          {activities.length === 0 && !catalogues.loading && (
            <Empty text="No hay tipificaciones." />
          )}
          {activities.map((activity) => {
            const activityConcepts = concepts.filter(
              (concept) => concept.actividad_id === activity.id,
            );
            const isActivityOpen = openActivities.includes(activity.id);
            return (
              <Box key={activity.id} borderBottom="1px solid" borderColor="gray.100" py="3">
                <HStack justify="space-between">
                  <HStack>
                    <Button
                      size="xs"
                      variant="ghost"
                      isDisabled={activityConcepts.length === 0}
                      onClick={() => toggle(setOpenActivities, activity.id)}
                    >
                      {isActivityOpen ? "-" : "+"}
                    </Button>
                    <Text fontWeight="bold">
                      Actividad: {activity.nombre} <Status active={activity.is_active} />
                    </Text>
                  </HStack>
                  <HStack spacing="2">
                    <Text fontSize="sm" color="gray.600">Orden</Text>
                    <Input
                      type="number"
                      min="0"
                      size="xs"
                      width="68px"
                      defaultValue={activity.orden}
                      isDisabled={updateActivity.isPending}
                      onBlur={(event) => {
                        const orden = Number(event.target.value);
                        if (Number.isInteger(orden) && orden >= 0 && orden !== activity.orden) {
                          updateActivity.mutate({ id: activity.id, orden });
                        }
                      }}
                    />
                    <Button
                      size="xs"
                      colorScheme="red"
                      variant="ghost"
                      onClick={() =>
                        confirmDelete(activity.nombre) &&
                        remove.mutate({ type: "actividad", id: activity.id })
                      }
                    >
                      Inactivar
                    </Button>
                  </HStack>
                </HStack>
                {isActivityOpen && activityConcepts.map((concept) => {
                  const conceptTypes = types.filter((type) => type.concepto_id === concept.id);
                  const isConceptOpen = openConcepts.includes(concept.id);
                  return (
                    <Box key={concept.id} ml={{ base: 3, md: 8 }} mt="3">
                      <HStack justify="space-between">
                        <HStack>
                          <Button
                            size="xs"
                            variant="ghost"
                            isDisabled={conceptTypes.length === 0}
                            onClick={() => toggle(setOpenConcepts, concept.id)}
                          >
                            {isConceptOpen ? "-" : "+"}
                          </Button>
                          <Text>
                            Concepto: {concept.nombre} <Status active={concept.is_active} />
                          </Text>
                        </HStack>
                        <HStack spacing="3">
                          <Switch
                            size="sm"
                            isChecked={concept.incluye_flujo_bruto_operativo}
                            isDisabled={updateConcept.isPending}
                            onChange={(event) => updateConcept.mutate({ id: concept.id, field: "incluye_flujo_bruto_operativo", value: event.target.checked })}
                          >
                            Flujo bruto operativo
                          </Switch>
                          <Switch
                            size="sm"
                            isChecked={concept.incluye_flujo_neto_operativo}
                            isDisabled={updateConcept.isPending}
                            onChange={(event) => updateConcept.mutate({ id: concept.id, field: "incluye_flujo_neto_operativo", value: event.target.checked })}
                          >
                            Flujo neto operativo
                          </Switch>
                          <Button
                            size="xs"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() =>
                              confirmDelete(concept.nombre) &&
                              remove.mutate({ type: "concepto", id: concept.id })
                            }
                          >
                            Inactivar
                          </Button>
                        </HStack>
                      </HStack>
                      {isConceptOpen && conceptTypes.map((type) => (
                        <HStack
                          key={type.id}
                          ml={{ base: 3, md: 8 }}
                          mt="2"
                          justify="space-between"
                        >
                          <Text fontSize="sm">
                            Tipo: {type.nombre} <Status active={type.is_active} />
                          </Text>
                          <Button
                            size="xs"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() =>
                              confirmDelete(type.nombre) &&
                              remove.mutate({ type: "tipo", id: type.id })
                            }
                          >
                            Inactivar
                          </Button>
                        </HStack>
                      ))}
                    </Box>
                  );
                })}
              </Box>
            );
          })}
        </CardBody>
      </Card>
    </Stack>
  );
}

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
        : api.createTipoCambio(form),
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

export function TipificationsAdminPage() {
  const queryClient = useQueryClient();
  const catalogues = useCatalogues(true);
  const [level, setLevel] = useState<"actividad" | "concepto" | "tipo">(
    "actividad",
  );
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const activities = catalogues.actividades.data ?? [];
  const concepts = catalogues.conceptos.data ?? [];
  const types = catalogues.tipos.data ?? [];
  const items =
    level === "actividad"
      ? activities
      : level === "concepto"
        ? concepts
        : types;
  const choose = (next: string) => {
    setId(next);
    const item = items.find((entry) => entry.id === next);
    setName(item?.nombre ?? "");
    const parentId =
      item && "actividad_id" in item && typeof item.actividad_id === "string"
        ? item.actividad_id
        : item && "concepto_id" in item && typeof item.concepto_id === "string"
          ? item.concepto_id
          : "";
    setParent(parentId);
  };
  const save = useMutation({
    mutationFn: () =>
      level === "actividad"
        ? api.updateActividad(id, { nombre: name })
        : level === "concepto"
          ? api.updateConcepto(id, { nombre: name, actividad_id: parent })
          : api.updateTipo(id, { nombre: name, concepto_id: parent }),
    onSuccess: () => {
      ["actividades", "conceptos", "tipos"].forEach(
        (key) => void queryClient.invalidateQueries({ queryKey: [key] }),
      );
      setId("");
    },
  });
  return (
    <Stack spacing="6">
      <Editor
        title="Editar tipificación"
        onSubmit={() => save.mutate()}
        loading={save.isPending}
        error={save.error}
      >
        <SimpleGrid columns={{ base: 1, md: 4 }} spacing="3">
          <Field label="Nivel">
            <Select
              value={level}
              onChange={(event) => {
                setLevel(
                  event.target.value as "actividad" | "concepto" | "tipo",
                );
                setId("");
              }}
            >
              <option value="actividad">Actividad</option>
              <option value="concepto">Concepto</option>
              <option value="tipo">Tipo</option>
            </Select>
          </Field>
          <Field label="Registro">
            <Select
              value={id}
              onChange={(event) => choose(event.target.value)}
              placeholder="Selecciona"
            >
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
            </Select>
          </Field>
          {level !== "actividad" && (
            <CatalogueSelect
              label="Padre"
              value={parent}
              onChange={setParent}
              items={(level === "concepto" ? activities : concepts) as Array<{ id: string; nombre: string }>}
            />
          )}
          <Field label="Nombre">
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
        </SimpleGrid>

      </Editor>
      <TipificationsPage />
    </Stack>
  );
}





