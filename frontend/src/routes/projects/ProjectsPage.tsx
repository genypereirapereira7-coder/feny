import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import { useNavigate } from "react-router-dom"
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
import type { Customer, PaginatedResponse, Project, ProjectStatus, Quotation, User } from "../../lib/types"

// Qual ação de avanço faz sentido em cada status (ARCHITECTURE.md §7.2) —
// as disparadas por cobrança/pagamento (confirm-initial-payment etc.) não
// têm rota de API própria, então nem aparecem aqui.
const PROXIMA_ACAO: Partial<Record<ProjectStatus, { rota: string; label: string }>> = {
  INITIAL_PAYMENT_CONFIRMED: { rota: "start-development", label: "Iniciar desenvolvimento" },
  IN_DEVELOPMENT: { rota: "complete-development", label: "Concluir desenvolvimento" },
  AWAITING_CLIENT_ACCEPTANCE: { rota: "accept", label: "Registrar aceite do cliente" },
  FINAL_PAYMENT_CONFIRMED: { rota: "mark-delivered", label: "Marcar como entregue" },
  DELIVERED: { rota: "enter-maintenance", label: "Entrar em manutenção" },
}

const TODOS_STATUS: ProjectStatus[] = [
  "APPROVED",
  "AWAITING_INITIAL_PAYMENT",
  "INITIAL_PAYMENT_CONFIRMED",
  "IN_DEVELOPMENT",
  "AWAITING_CLIENT_ACCEPTANCE",
  "ACCEPTED",
  "AWAITING_FINAL_PAYMENT",
  "FINAL_PAYMENT_CONFIRMED",
  "DELIVERED",
  "MAINTENANCE",
]

export function ProjectsPage() {
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [modalAberto, setModalAberto] = useState(false)
  const [filtroStatus, setFiltroStatus] = useState("")

  const { data, isLoading, isError } = useQuery({
    queryKey: ["projects", filtroStatus],
    queryFn: async () =>
      (await api.get<PaginatedResponse<Project>>("/projects/", { params: { status: filtroStatus || undefined } })).data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)

  const avancar = useMutation({
    mutationFn: ({ id, rota }: { id: string; rota: string }) => api.post(`/projects/${id}/${rota}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
      toast.success("Projeto atualizado.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível avançar o projeto.")),
  })

  const podeGerar = user && ["ADMIN", "MANAGER"].includes(user.role)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Projetos"
        actions={podeGerar && <Button onClick={() => setModalAberto(true)}>Gerar de orçamento</Button>}
      />

      <div className="mb-4 w-52">
        <Select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
          <option value="">Todos os status</option>
          {TODOS_STATUS.map((status) => (
            <option key={status} value={status}>
              {status.replaceAll("_", " ")}
            </option>
          ))}
        </Select>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhum projeto ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Nome</Th>
                  <Th>Cliente</Th>
                  <Th>Valor</Th>
                  <Th>Status</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((projeto) => {
                  const proxima = PROXIMA_ACAO[projeto.status]
                  return (
                    <Tr key={projeto.id}>
                      <Td
                        className="cursor-pointer font-medium text-slate-100"
                        onClick={() => navigate(`/projetos/${projeto.id}`)}
                      >
                        {projeto.name}
                      </Td>
                      <Td>{clientes?.[projeto.customer] ?? projeto.customer}</Td>
                      <Td>{formatBRL(projeto.amount)}</Td>
                      <Td>
                        <StatusBadge status={projeto.status} />
                      </Td>
                      <Td>
                        {proxima && (
                          <Button
                            variant="secondary"
                            disabled={avancar.isPending}
                            onClick={() => avancar.mutate({ id: projeto.id, rota: proxima.rota })}
                          >
                            {proxima.label}
                          </Button>
                        )}
                      </Td>
                    </Tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {modalAberto && <GerarProjetoModal onClose={() => setModalAberto(false)} />}
    </div>
  )
}

function GerarProjetoModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data: orcamentos } = useQuery({
    queryKey: ["quotations", "approved-for-project"],
    queryFn: async () => (await api.get<PaginatedResponse<Quotation>>("/quotations/")).data,
  })
  const { data: usuarios } = useQuery({
    queryKey: ["users-for-responsible"],
    queryFn: async () => (await api.get<PaginatedResponse<User>>("/users/")).data,
  })

  const [quotation, setQuotation] = useState("")
  const [name, setName] = useState("")
  const [responsible, setResponsible] = useState("")
  const [description, setDescription] = useState("")
  const [expectedDeliveryAt, setExpectedDeliveryAt] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const orcamentosAprovados = orcamentos?.results.filter((o) => o.status === "APPROVED") ?? []
  const responsaveisValidos = usuarios?.results.filter((u) => ["ADMIN", "MANAGER", "DEVELOPER"].includes(u.role)) ?? []

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/projects/", {
        quotation,
        name,
        responsible,
        description,
        expected_delivery_at: expectedDeliveryAt || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
      onClose()
    },
    onError: (erroRequisicao: unknown) => {
      const dados = (erroRequisicao as { response?: { data?: Record<string, unknown> } })?.response?.data
      const detail = dados && typeof dados.detail === "string" ? dados.detail : undefined
      const primeiroCampo = dados ? String(Object.values(dados).flat()[0]) : undefined
      setErro(detail ?? primeiroCampo ?? "Não foi possível gerar o projeto.")
    },
  })

  return (
    <Modal title="Gerar projeto de orçamento aprovado" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Orçamento aprovado">
          <Select value={quotation} onChange={(e) => setQuotation(e.target.value)} required>
            <option value="">Selecione…</option>
            {orcamentosAprovados.map((o) => (
              <option key={o.id} value={o.id}>
                {o.description.slice(0, 60)} — {o.amount}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Nome do projeto">
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Responsável">
          <Select value={responsible} onChange={(e) => setResponsible(e.target.value)} required>
            <option value="">Selecione…</option>
            {responsaveisValidos.map((u) => (
              <option key={u.id} value={u.id}>
                {u.username}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Descrição (opcional)">
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
        </Field>
        <Field label="Previsão de entrega (opcional)">
          <Input type="date" value={expectedDeliveryAt} onChange={(e) => setExpectedDeliveryAt(e.target.value)} />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Gerando…" : "Gerar projeto"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
