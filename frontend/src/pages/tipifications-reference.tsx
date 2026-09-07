import { useState } from "react";
import { Box, Button, Card, CardBody, HStack, Input, Stack, Text } from "@chakra-ui/react";
import { Empty, ErrorBox, Field, Loading, PageTitle, active } from "../components/common";
import { useCatalogues } from "../hooks/useCatalogues";

export function TipificationsReferencePage() {
  const catalogues = useCatalogues();
  const activities = active(catalogues.actividades.data);
  const concepts = active(catalogues.conceptos.data);
  const types = active(catalogues.tipos.data);
  const branches = active(catalogues.sucursales.data);
  const sellers = active(catalogues.vendedores.data);
  const [openActivities, setOpenActivities] = useState<string[]>([]);
  const [openConcepts, setOpenConcepts] = useState<string[]>([]);
  const [openBranches, setOpenBranches] = useState<string[]>([]);
  const [sellerSearch, setSellerSearch] = useState("");
  const isLoading = catalogues.loading || catalogues.sucursales.isLoading || catalogues.vendedores.isLoading;
  const error = catalogues.error ?? catalogues.sucursales.error ?? catalogues.vendedores.error;
  const toggle = (set: React.Dispatch<React.SetStateAction<string[]>>, id: string) =>
    set((items) => (items.includes(id) ? items.filter((item) => item !== id) : [...items, id]));
  const visibleSellers = sellers.filter((seller) =>
    `${seller.nombre} ${seller.codigo}`.toLocaleLowerCase().includes(sellerSearch.toLocaleLowerCase()),
  );
  const branchGroups = [
    ...branches.map((branch) => ({
      id: branch.id,
      name: branch.nombre,
      code: branch.codigo,
      sellers: visibleSellers.filter((seller) => seller.sucursal_id === branch.id),
    })),
    {
      id: "without-branch",
      name: "Sin sucursal",
      code: "",
      sellers: visibleSellers.filter((seller) => !seller.sucursal_id),
    },
  ].filter((group) => group.sellers.length > 0 || (group.id !== "without-branch" && !sellerSearch));

  return (
    <Stack spacing="6">
      <PageTitle
        title="Guía de tipificaciones"
        description="Referencias visuales para clasificar movimientos y asignar sucursales o vendedores."
      />
      {isLoading && <Loading />}
      {error && <ErrorBox error={error} />}
      {!isLoading && !error && activities.length === 0 && (
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
      <Box>
        <Text fontSize="lg" fontWeight="semibold">Sucursales y vendedores</Text>
        <Text color="gray.500" fontSize="sm" mt="1">
          Referencia de los vendedores asociados a cada sucursal.
        </Text>
      </Box>
      <Field label="Buscar vendedor">
        <Input
          placeholder="Nombre o código"
          value={sellerSearch}
          onChange={(event) => setSellerSearch(event.target.value)}
        />
      </Field>
      {branchGroups.length > 0 ? (
        <Card>
          <CardBody>
            {branchGroups.map((group) => {
              const isOpen = sellerSearch ? true : openBranches.includes(group.id);
              return (
                <Box key={group.id} borderBottom="1px solid" borderColor="gray.100" py="3">
                  <HStack>
                    <Button
                      size="xs"
                      variant="ghost"
                      isDisabled={group.sellers.length === 0}
                      onClick={() => toggle(setOpenBranches, group.id)}
                    >
                      {isOpen ? "-" : "+"}
                    </Button>
                    <Text fontWeight="bold">Sucursal: {group.name}</Text>
                    {group.code && <Text color="gray.500" fontSize="sm">({group.code})</Text>}
                  </HStack>
                  {isOpen && group.sellers.map((seller) => (
                    <Text key={seller.id} ml={{ base: 10, md: 16 }} mt="2" fontSize="sm">
                      Vendedor: {seller.nombre} <Text as="span" color="gray.500">({seller.codigo})</Text>
                    </Text>
                  ))}
                </Box>
              );
            })}
          </CardBody>
        </Card>
      ) : (
        <Empty text={sellerSearch ? "No se encontraron vendedores." : "No hay vendedores activos."} />
      )}
    </Stack>
  );
}
