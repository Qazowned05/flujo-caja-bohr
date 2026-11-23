import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Button,
  Card,
  CardBody,
  HStack,
  Input,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
} from "@chakra-ui/react";
import { api } from "../client/api";
import {
  DataTable,
  ErrorBox,
  Field,
  Loading,
  Metric,
  PageTitle,
  TablePagination,
} from "../components/common";
import { money } from "../lib/format";

const monthNames = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
const currentDate = new Date();
const pad = (value: number) => String(value).padStart(2, "0");
const periodDates = (year: number, month: number) => ({
  from: `${year}-${pad(month)}-01`,
  to: `${year}-${pad(month)}-${pad(new Date(year, month, 0).getDate())}`,
});
const resultColor = (value: number | string) =>
  Number(value) < 0 ? "red.600" : Number(value) > 0 ? "green.600" : "gray.500";
const percentage = (value: number, total: number) =>
  total ? `${((value / total) * 100).toFixed(1)}%` : "-";
type ProfitabilityKey = "margen_bruto" | "utilidad_neta";
type MatrixRow = {
  id: string;
  nombre: string;
  total: number;
  porCentro: Record<string, number>;
  percentageBase?: { total: number; porCentro: Record<string, number> };
  hasChildren: boolean;
  isPrimary?: boolean;
  alwaysExpanded?: boolean;
  indent?: number;
  drillRubroId?: string;
};

export function ProfitLossPage() {
  const [year, setYear] = useState(currentDate.getFullYear());
  const [month, setMonth] = useState(currentDate.getMonth() + 1);
  const periodChanged = useRef(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedRubro, setSelectedRubro] = useState<string>();
  const [detailSearch, setDetailSearch] = useState("");
  const [detailPage, setDetailPage] = useState(1);
  const summary = useQuery({
    queryKey: ["egyp-summary", year, month],
    queryFn: () =>
      api.egypSummary(
        new URLSearchParams({
          fecha_desde: periodDates(year, month).from,
          fecha_hasta: periodDates(year, month).to,
        }),
      ),
  });
  const latestPeriod = useQuery({
    queryKey: ["egyp-latest-period"],
    queryFn: () => api.egypLatestPeriod(),
  });
  useEffect(() => {
    const period = latestPeriod.data?.periodo;
    if (!period || periodChanged.current) return;
    const [latestYear, latestMonth] = period.split("-").map(Number);
    if (latestYear && latestMonth) {
      setYear(latestYear);
      setMonth(latestMonth);
      periodChanged.current = true;
    }
  }, [latestPeriod.data?.periodo]);
  const entries = useQuery({
    queryKey: ["egyp-entries", year, month, selectedRubro],
    enabled: Boolean(selectedRubro),
    queryFn: () =>
      api.egypEntries(
        new URLSearchParams({
          fecha_desde: periodDates(year, month).from,
          fecha_hasta: periodDates(year, month).to,
        }),
      ),
  });
  const rows = summary.data?.rubros ?? [];
  const children = new Map<string, typeof rows>();
  rows.forEach((row) => {
    if (row.padre_id)
      children.set(row.padre_id, [...(children.get(row.padre_id) ?? []), row]);
  });
  const visibleRows: typeof rows = [];
  const appendVisible = (parentId?: string) => {
    rows
      .filter((row) => (row.padre_id ?? undefined) === parentId)
      .forEach((row) => {
        visibleRows.push(row);
        if (expanded.has(row.rubro_id)) appendVisible(row.rubro_id);
      });
  };
  appendVisible();
  const descendantIds = (rubroId: string): Set<string> => {
    const ids = new Set([rubroId]);
    const addChildren = (parentId: string) =>
      (children.get(parentId) ?? []).forEach((child) => {
        ids.add(child.rubro_id);
        addChildren(child.rubro_id);
      });
    addChildren(rubroId);
    return ids;
  };
  const selectedIds = selectedRubro
    ? descendantIds(selectedRubro)
    : new Set<string>();
  const allParents = [...children.keys()];
  const operatingIncome = rows.find(
    (row) => row.codigo === "INGRESOS_OPERATIVOS",
  );
  const operatingIncomeCategories = operatingIncome
    ? children.get(operatingIncome.rubro_id) ?? []
    : [];
  const merchandiseCosts = rows.find(
    (row) => row.codigo === "COSTOS_MERCADERIA",
  );
  const merchandiseCostCategories = merchandiseCosts
    ? children.get(merchandiseCosts.rubro_id) ?? []
    : [];
  const operatingExpenseCodes = [
    "GASTOS_ADMIN",
    "GASTOS_PERSONAL",
    "GASTOS_LOGISTICOS",
    "PUBLICIDAD_MARKETING",
    "GASTOS_FINANCIEROS",
    "GASTOS_VARIOS",
  ];
  const expenseParents = operatingExpenseCodes.flatMap((code) => {
    const row = rows.find((item) => item.codigo === code);
    return row ? [row] : [];
  });
  const toMatrixRow = (
    row: (typeof rows)[number],
    options: Pick<
      MatrixRow,
      "hasChildren" | "indent" | "drillRubroId" | "percentageBase"
    >,
  ): MatrixRow => ({
    id: row.rubro_id,
    nombre: row.nombre,
    total: Number(row.total),
    porCentro: Object.fromEntries(
      Object.entries(row.por_centro).map(([code, value]) => [code, Number(value)]),
    ),
    ...options,
  });
  const rowTotals = (row: (typeof rows)[number]) => ({
    total: Number(row.total),
    porCentro: Object.fromEntries(
      Object.entries(row.por_centro).map(([code, value]) => [code, Number(value)]),
    ),
  });
  const expenseTotals = {
    total: expenseParents.reduce((total, row) => total + Number(row.total), 0),
    porCentro: Object.fromEntries(
      (summary.data?.centros ?? []).map((center) => [
        center.codigo,
        expenseParents.reduce(
          (total, row) => total + Number(row.por_centro[center.codigo] ?? 0),
          0,
        ),
      ]),
    ) as Record<string, number>,
  };
  const incomeGroupId = "matrix-ingresos-operativos";
  const costGroupId = "matrix-costos-mercaderia";
  const expenseGroupId = "matrix-gastos";
  const matrixRows: MatrixRow[] = [];
  if (operatingIncome) {
    matrixRows.push({
      ...toMatrixRow(operatingIncome, {
        hasChildren: operatingIncomeCategories.length > 0,
        drillRubroId: operatingIncome.rubro_id,
      }),
      id: incomeGroupId,
      nombre: "INGRESOS OPERATIVOS",
      isPrimary: true,
    });
    if (expanded.has(incomeGroupId)) {
      matrixRows.push(
        ...operatingIncomeCategories.map((row) =>
          toMatrixRow(row, {
            hasChildren: false,
            indent: 1,
            drillRubroId: row.rubro_id,
            percentageBase: rowTotals(operatingIncome),
          }),
        ),
      );
    }
  }
  if (merchandiseCosts) {
    matrixRows.push({
      ...toMatrixRow(merchandiseCosts, {
        hasChildren: merchandiseCostCategories.length > 0,
        drillRubroId: merchandiseCosts.rubro_id,
      }),
      id: costGroupId,
      isPrimary: true,
    });
    if (expanded.has(costGroupId)) {
      matrixRows.push(
        ...merchandiseCostCategories.map((row) =>
          toMatrixRow(row, { hasChildren: false, indent: 1, drillRubroId: row.rubro_id }),
        ),
      );
    }
  }
  if (expenseParents.length) {
    matrixRows.push({
      id: expenseGroupId,
      nombre: "GASTOS OPERATIVOS",
      total: expenseTotals.total,
      porCentro: expenseTotals.porCentro,
      hasChildren: true,
      isPrimary: true,
    });
    if (expanded.has(expenseGroupId)) {
      expenseParents.forEach((parent) => {
        const categories = children.get(parent.rubro_id) ?? [];
        matrixRows.push(
          toMatrixRow(parent, {
            hasChildren: categories.length > 0,
            indent: 1,
            drillRubroId: parent.rubro_id,
            percentageBase: expenseTotals,
          }),
        );
        if (expanded.has(parent.rubro_id)) {
          matrixRows.push(
            ...categories.map((row) =>
              toMatrixRow(row, {
                hasChildren: false,
                indent: 2,
                drillRubroId: row.rubro_id,
                percentageBase: rowTotals(parent),
              }),
            ),
          );
        }
      });
    }
  }
  const matrixExpandableIds = [
    ...(operatingIncomeCategories.length ? [incomeGroupId] : []),
    ...(merchandiseCostCategories.length ? [costGroupId] : []),
    ...(expenseParents.length
      ? [
          expenseGroupId,
          ...expenseParents
            .filter((row) => (children.get(row.rubro_id) ?? []).length > 0)
            .map((row) => row.rubro_id),
        ]
      : []),
  ];
  const matchingEntries = (entries.data ?? []).filter((entry) => {
    const value = detailSearch.trim().toLowerCase();
    return (
      selectedIds.has(entry.rubro_id) &&
      (!value ||
        [entry.descripcion, entry.documento ?? ""].some((field) =>
          field.toLowerCase().includes(value),
        ))
    );
  });
  const detailPageSize = 10;
  const safeDetailPage = Math.min(
    detailPage,
    Math.max(1, Math.ceil(matchingEntries.length / detailPageSize)),
  );
  const detailEntries = matchingEntries.slice(
    (safeDetailPage - 1) * detailPageSize,
    safeDetailPage * detailPageSize,
  );
  const profitabilityByCenter = new Map(
    summary.data?.rentabilidad_por_centro.map((item) => [
      item.centro_id,
      item,
    ]) ?? [],
  );
  const operationalIncomeRow = operatingIncome;
  const grossMarginRows = rows.filter(
    (row) => row.padre_id === operationalIncomeRow?.rubro_id,
  );
  const grossMarginCard = grossMarginRows
    .reduce((total, row) => total + Number(row.total), 0)
    + Number(merchandiseCosts?.total ?? 0);
  const totalExpenses = expenseParents
    .reduce((total, row) => total + Math.min(0, Number(row.total)), 0);
  const profitabilityRows: {
    label: string;
    key: ProfitabilityKey;
    total: string;
  }[] = summary.data
    ? [
        {
          label: "MARGEN BRUTO",
          key: "margen_bruto",
          total: String(grossMarginCard),
        },
        {
          label: "UTILIDAD NETA",
          key: "utilidad_neta",
          total: summary.data.utilidad_neta,
        },
      ]
    : [];
  const openHistory = (rubroId: string, centroId?: string) => {
    const params = new URLSearchParams({
      period: `${year}-${pad(month)}`,
      rubro_id: rubroId,
    });
    if (centroId) params.set("centro_id", centroId);
    window.location.assign(
      `/administracion/ganancias-perdidas/registros?${params.toString()}`,
    );
  };
  return (
    <Stack spacing="6">
      <PageTitle
        title="Ganancias y pérdidas"
        description="Consulta el resultado del período, abre un rubro y revisa los asientos que lo componen."
      />
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
            <Field label="Año">
              <Select
                value={year}
                onChange={(event) => {
                  periodChanged.current = true;
                  setYear(Number(event.target.value));
                }}
              >
                {Array.from(
                  { length: 5 },
                  (_, index) => currentDate.getFullYear() - 2 + index,
                ).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Mes">
              <Select
                value={month}
                onChange={(event) => {
                  periodChanged.current = true;
                  setMonth(Number(event.target.value));
                }}
              >
                {monthNames.map((name, index) => (
                  <option key={name} value={index + 1}>
                    {name}
                  </option>
                ))}
              </Select>
            </Field>
            <Box pt={{ base: 0, md: 8 }}>
              <Text fontSize="sm" color="gray.500">
                Haz clic en un rubro para ver su sustento.
              </Text>
            </Box>
          </SimpleGrid>
        </CardBody>
      </Card>
      {summary.isLoading && <Loading />}
      {summary.isError && <ErrorBox error={summary.error} />}
      {summary.data && (
        <>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
            <Card>
              <CardBody>
                <Metric
                  label="Margen bruto"
                  value={money(grossMarginCard, "PEN")}
                  color={resultColor(grossMarginCard)}
                />
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <Metric
                  label="Utilidad neta"
                  value={money(summary.data.utilidad_neta, "PEN")}
                  color={resultColor(summary.data.utilidad_neta)}
                />
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <Metric
                  label="Total de gastos"
                  value={money(totalExpenses, "PEN")}
                  color={resultColor(totalExpenses)}
                />
              </CardBody>
            </Card>
          </SimpleGrid>
          <HStack justify="space-between" flexWrap="wrap">
            <Text fontSize="sm" color="gray.500">
              Los importes positivos aumentan el resultado; los negativos lo
              reducen.
            </Text>
            <HStack>
              <Button
                size="sm"
                onClick={() => setExpanded(new Set(matrixExpandableIds))}
              >
                Expandir todo
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setExpanded(new Set())}
              >
                Contraer todo
              </Button>
            </HStack>
          </HStack>
          <Card>
            <CardBody p="0">
              <Box className="table-wrap matrix-wrap">
                <Table size="sm" variant="simple" className="matrix-table">
                  <Thead>
                    <Tr>
                      <Th minW="300px" className="matrix-label-cell">
                        Rubro de resultado
                      </Th>
                      {summary.data.centros.map((center) => (
                        <Th key={center.id} isNumeric whiteSpace="nowrap">
                          {center.nombre}
                        </Th>
                      ))}
                      <Th isNumeric className="matrix-total-cell">
                        Total
                      </Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {matrixRows.map((rubro) => {
                      const rowClass = rubro.isPrimary
                        ? "matrix-group-row"
                        : rubro.hasChildren
                          ? "matrix-expense-parent-row"
                          : "matrix-concept-row";
                      return (
                        <Tr key={rubro.id} className={rowClass}>
                          <Td className="matrix-label-cell">
                            <HStack pl={rubro.indent ? rubro.indent * 8 : 0}>
                              <Button
                                size="xs"
                                variant="ghost"
                                visibility={
                                  rubro.hasChildren && !rubro.alwaysExpanded
                                    ? "visible"
                                    : "hidden"
                                }
                                onClick={() =>
                                  setExpanded((current) => {
                                    const next = new Set(current);
                                    next.has(rubro.id)
                                      ? next.delete(rubro.id)
                                      : next.add(rubro.id);
                                    return next;
                                  })
                                }
                              >
                                {rubro.alwaysExpanded || expanded.has(rubro.id)
                                  ? "−"
                                  : "+"}
                              </Button>
                              {rubro.drillRubroId || rubro.isPrimary ? (
                                <Button
                                  size="sm"
                                  variant="link"
                                  color="inherit"
                                  fontWeight={rubro.hasChildren ? "bold" : "normal"}
                                  onClick={() => {
                                    if (rubro.isPrimary) {
                                      setExpanded((current) => {
                                        const next = new Set(current);
                                        next.has(rubro.id)
                                          ? next.delete(rubro.id)
                                          : next.add(rubro.id);
                                        return next;
                                      });
                                      return;
                                    }
                                    setSelectedRubro(rubro.drillRubroId);
                                    setDetailSearch("");
                                    setDetailPage(1);
                                  }}
                                >
                                  {rubro.nombre}
                                </Button>
                              ) : (
                                <Text fontWeight="bold">{rubro.nombre}</Text>
                              )}
                            </HStack>
                          </Td>
                           {summary.data.centros.map((center) => {
                              const value = rubro.porCentro[center.codigo] ?? 0;
                             return (
                               <Td
                                 key={center.id}
                                 isNumeric
                                 whiteSpace="nowrap"
                                 fontWeight={rubro.isPrimary ? "bold" : "normal"}
                                color={
                                    rubro.isPrimary
                                      ? Number(value) < 0
                                        ? "#8B1E2D"
                                        : Number(value) > 0
                                          ? "#00695C"
                                          : "#718096"
                                      : Number(value) < 0
                                        ? "red.600"
                                        : Number(value) > 0
                                          ? "green.600"
                                          : "gray.500"
                                  }
                                  style={
                                    rubro.isPrimary && Number(value) < 0
                                      ? { color: "#8B1E2D" }
                                      : undefined
                                  }
                               >
                                   <Stack spacing="0" align="flex-end">
                                     {rubro.drillRubroId ? (
                                       <Button
                                         size="sm"
                                         variant="link"
                                         color="inherit"
                                         fontWeight={rubro.isPrimary ? "bold" : "normal"}
                                         onClick={() =>
                                           openHistory(rubro.drillRubroId!, center.id)
                                         }
                                         isDisabled={!Number(value)}
                                       >
                                         {money(value, "PEN")}
                                       </Button>
                                     ) : (
                                       <Text>{money(value, "PEN")}</Text>
                                     )}
                                     {rubro.percentageBase && (
                                       <Text fontSize="xs" color="gray.500" fontWeight="normal">
                                         {percentage(
                                           Number(value),
                                           rubro.percentageBase.porCentro[center.codigo] ?? 0,
                                         )}
                                       </Text>
                                     )}
                                   </Stack>
                               </Td>
                             );
                           })}
                          <Td
                            isNumeric
                            whiteSpace="nowrap"
                            fontWeight={rubro.isPrimary ? "bold" : "semibold"}
                            className="matrix-total-cell"
                             color={
                               rubro.isPrimary
                                 ? rubro.total < 0
                                   ? "#8B1E2D"
                                   : rubro.total > 0
                                     ? "#00695C"
                                     : "#718096"
                                 : rubro.total < 0
                                   ? "red.700"
                                   : rubro.total > 0
                                     ? "green.700"
                                     : "gray.600"
                             }
                             style={
                               rubro.isPrimary && rubro.total < 0
                                 ? { color: "#8B1E2D" }
                                 : undefined
                             }
                          >
                              <Stack spacing="0" align="flex-end">
                                {rubro.drillRubroId ? (
                                  <Button
                                    size="sm"
                                    variant="link"
                                    color="inherit"
                                    fontWeight={rubro.isPrimary ? "bold" : "semibold"}
                                    isDisabled={!rubro.total}
                                    onClick={() => openHistory(rubro.drillRubroId!)}
                                  >
                                    {money(rubro.total, "PEN")}
                                  </Button>
                                ) : (
                                  <Text>{money(rubro.total, "PEN")}</Text>
                                )}
                                {rubro.percentageBase && (
                                  <Text fontSize="xs" color="gray.500" fontWeight="normal">
                                    {percentage(rubro.total, rubro.percentageBase.total)}
                                  </Text>
                                )}
                              </Stack>
                          </Td>
                        </Tr>
                      );
                    })}
                    {profitabilityRows.map((metric) => (
                      <Tr
                        key={metric.key}
                        className={
                          metric.key === "utilidad_neta"
                            ? "matrix-net-operating-row"
                            : "matrix-gross-operating-row"
                        }
                      >
                        <Td className="matrix-label-cell" fontWeight="bold">
                          {metric.label}
                        </Td>
                        {summary.data.centros.map((center) => {
                          const value =
                            metric.key === "margen_bruto"
                              ? grossMarginRows.reduce(
                                  (total, row) =>
                                    total + Number(row.por_centro[center.codigo] ?? 0),
                                  0,
                                ) + Number(merchandiseCosts?.por_centro[center.codigo] ?? 0)
                              : profitabilityByCenter.get(center.id)?.utilidad_neta;
                          return (
                            <Td
                              key={center.id}
                              isNumeric
                              whiteSpace="nowrap"
                              color={
                                Number(value ?? 0) < 0
                                  ? "#8B1E2D"
                                  : Number(value ?? 0) > 0
                                    ? "#00695C"
                                    : "#64748B"
                              }
                            >
                              {money(value ?? 0, "PEN")}
                            </Td>
                          );
                        })}
                        <Td
                          isNumeric
                          whiteSpace="nowrap"
                          className="matrix-total-cell"
                          fontWeight="bold"
                          color={
                            Number(metric.total) < 0
                              ? "#8B1E2D"
                              : Number(metric.total) > 0
                                ? "#00695C"
                                : "#64748B"
                          }
                        >
                          {money(metric.total, "PEN")}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
               {matrixRows.length === 0 && (
                <Text p="6" color="gray.500">
                  No hay asientos para el período.
                </Text>
              )}
            </CardBody>
          </Card>
          {selectedRubro && (
            <Card>
              <CardBody>
                <Stack spacing="4">
                  <HStack justify="space-between" flexWrap="wrap">
                    <Box>
                      <Text fontWeight="semibold">Detalle del rubro</Text>
                      <Text fontSize="sm" color="gray.500">
                        Busca y revisa los asientos que sustentan el total.
                      </Text>
                    </Box>
                    <Button
                      size="sm"
                      onClick={() => setSelectedRubro(undefined)}
                    >
                      Cerrar detalle
                    </Button>
                  </HStack>
                  <Input
                    value={detailSearch}
                    onChange={(event) => {
                      setDetailSearch(event.target.value);
                      setDetailPage(1);
                    }}
                    placeholder="Buscar por descripción o documento"
                  />
                  {entries.isLoading && <Loading />}
                  {entries.isError && <ErrorBox error={entries.error} />}
                  {entries.data && (
                    <>
                      <DataTable
                        headers={[
                          "Fecha",
                          "Descripción",
                          "Documento",
                          "Centro",
                          "Debe",
                          "Haber",
                        ]}
                        empty="No hay asientos que coincidan."
                      >
                        {detailEntries.map((entry) => (
                          <Tr key={entry.id}>
                            <Td>{entry.fecha}</Td>
                            <Td>{entry.descripcion}</Td>
                            <Td>{entry.documento ?? "-"}</Td>
                            <Td>
                              {summary.data.centros.find(
                                (center) =>
                                  center.id === entry.centro_resultado_id,
                              )?.nombre ?? "Sin centro"}
                            </Td>
                            <Td isNumeric>{money(entry.debe, entry.moneda)}</Td>
                            <Td isNumeric>
                              {money(entry.haber, entry.moneda)}
                            </Td>
                          </Tr>
                        ))}
                      </DataTable>
                      <TablePagination
                        total={matchingEntries.length}
                        page={safeDetailPage}
                        pageSize={detailPageSize}
                        onPageChange={setDetailPage}
                      />
                    </>
                  )}
                </Stack>
              </CardBody>
            </Card>
          )}
        </>
      )}
    </Stack>
  );
}
