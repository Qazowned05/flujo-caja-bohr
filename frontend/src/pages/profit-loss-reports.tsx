import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Button, Card, CardBody, Select, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api } from "../client/api";
import { ErrorBox, Field, PageTitle } from "../components/common";
import { download } from "../lib/download";

const today = new Date();
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
const monthEnd = (period: string) => {
  const [year, month] = period.split("-").map(Number);
  return `${year}-${String(month).padStart(2, "0")}-${new Date(year, month, 0).getDate()}`;
};

export function ProfitLossReportsPage() {
  const [period, setPeriod] = useState(currentMonth);
  const [rubroId, setRubroId] = useState("");
  const [centerId, setCenterId] = useState("");
  const [origin, setOrigin] = useState("");
  const centers = useQuery({ queryKey: ["egyp-centros"], queryFn: () => api.egypCentros() });
  const rubros = useQuery({ queryKey: ["egyp-rubros"], queryFn: () => api.egypRubros() });
  const exportReport = () => {
    const params = new URLSearchParams({ fecha_desde: `${period}-01`, fecha_hasta: monthEnd(period) });
    if (rubroId) params.set("rubro_id", rubroId);
    if (centerId) params.set("centro_id", centerId);
    if (origin) params.set("origen", origin);
    void api.download(`/api/v1/ganancias-perdidas/reporte.xlsx?${params}`).then((blob) => download(blob, `reporte_egyp_${period}.xlsx`));
  };
  return <Stack spacing="6">
    <PageTitle title="Reportes EGyP" description="Exporta el detalle de asientos por período, rubro, línea de negocio y origen." />
    {(centers.isError || rubros.isError) && <ErrorBox error={centers.error ?? rubros.error} />}
    <Card><CardBody><Stack spacing="5"><SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing="4"><Field label="Mes"><Select value={period} onChange={(event) => setPeriod(event.target.value)}>{Array.from({ length: 24 }, (_, index) => { const date = new Date(today.getFullYear(), today.getMonth() - index, 1); const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`; return <option key={value} value={value}>{value}</option>; })}</Select></Field><Field label="Rubro"><Select value={rubroId} onChange={(event) => setRubroId(event.target.value)}><option value="">Todos los rubros</option>{rubros.data?.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.codigo} - {item.nombre}</option>)}</Select></Field><Field label="Línea de negocio"><Select value={centerId} onChange={(event) => setCenterId(event.target.value)}><option value="">Todas las líneas</option>{centers.data?.map((item) => <option key={item.id} value={item.id}>{item.codigo} - {item.nombre}</option>)}</Select></Field><Field label="Origen"><Select value={origin} onChange={(event) => setOrigin(event.target.value)}><option value="">Todos los orígenes</option><option value="MANUAL">Manual</option><option value="IMPORTADO">Importado</option><option value="DISTRIBUIDO">Distribuido</option></Select></Field></SimpleGrid><Box><Text fontSize="sm" color="gray.500">El Excel incluye fecha, período, rubro, naturaleza, línea de negocio, debe, haber, resultado neto, origen, lote, fila y observaciones.</Text><Button mt="4" colorScheme="brand" onClick={exportReport}>Descargar reporte detallado</Button></Box></Stack></CardBody></Card>
  </Stack>;
}
