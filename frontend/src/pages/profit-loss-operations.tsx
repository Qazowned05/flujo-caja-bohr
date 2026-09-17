import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, Button, HStack, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, ModalOverlay, Select, SimpleGrid, Stack, Text, Textarea } from "@chakra-ui/react";
import { api, type AsientoResultado, type ReglaDistribucion } from "../client/api";
import { DataTable, Editor, ErrorBox, Field, PageTitle, TablePagination } from "../components/common";
import { money } from "../lib/format";

type RuleLine = { centro_resultado_id: string; porcentaje: string };
const currentDate = new Date();
const emptyEntry = { descripcion: "", importe: "", centro_resultado_id: "", rubro_id: "", observaciones: "" };
const emptyRule = { nombre: "", rubro_id: "", vigente_desde: "", lineas: [{ centro_resultado_id: "", porcentaje: "" }, { centro_resultado_id: "", porcentaje: "" }] as RuleLine[] };
const monthEnd = (period: string) => {
  const [year, month] = period.split("-").map(Number);
  return `${year}-${String(month).padStart(2, "0")}-${new Date(year, month, 0).getDate()}`;
};

export function ProfitLossOperationsPage() {
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState(`${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`);
  const [entry, setEntry] = useState(emptyEntry);
  const [editingEntry, setEditingEntry] = useState<AsientoResultado | null>(null);
  const [rule, setRule] = useState(emptyRule);
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [selectedRule, setSelectedRule] = useState<ReglaDistribucion | null>(null);
  const [ruleSearch, setRuleSearch] = useState("");
  const [rulePage, setRulePage] = useState(1);
  const [historyPeriod, setHistoryPeriod] = useState(`${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`);
  const [historyRubro, setHistoryRubro] = useState("");
  const [historyCenter, setHistoryCenter] = useState("");
  const [historySearch, setHistorySearch] = useState("");
  const [historyPage, setHistoryPage] = useState(1);
  const centers = useQuery({ queryKey: ["egyp-centros"], queryFn: () => api.egypCentros() });
  const rubros = useQuery({ queryKey: ["egyp-rubros"], queryFn: () => api.egypRubros() });
  const rules = useQuery({ queryKey: ["egyp-rules"], queryFn: () => api.egypReglas(true) });
  const parentIds = new Set((rubros.data ?? []).flatMap((item) => item.padre_id ? [item.padre_id] : []));
  const concepts = (rubros.data ?? []).filter((item) => item.is_active && !parentIds.has(item.id));
  const selectedRubro = concepts.find((item) => item.id === entry.rubro_id);
  const historyParams = new URLSearchParams({ fecha_desde: `${historyPeriod}-01`, fecha_hasta: monthEnd(historyPeriod), solo_origen: "true" });
  if (historyRubro) historyParams.set("rubro_id", historyRubro);
  if (historyCenter) historyParams.set("centro_id", historyCenter);
  if (historySearch.trim()) historyParams.set("busqueda", historySearch.trim());
  const entries = useQuery({ queryKey: ["egyp-entries-history", historyParams.toString()], queryFn: () => api.egypEntries(historyParams) });
  const refresh = () => ["egyp-rules", "egyp-summary", "egyp-entries", "egyp-entries-admin", "egyp-entries-history"].forEach((key) => void queryClient.invalidateQueries({ queryKey: [key] }));
  const saveEntry = useMutation({
    mutationFn: () => {
      if (!selectedRubro) throw new Error("Selecciona un concepto.");
      const amount = Number(entry.importe);
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Ingresa un monto mayor a cero.");
      const credit = ["INGRESO", "INGRESO_FINANCIERO"].includes(selectedRubro.naturaleza);
      const data = {
        fecha: monthEnd(period), descripcion: entry.descripcion || selectedRubro.nombre,
        documento: `Cierre ${period}`, moneda: "PEN", debe: credit ? 0 : amount, haber: credit ? amount : 0,
        centro_resultado_id: entry.centro_resultado_id || null, rubro_id: selectedRubro.id,
        observaciones: entry.observaciones || null,
      };
      return editingEntry ? api.updateEgypEntry(editingEntry.id, data) : api.createEgypEntry(data);
    },
    onSuccess: () => { refresh(); setEntry(emptyEntry); setEditingEntry(null); },
  });
  const cancelEntry = useMutation({
    mutationFn: (id: string) => api.cancelEgypEntry(id, "Anulado desde el historial EGyP"),
    onSuccess: refresh,
  });
  const saveRule = useMutation({
    mutationFn: () => api.createEgypRegla({ ...rule, vigente_desde: rule.vigente_desde || null, vigente_hasta: null, lineas: rule.lineas }),
    onSuccess: () => { refresh(); setRule(emptyRule); },
  });
  const matchingRules = (rules.data ?? []).filter((item) => item.is_active && item.nombre.toLowerCase().includes(ruleSearch.trim().toLowerCase()));
  const pageSize = 8;
  const safePage = Math.min(rulePage, Math.max(1, Math.ceil(matchingRules.length / pageSize)));
  const visibleRules = matchingRules.slice((safePage - 1) * pageSize, safePage * pageSize);
  const historyPageSize = 10;
  const historyEntries = entries.data ?? [];
  const safeHistoryPage = Math.min(historyPage, Math.max(1, Math.ceil(historyEntries.length / historyPageSize)));
  const visibleEntries = historyEntries.slice((safeHistoryPage - 1) * historyPageSize, safeHistoryPage * historyPageSize);
  const editEntry = (item: AsientoResultado) => {
    setEditingEntry(item);
    setPeriod(item.fecha.slice(0, 7));
    setEntry({ descripcion: item.descripcion, importe: String(Number(item.haber) || Number(item.debe)), centro_resultado_id: item.centro_resultado_id ?? "", rubro_id: item.rubro_id, observaciones: item.observaciones ?? "" });
  };

  return <Stack spacing="6">
    <PageTitle title="Cierre mensual EGyP" description="Registra y corrige los totales mensuales por concepto, sin IGV." />
    <Editor title={editingEntry ? "Editar registro" : "Ingresar registro"} onSubmit={() => saveEntry.mutate()} loading={saveEntry.isPending} error={saveEntry.error}>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3">
        <Field label="Mes" required><Input type="month" value={period} onChange={(event) => setPeriod(event.target.value)} /></Field>
        <Field label="Concepto" required><Select value={entry.rubro_id} onChange={(event) => setEntry({ ...entry, rubro_id: event.target.value })}><option value="">Selecciona concepto</option>{concepts.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field>
        <Field label="Monto sin IGV" required><Input type="number" min="0" step="0.01" value={entry.importe} onChange={(event) => setEntry({ ...entry, importe: event.target.value })} /></Field>
        <Field label="Linea de negocio"><Select value={entry.centro_resultado_id} onChange={(event) => setEntry({ ...entry, centro_resultado_id: event.target.value })}><option value="">Repartir automaticamente</option>{centers.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field>
        <Field label="Descripcion"><Input value={entry.descripcion} placeholder={selectedRubro?.nombre ?? "Opcional"} onChange={(event) => setEntry({ ...entry, descripcion: event.target.value })} /></Field>
        <Field label="Referencia"><Input value={`Cierre ${period}`} isReadOnly /></Field>
      </SimpleGrid>
      <Field label="Observaciones"><Textarea value={entry.observaciones} onChange={(event) => setEntry({ ...entry, observaciones: event.target.value })} /></Field>
      <Text fontSize="sm" color="gray.500">Deja la linea vacia solo para gastos compartidos con una regla de reparto activa.</Text>
      {editingEntry && <Button variant="ghost" onClick={() => { setEditingEntry(null); setEntry(emptyEntry); }}>Cancelar edicion</Button>}
    </Editor>
    <Stack spacing="3">
      <HStack justify="space-between" align="start" flexWrap="wrap"><Box><Text fontWeight="semibold">Reglas de distribución</Text><Text fontSize="sm" color="gray.500">Se aplican a gastos compartidos sin línea de negocio.</Text></Box><Button size="sm" colorScheme="brand" onClick={() => setShowRuleForm(!showRuleForm)}>{showRuleForm ? "Cerrar" : "Nueva regla"}</Button></HStack>
      {showRuleForm && <Editor title="Nueva regla de distribución" onSubmit={() => saveRule.mutate()} loading={saveRule.isPending} error={saveRule.error}>
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3"><Field label="Nombre" required><Input value={rule.nombre} onChange={(event) => setRule({ ...rule, nombre: event.target.value })} /></Field><Field label="Concepto a repartir" required><Select value={rule.rubro_id} onChange={(event) => setRule({ ...rule, rubro_id: event.target.value })}><option value="">Selecciona concepto</option>{concepts.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field><Field label="Vigente desde"><Input type="date" value={rule.vigente_desde} onChange={(event) => setRule({ ...rule, vigente_desde: event.target.value })} /></Field></SimpleGrid>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing="3" mt="3">{rule.lineas.map((line, index) => <HStack key={index}><Select value={line.centro_resultado_id} onChange={(event) => setRule({ ...rule, lineas: rule.lineas.map((current, currentIndex) => currentIndex === index ? { ...current, centro_resultado_id: event.target.value } : current) })}><option value="">Linea de negocio</option>{centers.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select><Input type="number" step="0.01" placeholder="%" value={line.porcentaje} onChange={(event) => setRule({ ...rule, lineas: rule.lineas.map((current, currentIndex) => currentIndex === index ? { ...current, porcentaje: event.target.value } : current) })} /></HStack>)}</SimpleGrid>
      </Editor>}
      {rules.data && <><Input value={ruleSearch} onChange={(event) => { setRuleSearch(event.target.value); setRulePage(1); }} placeholder="Buscar regla" /><DataTable headers={["Regla", "Concepto", ""]} empty="No hay reglas activas.">{visibleRules.map((item: ReglaDistribucion) => <tr key={item.id}><td>{item.nombre}</td><td>{concepts.find((rubro) => rubro.id === item.rubro_id)?.nombre ?? "-"}</td><td><Button size="sm" variant="outline" onClick={() => setSelectedRule(item)}>Ver detalle</Button></td></tr>)}</DataTable><TablePagination total={matchingRules.length} page={safePage} pageSize={pageSize} onPageChange={setRulePage} /></>}
    </Stack>
    <Stack spacing="3">
      <Box><Text fontWeight="semibold">Transacciones registradas</Text><Text fontSize="sm" color="gray.500">Busca, corrige registros manuales o anula una carga equivocada. La anulacion conserva la trazabilidad.</Text></Box>
      <SimpleGrid columns={{ base: 1, md: 4 }} spacing="3">
        <Field label="Mes"><Input type="month" value={historyPeriod} onChange={(event) => { setHistoryPeriod(event.target.value); setHistoryPage(1); }} /></Field>
        <Field label="Concepto"><Select value={historyRubro} onChange={(event) => { setHistoryRubro(event.target.value); setHistoryPage(1); }}><option value="">Todos los conceptos</option>{concepts.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field>
        <Field label="Linea de negocio"><Select value={historyCenter} onChange={(event) => { setHistoryCenter(event.target.value); setHistoryPage(1); }}><option value="">Todas las lineas</option>{centers.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field>
        <Field label="Buscar texto"><Input value={historySearch} onChange={(event) => { setHistorySearch(event.target.value); setHistoryPage(1); }} placeholder="Descripcion, referencia u observacion" /></Field>
      </SimpleGrid>
      {entries.error && <ErrorBox error={entries.error} />}
      <DataTable headers={["Fecha", "Concepto", "Linea", "Monto", "Descripcion", "Acciones"]} empty="No hay transacciones para los filtros seleccionados.">
        {visibleEntries.map((item) => { const editable = item.origen === "MANUAL" && item.es_resultado; return <tr key={item.id}><td>{item.fecha}</td><td>{concepts.find((rubro) => rubro.id === item.rubro_id)?.nombre ?? "Concepto"}</td><td>{centers.data?.find((center) => center.id === item.centro_resultado_id)?.nombre ?? (item.es_resultado ? "Sin linea" : "Repartido automaticamente")}</td><td>{money(Number(item.haber) || Number(item.debe), item.moneda)}</td><td><Text fontSize="sm">{item.descripcion}</Text>{item.observaciones && <Text fontSize="xs" color="gray.500">{item.observaciones}</Text>}</td><td><HStack><Button size="sm" onClick={() => editEntry(item)} isDisabled={!editable}>Editar</Button><Button size="sm" colorScheme="red" variant="outline" isLoading={cancelEntry.isPending} onClick={() => { if (window.confirm("Se anulara este registro y, si fue repartido, todos sus importes derivados. Esta accion conserva el historial.")) cancelEntry.mutate(item.id); }}>Anular</Button></HStack></td></tr>; })}
      </DataTable>
      <TablePagination total={historyEntries.length} page={safeHistoryPage} pageSize={historyPageSize} onPageChange={setHistoryPage} />
    </Stack>
    {selectedRule && <RuleDetailModal rule={selectedRule} centers={centers.data ?? []} concept={concepts.find((item) => item.id === selectedRule.rubro_id)?.nombre ?? "-"} onClose={() => setSelectedRule(null)} />}
  </Stack>;
}

function RuleDetailModal({ rule, centers, concept, onClose }: { rule: ReglaDistribucion; centers: { id: string; nombre: string }[]; concept: string; onClose: () => void }) {
  return <Modal isOpen onClose={onClose} size="lg"><ModalOverlay /><ModalContent><ModalHeader>Detalle de regla</ModalHeader><ModalBody><Stack spacing="5"><SimpleGrid columns={{ base: 1, md: 2 }} spacing="4"><Detail label="Nombre" value={rule.nombre} /><Detail label="Concepto" value={concept} /><Detail label="Vigente desde" value={rule.vigente_desde ?? "Sin fecha"} /><Detail label="Estado" value={rule.is_active ? "Activa" : "Inactiva"} /></SimpleGrid><Box><Text fontSize="sm" fontWeight="semibold" mb="2">Distribución</Text><Stack spacing="2">{rule.lineas.map((line) => <HStack key={line.centro_resultado_id} justify="space-between" borderWidth="1px" borderRadius="md" px="3" py="2"><Text>{centers.find((center) => center.id === line.centro_resultado_id)?.nombre ?? "Línea no disponible"}</Text><Text fontWeight="semibold">{line.porcentaje}%</Text></HStack>)}</Stack></Box></Stack></ModalBody><ModalFooter><Button onClick={onClose}>Cerrar</Button></ModalFooter></ModalContent></Modal>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <Box><Text fontSize="xs" color="gray.500">{label}</Text><Text fontSize="sm">{value}</Text></Box>;
}
