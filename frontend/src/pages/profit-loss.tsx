import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Button, Card, CardBody, HStack, Input, Select, SimpleGrid, Stack, Table, Tbody, Td, Text, Th, Thead, Tr } from "@chakra-ui/react";
import { api } from "../client/api";
import { DataTable, ErrorBox, Field, Loading, Metric, PageTitle, TablePagination } from "../components/common";
import { money } from "../lib/format";

const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
const currentDate = new Date();
const pad = (value: number) => String(value).padStart(2, "0");
const periodDates = (year: number, month: number) => ({
  from: `${year}-${pad(month)}-01`,
  to: `${year}-${pad(month)}-${pad(new Date(year, month, 0).getDate())}`,
});
type ProfitabilityKey = "ingresos_brutos" | "ingresos_netos" | "utilidad_bruta" | "utilidad_neta";

export function ProfitLossPage() {
  const [year, setYear] = useState(currentDate.getFullYear());
  const [month, setMonth] = useState(currentDate.getMonth() + 1);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedRubro, setSelectedRubro] = useState<string>();
  const [detailSearch, setDetailSearch] = useState("");
  const [detailPage, setDetailPage] = useState(1);
  const summary = useQuery({
    queryKey: ["egyp-summary", year, month],
    queryFn: () => api.egypSummary(new URLSearchParams({ fecha_desde: periodDates(year, month).from, fecha_hasta: periodDates(year, month).to })),
  });
  const entries = useQuery({
    queryKey: ["egyp-entries", year, month, selectedRubro],
    enabled: Boolean(selectedRubro),
    queryFn: () => api.egypEntries(new URLSearchParams({ fecha_desde: periodDates(year, month).from, fecha_hasta: periodDates(year, month).to })),
  });
  const rows = summary.data?.rubros ?? [];
  const children = new Map<string, typeof rows>();
  rows.forEach((row) => {
    if (row.padre_id) children.set(row.padre_id, [...(children.get(row.padre_id) ?? []), row]);
  });
  const visibleRows: typeof rows = [];
  const appendVisible = (parentId?: string) => {
    rows.filter((row) => (row.padre_id ?? undefined) === parentId).forEach((row) => {
      visibleRows.push(row);
      if (expanded.has(row.rubro_id)) appendVisible(row.rubro_id);
    });
  };
  appendVisible();
  const descendantIds = (rubroId: string): Set<string> => {
    const ids = new Set([rubroId]);
    const addChildren = (parentId: string) => (children.get(parentId) ?? []).forEach((child) => {
      ids.add(child.rubro_id);
      addChildren(child.rubro_id);
    });
    addChildren(rubroId);
    return ids;
  };
  const selectedIds = selectedRubro ? descendantIds(selectedRubro) : new Set<string>();
  const allParents = [...children.keys()];
  const matchingEntries = (entries.data ?? []).filter((entry) => {
    const value = detailSearch.trim().toLowerCase();
    return selectedIds.has(entry.rubro_id) && (!value || [entry.descripcion, entry.documento ?? ""].some((field) => field.toLowerCase().includes(value)));
  });
  const detailPageSize = 10;
  const safeDetailPage = Math.min(detailPage, Math.max(1, Math.ceil(matchingEntries.length / detailPageSize)));
  const detailEntries = matchingEntries.slice((safeDetailPage - 1) * detailPageSize, safeDetailPage * detailPageSize);
  const profitabilityByCenter = new Map(summary.data?.rentabilidad_por_centro.map((item) => [item.centro_id, item]) ?? []);
  const profitabilityRows: { label: string; key: ProfitabilityKey; total: string }[] = summary.data ? [
    { label: "INGRESOS BRUTOS", key: "ingresos_brutos", total: summary.data.ingresos_brutos },
    { label: "INGRESOS NETOS", key: "ingresos_netos", total: summary.data.ingresos_netos },
    { label: "UTILIDAD BRUTA", key: "utilidad_bruta", total: summary.data.utilidad_bruta },
    { label: "UTILIDAD NETA", key: "utilidad_neta", total: summary.data.utilidad_neta },
  ] : [];
  return <Stack spacing="6">
    <PageTitle title="Ganancias y pérdidas" description="Consulta el resultado del período, abre un rubro y revisa los asientos que lo componen." />
    <Card><CardBody><SimpleGrid columns={{ base: 1, md: 3 }} spacing="4"><Field label="Año"><Select value={year} onChange={(event) => setYear(Number(event.target.value))}>{Array.from({ length: 5 }, (_, index) => currentDate.getFullYear() - 2 + index).map((item) => <option key={item} value={item}>{item}</option>)}</Select></Field><Field label="Mes"><Select value={month} onChange={(event) => setMonth(Number(event.target.value))}>{monthNames.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}</Select></Field><Box pt={{ base: 0, md: 8 }}><Text fontSize="sm" color="gray.500">Haz clic en un rubro para ver su sustento.</Text></Box></SimpleGrid></CardBody></Card>
    {summary.isLoading && <Loading />}
    {summary.isError && <ErrorBox error={summary.error} />}
    {summary.data && <>
      <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing="4">
        <Card><CardBody><Metric label="Ingresos brutos" value={money(summary.data.ingresos_brutos, "PEN")} color="green.600" /></CardBody></Card>
        <Card><CardBody><Metric label="Margen bruto" value={money(summary.data.utilidad_bruta, "PEN")} /></CardBody></Card>
        <Card><CardBody><Metric label="Total de gastos" value={money(summary.data.gastos_operativos, "PEN")} color="red.600" /></CardBody></Card>
        <Card><CardBody><Metric label="Utilidad operativa" value={money(summary.data.utilidad_operativa, "PEN")} /></CardBody></Card>
      </SimpleGrid>
       <HStack justify="space-between" flexWrap="wrap"><Text fontSize="sm" color="gray.500">Los importes positivos aumentan el resultado; los negativos lo reducen.</Text><HStack><Button size="sm" onClick={() => setExpanded(new Set(allParents))}>Expandir todo</Button><Button size="sm" variant="outline" onClick={() => setExpanded(new Set())}>Contraer todo</Button></HStack></HStack>
       <Card><CardBody p="0"><Box className="table-wrap matrix-wrap"><Table size="sm" variant="simple" className="matrix-table"><Thead><Tr><Th minW="300px" className="matrix-label-cell">Rubro de resultado</Th>{summary.data.centros.map((center) => <Th key={center.id} isNumeric whiteSpace="nowrap">{center.nombre}</Th>)}<Th isNumeric className="matrix-total-cell">Total</Th></Tr></Thead><Tbody>{visibleRows.map((rubro) => {
          const hasChildren = children.has(rubro.rubro_id);
          const rowClass = hasChildren ? "matrix-activity-row" : "matrix-concept-row";
          return <Tr key={rubro.rubro_id} className={rowClass}><Td className="matrix-label-cell"><HStack pl={rubro.padre_id ? "8" : "0"}><Button size="xs" variant="ghost" visibility={hasChildren ? "visible" : "hidden"} onClick={() => setExpanded((current) => { const next = new Set(current); next.has(rubro.rubro_id) ? next.delete(rubro.rubro_id) : next.add(rubro.rubro_id); return next; })}>{expanded.has(rubro.rubro_id) ? "−" : "+"}</Button><Button size="sm" variant="link" color="inherit" fontWeight={hasChildren ? "bold" : "normal"} onClick={() => { setSelectedRubro(rubro.rubro_id); setDetailSearch(""); setDetailPage(1); }}>{rubro.nombre}</Button></HStack></Td>{summary.data.centros.map((center) => <Td key={center.id} isNumeric whiteSpace="nowrap" color={Number(rubro.por_centro[center.codigo] ?? 0) < 0 ? "red.600" : Number(rubro.por_centro[center.codigo] ?? 0) > 0 ? "green.600" : "gray.500"}>{money(rubro.por_centro[center.codigo] ?? 0, "PEN")}</Td>)}<Td isNumeric whiteSpace="nowrap" fontWeight="semibold" className="matrix-total-cell" color={Number(rubro.total) < 0 ? "red.700" : Number(rubro.total) > 0 ? "green.700" : "gray.600"}>{money(rubro.total, "PEN")}</Td></Tr>;
        })}{profitabilityRows.map((metric) => <Tr key={metric.key} className={metric.key === "utilidad_neta" ? "matrix-net-operating-row" : metric.key === "utilidad_bruta" ? "matrix-gross-operating-row" : "matrix-activity-row"}><Td className="matrix-label-cell" fontWeight="bold">{metric.label}</Td>{summary.data.centros.map((center) => { const value = profitabilityByCenter.get(center.id)?.[metric.key]; return <Td key={center.id} isNumeric whiteSpace="nowrap" color={metric.key.includes("utilidad") ? Number(value ?? 0) < 0 ? "red.600" : "green.600" : undefined}>{money(value ?? 0, "PEN")}</Td>; })}<Td isNumeric whiteSpace="nowrap" className="matrix-total-cell" fontWeight="bold">{money(metric.total, "PEN")}</Td></Tr>)}</Tbody></Table></Box>{visibleRows.length === 0 && <Text p="6" color="gray.500">No hay asientos para el período.</Text>}</CardBody></Card>
       {selectedRubro && <Card><CardBody><Stack spacing="4"><HStack justify="space-between" flexWrap="wrap"><Box><Text fontWeight="semibold">Detalle del rubro</Text><Text fontSize="sm" color="gray.500">Busca y revisa los asientos que sustentan el total.</Text></Box><Button size="sm" onClick={() => setSelectedRubro(undefined)}>Cerrar detalle</Button></HStack><Input value={detailSearch} onChange={(event) => { setDetailSearch(event.target.value); setDetailPage(1); }} placeholder="Buscar por descripción o documento" />{entries.isLoading && <Loading />}{entries.isError && <ErrorBox error={entries.error} />}{entries.data && <><DataTable headers={["Fecha", "Descripción", "Documento", "Centro", "Debe", "Haber"]} empty="No hay asientos que coincidan.">{detailEntries.map((entry) => <Tr key={entry.id}><Td>{entry.fecha}</Td><Td>{entry.descripcion}</Td><Td>{entry.documento ?? "-"}</Td><Td>{summary.data.centros.find((center) => center.id === entry.centro_resultado_id)?.nombre ?? "Sin centro"}</Td><Td isNumeric>{money(entry.debe, entry.moneda)}</Td><Td isNumeric>{money(entry.haber, entry.moneda)}</Td></Tr>)}</DataTable><TablePagination total={matchingEntries.length} page={safeDetailPage} pageSize={detailPageSize} onPageChange={setDetailPage} /></>}</Stack></CardBody></Card>}
    </>}
  </Stack>;
}
