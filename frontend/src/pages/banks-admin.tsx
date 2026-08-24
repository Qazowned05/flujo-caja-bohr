import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Button, HStack, Input, Select, SimpleGrid, Stack, Td, Tr } from "@chakra-ui/react";
import { api, type Banco, type Cuenta } from "../client/api";
import { active, confirmDelete, Cancel, DataTable, Editor, Empty, Field, Loading, PageTitle, Status } from "../components/common";
import { money } from "../lib/format";
export function BanksPage() {
  const queryClient = useQueryClient();
  const banks = useQuery({
    queryKey: ["bancos"],
    queryFn: () => api.bancos(true),
  });
  const accounts = useQuery({
    queryKey: ["cuentas"],
    queryFn: () => api.cuentas(true),
  });
  const [bank, setBank] = useState<Banco>();
  const [account, setAccount] = useState<Cuenta>();
  const [bankForm, setBankForm] = useState({ nombre: "", codigo: "" });
  const [accountForm, setAccountForm] = useState({
    banco_id: "",
    alias: "",
    numero_cuenta: "",
    moneda: "PEN",
    saldo_inicial: "0",
  });
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["bancos"] });
    void queryClient.invalidateQueries({ queryKey: ["cuentas"] });
  };
  const bankSave = useMutation({
    mutationFn: () =>
      bank ? api.updateBanco(bank.id, bankForm) : api.createBanco(bankForm),
    onSuccess: () => {
      invalidate();
      setBank(undefined);
      setBankForm({ nombre: "", codigo: "" });
    },
  });
  const accountSave = useMutation({
    mutationFn: () =>
      account
        ? api.updateCuenta(account.id, accountForm)
        : api.createCuenta(accountForm),
    onSuccess: () => {
      invalidate();
      setAccount(undefined);
      setAccountForm({
        banco_id: "",
        alias: "",
        numero_cuenta: "",
        moneda: "PEN",
        saldo_inicial: "0",
      });
    },
  });
  const removeBank = useMutation({
    mutationFn: api.deleteBanco,
    onSuccess: invalidate,
  });
  const removeAccount = useMutation({
    mutationFn: api.deleteCuenta,
    onSuccess: invalidate,
  });
  return (
    <Stack spacing="7">
      <PageTitle
        title="Bancos y cuentas"
        description="Mantén los bancos y las cuentas disponibles para registrar e importar movimientos."
      />
      <SimpleGrid columns={{ base: 1, xl: 2 }} spacing="5">
        <Editor
          title={bank ? "Editar banco" : "Nuevo banco"}
          onSubmit={() => bankSave.mutate()}
          loading={bankSave.isPending}
          error={bankSave.error}
        >
          <SimpleGrid columns={2} spacing="3">
            <Field label="Nombre" required>
              <Input
                value={bankForm.nombre}
                onChange={(event) =>
                  setBankForm({ ...bankForm, nombre: event.target.value })
                }
              />
            </Field>
            <Field label="Código" required>
              <Input
                value={bankForm.codigo}
                onChange={(event) =>
                  setBankForm({ ...bankForm, codigo: event.target.value })
                }
              />
            </Field>
          </SimpleGrid>
          <Cancel
            editing={Boolean(bank)}
            onClick={() => {
              setBank(undefined);
              setBankForm({ nombre: "", codigo: "" });
            }}
          />
        </Editor>
        <Editor
          title={account ? "Editar cuenta" : "Nueva cuenta"}
          onSubmit={() => accountSave.mutate()}
          loading={accountSave.isPending}
          error={accountSave.error}
        >
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing="3">
            <Field label="Banco" required>
              <Select
                value={accountForm.banco_id}
                onChange={(event) =>
                  setAccountForm({
                    ...accountForm,
                    banco_id: event.target.value,
                  })
                }
                placeholder="Selecciona banco"
              >
                {active(banks.data).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Alias" required>
              <Input
                value={accountForm.alias}
                onChange={(event) =>
                  setAccountForm({ ...accountForm, alias: event.target.value })
                }
              />
            </Field>
            <Field label="Número de cuenta" required>
              <Input
                value={accountForm.numero_cuenta}
                onChange={(event) =>
                  setAccountForm({
                    ...accountForm,
                    numero_cuenta: event.target.value,
                  })
                }
              />
            </Field>
            <Field label="Moneda" required>
              <Select
                value={accountForm.moneda}
                onChange={(event) =>
                  setAccountForm({
                    ...accountForm,
                    moneda: event.target.value,
                  })
                }
              >
                <option value="PEN">PEN</option>
                <option value="USD">USD</option>
              </Select>
            </Field>
            <Field label="Saldo inicial" required>
              <Input
                type="number"
                step="any"
                value={accountForm.saldo_inicial}
                onChange={(event) =>
                  setAccountForm({ ...accountForm, saldo_inicial: event.target.value })
                }
              />
              <small>Saldo de apertura usado en el flujo de caja.</small>
            </Field>
          </SimpleGrid>
          <Cancel
            editing={Boolean(account)}
            onClick={() => {
              setAccount(undefined);
              setAccountForm({
                banco_id: "",
                alias: "",
                numero_cuenta: "",
                moneda: "PEN",
                saldo_inicial: "0",
              });
            }}
          />
        </Editor>
      </SimpleGrid>
      {banks.data && (
        <DataTable
          headers={["Banco", "Código", "Estado", ""]}
          empty="No hay bancos."
        >
          {banks.data.map((item) => (
            <Tr key={item.id}>
              <Td>{item.nombre}</Td>
              <Td>{item.codigo}</Td>
              <Td>
                <Status active={item.is_active} />
              </Td>
              <Td>
                <HStack>
                  <Button
                    size="sm"
                    onClick={() => {
                      setBank(item);
                      setBankForm({ nombre: item.nombre, codigo: item.codigo });
                    }}
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() =>
                      confirmDelete(item.nombre) && removeBank.mutate(item.id)
                    }
                  >
                    Inactivar
                  </Button>
                </HStack>
              </Td>
            </Tr>
          ))}
        </DataTable>
      )}
      {accounts.data && (
        <DataTable
          headers={["Alias", "Banco", "Número", "Moneda", "Saldo inicial", "Estado", ""]}
          empty="No hay cuentas."
        >
          {accounts.data.map((item) => (
            <Tr key={item.id}>
              <Td>{item.alias}</Td>
              <Td>
                {banks.data?.find((bankItem) => bankItem.id === item.banco_id)
                  ?.nombre ?? "-"}
              </Td>
              <Td>{item.numero_cuenta}</Td>
              <Td>{item.moneda}</Td>
              <Td isNumeric>{money(item.saldo_inicial, item.moneda)}</Td>
              <Td>
                <Status active={item.is_active} />
              </Td>
              <Td>
                <HStack>
                  <Button
                    size="sm"
                    onClick={() => {
                      setAccount(item);
                      setAccountForm({
                        banco_id: item.banco_id,
                        alias: item.alias,
                        numero_cuenta: item.numero_cuenta,
                        moneda: item.moneda,
                        saldo_inicial: item.saldo_inicial,
                      });
                    }}
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() =>
                      confirmDelete(item.alias) && removeAccount.mutate(item.id)
                    }
                  >
                    Inactivar
                  </Button>
                </HStack>
              </Td>
            </Tr>
          ))}
        </DataTable>
      )}
    </Stack>
  );
}





