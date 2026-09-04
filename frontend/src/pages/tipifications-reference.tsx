import { useState } from "react";
import { Box, Button, Card, CardBody, HStack, Stack, Text } from "@chakra-ui/react";
import { Empty, ErrorBox, Loading, PageTitle, active } from "../components/common";
import { useCatalogues } from "../hooks/useCatalogues";

export function TipificationsReferencePage() {
  const catalogues = useCatalogues();
  const activities = active(catalogues.actividades.data);
  const concepts = active(catalogues.conceptos.data);
  const types = active(catalogues.tipos.data);
  const [openActivities, setOpenActivities] = useState<string[]>([]);
  const [openConcepts, setOpenConcepts] = useState<string[]>([]);
  const toggle = (set: React.Dispatch<React.SetStateAction<string[]>>, id: string) =>
    set((items) => (items.includes(id) ? items.filter((item) => item !== id) : [...items, id]));

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
      {activities.length > 0 && (
        <Card>
          <CardBody>
            {activities.map((activity) => {
              const activityConcepts = concepts.filter((concept) => concept.actividad_id === activity.id);
              const isActivityOpen = openActivities.includes(activity.id);
              return (
                <Box key={activity.id} borderBottom="1px solid" borderColor="gray.100" py="3">
                  <HStack>
                    <Button
                      size="xs"
                      variant="ghost"
                      isDisabled={activityConcepts.length === 0}
                      onClick={() => toggle(setOpenActivities, activity.id)}
                    >
                      {isActivityOpen ? "-" : "+"}
                    </Button>
                    <Text fontWeight="bold">Actividad: {activity.nombre}</Text>
                  </HStack>
                  {isActivityOpen && activityConcepts.map((concept) => {
                    const conceptTypes = types.filter((type) => type.concepto_id === concept.id);
                    const isConceptOpen = openConcepts.includes(concept.id);
                    return (
                      <Box key={concept.id} ml={{ base: 3, md: 8 }} mt="3">
                        <HStack>
                          <Button
                            size="xs"
                            variant="ghost"
                            isDisabled={conceptTypes.length === 0}
                            onClick={() => toggle(setOpenConcepts, concept.id)}
                          >
                            {isConceptOpen ? "-" : "+"}
                          </Button>
                          <Text>Concepto: {concept.nombre}</Text>
                        </HStack>
                        {isConceptOpen && conceptTypes.map((type) => (
                          <Text key={type.id} ml={{ base: 10, md: 16 }} mt="2" fontSize="sm">
                            Tipo: {type.nombre}
                          </Text>
                        ))}
                      </Box>
                    );
                  })}
                </Box>
              );
            })}
          </CardBody>
        </Card>
      )}
    </Stack>
  );
}
