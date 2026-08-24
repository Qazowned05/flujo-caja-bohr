import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Alert, AlertIcon, Box, Button, Card, CardBody, Heading, Input, Select, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api, type Cuenta, type Sucursal, type Vendedor } from "../client/api";
import { active, confirmDelete, AccountSelect, CatalogueSelect, ErrorBox, Field, Status } from "../components/common";
import { useCatalogues } from "../hooks/useCatalogues";
import { money, today } from "../lib/format";
export function ManualMovement() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<"real" | "projection">("real");
  const [projectionId, setProjectionId] = useState("");
  const [materialized, setMaterialized] = useState(false);
  const [form, setForm] = useState({
    fecha: today(),
    descripcion: "",
    monto: "",
    cuenta: "",
    documento: "",
    observaciones: "",
    operacion: "",
    sucursal: "",
    vendedor: "",
    actividad: "",
    concepto: "",
    tipo: "",
  });
  const catalogues = useCatalogues();
  const projections = useQuery({
    queryKey: ["pending-projections", form.cuenta],
    queryFn: () => api.transactions(new URLSearchParams({
      cuenta_bancaria_id: form.cuenta,
      origen: "PROYECCION",
      estado: "PROYECTADO",
      limit: "100",
    })),
    enabled: kind === "real" && Boolean(form.cuenta),
  });
  const mutation = useMutation({
    mutationFn: () => {
      const transactionValues = {
        fecha: form.fecha,
        descripcion: form.descripcion,
        monto: form.monto,
        actividad_id: form.actividad || null,
        concepto_id: form.concepto || null,
        tipo_id: form.tipo || null,
      };
      if (kind === "real") {
        const realValues = {
          ...transactionValues,
          n_operacion: form.operacion,
          documento: form.documento || null,
          observaciones: form.observaciones || null,
          sucursal_id: form.sucursal || null,
          vendedor_id: form.vendedor || null,
        };
        return projectionId
          ? api.materializeProjection(projectionId, realValues)
          : api.createManual({
            ...realValues,
            cuenta_bancaria_id: form.cuenta,
          });
      }
      return api.createProjection({
        ...transactionValues,
        cuenta_bancaria_id: form.cuenta,
      });
    },
    onSuccess: () => {
      setMaterialized(Boolean(projectionId));
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
      void queryClient.invalidateQueries({ queryKey: ["summary"] });
      void queryClient.invalidateQueries({
        queryKey: ["tipification-breakdown"],
      });
      setForm({
        fecha: today(),
        descripcion: "",
        monto: "",
        cuenta: "",
        documento: "",
        observaciones: "",
        operacion: "",
        sucursal: "",
        vendedor: "",
        actividad: "",
        concepto: "",
        tipo: "",
      });
      setProjectionId("");
    },
  });
  const concepts = active(catalogues.conceptos.data).filter(
    (item) => item.actividad_id === form.actividad,
  );
  const types = active(catalogues.tipos.data).filter(
    (item) => item.concepto_id === form.concepto,
  );
  return (
    <Stack spacing="6">
      <Box>
        <Heading size="lg">Nuevo movimiento manual</Heading>
        <Text color="gray.500">
          Registra una operación sin importar un extracto.
        </Text>
      </Box>
      <Card>
        <CardBody>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            <Field label="Tipo de movimiento">
              <Select
                value={kind}
                onChange={(event) =>
                  setKind(event.target.value as "real" | "projection")
                }
              >
                <option value="real">Movimiento real</option>
                <option value="projection">Proyección</option>
              </Select>
            </Field>
            <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} spacing="4">
              <Field label="Cuenta" required>
                <AccountSelect
                  value={form.cuenta}
                  onChange={(cuenta) => {
                    setProjectionId("");
                    setForm({ ...form, cuenta });
                  }}
                />
              </Field>
              <Field label="Fecha" required>
                <Input
                  type="date"
                  value={form.fecha}
                  onChange={(event) =>
                    setForm({ ...form, fecha: event.target.value })
                  }
                />
              </Field>
              <Field label="Monto" required>
                <Input
                  type="number"
                  step="0.01"
                  value={form.monto}
                  onChange={(event) =>
                    setForm({ ...form, monto: event.target.value })
                  }
                />
              </Field>
              <Field label="Descripción" required>
                <Input
                  value={form.descripcion}
                  onChange={(event) =>
                    setForm({ ...form, descripcion: event.target.value })
                  }
                />
              </Field>
               {kind === "real" && (
                 <Field label="N. operación" required>
                  <Input
                    required
                    value={form.operacion}
                    onChange={(event) =>
                      setForm({ ...form, operacion: event.target.value })
                    }
                  />
                 </Field>
               )}
               {kind === "real" && (
                 <Field label="Asociar a proyección">
                   <Select
                     value={projectionId}
                     disabled={!form.cuenta || projections.isLoading}
                     onChange={(event) => {
                       const id = event.target.value;
                       setProjectionId(id);
                       const projection = projections.data?.items.find((item) => item.id === id);
                       if (projection) {
                         setForm({
                           ...form,
                           fecha: projection.fecha,
                           descripcion: projection.descripcion,
                           monto: projection.monto,
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
              {kind === "real" && <>
                <Field label="Documento">
                  <Input
                    value={form.documento}
                    onChange={(event) =>
                      setForm({ ...form, documento: event.target.value })
                    }
                  />
                </Field>
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
                    (item) =>
                      !form.sucursal || item.sucursal_id === form.sucursal,
                  )}
                />
              </>}
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
                onChange={(concepto) =>
                  setForm({ ...form, concepto, tipo: "" })
                }
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
              {kind === "real" && <Field label="Observaciones">
                <Input
                  value={form.observaciones}
                  onChange={(event) =>
                    setForm({ ...form, observaciones: event.target.value })
                  }
                />
              </Field>}
            </SimpleGrid>
            <Button
              mt="6"
              type="submit"
              colorScheme="brand"
              isLoading={mutation.isPending}
              isDisabled={
                !form.cuenta ||
                !form.fecha ||
                !form.descripcion ||
                !form.monto ||
                (kind === "real" && !form.operacion.trim()) ||
                (kind === "projection" && (!form.actividad || !form.concepto || !form.tipo))
              }
            >
              {kind === "real"
                ? "Guardar movimiento real"
                : "Guardar proyección"}
            </Button>
            {mutation.isSuccess && (
              <Alert status="success" mt="4">
                <AlertIcon />
                {kind === "real"
                  ? materialized
                    ? "Proyección confirmada como movimiento real."
                    : "Movimiento real creado correctamente."
                  : "Proyección creada correctamente."}
              </Alert>
            )}
            {mutation.isError && (
              <Box mt="4">
                <ErrorBox error={mutation.error} />
              </Box>
            )}
          </form>
        </CardBody>
      </Card>
    </Stack>
  );
}





