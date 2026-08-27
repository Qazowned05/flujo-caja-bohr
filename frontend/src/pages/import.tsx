import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Box, Button, Card, CardBody, Heading, HStack, Input, Select, Stack, Text } from "@chakra-ui/react";
import { api, type Cuenta } from "../client/api";
import { active, confirmDelete, AccountSelect, ErrorBox, Field } from "../components/common";
import { download } from "../lib/download";
export function ImportPage() {
  const [account, setAccount] = useState("");
  const [file, setFile] = useState<File>();
  const [type, setType] = useState<"REAL" | "PROYECCION">("REAL");
  const result = useMutation({
    mutationFn: () =>
      file
        ? api.importCsv(account, file, type)
        : Promise.reject(new Error("Selecciona un archivo CSV.")),
  });
  return (
    <Stack spacing="6">
      <Box>
        <Heading size="lg">Importar movimientos</Heading>
          <Text color="gray.500">
           Carga un CSV y selecciona la cuenta bancaria destino. Las proyecciones
            requieren actividad, concepto y tipo en cada fila. Para un movimiento múltiple,
            separa los números de operación con comas en la misma celda.
        </Text>
      </Box>
      <Card maxW="720px">
        <CardBody>
          <Stack spacing="5">
            <Field label="Cuenta bancaria" required>
              <AccountSelect value={account} onChange={setAccount} />
            </Field>
            <Field label="Tipo de importación" required>
              <Select value={type} onChange={(event) => setType(event.target.value as "REAL" | "PROYECCION")}> 
                <option value="REAL">Movimientos reales</option>
                <option value="PROYECCION">Proyecciones</option>
              </Select>
            </Field>
            <Field label="Archivo CSV" required>
              <Input
                type="file"
                accept=".csv,text/csv"
                p="1"
                onChange={(event) => setFile(event.target.files?.[0])}
              />
            </Field>
            <HStack>
              <Button
                colorScheme="brand"
                isLoading={result.isPending}
                isDisabled={!account || !file}
                onClick={() => result.mutate()}
              >
                Procesar importación
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  void api
                    .download(`/api/v1/imports/plantilla.csv?tipo_importacion=${type}`)
                    .then((blob) => download(blob, type === "PROYECCION" ? "plantilla_proyecciones.csv" : "plantilla_importacion.csv"))
                }
              >
                Descargar plantilla
              </Button>
            </HStack>
            {result.isError && <ErrorBox error={result.error} />}
            {result.data && <ImportSummary result={result.data} />}
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
}
function ImportSummary({
  result,
}: {
  result: Awaited<ReturnType<typeof api.importCsv>>;
}) {
  return (
    <Box bg="green.50" borderRadius="md" p="4">
      <Text fontWeight="bold">Resultado de importación</Text>
      <Text mt="2">
        {result.filas_nuevas} nuevas · {result.filas_duplicadas} duplicadas ·{" "}
        {result.filas_error} con error
      </Text>
      {result.errores.map((error) => (
        <Text
          key={`${error.fila}-${error.mensaje}`}
          color="red.600"
          fontSize="sm"
        >
          Fila {error.fila}: {error.mensaje}
        </Text>
      ))}
    </Box>
  );
}





