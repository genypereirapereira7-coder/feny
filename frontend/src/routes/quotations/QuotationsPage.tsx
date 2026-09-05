import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Button,
  Card,
  ConfirmDialog,
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
  Textarea,
  Th,
  Td,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import { useLookup } from "../../lib/useLookup"
import type { Customer, PaginatedResponse, ProjectType, Quotation } from "../../lib/types"

const MENSAGEM_SUCESSO: Record<string, string> = {
  submit: "Orçamento enviado para aprovação.",
  approve: "Orçamento aprovado.",
  reject: "Orçamento rejeitado.",
  cancel: "Orçamento cancelado.",
}

const ROTULO_SERVICO: Record<ProjectType, string> = {
  SYSTEM: "Sistema",
  AUTOMATION: "Automação",
  WEBSITE: "Site",
  PWA: "PWA",
  APP: "Aplicativo",
  SAAS: "SaaS",
  OTHER: "Outro",
}

const TODOS_STATUS = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "CANCELLED"] as const

export function QuotationsPage() {
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [modalAberto, setModalAberto] = useState(false)
  const [motivoRejeicao, setMotivoRejeicao] = useState<{ id: string } | null>(null)
  const [aprovarConfirm, setAprovarConfirm] = useState<Quotation | null>(null)
  const [filtroStatus, setFiltroStatus] = useState("")
  const [filtroCliente, setFiltroCliente] = useState("")

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quotations", filtroStatus, filtroCliente],
    queryFn: async () =>
      (
        await api.get<PaginatedResponse<Quotation>>("/quotations/", {
          params: { status: filtroStatus || undefined, customer: filtroCliente || undefined },
        })
      ).data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)

  const acao = useMutation({
    mutationFn: ({ id, rota, body }: { id: string; rota: string; body?: object }) =>
      api.post(`/quotations/${id}/${rota}/`, body),
    onSuccess: (_dados, variaveis) => {
      queryClient.invalidateQueries({ queryKey: ["quotations"] })
      toast.success(MENSAGEM_SUCESSO[variaveis.rota] ?? "Feito.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível concluir a ação.")),
  })

  const podeCriar = user && ["ADMIN", "MANAGER", "SALES"].includes(user.role)
  const podeDecidir = user && ["ADMIN", "MANAGER"].includes(user.role)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Orçamentos"
        actions={podeCriar && <Button onClick={() => setModalAberto(true)}>Novo orçamento</Button>}
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <div className="w-44">
          <Select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
            <option value="">Todos os status</option>
            {TODOS_STATUS.map((status) => (
              <option key={status} value={status}>
                {status.replaceAll("_", " ")}
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
            <EmptyState message="Nenhum orçamento ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Cliente</Th>
                  <Th>Serviço</Th>
                  <Th>Valor</Th>
                  <Th>Status</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((orcamento) => (
                  <Tr key={orcamento.id}>
                    <Td
                      className="cursor-pointer font-medium text-slate-100"
                      onClick={() => navigate(`/orcamentos/${orcamento.id}`)}
                    >
                      {clientes?.[orcamento.customer] ?? orcamento.customer}
                    </Td>
                    <Td>{ROTULO_SERVICO[orcamento.service_type]}</Td>
                    <Td>{formatBRL(orcamento.amount)}</Td>
                    <Td>
                      <StatusBadge status={orcamento.status} />
                    </Td>
                    <Td>
                      <div className="flex gap-2">
                        {orcamento.status === "DRAFT" && (
                          <Button
                            variant="secondary"
                            disabled={acao.isPending}
                            onClick={() => acao.mutate({ id: orcamento.id, rota: "submit" })}
                          >
                            Enviar
                          </Button>
                        )}
                        {orcamento.status === "PENDING_APPROVAL" && podeDecidir && (
                          <>
                            <Button disabled={acao.isPending} onClick={() => setAprovarConfirm(orcamento)}>
                              Aprovar
                            </Button>
                            <Button
                              variant="danger"
                              disabled={acao.isPending}
                              onClick={() => setMotivoRejeicao({ id: orcamento.id })}
                            >
                              Rejeitar
                            </Button>
                          </>
                        )}
                        {(orcamento.status === "DRAFT" || orcamento.status === "PENDING_APPROVAL") && (
                          <Button
                            variant="ghost"
                            disabled={acao.isPending}
                            onClick={() => acao.mutate({ id: orcamento.id, rota: "cancel" })}
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

      {modalAberto && <NovoOrcamentoModal onClose={() => setModalAberto(false)} />}
      {motivoRejeicao && (
        <RejeitarModal
          onClose={() => setMotivoRejeicao(null)}
          onConfirm={(reason) => {
            acao.mutate({ id: motivoRejeicao.id, rota: "reject", body: { reason } })
            setMotivoRejeicao(null)
          }}
        />
      )}
      {aprovarConfirm && (
        <ConfirmDialog
          title="Aprovar este orçamento?"
          description={
            <>
              Cliente: {clientes?.[aprovarConfirm.customer] ?? aprovarConfirm.customer}
              <br />
              Valor: <strong className="text-slate-200">{formatBRL(aprovarConfirm.amount)}</strong>
            </>
          }
          confirmLabel="Aprovar"
          loading={acao.isPending}
          onClose={() => setAprovarConfirm(null)}
          onConfirm={() => {
            acao.mutate({ id: aprovarConfirm.id, rota: "approve" })
            setAprovarConfirm(null)
          }}
        />
      )}
    </div>
  )
}

function NovoOrcamentoModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const [customer, setCustomer] = useState("")
  const [serviceType, setServiceType] = useState<ProjectType>("WEBSITE")
  const [description, setDescription] = useState("")
  const [amount, setAmount] = useState("")
  const [deadlineDays, setDeadlineDays] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/quotations/", {
        customer,
        service_type: serviceType,
        description,
        amount,
        deadline_days: deadlineDays ? Number(deadlineDays) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotations"] })
      onClose()
    },
    onError: (erroRequisicao: unknown) => {
      const dados = (erroRequisicao as { response?: { data?: Record<string, string[]> } })?.response?.data
      setErro(dados ? String(Object.values(dados).flat()[0]) : "Não foi possível criar o orçamento.")
    },
  })

  return (
    <Modal title="Novo orçamento" onClose={onClose}>
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
        <Field label="Tipo de serviço">
          <Select value={serviceType} onChange={(e) => setServiceType(e.target.value as ProjectType)}>
            {Object.entries(ROTULO_SERVICO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Descrição">
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} required />
        </Field>
        <Field label="Valor (R$)">
          <Input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </Field>
        <Field label="Prazo (dias, opcional)">
          <Input type="number" min="1" value={deadlineDays} onChange={(e) => setDeadlineDays(e.target.value)} />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Criar orçamento"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function RejeitarModal({ onClose, onConfirm }: { onClose: () => void; onConfirm: (reason: string) => void }) {
  const [reason, setReason] = useState("")
  return (
    <Modal title="Rejeitar orçamento" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          onConfirm(reason)
        }}
        className="space-y-3"
      >
        <Field label="Motivo (opcional)">
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="danger">
            Rejeitar
          </Button>
        </div>
      </form>
    </Modal>
  )
}
