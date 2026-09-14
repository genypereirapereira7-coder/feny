import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { PAINEL } from "../../lib/rotas"
import { ChargeIssuedModal } from "../../components/ChargeIssuedModal"
import { ConfirmPaymentModal } from "../../components/ConfirmPaymentModal"
import { Button, Card, EmptyState, ErrorState, Spinner, StatusBadge, Table, Td, Th, Tr } from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import type { Charge, Customer, PaginatedResponse, Payment, Project } from "../../lib/types"

const ROTULO_TIPO: Record<string, string> = {
  INITIAL: "Sinal (30%)",
  FINAL: "Saldo (70%)",
  RECURRING: "Recorrente",
  SCOPE_CHANGE: "Alteração de escopo",
}

export function ChargeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [modalConfirmar, setModalConfirmar] = useState(false)
  const [cobrancaEmitida, setCobrancaEmitida] = useState<Charge | null>(null)

  const podeGerenciar = user && ["ADMIN", "FINANCE"].includes(user.role)

  const { data: cobranca, isLoading, isError } = useQuery({
    queryKey: ["charge", id],
    queryFn: async () => (await api.get<Charge>(`/finance/charges/${id}/`)).data,
  })
  const { data: cliente } = useQuery({
    queryKey: ["customer", cobranca?.customer],
    queryFn: async () => (await api.get<Customer>(`/customers/${cobranca?.customer}/`)).data,
    enabled: !!cobranca,
  })
  const { data: projeto } = useQuery({
    queryKey: ["project", cobranca?.project],
    queryFn: async () => (await api.get<Project>(`/projects/${cobranca?.project}/`)).data,
    enabled: !!cobranca?.project,
  })
  const { data: pagamentos } = useQuery({
    queryKey: ["payments", "charge", id],
    queryFn: async () =>
      (await api.get<PaginatedResponse<Payment>>("/finance/payments/", { params: { charge: id } })).data,
    enabled: !!cobranca,
  })

  const cancelar = useMutation({
    mutationFn: () => api.post(`/finance/charges/${id}/cancel/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["charge", id] })
      toast.success("Cobrança cancelada.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível cancelar a cobrança.")),
  })
  const emitir = useMutation({
    mutationFn: () => api.post<Charge>(`/finance/charges/${id}/issue/`),
    onSuccess: (resposta) => {
      queryClient.invalidateQueries({ queryKey: ["charge", id] })
      setCobrancaEmitida(resposta.data)
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível criar a cobrança neste momento.")),
  })

  if (isLoading) return <Spinner />
  if (isError || !cobranca) return <ErrorState message="Não foi possível carregar esta cobrança." />

  return (
    <div className="mx-auto max-w-3xl">
      <button
        type="button"
        onClick={() => navigate(`${PAINEL}/financeiro/cobrancas`)}
        className="mb-4 flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft size={14} /> Contas a receber
      </button>

      <Card className="space-y-4 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">{cliente?.legal_name ?? cobranca.customer}</h1>
            <p className="text-sm text-slate-500">
              {ROTULO_TIPO[cobranca.charge_type]}
              {projeto && ` — ${projeto.name}`}
            </p>
          </div>
          <StatusBadge status={cobranca.status} />
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">Valor</dt>
            <dd className="font-medium text-slate-100">{formatBRL(cobranca.amount)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Vencimento</dt>
            <dd className="text-slate-200">{cobranca.due_date}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Forma de pagamento</dt>
            <dd className="text-slate-200">{cobranca.payment_method}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Pago em</dt>
            <dd className="text-slate-200">
              {cobranca.paid_at ? new Date(cobranca.paid_at).toLocaleDateString("pt-BR") : "—"}
            </dd>
          </div>
        </dl>

        {cobranca.payment_link && (
          <div className="rounded-md border border-slate-800 bg-slate-950 p-3">
            <p className="mb-1 text-xs text-slate-500">Link de pagamento (Mercado Pago)</p>
            <a
              href={cobranca.payment_link}
              target="_blank"
              rel="noreferrer"
              className="break-all text-sm text-indigo-400 hover:underline"
            >
              {cobranca.payment_link}
            </a>
          </div>
        )}

        {podeGerenciar && cobranca.status === "PENDING" && (
          <div className="flex flex-wrap justify-end gap-2 border-t border-slate-800 pt-4">
            {!cobranca.external_id && (
              <Button variant="secondary" disabled={emitir.isPending} onClick={() => emitir.mutate()}>
                Emitir no Mercado Pago
              </Button>
            )}
            <Button onClick={() => setModalConfirmar(true)}>Confirmar pagamento</Button>
            <Button variant="ghost" disabled={cancelar.isPending} onClick={() => cancelar.mutate()}>
              Cancelar
            </Button>
          </div>
        )}
      </Card>

      <Card className="mt-6 p-4">
        <p className="mb-3 text-sm font-medium text-slate-300">Histórico de pagamento</p>
        {!pagamentos || pagamentos.results.length === 0 ? (
          <EmptyState message="Nenhum pagamento registrado ainda para esta cobrança." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Valor</Th>
                <Th>Método</Th>
                <Th>Identificador externo</Th>
                <Th>Pago em</Th>
              </tr>
            </thead>
            <tbody>
              {pagamentos.results.map((pagamento) => (
                <Tr key={pagamento.id}>
                  <Td className="font-medium text-slate-100">{formatBRL(pagamento.amount)}</Td>
                  <Td>{pagamento.method}</Td>
                  <Td>{pagamento.external_id}</Td>
                  <Td>{new Date(pagamento.paid_at).toLocaleString("pt-BR")}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {modalConfirmar && (
        <ConfirmPaymentModal chargeId={cobranca.id} amount={cobranca.amount} onClose={() => setModalConfirmar(false)} />
      )}
      {cobrancaEmitida && (
        <ChargeIssuedModal
          charge={cobrancaEmitida}
          customerName={cliente?.legal_name ?? ""}
          customerPhone={cliente?.phone ?? ""}
          onClose={() => setCobrancaEmitida(null)}
        />
      )}
    </div>
  )
}

