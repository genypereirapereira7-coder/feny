import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { type FormEvent, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button, Card, ConfirmDialog, ErrorState, Field, Modal, Spinner, StatusBadge, Textarea } from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import { useLookup } from "../../lib/useLookup"
import type { Customer, ProjectType, Quotation, User } from "../../lib/types"

const ROTULO_SERVICO: Record<ProjectType, string> = {
  SYSTEM: "Sistema",
  AUTOMATION: "Automação",
  WEBSITE: "Site",
  PWA: "PWA",
  APP: "Aplicativo",
  SAAS: "SaaS",
  OTHER: "Outro",
}

export function QuotationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [confirmando, setConfirmando] = useState<"approve" | null>(null)
  const [rejeitando, setRejeitando] = useState(false)

  const { data: orcamento, isLoading, isError } = useQuery({
    queryKey: ["quotation", id],
    queryFn: async () => (await api.get<Quotation>(`/quotations/${id}/`)).data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const { data: usuarios } = useLookup<User>("users-lookup", "/users/", (u) => u.username)

  const acao = useMutation({
    mutationFn: ({ rota, body }: { rota: string; body?: object }) => api.post(`/quotations/${id}/${rota}/`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotation", id] })
      toast.success("Feito.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível concluir a ação.")),
  })

  const podeDecidir = user && ["ADMIN", "MANAGER"].includes(user.role)

  if (isLoading) return <Spinner />
  if (isError || !orcamento) return <ErrorState message="Não foi possível carregar este orçamento." />

  const entrada = (Number(orcamento.amount) * 0.3).toFixed(2)
  const final = (Number(orcamento.amount) * 0.7).toFixed(2)

  return (
    <div className="mx-auto max-w-2xl">
      <button
        type="button"
        onClick={() => navigate("/orcamentos")}
        className="mb-4 flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft size={14} /> Orçamentos
      </button>

      <Card className="space-y-4 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">
              {clientes?.[orcamento.customer] ?? orcamento.customer}
            </h1>
            <p className="text-sm text-slate-500">{ROTULO_SERVICO[orcamento.service_type]}</p>
          </div>
          <StatusBadge status={orcamento.status} />
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">Vendedor</dt>
            <dd className="text-slate-200">{usuarios?.[orcamento.sales_rep] ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Valor total</dt>
            <dd className="font-medium text-slate-100">{formatBRL(orcamento.amount)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Prazo</dt>
            <dd className="text-slate-200">{orcamento.deadline_days ? `${orcamento.deadline_days} dias` : "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Criado em</dt>
            <dd className="text-slate-200">{new Date(orcamento.created_at).toLocaleDateString("pt-BR")}</dd>
          </div>
          {orcamento.decided_at && (
            <>
              <div>
                <dt className="text-slate-500">Decidido por</dt>
                <dd className="text-slate-200">{orcamento.decided_by ? usuarios?.[orcamento.decided_by] : "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Decidido em</dt>
                <dd className="text-slate-200">{new Date(orcamento.decided_at).toLocaleDateString("pt-BR")}</dd>
              </div>
            </>
          )}
        </dl>

        <div>
          <p className="mb-1 text-xs text-slate-500">Descrição</p>
          <p className="text-sm text-slate-300">{orcamento.description}</p>
        </div>

        {orcamento.notes && (
          <div>
            <p className="mb-1 text-xs text-slate-500">Observações</p>
            <p className="text-sm text-slate-300">{orcamento.notes}</p>
          </div>
        )}

        <div className="rounded-md border border-slate-800 bg-slate-950 p-3 text-sm">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Condições de pagamento (calculadas/confirmadas pelo backend na cobrança real)
          </p>
          <div className="flex justify-between">
            <span className="text-slate-400">Entrada — 30%</span>
            <span className="text-slate-200">{formatBRL(entrada)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Final — 70%</span>
            <span className="text-slate-200">{formatBRL(final)}</span>
          </div>
        </div>

        {orcamento.status === "PENDING_APPROVAL" && podeDecidir && (
          <div className="flex justify-end gap-2 border-t border-slate-800 pt-4">
            <Button variant="danger" onClick={() => setRejeitando(true)}>
              Rejeitar
            </Button>
            <Button onClick={() => setConfirmando("approve")}>Aprovar</Button>
          </div>
        )}
      </Card>

      {confirmando === "approve" && (
        <ConfirmDialog
          title="Aprovar este orçamento?"
          description={
            <>
              Cliente: {clientes?.[orcamento.customer] ?? orcamento.customer}
              <br />
              Valor: <strong className="text-slate-200">{formatBRL(orcamento.amount)}</strong>
            </>
          }
          confirmLabel="Aprovar"
          loading={acao.isPending}
          onClose={() => setConfirmando(null)}
          onConfirm={() => {
            acao.mutate({ rota: "approve" })
            setConfirmando(null)
          }}
        />
      )}

      {rejeitando && (
        <RejeitarModal
          onClose={() => setRejeitando(false)}
          onConfirm={(reason) => {
            acao.mutate({ rota: "reject", body: { reason } })
            setRejeitando(false)
          }}
        />
      )}
    </div>
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
