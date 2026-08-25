import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DayPicker, type DateRange } from "react-day-picker";
import "react-day-picker/style.css";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  Checkbox,
  Flex,
  Heading,
  Popover,
  PopoverBody,
  PopoverContent,
  PopoverTrigger,
  Select,
  SimpleGrid,
  Stack,
  Text,
} from "@chakra-ui/react";
import { api } from "../client/api";
import { active, ErrorBox, Field, Loading, Metric } from "../components/common";
import { TipificationMatrix } from "../components/dashboard/TipificationMatrix";
import { useCatalogues } from "../hooks/useCatalogues";
import { money } from "../lib/format";

const localIsoDate = (date: Date) => {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
};

const currentMonthStart = () => {
  const today = new Date();
  return localIsoDate(new Date(today.getFullYear(), today.getMonth(), 1));
};

const currentMonthEnd = () => {
  const today = new Date();
  return localIsoDate(new Date(today.getFullYear(), today.getMonth() + 1, 0));
};

const toDate = (value: string) => (value ? new Date(`${value}T00:00:00`) : undefined);
const toDateValue = (value: Date) =>
  `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;

function DateRangeFilter({
  from,
  until,
  onChange,
}: {
  from: string;
  until: string;
  onChange: (range: DateRange | undefined) => void;
}) {
  const selected = from ? { from: toDate(from), to: toDate(until) } : undefined;
  const label = from ? `${from}${until && until !== from ? ` a ${until}` : ""}` : "Seleccionar rango";
  return (
    <Popover placement="bottom-start">
      <PopoverTrigger>
        <Box as="button" w="full" borderWidth="1px" borderRadius="md" px="3" py="2" textAlign="left">
          {label}
        </Box>
      </PopoverTrigger>
      <PopoverContent w="auto"><PopoverBody p="2"><DayPicker mode="range" selected={selected} onSelect={onChange} /></PopoverBody></PopoverContent>
    </Popover>
  );
}

export function Dashboard() {
  const [from, setFrom] = useState(currentMonthStart);
  const [until, setUntil] = useState(currentMonthEnd);
  const [projected, setProjected] = useState(true);
  const [account, setAccount] = useState("");
  const [activity, setActivity] = useState("");
  const [currency, setCurrency] = useState("PEN");
  const accounts = useQuery({
    queryKey: ["cuentas", "active"],
    queryFn: () => api.cuentas(),
  });
  const catalogues = useCatalogues();
  const params = new URLSearchParams({
    fecha_desde: from,
    fecha_hasta: until,
    incluir_proyecciones: String(projected),
    ...(account ? { cuenta_bancaria_id: account } : {}),
    ...(activity ? { actividad_id: activity } : {}),
  });
  const summary = useQuery({
    queryKey: ["summary", from, until, projected, account, activity],
    queryFn: () => api.summary(params),
  });
  const breakdown = useQuery({
    queryKey: ["tipification-breakdown", from, until, projected, account, activity, currency],
    queryFn: () =>
      api.tipificationBreakdown(
        new URLSearchParams({
          ...Object.fromEntries(params),
          moneda_visualizacion: currency,
        }),
      ),
  });

  return (
    <Stack spacing="7">
      <Box>
        <Heading size="lg">Flujo de caja</Heading>
        <Text color="gray.500" mt="1">
          Visión consolidada de ingresos, egresos y proyecciones.
        </Text>
      </Box>
      {summary.isLoading && <Loading />}
      {summary.isError && <ErrorBox error={summary.error} />}
      {summary.data && <SimpleGrid columns={{ base: 1, xl: 2 }} spacing="5">
        {summary.data.saldos_finales.map((balance) => {
          const totals = summary.data.por_divisa.find((item) => item.moneda === balance.moneda);
          return <Card key={balance.moneda} className="metric-card"><CardBody>
            <Flex justify="space-between"><Text fontWeight="bold">{balance.moneda}</Text>{totals && <Badge colorScheme="green">{totals.cantidad_reales} reales</Badge>}</Flex>
            <SimpleGrid columns={projected ? 3 : 2} mt="6" spacing="3">
              <Metric label="Saldo real" value={money(balance.saldo_real, balance.moneda)} />
              {projected ? <Metric label="Proyectado" value={money(totals?.neto_proyectado ?? "0", balance.moneda)} color="purple.600" /> : null}
              <Metric label="Saldo final" value={money(balance.saldo_final, balance.moneda)} color="brand.600" />
            </SimpleGrid>
          </CardBody></Card>;
        })}
      </SimpleGrid>}
      <SimpleGrid columns={{ base: 1, md: 2, xl: 5 }} spacing="3" alignItems="end" bg="white" borderWidth="1px" borderRadius="md" p="3">
        <Field label="Período">
          <DateRangeFilter
            from={from}
            until={until}
            onChange={(range) => {
              setFrom(range?.from ? toDateValue(range.from) : "");
              setUntil(range?.to ? toDateValue(range.to) : "");
            }}
          />
        </Field>
        <Field label="Cuenta">
          <Select value={account} onChange={(event) => setAccount(event.target.value)}>
            <option value="">Todas las cuentas</option>
            {active(accounts.data).map((item) => <option key={item.id} value={item.id}>{item.alias} ({item.moneda})</option>)}
          </Select>
        </Field>
        <Field label="Actividad">
          <Select value={activity} onChange={(event) => setActivity(event.target.value)}>
            <option value="">Todas las actividades</option>
            {active(catalogues.actividades.data).map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </Select>
        </Field>
        <Field label="Moneda visualización">
          <Select value={currency} onChange={(event) => setCurrency(event.target.value)}>
            <option value="PEN">PEN</option><option value="USD">USD</option>
          </Select>
        </Field>
        <Checkbox colorScheme="brand" isChecked={projected} onChange={(event) => setProjected(event.target.checked)}>
          Incluir proyecciones
        </Checkbox>
      </SimpleGrid>
      <Card>
        <CardBody p="0">
          <Box p="5" borderBottom="1px solid" borderColor="gray.100">
            <Heading size="md">Matriz de tipificaciones</Heading>
            <Text color="gray.500" fontSize="sm" mt="1">Actividad / Concepto / Tipo por día en {currency}.</Text>
          </Box>
          {breakdown.isLoading && <Loading />}
          {breakdown.isError && <Box p="5"><ErrorBox error={breakdown.error} /></Box>}
          {breakdown.data && <TipificationMatrix data={breakdown.data} currency={currency} account={account} />}
        </CardBody>
      </Card>
      {!projected && <Alert status="info"><AlertIcon /><AlertDescription>Proyecciones excluidas del resumen y del desglose.</AlertDescription></Alert>}
    </Stack>
  );
}
