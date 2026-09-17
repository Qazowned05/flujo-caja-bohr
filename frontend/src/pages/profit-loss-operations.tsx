import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, Button, Card, CardBody, HStack, Input, Select, SimpleGrid, Stack, Text, Textarea } from "@chakra-ui/react";
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
    <PageTitle title="Cierre mensual EGyP" description="Registra totales mensuales, no facturas individuales. El sistema distribuye los gastos compartidos." />
    <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
      <Card borderTop="3px solid" borderColor="brand.500"><CardBody><Text fontSize="xs" color="brand.600" fontWeight="bold">1. ELIGE EL MES</Text><Text mt="1" fontWeight="semibold">Cierre mensual</Text><Text mt="1" fontSize="sm" color="gray.500">La fecha se guarda automaticamente al ultimo dia del mes.</Text></CardBody></Card>
      <Card borderTop="3px solid" borderColor="brand.500"><CardBody><Text fontSize="xs" color="brand.600" fontWeight="bold">2. INGRESA EL TOTAL</Text><Text mt="1" fontWeight="semibold">Un importe por concepto</Text><Text mt="1" fontSize="sm" color="gray.500">Ventas, notas de credito, costos o gastos consolidados sin IGV.</Text></CardBody></Card>
      <Card borderTop="3px solid" borderColor="brand.500"><CardBody><Text fontSize="xs" color="brand.600" fontWeight="bold">3. REVISA EL RESULTADO</Text><Text mt="1" fontWeight="semibold">Margen y utilidad</Text><Text mt="1" fontSize="sm" color="gray.500">Los gastos sin linea se reparten segun su regla activa.</Text></CardBody></Card>
    </SimpleGrid>
    <Editor title={editingEntry ? "Editar total mensual" : "Registrar total del mes"} onSubmit={() => saveEntry.mutate()} loading={saveEntry.isPending} error={saveEntry.error}>
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
    <Editor title="Nueva regla de reparto" onSubmit={() => saveRule.mutate()} loading={saveRule.isPending} error={saveRule.error}>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3"><Field label="Nombre" required><Input value={rule.nombre} onChange={(event) => setRule({ ...rule, nombre: event.target.value })} /></Field><Field label="Concepto a repartir" required><Select value={rule.rubro_id} onChange={(event) => setRule({ ...rule, rubro_id: event.target.value })}><option value="">Selecciona concepto</option>{concepts.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field><Field label="Vigente desde"><Input type="date" value={rule.vigente_desde} onChange={(event) => setRule({ ...rule, vigente_desde: event.target.value })} /></Field></SimpleGrid>
      <SimpleGrid columns={{ base: 1, md: 2 }} spacing="3" mt="3">{rule.lineas.map((line, index) => <HStack key={index}><Select value={line.centro_resultado_id} onChange={(event) => setRule({ ...rule, lineas: rule.lineas.map((current, currentIndex) => currentIndex === index ? { ...current, centro_resultado_id: event.target.value } : current) })}><option value="">Linea de negocio</option>{centers.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select><Input type="number" step="0.01" placeholder="%" value={line.porcentaje} onChange={(event) => setRule({ ...rule, lineas: rule.lineas.map((current, currentIndex) => currentIndex === index ? { ...current, porcentaje: event.target.value } : current) })} /></HStack>)}</SimpleGrid>
    </Editor>
    {rules.data && <Stack spacing="3"><Box><Text fontWeight="semibold">Reglas de reparto vigentes</Text><Text fontSize="sm" color="gray.500">Los gastos compartidos se distribuyen automaticamente al dejar la linea vacia.</Text></Box><Input value={ruleSearch} onChange={(event) => { setRuleSearch(event.target.value); setRulePage(1); }} placeholder="Buscar regla" /><DataTable headers={["Regla", "Concepto", "Distribucion"]} empty="No hay reglas activas.">{visibleRules.map((item: ReglaDistribucion) => <tr key={item.id}><td>{item.nombre}</td><td>{concepts.find((rubro) => rubro.id === item.rubro_id)?.nombre}</td><td>{item.lineas.map((line) => `${centers.data?.find((center) => center.id === line.centro_resultado_id)?.nombre ?? "Linea"}: ${line.porcentaje}%`).join(" · ")}</td></tr>)}</DataTable><TablePagination total={matchingRules.length} page={safePage} pageSize={pageSize} onPageChange={setRulePage} /></Stack>}
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
  </Stack>;
}
