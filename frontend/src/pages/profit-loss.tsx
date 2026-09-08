import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, CardBody, HStack, Select, SimpleGrid, Stack, Td, Text, Tr } from "@chakra-ui/react";
import { api } from "../client/api";
import { DataTable, ErrorBox, Field, Loading, Metric, PageTitle } from "../components/common";
import { money } from "../lib/format";

const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
const currentDate = new Date();
const pad = (value: number) => String(value).padStart(2, "0");
const periodDates = (year: number, month: number) => ({
  from: `${year}-${pad(month)}-01`,
  to: `${year}-${pad(month)}-${pad(new Date(year, month, 0).getDate())}`,
});

export function ProfitLossPage() {
  const [year, setYear] = useState(currentDate.getFullYear());
  const [month, setMonth] = useState(currentDate.getMonth() + 1);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedRubro, setSelectedRubro] = useState<string>();
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
  return <Stack spacing="6">
    <PageTitle title="Ganancias y pérdidas" description="Resultado contable trazable por rubro y línea de negocio." />
    <Card><CardBody><SimpleGrid columns={{ base: 1, md: 2 }} spacing="4"><Field label="Año"><Select value={year} onChange={(event) => setYear(Number(event.target.value))}>{Array.from({ length: 5 }, (_, index) => currentDate.getFullYear() - 2 + index).map((item) => <option key={item} value={item}>{item}</option>)}</Select></Field><Field label="Mes"><Select value={month} onChange={(event) => setMonth(Number(event.target.value))}>{monthNames.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}</Select></Field></SimpleGrid></CardBody></Card>
    {summary.isLoading && <Loading />}
    {summary.isError && <ErrorBox error={summary.error} />}
    {summary.data && <>
      <SimpleGrid columns={{ base: 1, md: 2, xl: 5 }} spacing="4">
        <Card><CardBody><Metric label="Ingresos netos" value={money(summary.data.ingresos_netos, "PEN")} color="green.600" /></CardBody></Card>
        <Card><CardBody><Metric label="Utilidad bruta" value={money(summary.data.utilidad_bruta, "PEN")} /></CardBody></Card>
        <Card><CardBody><Metric label="Gastos operativos" value={money(summary.data.gastos_operativos, "PEN")} color="red.600" /></CardBody></Card>
        <Card><CardBody><Metric label="Utilidad operativa" value={money(summary.data.utilidad_operativa, "PEN")} /></CardBody></Card>
        <Card><CardBody><Metric label="Utilidad neta" value={money(summary.data.utilidad_neta, "PEN")} color={Number(summary.data.utilidad_neta) < 0 ? "red.600" : "green.600"} /></CardBody></Card>
      </SimpleGrid>
      <HStack><Button size="sm" onClick={() => setExpanded(new Set(allParents))}>Expandir todo</Button><Button size="sm" variant="outline" onClick={() => setExpanded(new Set())}>Contraer todo</Button></HStack>
      <DataTable headers={["Rubro", ...summary.data.centros.map((center) => center.nombre), "Total"]} empty="No hay asientos para el período.">
        {visibleRows.map((rubro) => {
          const hasChildren = children.has(rubro.rubro_id);
          return <Tr key={rubro.rubro_id}><Td><HStack pl={rubro.padre_id ? "5" : "0"}><Button size="xs" visibility={hasChildren ? "visible" : "hidden"} onClick={() => setExpanded((current) => { const next = new Set(current); next.has(rubro.rubro_id) ? next.delete(rubro.rubro_id) : next.add(rubro.rubro_id); return next; })}>{expanded.has(rubro.rubro_id) ? "−" : "+"}</Button><Button size="sm" variant="link" color="inherit" fontWeight={rubro.padre_id ? "normal" : "bold"} onClick={() => setSelectedRubro(rubro.rubro_id)}>{rubro.nombre}</Button></HStack></Td>{summary.data.centros.map((center) => <Td key={center.id} isNumeric>{money(rubro.por_centro[center.codigo] ?? 0, "PEN")}</Td>)}<Td isNumeric fontWeight="semibold">{money(rubro.total, "PEN")}</Td></Tr>;
        })}
      </DataTable>
      {selectedRubro && <Card><CardBody><Stack spacing="3"><HStack justify="space-between"><Text fontWeight="semibold">Asientos que componen el rubro</Text><Button size="sm" onClick={() => setSelectedRubro(undefined)}>Cerrar detalle</Button></HStack>{entries.isLoading && <Loading />}{entries.isError && <ErrorBox error={entries.error} />}{entries.data && <DataTable headers={["Fecha", "Cuenta", "Descripción", "Documento", "Centro", "Debe", "Haber"]} empty="No hay asientos para este rubro.">{entries.data.filter((entry) => selectedIds.has(entry.rubro_id)).map((entry) => <Tr key={entry.id}><Td>{entry.fecha}</Td><Td>{entry.cuenta_contable}</Td><Td>{entry.descripcion}</Td><Td>{entry.documento ?? "-"}</Td><Td>{summary.data.centros.find((center) => center.id === entry.centro_resultado_id)?.nombre ?? "Sin centro"}</Td><Td isNumeric>{money(entry.debe, entry.moneda)}</Td><Td isNumeric>{money(entry.haber, entry.moneda)}</Td></Tr>)}</DataTable>}</Stack></CardBody></Card>}
    </>}
  </Stack>;
}
