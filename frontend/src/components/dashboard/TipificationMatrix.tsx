import { Fragment, useState, type Dispatch, type SetStateAction } from "react";
import { Alert, AlertDescription, AlertIcon, Box, Button, Table, Tbody, Td, Th, Thead, Tr } from "@chakra-ui/react";
import { api } from "../../client/api";
import { money } from "../../lib/format";

type RowIds = { activity?: string | null; concept?: string | null; type?: string | null };
type Level = "activity" | "concept" | "type";
type Breakdown = Awaited<ReturnType<typeof api.tipificationBreakdown>>;
type BreakdownConcept = Breakdown["actividades"][number]["conceptos"][number];

const LEVEL_STYLES: Record<Level, { fontSize: string; fontWeight: string; bg: string; colorPos: string; colorNeg: string; colorZero: string; totalBg: string }> = {
  activity: { fontSize: "sm", fontWeight: "bold", bg: "gray.50", colorPos: "green.700", colorNeg: "red.700", colorZero: "gray.700", totalBg: "gray.100" },
  concept: { fontSize: "xs", fontWeight: "semibold", bg: "white", colorPos: "green.600", colorNeg: "red.600", colorZero: "gray.500", totalBg: "gray.50" },
  type: { fontSize: "xs", fontWeight: "normal", bg: "white", colorPos: "green.500", colorNeg: "red.500", colorZero: "gray.400", totalBg: "gray.50" },
};

export function TipificationMatrix({ data, currency, account }: { data: Awaited<ReturnType<typeof api.tipificationBreakdown>>; currency: string; account: string }) {
  const [openActivities, setOpenActivities] = useState<string[]>([]);
  const [openConcepts, setOpenConcepts] = useState<string[]>([]);
  const toggle = (set: Dispatch<SetStateAction<string[]>>, key: string) => set((items) => items.includes(key) ? items.filter((item) => item !== key) : [...items, key]);
  const colorFor = (value: string | number, level: Level) => {
    const s = LEVEL_STYLES[level];
    return Number(value) > 0 ? s.colorPos : Number(value) < 0 ? s.colorNeg : s.colorZero;
  };
  const goToTransactions = (date: string, ids: RowIds) => {
    const search = new URLSearchParams({
      fecha_desde: date,
      fecha_hasta: date,
      ...(account ? { cuenta_bancaria_id: account } : {}),
      ...(ids.activity ? { actividad_id: ids.activity } : {}),
      ...(ids.concept ? { concepto_id: ids.concept } : {}),
      ...(ids.type ? { tipo_id: ids.type } : {}),
      ...(ids.activity === null ? { estado: "PENDIENTE_TIPIFICAR" } : {}),
    });
    window.location.assign(`/transacciones?${search}`);
  };
  const cells = (values: Record<string, string>, total: string, ids: RowIds, level: Level, links = true, textColor?: string, totalBg?: string) => {
    const s = LEVEL_STYLES[level];
    return <>
      {data.fechas.map((date) => {
        const value = values[date];
        const hasValue = value !== undefined;
        const clickable = links && hasValue && Number(value) !== 0;
        return <Td key={date} isNumeric whiteSpace="nowrap" fontSize={s.fontSize} color={textColor ?? (hasValue ? colorFor(value, level) : s.colorZero)} className={clickable ? "matrix-daily-cell" : undefined} onClick={clickable ? () => goToTransactions(date, ids) : undefined}>{hasValue ? money(value, currency) : "-"}</Td>;
      })}
      <Td isNumeric whiteSpace="nowrap" fontSize={s.fontSize} color={textColor ?? colorFor(total, level)} bg={totalBg ?? s.totalBg} className="matrix-total-cell">{money(total, currency)}</Td>
    </>;
  };
  const balanceCells = (field: "saldo_inicial" | "saldo_final", total: string) => <>
    {data.fechas.map((date) => {
      const value = data.saldos_por_fecha[date]?.[field] ?? "0";
      return <Td key={date} isNumeric whiteSpace="nowrap" color={colorFor(value, "activity")}>{money(value, currency)}</Td>;
    })}
    <Td isNumeric whiteSpace="nowrap" color={colorFor(total, "activity")} fontWeight={field === "saldo_final" ? "bold" : "normal"} className="matrix-total-cell">{money(total, currency)}</Td>
  </>;
  const operatingSubtotal = (concepts: BreakdownConcept[]) => {
    const values = Object.fromEntries(data.fechas.map((date) => [date, "0"]));
    let total = 0;
    for (const concept of concepts) {
      total += Number(concept.total);
      for (const [date, value] of Object.entries(concept.valores_por_fecha)) {
        values[date] = String(Number(values[date]) + Number(value));
      }
    }
    return { values, total: String(total) };
  };
  const movementsTotal = String(
    Object.values(data.movimientos_diarios_por_fecha).reduce((total, value) => total + Number(value), 0),
  );
  const firstDate = data.fechas[0];
  const lastDate = data.fechas[data.fechas.length - 1];
  const initialTotal = firstDate ? data.saldos_por_fecha[firstDate]?.saldo_inicial ?? "0" : "0";
  const finalTotal = lastDate ? data.saldos_por_fecha[lastDate]?.saldo_final ?? "0" : "0";
  return <>
    {data.cantidad_sin_tasa > 0 && <Alert status="warning" borderRadius="0"><AlertIcon /><AlertDescription>{data.cantidad_sin_tasa} movimiento(s) no se convirtieron por falta de tasa de cambio.</AlertDescription></Alert>}
    <Box className="table-wrap matrix-wrap"><Table size="sm" variant="simple" className="matrix-table"><Thead><Tr>
      <Th minW="280px" className="matrix-label-cell">Actividad / Concepto / Tipo</Th>
      {data.fechas.map((date) => <Th key={date} isNumeric whiteSpace="nowrap">{date.slice(8, 10)}</Th>)}
      <Th isNumeric className="matrix-total-cell">Total</Th>
    </Tr></Thead><Tbody>
      {data.actividades.map((activity) => {
       const activityKey = `a-${activity.id ?? activity.nombre}`;
       const isActivityOpen = openActivities.includes(activityKey);
       const grossOperating = activity.conceptos.filter((concept) => concept.incluye_flujo_bruto_operativo);
       const netOperating = activity.conceptos.filter((concept) => concept.incluye_flujo_neto_operativo);
       const grossSubtotal = operatingSubtotal(grossOperating);
       const netSubtotal = operatingSubtotal(netOperating);
       const grossLastConceptId = grossOperating.at(-1)?.id;
       const netLastConceptId = netOperating.at(-1)?.id;
       return <Fragment key={activityKey}><Tr className="matrix-activity-row"><Td className="matrix-label-cell" bg={LEVEL_STYLES.activity.bg}><Button size="xs" mr="2" variant="ghost" onClick={() => toggle(setOpenActivities, activityKey)}>{isActivityOpen ? "−" : "+"}</Button>{activity.nombre}</Td>{cells(activity.valores_por_fecha, activity.total, { activity: activity.id }, "activity")}</Tr>
        {isActivityOpen && activity.conceptos.map((concept) => {
          const conceptKey = `${activityKey}-c-${concept.id ?? concept.nombre}`;
          const isConceptOpen = openConcepts.includes(conceptKey);
          return <Fragment key={conceptKey}>
            <Tr className="matrix-concept-row"><Td pl="9" className="matrix-label-cell" bg={LEVEL_STYLES.concept.bg}><Button size="xs" mr="2" variant="ghost" onClick={() => toggle(setOpenConcepts, conceptKey)}>{isConceptOpen ? "−" : "+"}</Button>{concept.nombre}</Td>{cells(concept.valores_por_fecha, concept.total, { activity: activity.id, concept: concept.id }, "concept")}</Tr>
            {isConceptOpen && concept.tipos.map((type) => <Tr key={`${conceptKey}-t-${type.id ?? type.nombre}`} className="matrix-type-row"><Td pl="16" className="matrix-label-cell" fontSize="xs" color="gray.600" bg={LEVEL_STYLES.type.bg}>{type.nombre}</Td>{cells(type.valores_por_fecha, type.total, { activity: activity.id, concept: concept.id, type: type.id }, "type")}</Tr>)}
            {concept.id === grossLastConceptId && <Tr className="matrix-gross-operating-row"><Td pl="9" className="matrix-label-cell">FLUJO BRUTO OPERATIVO</Td>{cells(grossSubtotal.values, grossSubtotal.total, {}, "activity", false, "white", "gray.700")}</Tr>}
            {concept.id === netLastConceptId && <Tr className="matrix-net-operating-row"><Td pl="9" className="matrix-label-cell">FLUJO NETO OPERATIVO</Td>{cells(netSubtotal.values, netSubtotal.total, {}, "activity", false, "white", "gray.700")}</Tr>}
          </Fragment>;
        })}
      </Fragment>;
    })}<Tr className="matrix-initial-balance-row"><Td className="matrix-label-cell">Saldo inicial</Td>{balanceCells("saldo_inicial", initialTotal)}</Tr><Tr className="matrix-daily-movements-row"><Td className="matrix-label-cell">Movimientos diarios</Td>{cells(data.movimientos_diarios_por_fecha, movementsTotal, {}, "activity", false)}</Tr><Tr className="matrix-final-balance-row"><Td className="matrix-label-cell" fontWeight="bold">Saldo final</Td>{balanceCells("saldo_final", finalTotal)}</Tr></Tbody></Table></Box>
  </>;
}
