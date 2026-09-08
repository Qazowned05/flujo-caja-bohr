import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertDialog, AlertDialogBody, AlertDialogContent, AlertDialogFooter, AlertDialogHeader, AlertDialogOverlay, Badge, Box, Button, Card, CardBody, Flex, Heading, HStack, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, ModalOverlay, Popover, PopoverBody, PopoverContent, PopoverTrigger, Select, SimpleGrid, Spinner, Stack, Table, Tag, TagCloseButton, TagLabel, Tbody, Td, Text, Th, Thead, Tr, useDisclosure } from "@chakra-ui/react";
import { DayPicker, type DateRange } from "react-day-picker";
import "react-day-picker/style.css";
import { api, type Transaction } from "../client/api";
import { active, CatalogueSelect, Empty, ErrorBox, Field, Loading } from "../components/common";
import { useCatalogues } from "../hooks/useCatalogues";
import { money } from "../lib/format";

const statusLabel: Record<Transaction["estado"], string> = {
  PENDIENTE_TIPIFICAR: "Sin tipificar",
  TIPIFICADO: "Tipificado",
  PROYECTADO: "Proyección",
  CONFIRMADO: "Confirmado",
};

const statusColor: Record<Transaction["estado"], "red" | "green" | "yellow" | "gray"> = {
  PENDIENTE_TIPIFICAR: "red",
  TIPIFICADO: "green",
  PROYECTADO: "yellow",
  CONFIRMADO: "gray",
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
        <Button w="full" variant="outline" justifyContent="flex-start" fontWeight="normal">
          {label}
        </Button>
      </PopoverTrigger>
      <PopoverContent w="auto">
        <PopoverBody p="2">
          <DayPicker mode="range" selected={selected} onSelect={onChange} />
        </PopoverBody>
      </PopoverContent>
    </Popover>
  );
}

export function Transactions() {
  const initialFilters = new URLSearchParams(window.location.search);
  const [status, setStatus] = useState(() => initialFilters.get("estado") ?? "");
  const [account, setAccount] = useState(() => initialFilters.get("cuenta_bancaria_id") ?? "");
  const [from, setFrom] = useState(() => initialFilters.get("fecha_desde") ?? "");
  const [until, setUntil] = useState(() => initialFilters.get("fecha_hasta") ?? "");
  const [activityId, setActivityId] = useState(() => initialFilters.get("actividad_id") ?? "");
  const [conceptId, setConceptId] = useState(() => initialFilters.get("concepto_id") ?? "");
  const [typeId, setTypeId] = useState(() => initialFilters.get("tipo_id") ?? "");
  const [createdById, setCreatedById] = useState(() => initialFilters.get("created_by_id") ?? "");
  const [documentFilter, setDocumentFilter] = useState(() => initialFilters.get("con_documento") ?? "");
  const [origin, setOrigin] = useState(() => initialFilters.get("origen") ?? "");
  const [search, setSearch] = useState(() => initialFilters.get("busqueda") ?? "");
  const [offset, setOffset] = useState(0);
  const [viewing, setViewing] = useState<Transaction>();
  const [editing, setEditing] = useState<Transaction>();
  const limit = 10;
  const accounts = useQuery({
    queryKey: ["cuentas", "active"],
    queryFn: () => api.cuentas(),
  });
  const user = useQuery({ queryKey: ["me"], queryFn: api.me });
  const users = useQuery({ queryKey: ["users"], queryFn: api.users, enabled: user.data?.rol === "admin" });
  const catalogues = useCatalogues();
  const data = useQuery({
    queryKey: ["transactions", status, account, from, until, activityId, conceptId, typeId, createdById, documentFilter, origin, search, offset],
    queryFn: () =>
      api.transactions(
        new URLSearchParams({
          offset: String(offset),
          limit: String(limit),
          ...(status ? { estado: status } : {}),
          ...(account ? { cuenta_bancaria_id: account } : {}),
          ...(from ? { fecha_desde: from } : {}),
          ...(until ? { fecha_hasta: until } : {}),
          ...(activityId ? { actividad_id: activityId } : {}),
          ...(conceptId ? { concepto_id: conceptId } : {}),
          ...(typeId ? { tipo_id: typeId } : {}),
          ...(createdById ? { created_by_id: createdById } : {}),
          ...(documentFilter ? { con_documento: documentFilter } : {}),
          ...(origin ? { origen: origin } : {}),
          ...(search.trim() ? { busqueda: search.trim() } : {}),
        }),
      ),
  });
  const accountById = new Map(
    active(accounts.data).map((item) => [item.id, item]),
  );
  const activityById = new Map(active(catalogues.actividades.data).map((item) => [item.id, item.nombre]));
  const conceptById = new Map(active(catalogues.conceptos.data).map((item) => [item.id, item.nombre]));
  const typeById = new Map(active(catalogues.tipos.data).map((item) => [item.id, item.nombre]));
  const branchById = new Map(active(catalogues.sucursales.data).map((item) => [item.id, item.nombre]));
  const sellerById = new Map(active(catalogues.vendedores.data).map((item) => [item.id, item.nombre]));
  const hasBreakdownFilters = Boolean(from || until || activityId || conceptId || typeId || origin);
  const clearBreakdownFilters = () => {
    setAccount("");
    setFrom("");
    setUntil("");
    setActivityId("");
    setConceptId("");
    setTypeId("");
    setCreatedById("");
    setOrigin("");
    setSearch("");
    setOffset(0);
    window.history.replaceState({}, "", "/transacciones");
  };
  const totalPages = data.data ? Math.ceil(data.data.total / limit) : 0;
  const currentPage = Math.floor(offset / limit) + 1;
  const visiblePages = totalPages <= 7
    ? Array.from({ length: totalPages }, (_, index) => index + 1)
    : currentPage <= 5
      ? [1, 2, 3, 4, 5, null, totalPages]
      : currentPage >= totalPages - 4
        ? [1, null, totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages]
        : [1, null, currentPage - 1, currentPage, currentPage + 1, null, totalPages];
  const goToPage = (page: number) => setOffset((page - 1) * limit);
  return (
    <Stack spacing="6">
      <Box>
        <Heading size="lg">Transacciones</Heading>
        <Text color="gray.500">
          Movimientos registrados y sus estados operativos.
        </Text>
      </Box>
      <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} spacing="3" alignItems="end">
          <Field label="Estado">
            <Select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setOffset(0);
              }}
            >
              <option value="">Todos los estados</option>
              <option value="PENDIENTE_TIPIFICAR">Pendiente tipificar</option>
              <option value="TIPIFICADO">Tipificado</option>
              <option value="PROYECTADO">Proyectado</option>
            </Select>
          </Field>
           <Field label="Registrado por">
             <Select
               value={createdById}
               onChange={(event) => {
                 setCreatedById(event.target.value);
                 setOffset(0);
               }}
             >
               <option value="">Todos los usuarios</option>
               {user.data && <option value={user.data.id}>Mis transacciones</option>}
               {users.data?.filter((item) => item.id !== user.data?.id).map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
             </Select>
           </Field>
           <Field label="Cuenta bancaria">
            <Select
              value={account}
              onChange={(event) => {
                setAccount(event.target.value);
                setOffset(0);
              }}
            >
              <option value="">Todas las cuentas</option>
              {active(accounts.data).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.alias} ({item.moneda})
                </option>
              ))}
            </Select>
           </Field>
           <Field label="Buscar">
             <Input
               placeholder="N. operación o descripción"
               value={search}
               onChange={(event) => {
                 setSearch(event.target.value);
                 setOffset(0);
               }}
             />
           </Field>
           <Field label="Período">
             <DateRangeFilter
               from={from}
               until={until}
               onChange={(range) => {
                 setFrom(range?.from ? toDateValue(range.from) : "");
                 setUntil(range?.to ? toDateValue(range.to) : "");
                 setOffset(0);
               }}
             />
           </Field>
            <Field label="Documento">
              <Select
               value={documentFilter}
               onChange={(event) => {
                 setDocumentFilter(event.target.value);
                 setOffset(0);
               }}
             >
               <option value="">Con y sin documento</option>
               <option value="true">Con documento</option>
               <option value="false">Sin documento</option>
              </Select>
            </Field>
            <Field label="Origen">
              <Select
                value={origin}
                onChange={(event) => {
                  setOrigin(event.target.value);
                  setOffset(0);
                }}
              >
                <option value="">Todos los orígenes</option>
                <option value="IMPORTADO">Importado</option>
                <option value="MANUAL">Manual</option>
                <option value="MULTIPLE">Múltiple</option>
                <option value="PROYECCION">Proyección</option>
              </Select>
            </Field>
      </SimpleGrid>
      {hasBreakdownFilters && (
        <HStack flexWrap="wrap" spacing="2" bg="white" borderWidth="1px" borderRadius="md" p="3">
          <Text fontSize="sm" fontWeight="medium">Filtros del desglose</Text>
          {from && <Badge colorScheme="blue">Fecha: {from}{until && until !== from ? ` a ${until}` : ""}</Badge>}
          {activityId && <Badge>Actividad: {activityById.get(activityId) ?? activityId} ({activityId})</Badge>}
          {conceptId && <Badge>Concepto: {conceptById.get(conceptId) ?? conceptId} ({conceptId})</Badge>}
           {typeId && <Badge>Tipo: {typeById.get(typeId) ?? typeId} ({typeId})</Badge>}
           {origin && <Badge>Origen: {origin}</Badge>}
          <Button size="xs" variant="ghost" onClick={clearBreakdownFilters}>Limpiar filtros</Button>
        </HStack>
      )}
      {data.isLoading && <Loading />}
      {data.isError && <ErrorBox error={data.error} />}
      {data.data && (
        <Card>
          <CardBody p="0">
            <Box className="table-wrap">
              <Table size="sm" fontSize="xs" sx={{ "th, td": { fontSize: "xs" } }}>
                <Thead>
                  <Tr>
                    <Th>Fecha</Th>
                    <Th>Descripción</Th>
                    <Th>Operación</Th>
                    <Th>Cuenta / moneda</Th>
                    <Th>Sucursal</Th>
                    <Th>Vendedor</Th>
                    <Th>Tipificación</Th>
                    <Th isNumeric>Monto</Th>
                    <Th>Estado</Th>
                    <Th>Registrado por</Th>
                    <Th>Acciones</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {data.data.items.map((row) => (
                    <Tr key={row.id}>
                      <Td whiteSpace="nowrap">{row.fecha}</Td>
                      <Td>{row.descripcion}</Td>
                      <Td>{row.numeros_operacion.join(", ") || "-"}</Td>
                      <Td>
                        <Text fontWeight="medium" fontSize="xs">
                          {accountById.get(row.cuenta_bancaria_id)?.alias ?? "Cuenta no disponible"}
                        </Text>
                        <Text fontSize="2xs">{row.moneda}</Text>
                      </Td>
                      <Td>{row.sucursal_id ? branchById.get(row.sucursal_id) ?? "Sucursal no disponible" : "-"}</Td>
                      <Td>{row.vendedor_id ? sellerById.get(row.vendedor_id) ?? "Vendedor no disponible" : "-"}</Td>
                      <Td>
                        {row.actividad_id && row.concepto_id && row.tipo_id
                          ? `${activityById.get(row.actividad_id) ?? row.actividad_id} / ${conceptById.get(row.concepto_id) ?? row.concepto_id} / ${typeById.get(row.tipo_id) ?? row.tipo_id}`
                          : "Sin tipificar"}
                      </Td>
                      <Td
                        isNumeric
                        whiteSpace="nowrap"
                        color={Number(row.monto) < 0 ? "red.600" : "green.600"}
                      >
                        {money(row.monto, row.moneda)}
                      </Td>
                      <Td>
                        <Badge colorScheme={statusColor[row.estado]}>{statusLabel[row.estado]}</Badge>
                      </Td>
                      <Td>{row.created_by.nombre}</Td>
                      <Td>
                        <HStack spacing="1">
                          <Button size="xs" variant="ghost" onClick={() => setViewing(row)}>
                            Ver
                          </Button>
                          <Button
                            size="xs"
                            variant="outline"
                            onClick={() => setEditing(row)}
                          >
                            Editar
                          </Button>
                          {user.data?.rol === "admin" && row.is_active && (
                            <CancelTransactionButton transaction={row} />
                          )}
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
            {!data.data.items.length && (
              <Empty text="No se encontraron transacciones." />
            )}
            <Flex p="4" justify="space-between">
              <Text fontSize="sm">{data.data.total} resultados</Text>
              <HStack spacing="1">
                <Button
                  size="xs"
                  aria-label="Retroceder cinco páginas"
                  onClick={() => goToPage(Math.max(1, currentPage - 5))}
                  isDisabled={currentPage === 1}
                >
                  &lt;&lt;
                </Button>
                <Button
                  size="xs"
                  aria-label="Página anterior"
                  onClick={() => goToPage(currentPage - 1)}
                  isDisabled={currentPage === 1}
                >
                  &lt;
                </Button>
                {visiblePages.map((page, index) => page === null ? (
                  <Text key={`ellipsis-${index}`} px="1">...</Text>
                ) : (
                  <Button
                    key={page}
                    size="xs"
                    colorScheme={page === currentPage ? "brand" : undefined}
                    variant={page === currentPage ? "solid" : "ghost"}
                    onClick={() => goToPage(page)}
                  >
                    {page}
                  </Button>
                ))}
                <Button
                  size="xs"
                  aria-label="Página siguiente"
                  onClick={() => goToPage(currentPage + 1)}
                  isDisabled={currentPage >= totalPages}
                >
                  &gt;
                </Button>
                <Button
                  size="xs"
                  aria-label="Avanzar cinco páginas"
                  onClick={() => goToPage(Math.min(totalPages, currentPage + 5))}
                  isDisabled={currentPage >= totalPages}
                >
                  &gt;&gt;
                </Button>
              </HStack>
            </Flex>
          </CardBody>
        </Card>
      )}
      {viewing && <TransactionDetailModal transaction={viewing} onClose={() => setViewing(undefined)} />}
      {editing && (
        <TransactionEditModal
          transaction={editing}
          isAdmin={user.data?.rol === "admin"}
          onClose={() => setEditing(undefined)}
        />
      )}
    </Stack>
  );
}

function TransactionDetailModal({
  transaction,
  onClose,
}: {
  transaction: Transaction;
  onClose: () => void;
}) {
  const catalogues = useCatalogues();
  const accountById = new Map(active(catalogues.cuentas.data).map((item) => [item.id, `${item.alias} (${item.moneda})`]));
  const branchById = new Map(active(catalogues.sucursales.data).map((item) => [item.id, item.nombre]));
  const sellerById = new Map(active(catalogues.vendedores.data).map((item) => [item.id, item.nombre]));
  const activityById = new Map(active(catalogues.actividades.data).map((item) => [item.id, item.nombre]));
  const conceptById = new Map(active(catalogues.conceptos.data).map((item) => [item.id, item.nombre]));
  const typeById = new Map(active(catalogues.tipos.data).map((item) => [item.id, item.nombre]));
  const reference = (id: string | null, names: Map<string, string>) =>
    id ? names.get(id) ?? "No disponible" : "-";

  return (
    <Modal isOpen onClose={onClose} size="2xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Detalle de transacción</ModalHeader>
        <ModalBody>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
            <DetailField label="ID" value={transaction.id} />
            <DetailField label="Fecha" value={transaction.fecha} />
            <DetailField label="Descripción" value={transaction.descripcion} />
            <DetailField label="N. operación" value={transaction.numeros_operacion.join(", ") || "-"} />
            <DetailField label="Monto" value={money(transaction.monto, transaction.moneda)} />
            <DetailField label="Moneda" value={transaction.moneda} />
            <DetailField label="Documento" value={transaction.documento ?? "-"} />
            <DetailField label="Observaciones" value={transaction.observaciones ?? "-"} />
            <DetailField label="Sucursal" value={reference(transaction.sucursal_id, branchById)} />
            <DetailField label="Vendedor" value={reference(transaction.vendedor_id, sellerById)} />
            <DetailField label="Cuenta bancaria" value={reference(transaction.cuenta_bancaria_id, accountById)} />
            <DetailField label="Actividad" value={reference(transaction.actividad_id, activityById)} />
            <DetailField label="Concepto" value={reference(transaction.concepto_id, conceptById)} />
            <DetailField label="Tipo" value={reference(transaction.tipo_id, typeById)} />
            <DetailField label="Origen" value={transaction.origen} />
            <DetailField label="Estado" value={statusLabel[transaction.estado]} />
            <DetailField label="Creado por" value={transaction.created_by.nombre} />
            <DetailField label="Actualizado por" value={transaction.updated_by.nombre} />
            <DetailField label="Creado el" value={transaction.created_at} />
            <DetailField label="Actualizado el" value={transaction.updated_at} />
          </SimpleGrid>
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Cerrar</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return <Box><Text fontSize="xs" color="gray.500">{label}</Text><Text fontSize="sm" wordBreak="break-word">{value}</Text></Box>;
}

function CancelTransactionButton({
  transaction,
}: {
  transaction: Transaction;
}) {
  const dialog = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const queryClient = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => api.cancelTransaction(transaction.id),
    onSuccess: () => {
      ["transactions", "summary", "tipification-breakdown"].forEach(
        (key) => void queryClient.invalidateQueries({ queryKey: [key] }),
      );
      dialog.onClose();
    },
  });
  return (
    <>
      <Button
        size="xs"
        variant="ghost"
        colorScheme="red"
        onClick={dialog.onOpen}
      >
        Anular
      </Button>
      <AlertDialog
        isOpen={dialog.isOpen}
        leastDestructiveRef={cancelRef}
        onClose={dialog.onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader>Anular operación</AlertDialogHeader>
            <AlertDialogBody>
              La transacción no se borra de la base de datos: se excluye del
              flujo de caja y se mantiene para auditoría.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={dialog.onClose}>
                Cancelar
              </Button>
              <Button
                colorScheme="red"
                ml="3"
                isLoading={cancel.isPending}
                onClick={() => cancel.mutate()}
              >
                Anular operación
              </Button>
            </AlertDialogFooter>
            {cancel.isError && (
              <Box px="6" pb="4">
                <ErrorBox error={cancel.error} />
              </Box>
            )}
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
}

function TransactionEditModal({
  transaction,
  isAdmin,
  onClose,
}: {
  transaction: Transaction;
  isAdmin: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const catalogues = useCatalogues();
  const [form, setForm] = useState({
    documento: transaction.documento ?? "",
    observaciones: transaction.observaciones ?? "",
    sucursal: transaction.sucursal_id ?? "",
    vendedor: transaction.vendedor_id ?? "",
    actividad: transaction.actividad_id ?? "",
    concepto: transaction.concepto_id ?? "",
    tipo: transaction.tipo_id ?? "",
    nOperacion: transaction.n_operacion ?? "",
    monto: String(transaction.monto),
  });
  const [projectionId, setProjectionId] = useState("");
  const [operations, setOperations] = useState(transaction.numeros_operacion);
  const [operationInput, setOperationInput] = useState("");
  const projections = useQuery({
    queryKey: ["pending-projections", transaction.cuenta_bancaria_id],
    queryFn: () => api.transactions(new URLSearchParams({
      cuenta_bancaria_id: transaction.cuenta_bancaria_id,
      origen: "PROYECCION",
      estado: "PROYECTADO",
      limit: "100",
    })),
    enabled: transaction.origen !== "PROYECCION" && transaction.is_active,
  });
  const concepts = active(catalogues.conceptos.data).filter(
    (item) => item.actividad_id === form.actividad,
  );
  const types = active(catalogues.tipos.data).filter(
    (item) => item.concepto_id === form.concepto,
  );
  const save = useMutation({
    mutationFn: async () => {
      await api.updateTransaction(transaction.id, {
        documento: form.documento || null,
        observaciones: form.observaciones || null,
        sucursal_id: form.sucursal || null,
        vendedor_id: form.vendedor || null,
        actividad_id: form.actividad || null,
        concepto_id: form.concepto || null,
        tipo_id: form.tipo || null,
        ...(projectionId ? { proyeccion_id: projectionId } : {}),
        ...(isAdmin && {
          monto: form.monto,
          ...(transaction.origen !== "MULTIPLE" && transaction.origen !== "PROYECCION"
            ? { n_operacion: form.nOperacion }
            : {}),
        }),
      });
      return isAdmin && transaction.origen === "MULTIPLE"
        ? api.updateMultipleOperations(transaction.id, operations)
        : undefined;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
      void queryClient.invalidateQueries({ queryKey: ["summary"] });
      void queryClient.invalidateQueries({
        queryKey: ["tipification-breakdown"],
      });
      onClose();
    },
  });
  return (
    <Modal isOpen onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Editar transacción</ModalHeader>
        <ModalBody>
          <Text fontSize="sm" color="gray.500" mb="4">
            La fecha no se puede modificar aquí. Solo administradores pueden modificar el monto y los números de operación.
          </Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
            {isAdmin && transaction.origen === "MULTIPLE" && (
              <Field label="Números de operación" required>
                <Box borderWidth="1px" borderRadius="md" p="2">
                  <HStack spacing="2" flexWrap="wrap">
                    {operations.map((operation) => <Tag key={operation} colorScheme="brand"><TagLabel>{operation}</TagLabel><TagCloseButton onClick={() => setOperations((current) => current.filter((item) => item !== operation))} /></Tag>)}
                    <Input
                      variant="unstyled"
                      minW="140px"
                      value={operationInput}
                      placeholder="Agregar operación"
                      onChange={(event) => setOperationInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          const values = operationInput.split(/[\n,;\t]+/).map((item) => item.trim()).filter(Boolean);
                          setOperations((current) => [...current, ...values.filter((item) => !current.includes(item))]);
                          setOperationInput("");
                        }
                      }}
                    />
                  </HStack>
                </Box>
                <Text fontSize="xs" color="gray.500" mt="1">Presiona Enter para agregar. Se requieren al menos dos operaciones.</Text>
              </Field>
            )}
            {isAdmin && transaction.origen !== "MULTIPLE" && transaction.origen !== "PROYECCION" && (
              <Field label="N. operación" required>
                <Input
                  value={form.nOperacion}
                  onChange={(event) => setForm({ ...form, nOperacion: event.target.value })}
                />
              </Field>
            )}
            {isAdmin && (
              <Field label="Monto" required>
                <Input
                  type="number"
                  step="0.01"
                  value={form.monto}
                  onChange={(event) => setForm({ ...form, monto: event.target.value })}
                />
              </Field>
            )}
            <CatalogueSelect
              label="Sucursal"
              value={form.sucursal}
              onChange={(sucursal) =>
                setForm({ ...form, sucursal, vendedor: "" })
              }
              items={active(catalogues.sucursales.data)}
            />
            <CatalogueSelect
              label="Vendedor"
              value={form.vendedor}
              onChange={(vendedor) => setForm({ ...form, vendedor })}
              items={active(catalogues.vendedores.data).filter(
                (item) => !form.sucursal || item.sucursal_id === form.sucursal,
              )}
            />
            <CatalogueSelect
              label="Actividad"
              value={form.actividad}
              onChange={(actividad) =>
                setForm({ ...form, actividad, concepto: "", tipo: "" })
              }
              items={active(catalogues.actividades.data)}
            />
            <CatalogueSelect
              label="Concepto"
              value={form.concepto}
              onChange={(concepto) => setForm({ ...form, concepto, tipo: "" })}
              items={concepts}
              disabled={!form.actividad}
            />
            <CatalogueSelect
              label="Tipo"
              value={form.tipo}
              onChange={(tipo) => setForm({ ...form, tipo })}
              items={types}
              disabled={!form.concepto}
            />
            {transaction.origen !== "PROYECCION" && transaction.is_active && (
              <Field label="Proyección asociada">
                <Select
                  value={projectionId}
                  isDisabled={projections.isLoading}
                  onChange={(event) => {
                    const id = event.target.value;
                    setProjectionId(id);
                    const projection = projections.data?.items.find((item) => item.id === id);
                    if (projection) {
                      setForm({
                        ...form,
                        actividad: projection.actividad_id ?? "",
                        concepto: projection.concepto_id ?? "",
                        tipo: projection.tipo_id ?? "",
                      });
                    }
                  }}
                >
                  <option value="">No asociar una proyección</option>
                  {projections.data?.items.map((projection) => (
                    <option key={projection.id} value={projection.id}>
                      {projection.fecha} | {projection.descripcion} | {money(projection.monto, projection.moneda)}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <Field label="Documento">
              <Input
                value={form.documento}
                onChange={(event) =>
                  setForm({ ...form, documento: event.target.value })
                }
              />
            </Field>
            <Field label="Observaciones">
              <Input
                value={form.observaciones}
                onChange={(event) =>
                  setForm({ ...form, observaciones: event.target.value })
                }
              />
            </Field>
          </SimpleGrid>
          {save.isError && (
            <Box mt="4">
              <ErrorBox error={save.error} />
            </Box>
          )}
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Cancelar</Button>
          <Button
            ml="3"
            colorScheme="brand"
            isLoading={save.isPending}
            isDisabled={transaction.origen === "MULTIPLE" && operations.length < 2}
            onClick={() => save.mutate()}
          >
            Guardar cambios
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

function AccountSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const accounts = useQuery({
    queryKey: ["cuentas", "active"],
    queryFn: () => api.cuentas(),
  });
  if (accounts.isLoading) return <Spinner size="sm" />;
  if (accounts.isError) return <ErrorBox error={accounts.error} />;
  return (
    <Select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Selecciona una cuenta"
      required
    >
      {active(accounts.data).map((account) => (
        <option key={account.id} value={account.id}>
          {account.alias} ({account.moneda})
        </option>
      ))}
    </Select>
  );
}





