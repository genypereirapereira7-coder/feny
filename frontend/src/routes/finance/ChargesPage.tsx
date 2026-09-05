import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChargeIssuedModal } from "../../components/ChargeIssuedModal"
import { ConfirmPaymentModal } from "../../components/ConfirmPaymentModal"
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
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
import { useLookup, useLookupObjects } from "../../lib/useLookup"
import type { Charge, ChargeStatus, Customer, PaginatedResponse, Project } from "../../lib/types"

const ROTULO_TIPO: Record<string, string> = {
  INITIAL: "Sinal (30%)",
  FINAL: "Saldo (70%)",
  RECURRING: "Recorrente",
  SCOPE_CHANGE: "Alteração de escopo",
}

const TODOS_STATUS: ChargeStatus[] = ["PENDING", "PROCESSING", "PAID", "OVERDUE", "CANCELLED", "FAILED"]

export function ChargesPage() {
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [modalGerar, setModalGerar] = useState(false)
  const [modalConfirmar, setModalConfirmar] = useState<Charge | null>(null)
  const [cobrancaEmitida, setCobrancaEmitida] = useState<Charge | null>(null)
  const [filtroStatus, setFiltroStatus] = useState("")
  const [filtroCliente, setFiltroCliente] = useState("")

  // ChargePermission no backend: só ADMIN/FINANCE agem — MANAGER só vê (§9).
  const podeGerenciar = user && ["ADMIN", "FINANCE"].includes(user.role)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["charges", filtroStatus, filtroCliente],
    queryFn: async () =>
      (
        await api.get<PaginatedResponse<Charge>>("/finance/charges/", {
          params: { status: filtroStatus || undefined, customer: filtroCliente || undefined },
        })
      ).data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const { data: clientesCompletos } = useLookupObjects<Customer>("customers", "/customers/")

  const cancelar = useMutation({
    mutationFn: (id: string) => api.post(`/finance/charges/${id}/cancel/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["charges"] })
      toast.success("Cobrança cancelada.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível cancelar a cobrança.")),
  })
  const emitir = useMutation({
    mutationFn: (id: string) => api.post<Charge>(`/finance/charges/${id}/issue/`),
    onSuccess: (resposta) => {
      queryClient.invalidateQueries({ queryKey: ["charges"] })
      setCobrancaEmitida(resposta.data)
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível criar a cobrança neste momento.")),
  })

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Contas a receber"
        actions={podeGerenciar && <Button onClick={() => setModalGerar(true)}>Gerar cobrança</Button>}
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <div className="w-44">
          <Select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
            <option value="">Todos os status</option>
            {TODOS_STATUS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-56">
          <Select value={filtroCliente} onChange={(e) => setFiltroCliente(e.target.value)}>
            <option value="">Todos os clientes</option>
            {clientes &&
              Object.entries(clientes).map(([id, nome]) => (
                <option key={id} value={id}>
                  {nome}
                </option>
              ))}
          </Select>
        </div>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhuma cobrança ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Cliente</Th>
                  <Th>Tipo</Th>
                  <Th>Valor</Th>
                  <Th>Vencimento</Th>
                  <Th>Status</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((cobranca) => (
                  <Tr key={cobranca.id}>
                    <Td
                      className="cursor-pointer font-medium text-slate-100"
                      onClick={() => navigate(`/financeiro/cobrancas/${cobranca.id}`)}
                    >
                      {clientes?.[cobranca.customer] ?? cobranca.customer}
                    </Td>
                    <Td>{ROTULO_TIPO[cobranca.charge_type]}</Td>
                    <Td>{formatBRL(cobranca.amount)}</Td>
                    <Td>{cobranca.due_date}</Td>
                    <Td>
                      <StatusBadge status={cobranca.status} />
                    </Td>
                    <Td>
                      {podeGerenciar && cobranca.status === "PENDING" && (
                        <div className="flex flex-wrap gap-2">
                          {!cobranca.external_id && (
                            <Button variant="secondary" disabled={emitir.isPending} onClick={() => emitir.mutate(cobranca.id)}>
                              Emitir no Mercado Pago
                            </Button>
                          )}
                          <Button onClick={() => setModalConfirmar(cobranca)}>Confirmar pagamento</Button>
                          <Button variant="ghost" disabled={cancelar.isPending} onClick={() => cancelar.mutate(cobranca.id)}>
                            Cancelar
                          </Button>
                        </div>
                      )}
                      {cobranca.payment_link && (
                        <a
                          href={cobranca.payment_link}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 block text-xs text-indigo-400 hover:underline"
                        >
                          Link de pagamento
                        </a>
                      )}
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {modalGerar && <GerarCobrancaModal onClose={() => setModalGerar(false)} />}
      {modalConfirmar && (
        <ConfirmPaymentModal chargeId={modalConfirmar.id} amount={modalConfirmar.amount} onClose={() => setModalConfirmar(null)} />
      )}
      {cobrancaEmitida && (
        <ChargeIssuedModal
          charge={cobrancaEmitida}
          customerName={clientes?.[cobrancaEmitida.customer] ?? ""}
          customerPhone={clientesCompletos?.[cobrancaEmitida.customer]?.phone ?? ""}
          onClose={() => setCobrancaEmitida(null)}
        />
      )}
    </div>
  )
}

function GerarCobrancaModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data: projetos } = useQuery({
    queryKey: ["projects", "for-charge"],
    queryFn: async () => (await api.get<PaginatedResponse<Project>>("/projects/")).data,
  })
  const [project, setProject] = useState("")
  const [tipo, setTipo] = useState<"create-initial" | "create-final">("create-initial")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => api.post(`/finance/charges/${tipo}/`, { project }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["charges"] })
      onClose()
    },
    onError: (erroRequisicao: unknown) => {
      const dados = (erroRequisicao as { response?: { data?: Record<string, unknown> } })?.response?.data
      const detail = dados && "detail" in dados ? String(dados.detail) : undefined
      setErro(detail ?? "Não foi possível gerar a cobrança — confira se o projeto está na etapa certa.")
    },
  })

  return (
    <Modal title="Gerar cobrança" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value as typeof tipo)}>
            <option value="create-initial">Sinal (30%) — projeto recém aprovado</option>
            <option value="create-final">Saldo (70%) — projeto aceito pelo cliente</option>
          </Select>
        </Field>
        <Field label="Projeto">
          <Select value={project} onChange={(e) => setProject(e.target.value)} required>
            <option value="">Selecione…</option>
            {projetos?.results.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Gerando…" : "Gerar cobrança"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
