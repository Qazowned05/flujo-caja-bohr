import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Alert, AlertIcon, Box, Button, Card, CardBody, Heading, HStack, Input, Select, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api, type BulkResult } from "../client/api";
import { active, confirmDelete, ErrorBox, Field, Status } from "../components/common";
import { download } from "../lib/download";
import { useCatalogues } from "../hooks/useCatalogues";
export function Reports() {
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<BulkResult>();
  const [createdById, setCreatedById] = useState("");
  const [auditAccount, setAuditAccount] = useState("");
  const [auditActivity, setAuditActivity] = useState("");
  const [auditConcept, setAuditConcept] = useState("");
  const [auditType, setAuditType] = useState("");
  const [auditFrom, setAuditFrom] = useState("");
  const [auditUntil, setAuditUntil] = useState("");
  const [auditMovementType, setAuditMovementType] = useState("TODOS");
  const [auditRecordStatus, setAuditRecordStatus] = useState("TODOS");
  const [auditTransactionStatus, setAuditTransactionStatus] = useState("");
  const user = useQuery({ queryKey: ["me"], queryFn: api.me });
  const catalogues = useCatalogues();
  const users = useQuery({
    queryKey: ["users"],
    queryFn: api.users,
    enabled: user.data?.rol === "admin",
  });
  const mutation = useMutation({
    mutationFn: (confirm: boolean) =>
      file
        ? api.bulkUpdate(file, confirm)
        : Promise.reject(new Error("Selecciona un archivo Excel.")),
    onSuccess: setPreview,
  });
  const auditConcepts = active(catalogues.conceptos.data).filter(
    (concept) => concept.actividad_id === auditActivity,
  );
  const auditTypes = active(catalogues.tipos.data).filter(
    (type) => type.concepto_id === auditConcept,
  );
  return (
    <Stack spacing="6">
      <Box>
        <Heading size="lg">Reportes y tipificación</Heading>
        <Text color="gray.500">
          Descarga pendientes o valida una actualización masiva antes de
          aplicarla.
        </Text>
      </Box>
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing="5">
        <Card>
          <CardBody>
            <Heading size="sm">Pendientes de tipificar</Heading>
            <Field label="Registrado por">
              <Select value={createdById} onChange={(event) => setCreatedById(event.target.value)}>
                <option value="">Todos los usuarios</option>
                {user.data && <option value={user.data.id}>Mis pendientes</option>}
                {user.data?.rol === "admin" && users.data?.filter((item) => item.id !== user.data?.id).map((item) => (
                  <option key={item.id} value={item.id}>{item.nombre}</option>
                ))}
              </Select>
            </Field>
            <Button
              mt="4"
              variant="outline"
              onClick={() =>
                void api
                  .download(`/api/v1/reports/no-tipificados.xlsx${createdById ? `?created_by_id=${createdById}` : ""}`)
                  .then((blob) => download(blob, "no-tipificados.xlsx"))
              }
            >
              Descargar Excel
            </Button>
            <Box mt="6" pt="5" borderTopWidth="1px">
              <Heading size="sm">Actualización masiva</Heading>
              <Text fontSize="sm" color="gray.500" mt="1">
                Valida el archivo antes de aplicar los cambios.
              </Text>
              <Input
                mt="4"
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                p="1"
                onChange={(event) => {
                  setFile(event.target.files?.[0]);
                  setPreview(undefined);
                }}
              />
              <HStack mt="4">
                <Button
                  colorScheme="brand"
                  isLoading={mutation.isPending}
                  isDisabled={!file}
                  onClick={() => mutation.mutate(false)}
                >
                  Validar archivo
                </Button>
                <Button
                  colorScheme="green"
                  isLoading={mutation.isPending}
                  isDisabled={!preview || preview.aplicado || Boolean(preview.filas_error)}
                  onClick={() => mutation.mutate(true)}
                >
                  Actualizar registros
                </Button>
              </HStack>
              {mutation.isError && (
                <Box mt="4">
                  <ErrorBox error={mutation.error} />
                </Box>
              )}
            </Box>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Heading size="sm">Auditoría de transacciones</Heading>
            <Text fontSize="sm" color="gray.500" mt="1">
              Exporta todos los campos, fuente, origen, estado y proyección.
            </Text>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing="3" mt="4">
              <Field label="Cuenta bancaria">
                <Select value={auditAccount} onChange={(event) => setAuditAccount(event.target.value)}>
                  <option value="">Todas las cuentas</option>
                  {active(catalogues.cuentas.data).map((account) => <option key={account.id} value={account.id}>{account.alias} ({account.moneda})</option>)}
                </Select>
              </Field>
              <Field label="Actividad">
                <Select value={auditActivity} onChange={(event) => {
                  setAuditActivity(event.target.value);
                  setAuditConcept("");
                  setAuditType("");
                }}>
                  <option value="">Todas las actividades</option>
                  {active(catalogues.actividades.data).map((activity) => <option key={activity.id} value={activity.id}>{activity.nombre}</option>)}
                </Select>
              </Field>
              <Field label="Concepto">
                <Select value={auditConcept} isDisabled={!auditActivity} onChange={(event) => {
                  setAuditConcept(event.target.value);
                  setAuditType("");
                }}>
                  <option value="">Todos los conceptos</option>
                  {auditConcepts.map((concept) => <option key={concept.id} value={concept.id}>{concept.nombre}</option>)}
                </Select>
              </Field>
              <Field label="Tipo">
                <Select value={auditType} isDisabled={!auditConcept} onChange={(event) => setAuditType(event.target.value)}>
                  <option value="">Todos los tipos</option>
                  {auditTypes.map((type) => <option key={type.id} value={type.id}>{type.nombre}</option>)}
                </Select>
              </Field>
              <Field label="Desde"><Input type="date" value={auditFrom} onChange={(event) => setAuditFrom(event.target.value)} /></Field>
              <Field label="Hasta"><Input type="date" value={auditUntil} onChange={(event) => setAuditUntil(event.target.value)} /></Field>
              <Field label="Clase de movimiento">
                <Select value={auditMovementType} onChange={(event) => setAuditMovementType(event.target.value)}>
                  <option value="TODOS">Todos</option>
                  <option value="PROYECCIONES">Solo proyecciones</option>
                  <option value="REALES">Solo movimientos reales</option>
                </Select>
              </Field>
              <Field label="Registro">
                <Select value={auditRecordStatus} onChange={(event) => setAuditRecordStatus(event.target.value)}>
                  <option value="TODOS">Activos y anulados</option>
                  <option value="ACTIVOS">Solo activos</option>
                  <option value="ANULADOS">Solo anulados</option>
                </Select>
              </Field>
              <Field label="Estado de transacción">
                <Select value={auditTransactionStatus} onChange={(event) => setAuditTransactionStatus(event.target.value)}>
                  <option value="">Todos los estados</option>
                  <option value="PENDIENTE_TIPIFICAR">Pendiente de tipificar</option>
                  <option value="TIPIFICADO">Tipificado</option>
                  <option value="PROYECTADO">Proyectado</option>
                  <option value="CONFIRMADO">Confirmado</option>
                </Select>
              </Field>
            </SimpleGrid>
            <HStack mt="5" justify="flex-end">
              <Button
                variant="outline"
                onClick={() => {
                const params = new URLSearchParams({
                  ...(auditAccount ? { cuenta_bancaria_id: auditAccount } : {}),
                  ...(auditActivity ? { actividad_id: auditActivity } : {}),
                  ...(auditConcept ? { concepto_id: auditConcept } : {}),
                  ...(auditType ? { tipo_id: auditType } : {}),
                  ...(auditFrom ? { fecha_desde: auditFrom } : {}),
                  ...(auditUntil ? { fecha_hasta: auditUntil } : {}),
                  tipo_movimiento: auditMovementType,
                  estado_registro: auditRecordStatus,
                  ...(auditTransactionStatus ? { estado: auditTransactionStatus } : {}),
                });
                void api.download(`/api/v1/reports/auditoria.xlsx?${params}`).then((blob) => download(blob, "auditoria_transacciones.xlsx"));
                }}
              >
                Descargar auditoría Excel
              </Button>
            </HStack>
          </CardBody>
        </Card>
      </SimpleGrid>
      {preview && <Preview result={preview} />}
    </Stack>
  );
}
function Preview({ result }: { result: BulkResult }) {
  return (
    <Card>
      <CardBody>
        <Heading size="sm">
          {result.aplicado ? "Cambios aplicados" : "Vista previa"}
        </Heading>
        <Text mt="2">
          {result.filas_validas} filas válidas · {result.filas_error} con error
        </Text>
        {result.errores.map((error) => (
          <Alert key={`${error.fila}-${error.mensaje}`} status="error" mt="2">
            <AlertIcon />
            Fila {error.fila}: {error.mensaje}
          </Alert>
        ))}
      </CardBody>
    </Card>
  );
}





