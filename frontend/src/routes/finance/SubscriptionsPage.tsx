import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  StatusBadge,
  Table,
  Th,
  Td,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import { useLookup } from "../../lib/useLookup"
import type { Customer, PaginatedResponse, Subscription } from "../../lib/types"

const MENSAGEM_SUCESSO: Record<string, string> = {
  pause: "Assinatura pausada.",
  resume: "Assinatura retomada.",
  cancel: "Assinatura cancelada.",
}

export function SubscriptionsPage() {
  const { user } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [modalAberto, setModalAberto] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: async () => (await api.get<PaginatedResponse<Subscription>>("/finance/subscriptions/")).data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)

  const transicao = useMutation({
    mutationFn: ({ id, rota }: { id: string; rota: string }) => api.post(`/finance/subscriptions/${id}/${rota}/`),
    onSuccess: (_dados, variaveis) => {
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] })
      toast.success(MENSAGEM_SUCESSO[variaveis.rota] ?? "Feito.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível concluir a ação.")),
  })

  // SubscriptionPermission no backend: só ADMIN/FINANCE agem — MANAGER só vê (§9).
  const podeGerenciar = user && ["ADMIN", "FINANCE"].includes(user.role)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Recorrências"
        actions={podeGerenciar && <Button onClick={() => setModalAberto(true)}>Nova assinatura</Button>}
      />

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhuma assinatura ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Cliente</Th>
                  <Th>Serviço</Th>
                  <Th>Valor/mês</Th>
                  <Th>Próxima cobrança</Th>
                  <Th>Status</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((assinatura) => (
                  <Tr key={assinatura.id}>
                    <Td className="font-medium text-slate-100">
                      {clientes?.[assinatura.customer] ?? assinatura.customer}
                    </Td>
                    <Td>{assinatura.service_description}</Td>
                    <Td>{formatBRL(assinatura.amount)}</Td>
                    <Td>{assinatura.next_billing_date}</Td>
                    <Td>
                      <StatusBadge status={assinatura.status} />
                    </Td>
                    <Td>
                      <div className="flex gap-2">
                        {podeGerenciar && assinatura.status === "ACTIVE" && (
                          <Button
                            variant="secondary"
                            disabled={transicao.isPending}
                            onClick={() => transicao.mutate({ id: assinatura.id, rota: "pause" })}
                          >
                            Pausar
                          </Button>
                        )}
                        {podeGerenciar && assinatura.status === "PAUSED" && (
                          <Button disabled={transicao.isPending} onClick={() => transicao.mutate({ id: assinatura.id, rota: "resume" })}>
                            Retomar
                          </Button>
                        )}
                        {podeGerenciar && assinatura.status !== "CANCELLED" && (
                          <Button
                            variant="ghost"
                            disabled={transicao.isPending}
                            onClick={() => transicao.mutate({ id: assinatura.id, rota: "cancel" })}
                          >
                            Cancelar
                          </Button>
                        )}
                      </div>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {modalAberto && <NovaAssinaturaModal onClose={() => setModalAberto(false)} />}
    </div>
  )
}

function NovaAssinaturaModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const [customer, setCustomer] = useState("")
  const [serviceDescription, setServiceDescription] = useState("")
  const [amount, setAmount] = useState("")
  const [startDate, setStartDate] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/finance/subscriptions/", {
        customer,
        service_description: serviceDescription,
        amount,
        start_date: startDate,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] })
      onClose()
    },
    onError: () => setErro("Não foi possível criar a assinatura."),
  })

  return (
    <Modal title="Nova assinatura" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Cliente">
          <Select value={customer} onChange={(e) => setCustomer(e.target.value)} required>
            <option value="">Selecione…</option>
            {clientes &&
              Object.entries(clientes).map(([id, nome]) => (
                <option key={id} value={id}>
                  {nome}
                </option>
              ))}
          </Select>
        </Field>
        <Field label="Descrição do serviço">
          <Input
            value={serviceDescription}
            onChange={(e) => setServiceDescription(e.target.value)}
            placeholder="Hospedagem, manutenção..."
            required
          />
        </Field>
        <Field label="Valor mensal (R$)">
          <Input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </Field>
        <Field label="Início da cobrança">
          <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Criar assinatura"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
