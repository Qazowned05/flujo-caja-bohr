import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  Box,
  Button,
  Card,
  CardBody,
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
  useDisclosure,
} from "@chakra-ui/react";
import {
  api,
  type AsientoResultado,
  type ReglaDistribucion,
} from "../client/api";
import {
  DataTable,
  Editor,
  ErrorBox,
  Field,
  PageTitle,
  TablePagination,
} from "../components/common";
import { money } from "../lib/format";
import { download } from "../lib/download";

type RuleLine = { centro_resultado_id: string; porcentaje: string };
type RuleForm = {
  nombre: string;
  vigente_desde: string;
  vigente_hasta: string;
  lineas: RuleLine[];
};
const currentDate = new Date();
const initialHistoryFilters = new URLSearchParams(window.location.search);
const initialHistoryPeriod = /^\d{4}-\d{2}$/.test(
  initialHistoryFilters.get("period") ?? "",
)
  ? initialHistoryFilters.get("period")!
  : `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`;
const emptyEntry = {
  descripcion: "",
  importe: "",
  centro_resultado_id: "",
  regla_distribucion_id: "",
  rubro_padre_id: "",
  rubro_id: "",
  observaciones: "",
};
const emptyRule: RuleForm = {
  nombre: "",
  vigente_desde: "",
  vigente_hasta: "",
  lineas: [
    { centro_resultado_id: "", porcentaje: "" },
    { centro_resultado_id: "", porcentaje: "" },
  ] as RuleLine[],
};
const monthEnd = (period: string) => {
  const [year, month] = period.split("-").map(Number);
  return `${year}-${String(month).padStart(2, "0")}-${new Date(year, month, 0).getDate()}`;
};

export function ProfitLossOperationsPage() {
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState(
    `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`,
  );
  const [entry, setEntry] = useState(emptyEntry);
  const [editingEntry, setEditingEntry] = useState<AsientoResultado | null>(
    null,
  );
  const [rule, setRule] = useState(emptyRule);
  const [editingRule, setEditingRule] = useState<ReglaDistribucion | null>(
    null,
  );
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [selectedRule, setSelectedRule] = useState<ReglaDistribucion | null>(
    null,
  );
  const [ruleSearch, setRuleSearch] = useState("");
  const [rulePage, setRulePage] = useState(1);
  const [historyPeriod, setHistoryPeriod] = useState(
    initialHistoryPeriod,
  );
  const [historyRubro, setHistoryRubro] = useState(
    initialHistoryFilters.get("rubro_id") ?? "",
  );
  const [historyCenter, setHistoryCenter] = useState(
    initialHistoryFilters.get("centro_id") ?? "",
  );
  const [historySearch, setHistorySearch] = useState("");
  const [historyPage, setHistoryPage] = useState(1);
  const [importFile, setImportFile] = useState<File>();
  const centers = useQuery({
    queryKey: ["egyp-centros"],
    queryFn: () => api.egypCentros(),
  });
  const rubros = useQuery({
    queryKey: ["egyp-rubros"],
    queryFn: () => api.egypRubros(),
  });
  const rules = useQuery({
    queryKey: ["egyp-rules"],
    queryFn: () => api.egypReglas(true),
  });
  const parents = (rubros.data ?? []).filter(
    (item) => item.is_active && !item.padre_id,
  );
  const concepts = (rubros.data ?? []).filter(
    (item) => item.is_active && Boolean(item.padre_id),
  );
  const categories = concepts.filter(
    (item) => item.padre_id === entry.rubro_padre_id,
  );
  const selectedCategory = concepts.find((item) => item.id === entry.rubro_id);
  const historyParams = new URLSearchParams({
    fecha_desde: `${historyPeriod}-01`,
    fecha_hasta: monthEnd(historyPeriod),
    solo_resultado: "true",
  });
  if (historyRubro) historyParams.set("rubro_id", historyRubro);
  if (historyCenter) historyParams.set("centro_id", historyCenter);
  if (historySearch.trim()) historyParams.set("busqueda", historySearch.trim());
  const entries = useQuery({
    queryKey: ["egyp-entries-history", historyParams.toString()],
    queryFn: () => api.egypEntries(historyParams),
  });
  const refresh = () =>
    [
      "egyp-rules",
      "egyp-summary",
      "egyp-entries",
      "egyp-entries-admin",
      "egyp-entries-history",
    ].forEach((key) => void queryClient.invalidateQueries({ queryKey: [key] }));
  const saveEntry = useMutation({
    mutationFn: () => {
      if (!selectedCategory) throw new Error("Selecciona una categoría.");
      const amount = Number(entry.importe);
      if (!Number.isFinite(amount) || amount <= 0)
        throw new Error("Ingresa un monto mayor a cero.");
      const credit = ["INGRESO", "INGRESO_FINANCIERO"].includes(
        selectedCategory.naturaleza,
      );
      const data = {
        fecha: monthEnd(period),
        descripcion: entry.descripcion || selectedCategory.nombre,
        documento: `Cierre ${period}`,
        moneda: "PEN",
        debe: credit ? 0 : amount,
        haber: credit ? amount : 0,
        centro_resultado_id: entry.centro_resultado_id || null,
        regla_distribucion_id: entry.regla_distribucion_id || null,
        rubro_id: selectedCategory.id,
        observaciones: entry.observaciones || null,
      };
      return editingEntry
        ? api.updateEgypEntry(editingEntry.id, data)
        : api.createEgypEntry(data);
    },
    onSuccess: () => {
      refresh();
      setEntry(emptyEntry);
      setEditingEntry(null);
    },
  });
  const importEntries = useMutation({
    mutationFn: () =>
      importFile
        ? api.importEgyp(importFile)
        : Promise.reject(new Error("Selecciona un archivo Excel.")),
    onSuccess: () => {
      refresh();
      setImportFile(undefined);
    },
  });
  const saveRule = useMutation({
    mutationFn: () => {
      const data = {
        ...rule,
        vigente_desde: rule.vigente_desde || null,
        vigente_hasta: rule.vigente_hasta || null,
        lineas: rule.lineas,
      };
      return editingRule
        ? api.updateEgypRegla(editingRule.id, data)
        : api.createEgypRegla(data);
    },
    onSuccess: () => {
      refresh();
      setRule(emptyRule);
      setEditingRule(null);
      setShowRuleForm(false);
    },
  });
  const deleteRule = useMutation({
    mutationFn: (id: string) => api.deleteEgypRegla(id),
    onSuccess: refresh,
  });
  const matchingRules = (rules.data ?? []).filter(
    (item) =>
      item.is_active &&
      item.nombre.toLowerCase().includes(ruleSearch.trim().toLowerCase()),
  );
  const pageSize = 8;
  const safePage = Math.min(
    rulePage,
    Math.max(1, Math.ceil(matchingRules.length / pageSize)),
  );
  const visibleRules = matchingRules.slice(
    (safePage - 1) * pageSize,
    safePage * pageSize,
  );
  const historyPageSize = 10;
  const historyEntries = entries.data ?? [];
  const safeHistoryPage = Math.min(
    historyPage,
    Math.max(1, Math.ceil(historyEntries.length / historyPageSize)),
  );
  const visibleEntries = historyEntries.slice(
    (safeHistoryPage - 1) * historyPageSize,
    safeHistoryPage * historyPageSize,
  );
  const editEntry = (item: AsientoResultado) => {
    setEditingEntry(item);
    setPeriod(item.fecha.slice(0, 7));
    setEntry({
      descripcion: item.descripcion,
      importe: String(Number(item.haber) || Number(item.debe)),
      centro_resultado_id: item.centro_resultado_id ?? "",
      regla_distribucion_id: "",
      rubro_padre_id:
        concepts.find((rubro) => rubro.id === item.rubro_id)?.padre_id ?? "",
      rubro_id: item.rubro_id,
      observaciones: item.observaciones ?? "",
    });
  };
  const editRule = (item: ReglaDistribucion) => {
    setEditingRule(item);
    setRule({
      nombre: item.nombre,
      vigente_desde: item.vigente_desde ?? "",
      vigente_hasta: item.vigente_hasta ?? "",
      lineas: item.lineas.map((line) => ({
        centro_resultado_id: line.centro_resultado_id,
        porcentaje: String(line.porcentaje),
      })),
    });
    setShowRuleForm(true);
  };

  return (
    <Stack spacing="6" w="full" minW="0">
      <PageTitle
        title="Cierre mensual EGyP"
        description="Registra y corrige los totales mensuales por concepto, sin IGV."
      />
      <Editor
        title="Ingresar registro"
        onSubmit={() => saveEntry.mutate()}
        loading={saveEntry.isPending}
        error={saveEntry.error}
      >
        <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing="3">
          <Field label="Mes" required>
            <Input
              type="month"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
            />
          </Field>
          <Field label="Rubro" required>
            <Select
              value={entry.rubro_padre_id}
              onChange={(event) =>
                setEntry({
                  ...entry,
                  rubro_padre_id: event.target.value,
                  rubro_id: "",
                })
              }
            >
              <option value="">Selecciona rubro</option>
              {parents.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Categoría" required>
            <Select
              value={entry.rubro_id}
              isDisabled={!entry.rubro_padre_id}
              onChange={(event) =>
                setEntry({ ...entry, rubro_id: event.target.value })
              }
            >
              <option value="">Selecciona categoría</option>
              {categories.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Monto sin IGV" required>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={entry.importe}
              onChange={(event) =>
                setEntry({ ...entry, importe: event.target.value })
              }
            />
          </Field>
          <Field label="Linea de negocio">
            <Select
              value={entry.centro_resultado_id}
              onChange={(event) =>
                setEntry({
                  ...entry,
                  centro_resultado_id: event.target.value,
                  regla_distribucion_id: event.target.value
                    ? ""
                    : entry.regla_distribucion_id,
                })
              }
            >
              <option value="">Selecciona una linea</option>
              {centers.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Regla de distribución">
            <Select
              value={entry.regla_distribucion_id}
              onChange={(event) =>
                setEntry({
                  ...entry,
                  regla_distribucion_id: event.target.value,
                  centro_resultado_id: event.target.value ? "" : entry.centro_resultado_id,
                })
              }
            >
              <option value="">Selecciona una regla</option>
              {rules.data
                ?.filter((item) => item.is_active)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="Descripcion">
            <Input
              value={entry.descripcion}
              placeholder={selectedCategory?.nombre ?? "Opcional"}
              onChange={(event) =>
                setEntry({ ...entry, descripcion: event.target.value })
              }
            />
          </Field>
          <Field label="Referencia">
            <Input value={`Cierre ${period}`} isReadOnly />
          </Field>
        </SimpleGrid>
        <Field label="Observaciones">
          <Textarea
            value={entry.observaciones}
            onChange={(event) =>
              setEntry({ ...entry, observaciones: event.target.value })
            }
          />
        </Field>
        <Text fontSize="sm" color="gray.500">
          Selecciona una línea de negocio o una regla de distribución. La regla
          se puede usar con cualquier rubro y categoría.
        </Text>
      </Editor>
      <Card borderTop="3px solid" borderColor="brand.500">
        <CardBody>
          <Stack spacing="4">
            <Box>
              <Text fontWeight="semibold">Importación masiva EGyP</Text>
              <Text fontSize="sm" color="gray.500">
                Descarga la plantilla, complétala por período y carga todos los
                asientos en una sola operación.
              </Text>
            </Box>
            <HStack flexWrap="wrap">
              <Input
                type="file"
                accept=".xlsx"
                p="1"
                maxW="360px"
                onChange={(event) => setImportFile(event.target.files?.[0])}
              />
              <Button
                variant="outline"
                onClick={() =>
                  void api
                    .download("/api/v1/ganancias-perdidas/plantilla.xlsx")
                    .then((blob) => download(blob, "plantilla_egyp.xlsx"))
                }
              >
                Descargar plantilla
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  void api
                    .download("/api/v1/ganancias-perdidas/plantilla.xlsx?incluir_asientos=true")
                    .then((blob) => download(blob, "asientos_egyp_actuales.xlsx"))
                }
              >
                Exportar asientos actuales
              </Button>
              <Button
                colorScheme="brand"
                isDisabled={!importFile}
                isLoading={importEntries.isPending}
                onClick={() => importEntries.mutate()}
              >
                Importar asientos
              </Button>
            </HStack>
            {importEntries.isError && <ErrorBox error={importEntries.error} />}
            {importEntries.data && (
              <Text color="green.600">
                Se importaron {importEntries.data.filas_nuevas} asientos en el
                lote {importEntries.data.lote_id}.
              </Text>
            )}
          </Stack>
        </CardBody>
      </Card>
      <Stack spacing="3">
        <HStack justify="space-between" align="start" flexWrap="wrap">
          <Box>
            <Text fontWeight="semibold">Reglas de distribución</Text>
            <Text fontSize="sm" color="gray.500">
              Distribuyen gastos compartidos entre líneas de negocio,
              independientemente del rubro y la categoría.
            </Text>
          </Box>
          <Button
            size="sm"
            colorScheme="brand"
            onClick={() => {
              setShowRuleForm(!showRuleForm);
              if (showRuleForm) {
                setEditingRule(null);
                setRule(emptyRule);
              }
            }}
          >
            {showRuleForm ? "Cerrar" : "Nueva regla"}
          </Button>
        </HStack>
        {showRuleForm && (
          <RuleFormModal
            rule={rule}
            centers={centers.data ?? []}
            editing={Boolean(editingRule)}
            loading={saveRule.isPending}
            error={saveRule.error}
            onChange={setRule}
            onClose={() => {
              setEditingRule(null);
              setRule(emptyRule);
              setShowRuleForm(false);
            }}
            onSave={() => saveRule.mutate()}
          />
        )}
        {rules.data && (
          <>
            <Card>
              <CardBody>
                <Input
                  value={ruleSearch}
                  onChange={(event) => {
                    setRuleSearch(event.target.value);
                    setRulePage(1);
                  }}
                  placeholder="Buscar regla"
                />
              </CardBody>
            </Card>
            <DataTable
              headers={[
                "Regla",
                "Vigente desde",
                "Vigente hasta",
                "Acciones",
              ]}
              columnWidths={["45%", "18%", "18%", "19%"]}
              empty="No hay reglas activas."
            >
              {visibleRules.map((item: ReglaDistribucion) => (
                <Tr key={item.id}>
                  <Td>{item.nombre}</Td>
                  <Td whiteSpace="nowrap">
                    {item.vigente_desde ?? "Desde siempre"}
                  </Td>
                  <Td whiteSpace="nowrap">
                    {item.vigente_hasta ?? "Sin límite"}
                  </Td>
                  <Td>
                    <HStack justify="flex-end" spacing="1">
                      <Button
                        size="xs"
                        variant="ghost"
                        onClick={() => setSelectedRule(item)}
                      >
                        Ver
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => editRule(item)}
                      >
                        Editar
                      </Button>
                      <Button
                        size="xs"
                        variant="ghost"
                        colorScheme="red"
                        isLoading={deleteRule.isPending}
                        onClick={() => {
                          if (
                            window.confirm(
                              `Se anulará la regla ${item.nombre}. Esta acción conserva el historial.`,
                            )
                          )
                            deleteRule.mutate(item.id);
                        }}
                      >
                        Anular
                      </Button>
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </DataTable>
            <TablePagination
              total={matchingRules.length}
              page={safePage}
              pageSize={pageSize}
              onPageChange={setRulePage}
            />
          </>
        )}
      </Stack>
      <Stack spacing="3" display="none">
        <Box>
          <Text fontWeight="semibold">Transacciones registradas</Text>
          <Text fontSize="sm" color="gray.500">
            Busca, corrige registros manuales o anula una carga equivocada. La
            anulacion conserva la trazabilidad.
          </Text>
        </Box>
        <Card>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing="3">
              <Field label="Mes">
                <Input
                  type="month"
                  value={historyPeriod}
                  onChange={(event) => {
                    setHistoryPeriod(event.target.value);
                    setHistoryPage(1);
                  }}
                />
              </Field>
              <Field label="Concepto">
                <Select
                  value={historyRubro}
                  onChange={(event) => {
                    setHistoryRubro(event.target.value);
                    setHistoryPage(1);
                  }}
                >
                  <option value="">Todos los conceptos</option>
                  {concepts.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nombre}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Linea de negocio">
                <Select
                  value={historyCenter}
                  onChange={(event) => {
                    setHistoryCenter(event.target.value);
                    setHistoryPage(1);
                  }}
                >
                  <option value="">Todas las lineas</option>
                  {centers.data?.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nombre}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Buscar texto">
                <Input
                  value={historySearch}
                  onChange={(event) => {
                    setHistorySearch(event.target.value);
                    setHistoryPage(1);
                  }}
                  placeholder="Descripcion, referencia u observacion"
                />
              </Field>
            </SimpleGrid>
          </CardBody>
        </Card>
        {entries.error && <ErrorBox error={entries.error} />}
        <DataTable
          headers={[
            "Fecha",
            "Concepto",
            "Linea",
            "Distribución",
            "Monto",
            "Descripcion",
            "Acciones",
          ]}
          columnWidths={["11%", "17%", "14%", "17%", "13%", "18%", "10%"]}
          empty="No hay transacciones para los filtros seleccionados."
        >
          {visibleEntries.map((item) => {
            const editable = item.es_resultado;
            return (
              <Tr key={item.id}>
                <Td whiteSpace="nowrap">{item.fecha}</Td>
                <Td>
                  {concepts.find((rubro) => rubro.id === item.rubro_id)
                    ?.nombre ?? "Concepto"}
                </Td>
                <Td>
                  {centers.data?.find(
                    (center) => center.id === item.centro_resultado_id,
                  )?.nombre ??
                    (item.es_resultado
                      ? "Sin linea"
                      : "Repartido automaticamente")}
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
                  <HStack justify="flex-end" spacing="1">
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => editEntry(item)}
                      isDisabled={!editable}
                    >
                      Editar
                    </Button>
                    <DeleteEgypEntryButton entry={item} onDeleted={refresh} />
                  </HStack>
                </Td>
              </Tr>
            );
          })}
        </DataTable>
        <TablePagination
          total={historyEntries.length}
          page={safeHistoryPage}
          pageSize={historyPageSize}
          onPageChange={setHistoryPage}
        />
      </Stack>
      {editingEntry && (
        <Modal
          isOpen
          onClose={() => {
            setEditingEntry(null);
            setEntry(emptyEntry);
          }}
          size="xl"
        >
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Editar transacción</ModalHeader>
            <ModalBody>
              <Text fontSize="sm" color="gray.500" mb="4">
                Actualiza los datos del asiento y guarda los cambios.
              </Text>
              <Stack spacing="4">
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
                  <Field label="Mes" required>
                    <Input
                      type="month"
                      value={period}
                      onChange={(event) => setPeriod(event.target.value)}
                    />
                  </Field>
                  <Field label="Rubro" required>
                    <Select
                      value={entry.rubro_padre_id}
                      onChange={(event) =>
                        setEntry({
                          ...entry,
                          rubro_padre_id: event.target.value,
                          rubro_id: "",
                        })
                      }
                    >
                      <option value="">Selecciona rubro</option>
                      {parents.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.nombre}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Categoría" required>
                    <Select
                      value={entry.rubro_id}
                      isDisabled={!entry.rubro_padre_id}
                      onChange={(event) =>
                        setEntry({ ...entry, rubro_id: event.target.value })
                      }
                    >
                      <option value="">Selecciona categoría</option>
                      {categories.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.nombre}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Monto sin IGV" required>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={entry.importe}
                      onChange={(event) =>
                        setEntry({ ...entry, importe: event.target.value })
                      }
                    />
                  </Field>
                  <Field label="Linea de negocio">
                    <Select
                      value={entry.centro_resultado_id}
                      onChange={(event) =>
                        setEntry({
                          ...entry,
                          centro_resultado_id: event.target.value,
                        })
                      }
                    >
                      <option value="">Repartir automaticamente</option>
                      {centers.data?.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.nombre}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Descripcion">
                    <Input
                      value={entry.descripcion}
                      placeholder={selectedCategory?.nombre ?? "Opcional"}
                      onChange={(event) =>
                        setEntry({ ...entry, descripcion: event.target.value })
                      }
                    />
                  </Field>
                  <Field label="Referencia">
                    <Input value={`Cierre ${period}`} isReadOnly />
                  </Field>
                </SimpleGrid>
                <Field label="Observaciones">
                  <Textarea
                    value={entry.observaciones}
                    onChange={(event) =>
                      setEntry({ ...entry, observaciones: event.target.value })
                    }
                  />
                </Field>
                <Text fontSize="sm" color="gray.500">
                  Deja la linea vacia solo para gastos compartidos con una regla
                  de reparto activa.
                </Text>
                {saveEntry.error && <ErrorBox error={saveEntry.error} />}
              </Stack>
            </ModalBody>
            <ModalFooter>
              <Button
                onClick={() => {
                  setEditingEntry(null);
                  setEntry(emptyEntry);
                }}
              >
                Cancelar
              </Button>
              <Button
                ml="3"
                colorScheme="brand"
                isLoading={saveEntry.isPending}
                onClick={() => saveEntry.mutate()}
              >
                Guardar cambios
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      )}
      {selectedRule && (
        <RuleDetailModal
          rule={selectedRule}
          centers={centers.data ?? []}
          onClose={() => setSelectedRule(null)}
        />
      )}
    </Stack>
  );
}

function RuleFormModal({
  rule,
  centers,
  editing,
  loading,
  error,
  onChange,
  onClose,
  onSave,
}: {
  rule: RuleForm;
  centers: { id: string; nombre: string }[];
  editing: boolean;
  loading: boolean;
  error: Error | null;
  onChange: (rule: RuleForm) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <Modal isOpen onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          {editing ? "Editar regla de distribución" : "Nueva regla de distribución"}
        </ModalHeader>
        <ModalBody>
          <Stack spacing="5">
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
              <Field label="Nombre" required>
                <Input
                  value={rule.nombre}
                  onChange={(event) =>
                    onChange({ ...rule, nombre: event.target.value })
                  }
                />
              </Field>
              <Field label="Vigente desde">
                <Input
                  type="date"
                  value={rule.vigente_desde}
                  onChange={(event) =>
                    onChange({ ...rule, vigente_desde: event.target.value })
                  }
                />
              </Field>
              <Field label="Vigente hasta">
                <Input
                  type="date"
                  min={rule.vigente_desde || undefined}
                  value={rule.vigente_hasta}
                  onChange={(event) =>
                    onChange({ ...rule, vigente_hasta: event.target.value })
                  }
                />
              </Field>
            </SimpleGrid>
            <Box>
              <Text fontSize="sm" fontWeight="semibold" mb="2">
                Distribución
              </Text>
              <Stack spacing="2">
                {rule.lineas.map((line, index) => (
                  <HStack key={index}>
                    <Select
                      value={line.centro_resultado_id}
                      onChange={(event) =>
                        onChange({
                          ...rule,
                          lineas: rule.lineas.map((current, currentIndex) =>
                            currentIndex === index
                              ? {
                                  ...current,
                                  centro_resultado_id: event.target.value,
                                }
                              : current,
                          ),
                        })
                      }
                    >
                      <option value="">Linea de negocio</option>
                      {centers.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.nombre}
                        </option>
                      ))}
                    </Select>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="%"
                      value={line.porcentaje}
                      onChange={(event) =>
                        onChange({
                          ...rule,
                          lineas: rule.lineas.map((current, currentIndex) =>
                            currentIndex === index
                              ? { ...current, porcentaje: event.target.value }
                              : current,
                          ),
                        })
                      }
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      colorScheme="red"
                      isDisabled={rule.lineas.length === 2}
                      onClick={() =>
                        onChange({
                          ...rule,
                          lineas: rule.lineas.filter(
                            (_, currentIndex) => currentIndex !== index,
                          ),
                        })
                      }
                    >
                      Quitar
                    </Button>
                  </HStack>
                ))}
              </Stack>
              <Button
                mt="3"
                size="sm"
                variant="outline"
                onClick={() =>
                  onChange({
                    ...rule,
                    lineas: [
                      ...rule.lineas,
                      { centro_resultado_id: "", porcentaje: "" },
                    ],
                  })
                }
              >
                Agregar línea de negocio
              </Button>
            </Box>
            {error && <ErrorBox error={error} />}
          </Stack>
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Cancelar</Button>
          <Button ml="3" colorScheme="brand" isLoading={loading} onClick={onSave}>
            {editing ? "Guardar cambios" : "Crear regla"}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

function RuleDetailModal({
  rule,
  centers,
  onClose,
}: {
  rule: ReglaDistribucion;
  centers: { id: string; nombre: string }[];
  onClose: () => void;
}) {
  return (
    <Modal isOpen onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Detalle de regla</ModalHeader>
        <ModalBody>
          <Stack spacing="5">
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
              <Detail label="Nombre" value={rule.nombre} />
              <Detail
                label="Vigente desde"
                value={rule.vigente_desde ?? "Desde siempre"}
              />
              <Detail
                label="Vigente hasta"
                value={rule.vigente_hasta ?? "Sin límite"}
              />
              <Detail
                label="Estado"
                value={rule.is_active ? "Activa" : "Inactiva"}
              />
            </SimpleGrid>
            <Box>
              <Text fontSize="sm" fontWeight="semibold" mb="2">
                Distribución
              </Text>
              <Stack spacing="2">
                {rule.lineas.map((line) => (
                  <HStack
                    key={line.centro_resultado_id}
                    justify="space-between"
                    borderWidth="1px"
                    borderRadius="md"
                    px="3"
                    py="2"
                  >
                    <Text>
                      {centers.find(
                        (center) => center.id === line.centro_resultado_id,
                      )?.nombre ?? "Línea no disponible"}
                    </Text>
                    <Text fontWeight="semibold">{line.porcentaje}%</Text>
                  </HStack>
                ))}
              </Stack>
            </Box>
          </Stack>
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Cerrar</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Text fontSize="xs" color="gray.500">
        {label}
      </Text>
      <Text fontSize="sm">{value}</Text>
    </Box>
  );
}

function DeleteEgypEntryButton({
  entry,
  onDeleted,
}: {
  entry: AsientoResultado;
  onDeleted: () => void;
}) {
  const dialog = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const remove = useMutation({
    mutationFn: () => api.deleteEgypEntry(entry.id),
    onSuccess: () => {
      onDeleted();
      dialog.onClose();
    },
  });
  return (
    <>
      <Button
        size="xs"
        variant="ghost"
        colorScheme="red"
        onClick={dialog.onOpen}
      >
        Eliminar
      </Button>
      <AlertDialog
        isOpen={dialog.isOpen}
        leastDestructiveRef={cancelRef}
        onClose={dialog.onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader>Eliminar permanentemente</AlertDialogHeader>
            <AlertDialogBody>
              Esta acción eliminará el asiento de forma definitiva. Si tiene una
              distribución asociada, también se eliminarán sus líneas derivadas.
              No se puede deshacer.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={dialog.onClose}>
                Cancelar
              </Button>
              <Button
                colorScheme="red"
                ml="3"
                isLoading={remove.isPending}
                onClick={() => remove.mutate()}
              >
                Eliminar permanentemente
              </Button>
            </AlertDialogFooter>
            {remove.isError && (
              <Box px="6" pb="4">
                <ErrorBox error={remove.error} />
              </Box>
            )}
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
}
