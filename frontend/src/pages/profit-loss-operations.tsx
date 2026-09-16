import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, Button, Card, CardBody, HStack, Input, Select, SimpleGrid, Stack, Text, Textarea } from "@chakra-ui/react";
import { api, type ReglaDistribucion } from "../client/api";
import { DataTable, Editor, ErrorBox, Field, PageTitle, TablePagination } from "../components/common";

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
  const [rule, setRule] = useState(emptyRule);
  const [ruleSearch, setRuleSearch] = useState("");
  const [rulePage, setRulePage] = useState(1);
  const centers = useQuery({ queryKey: ["egyp-centros"], queryFn: () => api.egypCentros() });
  const rubros = useQuery({ queryKey: ["egyp-rubros"], queryFn: () => api.egypRubros() });
  const rules = useQuery({ queryKey: ["egyp-rules"], queryFn: () => api.egypReglas(true) });
  const parentIds = new Set((rubros.data ?? []).flatMap((item) => item.padre_id ? [item.padre_id] : []));
  const concepts = (rubros.data ?? []).filter((item) => item.is_active && !parentIds.has(item.id));
  const selectedRubro = concepts.find((item) => item.id === entry.rubro_id);
  const refresh = () => ["egyp-rules", "egyp-summary", "egyp-entries", "egyp-entries-admin"].forEach((key) => void queryClient.invalidateQueries({ queryKey: [key] }));
  const saveEntry = useMutation({
    mutationFn: () => {
      if (!selectedRubro) throw new Error("Selecciona un concepto.");
      const amount = Number(entry.importe);
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Ingresa un monto mayor a cero.");
      const credit = ["INGRESO", "INGRESO_FINANCIERO"].includes(selectedRubro.naturaleza);
      return api.createEgypEntry({
        fecha: monthEnd(period), descripcion: entry.descripcion || selectedRubro.nombre,
        documento: `Cierre ${period}`, moneda: "PEN", debe: credit ? 0 : amount, haber: credit ? amount : 0,
        centro_resultado_id: entry.centro_resultado_id || null, rubro_id: selectedRubro.id,
        observaciones: entry.observaciones || null,
      });
    },
    onSuccess: () => { refresh(); setEntry(emptyEntry); },
  });
  const saveRule = useMutation({
    mutationFn: () => api.createEgypRegla({ ...rule, vigente_desde: rule.vigente_desde || null, vigente_hasta: null, lineas: rule.lineas }),
    onSuccess: () => { refresh(); setRule(emptyRule); },
  });
  const matchingRules = (rules.data ?? []).filter((item) => item.is_active && item.nombre.toLowerCase().includes(ruleSearch.trim().toLowerCase()));
  const pageSize = 8;
  const safePage = Math.min(rulePage, Math.max(1, Math.ceil(matchingRules.length / pageSize)));
  const visibleRules = matchingRules.slice((safePage - 1) * pageSize, safePage * pageSize);

  return <Stack spacing="6">
    <PageTitle title="Cierre mensual EGyP" description="Registra totales mensuales, no facturas individuales. El sistema distribuye los gastos compartidos." />
    <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
      <Card borderTop="3px solid" borderColor="brand.500"><CardBody><Text fontSize="xs" color="brand.600" fontWeight="bold">1. ELIGE EL MES</Text><Text mt="1" fontWeight="semibold">Cierre mensual</Text><Text mt="1" fontSize="sm" color="gray.500">La fecha se guarda automaticamente al ultimo dia del mes.</Text></CardBody></Card>
      <Card borderTop="3px solid" borderColor="brand.500"><CardBody><Text fontSize="xs" color="brand.600" fontWeight="bold">2. INGRESA EL TOTAL</Text><Text mt="1" fontWeight="semibold">Un importe por concepto</Text><Text mt="1" fontSize="sm" color="gray.500">Ventas, notas de credito, costos o gastos consolidados sin IGV.</Text></CardBody></Card>
      <Card borderTop="3px solid" borderColor="brand.500"><CardBody><Text fontSize="xs" color="brand.600" fontWeight="bold">3. REVISA EL RESULTADO</Text><Text mt="1" fontWeight="semibold">Margen y utilidad</Text><Text mt="1" fontSize="sm" color="gray.500">Los gastos sin linea se reparten segun su regla activa.</Text></CardBody></Card>
    </SimpleGrid>
    <Editor title="Registrar total del mes" onSubmit={() => saveEntry.mutate()} loading={saveEntry.isPending} error={saveEntry.error}>
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
    </Editor>
    <Editor title="Nueva regla de reparto" onSubmit={() => saveRule.mutate()} loading={saveRule.isPending} error={saveRule.error}>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3"><Field label="Nombre" required><Input value={rule.nombre} onChange={(event) => setRule({ ...rule, nombre: event.target.value })} /></Field><Field label="Concepto a repartir" required><Select value={rule.rubro_id} onChange={(event) => setRule({ ...rule, rubro_id: event.target.value })}><option value="">Selecciona concepto</option>{concepts.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select></Field><Field label="Vigente desde"><Input type="date" value={rule.vigente_desde} onChange={(event) => setRule({ ...rule, vigente_desde: event.target.value })} /></Field></SimpleGrid>
      <SimpleGrid columns={{ base: 1, md: 2 }} spacing="3" mt="3">{rule.lineas.map((line, index) => <HStack key={index}><Select value={line.centro_resultado_id} onChange={(event) => setRule({ ...rule, lineas: rule.lineas.map((current, currentIndex) => currentIndex === index ? { ...current, centro_resultado_id: event.target.value } : current) })}><option value="">Linea de negocio</option>{centers.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select><Input type="number" step="0.01" placeholder="%" value={line.porcentaje} onChange={(event) => setRule({ ...rule, lineas: rule.lineas.map((current, currentIndex) => currentIndex === index ? { ...current, porcentaje: event.target.value } : current) })} /></HStack>)}</SimpleGrid>
    </Editor>
    {rules.data && <Stack spacing="3"><Box><Text fontWeight="semibold">Reglas de reparto vigentes</Text><Text fontSize="sm" color="gray.500">Los gastos compartidos se distribuyen automaticamente al dejar la linea vacia.</Text></Box><Input value={ruleSearch} onChange={(event) => { setRuleSearch(event.target.value); setRulePage(1); }} placeholder="Buscar regla" /><DataTable headers={["Regla", "Concepto", "Distribucion"]} empty="No hay reglas activas.">{visibleRules.map((item: ReglaDistribucion) => <tr key={item.id}><td>{item.nombre}</td><td>{concepts.find((rubro) => rubro.id === item.rubro_id)?.nombre}</td><td>{item.lineas.map((line) => `${centers.data?.find((center) => center.id === line.centro_resultado_id)?.nombre ?? "Linea"}: ${line.porcentaje}%`).join(" · ")}</td></tr>)}</DataTable><TablePagination total={matchingRules.length} page={safePage} pageSize={pageSize} onPageChange={setRulePage} /></Stack>}
  </Stack>;
}
