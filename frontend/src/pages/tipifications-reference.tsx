import { Box, Card, CardBody, Stack, Tag, Text } from "@chakra-ui/react";
import { Empty, ErrorBox, Loading, PageTitle, active } from "../components/common";
import { useCatalogues } from "../hooks/useCatalogues";

export function TipificationsReferencePage() {
  const catalogues = useCatalogues();
  const activities = active(catalogues.actividades.data);
  const concepts = active(catalogues.conceptos.data);
  const types = active(catalogues.tipos.data);

  return (
    <Stack spacing="6">
      <PageTitle
        title="Guía de tipificaciones"
        description="Referencia visual para clasificar movimientos: Actividad > Concepto > Tipo."
      />
      {catalogues.loading && <Loading />}
      {catalogues.error && <ErrorBox error={catalogues.error} />}
      {!catalogues.loading && !catalogues.error && activities.length === 0 && (
        <Empty text="No hay tipificaciones activas." />
      )}
      {activities.map((activity) => {
        const activityConcepts = concepts.filter((concept) => concept.actividad_id === activity.id);
        return (
          <Card key={activity.id}>
            <CardBody>
              <Text fontSize="xs" fontWeight="bold" color="brand.600" letterSpacing="wide">
                ACTIVIDAD
              </Text>
              <Text fontSize="lg" fontWeight="bold" mt="1">
                {activity.nombre}
              </Text>
              {activityConcepts.length === 0 ? (
                <Text color="gray.500" fontSize="sm" mt="3">
                  Sin conceptos activos.
                </Text>
              ) : (
                <Stack mt="4" spacing="4">
                  {activityConcepts.map((concept) => {
                    const conceptTypes = types.filter((type) => type.concepto_id === concept.id);
                    return (
                      <Box key={concept.id} borderLeftWidth="3px" borderColor="teal.200" pl="4">
                        <Text fontSize="xs" fontWeight="bold" color="gray.500" letterSpacing="wide">
                          CONCEPTO
                        </Text>
                        <Text fontWeight="semibold">{concept.nombre}</Text>
                        <Box mt="2">
                          <Text fontSize="xs" fontWeight="bold" color="gray.500" letterSpacing="wide">
                            TIPOS
                          </Text>
                          {conceptTypes.length ? (
                            <Stack direction="row" flexWrap="wrap" mt="1">
                              {conceptTypes.map((type) => <Tag key={type.id}>{type.nombre}</Tag>)}
                            </Stack>
                          ) : (
                            <Text color="gray.500" fontSize="sm">Sin tipos activos.</Text>
                          )}
                        </Box>
                      </Box>
                    );
                  })}
                </Stack>
              )}
            </CardBody>
          </Card>
        );
      })}
    </Stack>
  );
}
