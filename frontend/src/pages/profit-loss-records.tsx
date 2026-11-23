import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  CardBody,
  Checkbox,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  SimpleGrid,
  Stack,
  Td,
  Text,
  Textarea,
  Tr,
} from "@chakra-ui/react";
import { api, type AsientoResultado } from "../client/api";
import {
  DataTable,
  ErrorBox,
  Field,
  Metric,
  PageTitle,
  TablePagination,
} from "../components/common";
import { money } from "../lib/format";

const currentDate = new Date();
const filtersFromUrl = new URLSearchParams(window.location.search);
const monthEnd = (period: string) => {
  const [year, month] = period.split("-").map(Number);
  return `${year}-${String(month).padStart(2, "0")}-${new Date(year, month, 0).getDate()}`;
};

export function ProfitLossRecordsPage() {
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState(
    /^\d{4}-\d{2}$/.test(filtersFromUrl.get("period") ?? "")
      ? filtersFromUrl.get("period")!
      : `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`,
  );
  const [parentId, setParentId] = useState("");
  const [rubroId, setRubroId] = useState(filtersFromUrl.get("rubro_id") ?? "");
  const [centerId, setCenterId] = useState(filtersFromUrl.get("centro_id") ?? "");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [editingEntry, setEditingEntry] = useState<AsientoResultado | null>(null);
  const [editingDate, setEditingDate] = useState("");
  const [editingParentId, setEditingParentId] = useState("");
  const [editingRubroId, setEditingRubroId] = useState("");
  const [editingCenterId, setEditingCenterId] = useState("");
  const [editingAmount, setEditingAmount] = useState("");
  const [editingDescription, setEditingDescription] = useState("");
  const [editingNotes, setEditingNotes] = useState("");
  const centers = useQuery({
    queryKey: ["egyp-centros"],
    queryFn: () => api.egypCentros(),
  });
  const rubros = useQuery({
    queryKey: ["egyp-rubros"],
    queryFn: () => api.egypRubros(),
  });
  const parents = (rubros.data ?? []).filter(
    (item) => item.is_active && !item.padre_id,
  );
  const categories = (rubros.data ?? []).filter(
    (item) => item.is_active && Boolean(item.padre_id),
  );
  const visibleCategories = parentId
    ? categories.filter((item) => item.padre_id === parentId)
    : categories;
  const editingCategories = categories.filter(
    (item) => item.padre_id === editingParentId,
  );
  const params = new URLSearchParams({
    fecha_desde: `${period}-01`,
    fecha_hasta: monthEnd(period),
    solo_resultado: "true",
  });
  if (rubroId) params.set("rubro_id", rubroId);
  if (centerId) params.set("centro_id", centerId);
  if (search.trim()) params.set("busqueda", search.trim());
  const entries = useQuery({
    queryKey: ["egyp-entries-history", params.toString()],
    queryFn: () => api.egypEntries(params),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteEgypEntry(id),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["egyp-entries-history"] }),
  });
  const removeSelected = useMutation({
    mutationFn: () => api.deleteEgypEntries([...selectedIds]),
    onSuccess: () => {
      setSelectedIds(new Set());
      void queryClient.invalidateQueries({ queryKey: ["egyp-entries-history"] });
      void queryClient.invalidateQueries({ queryKey: ["egyp-summary"] });
    },
  });
  const updateCenter = useMutation({
    mutationFn: () => {
      if (!editingEntry) throw new Error("No hay un registro seleccionado.");
      if (!editingCenterId) throw new Error("Selecciona una línea de negocio.");
      const category = categories.find((item) => item.id === editingRubroId);
      if (!category) throw new Error("Selecciona una categoría.");
      const amount = Number(editingAmount);
      if (!Number.isFinite(amount) || amount <= 0)
        throw new Error("Ingresa un monto mayor a cero.");
      const credit = ["INGRESO", "INGRESO_FINANCIERO"].includes(
        category.naturaleza,
      );
      return api.updateEgypEntry(editingEntry.id, {
        fecha: editingDate,
        descripcion: editingDescription.trim() || category.nombre,
        documento: editingEntry.documento,
        moneda: editingEntry.moneda,
        debe: credit ? 0 : amount,
        haber: credit ? amount : 0,
        centro_resultado_id: editingCenterId,
        rubro_id: category.id,
        observaciones: editingNotes.trim() || null,
      });
    },
    onSuccess: () => {
      setEditingEntry(null);
      void queryClient.invalidateQueries({ queryKey: ["egyp-entries-history"] });
      void queryClient.invalidateQueries({ queryKey: ["egyp-summary"] });
    },
  });
  const pageSize = 15;
  const total = entries.data?.length ?? 0;
  const safePage = Math.min(page, Math.max(1, Math.ceil(total / pageSize)));
  const visibleEntries = (entries.data ?? []).slice(
    (safePage - 1) * pageSize,
    safePage * pageSize,
  );
  const filteredTotal = (entries.data ?? []).reduce(
    (total, item) => total + Number(item.haber) - Number(item.debe),
    0,
  );
  const selectedEntries = (entries.data ?? []).filter((item) =>
    selectedIds.has(item.id),
  );
  const selectedTotal = selectedEntries.reduce(
    (total, item) => total + Number(item.haber) - Number(item.debe),
    0,
  );
  const selectVisible = (checked: boolean) =>
    setSelectedIds((current) => {
      const next = new Set(current);
      visibleEntries.forEach((item) =>
        checked ? next.add(item.id) : next.delete(item.id),
      );
      return next;
    });

  return (
    <Stack spacing="6" w="full" minW="0">
      <PageTitle
        title="Registros EGyP"
        description="Consulta los asientos que sustentan el resultado y su distribución por línea de negocio."
      />
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 2, xl: 5 }} spacing="3">
            <Field label="Mes">
              <Input
                type="month"
                value={period}
                onChange={(event) => {
                  setPeriod(event.target.value);
                  setPage(1);
                }}
              />
            </Field>
            <Field label="Rubro">
              <Select
                value={parentId}
                onChange={(event) => {
                  setParentId(event.target.value);
                  setRubroId("");
                  setPage(1);
                }}
              >
                <option value="">Todos los rubros</option>
                {parents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Categoría">
              <Select
                value={rubroId}
                onChange={(event) => {
                  setRubroId(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">Todas las categorías</option>
                {visibleCategories.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Línea de negocio">
              <Select
                value={centerId}
                onChange={(event) => {
                  setCenterId(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">Todas las líneas</option>
                {centers.data?.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Buscar texto">
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Descripción, referencia u observación"
              />
            </Field>
          </SimpleGrid>
          <HStack justify="flex-end" mt="4">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setPeriod(
                  `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`,
                );
                setParentId("");
                setRubroId("");
                setCenterId("");
                setSearch("");
                setPage(1);
                setSelectedIds(new Set());
              }}
            >
              Limpiar filtros
            </Button>
          </HStack>
        </CardBody>
      </Card>
      <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
        <Card>
          <CardBody>
            <Metric
              label={`Total filtrado (${total} asientos)`}
              value={money(filteredTotal, "PEN")}
              color={filteredTotal < 0 ? "red.600" : "green.600"}
            />
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Metric
              label={`Seleccionado (${selectedEntries.length} asientos)`}
              value={money(selectedTotal, "PEN")}
              color={selectedTotal < 0 ? "red.600" : "green.600"}
            />
          </CardBody>
        </Card>
      </SimpleGrid>
      {entries.error && <ErrorBox error={entries.error} />}
      {remove.error && <ErrorBox error={remove.error} />}
      {removeSelected.error && <ErrorBox error={removeSelected.error} />}
      <HStack justify="flex-end">
        <Button size="sm" variant="outline" onClick={() => selectVisible(true)}>
          Seleccionar página
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
          Limpiar selección
        </Button>
        <Button
          size="sm"
          colorScheme="red"
          isDisabled={!selectedEntries.length}
          isLoading={removeSelected.isPending}
          onClick={() => {
            if (
              window.confirm(
                `Se eliminarán ${selectedEntries.length} registros seleccionados. No se puede deshacer.`,
              )
            )
              removeSelected.mutate();
          }}
        >
          Eliminar seleccionados
        </Button>
      </HStack>
      <DataTable
        headers={[
          "Selec.",
          "Fecha",
          "Rubro",
          "Categoría",
          "Línea",
          "Distribución",
          "Monto",
          "Descripción",
          "Acciones",
        ]}
        columnWidths={["5%", "9%", "12%", "13%", "12%", "15%", "10%", "17%", "7%"]}
        empty="No hay transacciones para los filtros seleccionados."
      >
        {visibleEntries.map((item) => {
          const category = categories.find((rubro) => rubro.id === item.rubro_id);
          const parent = parents.find((rubro) => rubro.id === category?.padre_id);
          return (
            <Tr key={item.id}>
              <Td>
                <Checkbox
                  isChecked={selectedIds.has(item.id)}
                  onChange={(event) =>
                    setSelectedIds((current) => {
                      const next = new Set(current);
                      event.target.checked ? next.add(item.id) : next.delete(item.id);
                      return next;
                    })
                  }
                />
              </Td>
              <Td whiteSpace="nowrap">{item.fecha}</Td>
              <Td>{parent?.nombre ?? "-"}</Td>
              <Td>{category?.nombre ?? "Categoría no disponible"}</Td>
              <Td>
                {centers.data?.find((center) => center.id === item.centro_resultado_id)
                  ?.nombre ?? "Sin línea"}
              </Td>
              <Td>
                {item.regla_distribucion_nombre ? (
                  <Text fontSize="sm">
                    {item.regla_distribucion_nombre} ({item.porcentaje_distribucion}%)
                  </Text>
                ) : item.origen === "DISTRIBUIDO" ? (
                  <Text fontSize="xs" color="gray.500">
                    Distribución automática histórica
                  </Text>
                ) : (
                  "-"
                )}
              </Td>
              <Td isNumeric whiteSpace="nowrap">
                {money(Number(item.haber) || Number(item.debe), item.moneda)}
              </Td>
              <Td>
                <Text>{item.descripcion}</Text>
                {item.observaciones && (
                  <Text fontSize="xs" color="gray.500">
                    {item.observaciones}
                  </Text>
                )}
              </Td>
              <Td>
                <HStack justify="flex-end">
                  <Button
                    size="xs"
                    variant="outline"
                    isDisabled={item.origen === "DISTRIBUIDO"}
                    onClick={() => {
                      setEditingEntry(item);
                      const category = categories.find(
                        (rubro) => rubro.id === item.rubro_id,
                      );
                      setEditingDate(item.fecha);
                      setEditingParentId(category?.padre_id ?? "");
                      setEditingRubroId(item.rubro_id);
                      setEditingCenterId(item.centro_resultado_id ?? "");
                      setEditingAmount(
                        String(Number(item.haber) || Number(item.debe)),
                      );
                      setEditingDescription(item.descripcion);
                      setEditingNotes(item.observaciones ?? "");
                    }}
                  >
                    Editar
                  </Button>
                  <Button
                    size="xs"
                    variant="ghost"
                    colorScheme="red"
                    isLoading={remove.isPending}
                    onClick={() => {
                      if (
                        window.confirm(
                          "Se eliminará este registro y sus líneas distribuidas. No se puede deshacer.",
                        )
                      )
                        remove.mutate(item.id);
                    }}
                  >
                    Eliminar
                  </Button>
                </HStack>
              </Td>
            </Tr>
          );
        })}
      </DataTable>
      <TablePagination
        total={total}
        page={safePage}
        pageSize={pageSize}
        onPageChange={setPage}
      />
      {editingEntry && (
        <Modal
          isOpen
          onClose={() => setEditingEntry(null)}
          size="md"
        >
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Editar registro EGyP</ModalHeader>
            <ModalBody>
              <Stack spacing="4">
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
                  <Field label="Fecha" required>
                    <Input
                      type="date"
                      value={editingDate}
                      onChange={(event) => setEditingDate(event.target.value)}
                    />
                  </Field>
                  <Field label="Monto sin IGV" required>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editingAmount}
                      onChange={(event) => setEditingAmount(event.target.value)}
                    />
                  </Field>
                  <Field label="Rubro" required>
                    <Select
                      value={editingParentId}
                      onChange={(event) => {
                        setEditingParentId(event.target.value);
                        setEditingRubroId("");
                      }}
                    >
                      <option value="">Selecciona un rubro</option>
                      {parents.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.nombre}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Categoría" required>
                    <Select
                      value={editingRubroId}
                      isDisabled={!editingParentId}
                      onChange={(event) => setEditingRubroId(event.target.value)}
                    >
                      <option value="">Selecciona una categoría</option>
                      {editingCategories.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.nombre}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </SimpleGrid>
                <Field label="Línea de negocio" required>
                  <Select
                    value={editingCenterId}
                    onChange={(event) => setEditingCenterId(event.target.value)}
                  >
                    <option value="">Selecciona una línea</option>
                    {centers.data?.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.codigo} - {item.nombre}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Descripción">
                  <Input
                    value={editingDescription}
                    onChange={(event) => setEditingDescription(event.target.value)}
                  />
                </Field>
                <Field label="Observaciones">
                  <Textarea
                    value={editingNotes}
                    onChange={(event) => setEditingNotes(event.target.value)}
                  />
                </Field>
                {updateCenter.error && <ErrorBox error={updateCenter.error} />}
              </Stack>
            </ModalBody>
            <ModalFooter>
              <Button onClick={() => setEditingEntry(null)}>Cancelar</Button>
              <Button
                ml="3"
                colorScheme="brand"
                isLoading={updateCenter.isPending}
                onClick={() => updateCenter.mutate()}
              >
                Guardar cambios
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      )}
    </Stack>
  );
}
