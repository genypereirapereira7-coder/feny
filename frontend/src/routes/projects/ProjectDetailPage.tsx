import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { PAINEL } from "../../lib/rotas"
import { DocumentsPanel } from "../../components/DocumentsPanel"
import { ProjectTimeline } from "../../components/ProjectTimeline"
import { Button, Card, EmptyState, ErrorState, Spinner, StatusBadge, Table, Td, Th, Tr } from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import { useLookup } from "../../lib/useLookup"
import type { Charge, Customer, PaginatedResponse, Project, ProjectStatus, User } from "../../lib/types"

const PROXIMA_ACAO: Partial<Record<ProjectStatus, { rota: string; label: string }>> = {
  INITIAL_PAYMENT_CONFIRMED: { rota: "start-development", label: "Iniciar desenvolvimento" },
  IN_DEVELOPMENT: { rota: "complete-development", label: "Concluir desenvolvimento" },
  AWAITING_CLIENT_ACCEPTANCE: { rota: "accept", label: "Registrar aceite do cliente" },
  FINAL_PAYMENT_CONFIRMED: { rota: "mark-delivered", label: "Marcar como entregue" },
  DELIVERED: { rota: "enter-maintenance", label: "Entrar em manutenção" },
}

type Aba = "geral" | "financeiro" | "documentos"

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [aba, setAba] = useState<Aba>("geral")

  const { data: projeto, isLoading, isError } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => (await api.get<Project>(`/projects/${id}/`)).data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const { data: usuarios } = useLookup<User>("users-lookup", "/users/", (u) => u.username)

  const avancar = useMutation({
    mutationFn: (rota: string) => api.post(`/projects/${id}/${rota}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", id] })
      toast.success("Projeto atualizado.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível avançar o projeto.")),
  })

  const vePainelFinanceiro = user && ["ADMIN", "MANAGER", "FINANCE"].includes(user.role)

  if (isLoading) return <Spinner />
  if (isError || !projeto) return <ErrorState message="Não foi possível carregar este projeto." />

  const proxima = PROXIMA_ACAO[projeto.status]
  const abas: { id: Aba; label: string }[] = [
    { id: "geral", label: "Visão geral" },
    ...(vePainelFinanceiro ? ([{ id: "financeiro", label: "Financeiro" }] as const) : []),
    { id: "documentos", label: "Documentos" },
  ]

  return (
    <div className="mx-auto max-w-5xl">
      <button
        type="button"
        onClick={() => navigate(`${PAINEL}/projetos`)}
        className="mb-4 flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft size={14} /> Projetos
      </button>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">{projeto.name}</h1>
          <p className="mt-1 text-sm text-slate-500">{clientes?.[projeto.customer] ?? projeto.customer}</p>
        </div>
        <div className="text-right">
          <StatusBadge status={projeto.status} />
          <p className="mt-1 text-sm font-medium text-slate-200">{formatBRL(projeto.amount)}</p>
        </div>
      </div>

      <div className="mb-6 flex gap-1 border-b border-slate-800">
        {abas.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setAba(item.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${
              aba === item.id
                ? "border-indigo-500 text-slate-100"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {aba === "geral" && (
        <div className="grid gap-6 sm:grid-cols-[1fr_2fr]">
          <Card className="space-y-3 p-4">
            <p className="text-sm font-medium text-slate-300">Informações</p>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Responsável</dt>
                <dd className="text-slate-200">{usuarios?.[projeto.responsible] ?? "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Previsão de entrega</dt>
                <dd className="text-slate-200">
                  {projeto.expected_delivery_at
                    ? new Date(`${projeto.expected_delivery_at}T00:00:00`).toLocaleDateString("pt-BR")
                    : "—"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Entregue em</dt>
                <dd className="text-slate-200">
                  {projeto.delivered_at ? new Date(projeto.delivered_at).toLocaleDateString("pt-BR") : "—"}
                </dd>
              </div>
            </dl>
            {projeto.description && (
              <div>
                <p className="mb-1 text-xs text-slate-500">Descrição</p>
                <p className="text-sm text-slate-300">{projeto.description}</p>
              </div>
            )}
            {proxima && (
              <Button className="w-full" disabled={avancar.isPending} onClick={() => avancar.mutate(proxima.rota)}>
                {proxima.label}
              </Button>
            )}
          </Card>

          <Card className="p-4">
            <p className="mb-4 text-sm font-medium text-slate-300">Linha do tempo</p>
            <ProjectTimeline status={projeto.status} />
          </Card>
        </div>
      )}

      {aba === "financeiro" && vePainelFinanceiro && <AbaFinanceiro projectId={projeto.id} />}
      {aba === "documentos" && <DocumentsPanel projectId={projeto.id} />}
    </div>
  )
}

function AbaFinanceiro({ projectId }: { projectId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["charges", "project", projectId],
    queryFn: async () =>
      (await api.get<PaginatedResponse<Charge>>("/finance/charges/", { params: { project: projectId } })).data,
  })

  if (isLoading) return <Spinner />
  if (isError) return <ErrorState />

  return (
    <Card>
      {!data || data.results.length === 0 ? (
        <EmptyState message="Nenhuma cobrança deste projeto ainda." />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Tipo</Th>
              <Th>Valor</Th>
              <Th>Vencimento</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((cobranca) => (
              <Tr key={cobranca.id}>
                <Td>{cobranca.charge_type}</Td>
                <Td className="font-medium text-slate-100">{formatBRL(cobranca.amount)}</Td>
                <Td>{cobranca.due_date}</Td>
                <Td>
                  <StatusBadge status={cobranca.status} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  )
}
