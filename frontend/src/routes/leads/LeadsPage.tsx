import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { MessageCircle, Search } from "lucide-react"
import { useState } from "react"
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
  Td,
  Textarea,
  Th,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import { useLookup } from "../../lib/useLookup"
import type { Customer, Lead, LeadStatus, PaginatedResponse } from "../../lib/types"

const ROTULO_STATUS: Record<LeadStatus, string> = {
  NEW: "Novo",
  CONTACTED: "Em contato",
  QUALIFIED: "Qualificado",
  CONVERTED: "Convertido",
  DISCARDED: "Descartado",
}

const FILTROS: { valor: string; label: string }[] = [
  { valor: "", label: "Todos" },
  { valor: "NEW", label: "Novos" },
  { valor: "CONTACTED", label: "Em contato" },
  { valor: "QUALIFIED", label: "Qualificados" },
  { valor: "CONVERTED", label: "Convertidos" },
  { valor: "DISCARDED", label: "Descartados" },
]

function formatarTelefone(digitos: string): string {
  if (digitos.length === 11) return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`
  if (digitos.length === 10) return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 6)}-${digitos.slice(6)}`
  return digitos
}

export function LeadsPage() {
  const { user } = useAuth()
  const [statusFiltro, setStatusFiltro] = useState("")
  const [busca, setBusca] = useState("")
  const [leadAberto, setLeadAberto] = useState<Lead | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["leads", statusFiltro, busca],
    queryFn: async () =>
      (
        await api.get<PaginatedResponse<Lead>>("/leads/", {
          params: { status: statusFiltro || undefined, search: busca || undefined },
        })
      ).data,
  })

  // Suporte só consulta (ver `apps/leads/permissions.py`) — sem os botões de
  // ação, em vez de mostrar botão que sempre devolve 403.
  const podeAtender = !!user && ["ADMIN", "MANAGER", "SALES"].includes(user.role)

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Leads do site" />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-1.5">
          {FILTROS.map((filtro) => (
            <button
              key={filtro.valor}
              type="button"
              onClick={() => setStatusFiltro(filtro.valor)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                statusFiltro === filtro.valor
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-800 text-slate-400 hover:bg-slate-800"
              }`}
            >
              {filtro.label}
            </button>
          ))}
        </div>

        <div className="relative ml-auto w-full max-w-xs">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, empresa, e-mail…"
            className="pl-9"
          />
        </div>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState
              message={
                busca || statusFiltro
                  ? "Nenhum lead com esse filtro."
                  : "Nenhum contato pelo site ainda — os que chegarem aparecem aqui."
              }
            />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Contato</Th>
                  <Th>Precisa de</Th>
                  <Th>Faixa</Th>
                  <Th>Status</Th>
                  <Th>Chegou em</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((lead) => (
                  <Tr key={lead.id}>
                    <Td className="cursor-pointer" onClick={() => setLeadAberto(lead)}>
                      <p className="font-medium text-slate-100">{lead.name}</p>
                      <p className="text-xs text-slate-500">
                        {lead.company ? `${lead.company} · ` : ""}
                        {lead.email}
                      </p>
                    </Td>
                    <Td className="text-sm">{lead.service_type_display}</Td>
                    <Td className="text-xs text-slate-400">{lead.budget_range_display}</Td>
                    <Td>
                      <StatusBadge status={lead.status} label={ROTULO_STATUS[lead.status]} />
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {new Date(lead.created_at).toLocaleDateString("pt-BR")}
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {leadAberto && (
        <DetalheLead
          lead={leadAberto}
          podeAtender={podeAtender}
          onClose={() => setLeadAberto(null)}
          onAtualizar={setLeadAberto}
        />
      )}
    </div>
  )
}

function DetalheLead({
  lead,
  podeAtender,
  onClose,
  onAtualizar,
}: {
  lead: Lead
  podeAtender: boolean
  onClose: () => void
  onAtualizar: (lead: Lead) => void
}) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [confirmandoDescarte, setConfirmandoDescarte] = useState(false)
  const [convertendo, setConvertendo] = useState(false)
  const [motivo, setMotivo] = useState("")
  const [anotacoes, setAnotacoes] = useState(lead.internal_notes)

  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (cliente) => cliente.legal_name)
  const [clienteEscolhido, setClienteEscolhido] = useState("")

  const aoConcluir = (atualizado: Lead, mensagem: string) => {
    queryClient.invalidateQueries({ queryKey: ["leads"] })
    onAtualizar(atualizado)
    toast.success(mensagem)
  }

  const acao = useMutation({
    mutationFn: async ({ nome, corpo }: { nome: string; corpo?: Record<string, string> }) =>
      (await api.post<Lead>(`/leads/${lead.id}/${nome}/`, corpo ?? {})).data,
    onSuccess: (atualizado) => aoConcluir(atualizado, "Lead atualizado."),
    onError: (erro) => toast.error(extrairMensagemErro(erro, "Não foi possível atualizar o lead.")),
  })

  const salvarAnotacoes = useMutation({
    mutationFn: async () =>
      (await api.patch<Lead>(`/leads/${lead.id}/`, { internal_notes: anotacoes })).data,
    onSuccess: (atualizado) => aoConcluir(atualizado, "Anotações salvas."),
    onError: (erro) => toast.error(extrairMensagemErro(erro, "Não foi possível salvar as anotações.")),
  })

  const ocupado = acao.isPending || salvarAnotacoes.isPending
  const telefone = formatarTelefone(lead.phone)

  return (
    <Modal title={lead.name} onClose={onClose}>
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={lead.status} label={ROTULO_STATUS[lead.status]} />
          <span className="text-xs text-slate-500">
            Chegou em {new Date(lead.created_at).toLocaleString("pt-BR")}
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <Dado rotulo="Empresa" valor={lead.company || "—"} />
          <Dado rotulo="Precisa de" valor={lead.service_type_display} />
          <Dado rotulo="E-mail" valor={lead.email} />
          <Dado rotulo="Faixa" valor={lead.budget_range_display} />
          <Dado rotulo="WhatsApp" valor={telefone} />
          <Dado rotulo="Responsável" valor={lead.handled_by_name || "—"} />
        </dl>

        <div>
          <p className="mb-1 text-xs font-medium text-slate-400">Mensagem</p>
          <p className="whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">
            {lead.message}
          </p>
        </div>

        {lead.customer_name && (
          <p className="text-sm text-emerald-400">Convertido no cliente {lead.customer_name}.</p>
        )}

        <a
          href={`https://wa.me/55${lead.phone}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 text-sm text-emerald-400 hover:text-emerald-300"
        >
          <MessageCircle size={15} /> Chamar no WhatsApp
        </a>

        {podeAtender && (
          <>
            <div>
              <Field label="Anotações internas">
                <Textarea rows={3} value={anotacoes} onChange={(e) => setAnotacoes(e.target.value)} />
              </Field>
              <div className="mt-2 flex justify-end">
                <Button
                  variant="secondary"
                  onClick={() => salvarAnotacoes.mutate()}
                  disabled={ocupado || anotacoes === lead.internal_notes}
                >
                  Salvar anotações
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-800 pt-4">
              {lead.status === "NEW" && (
                <Button onClick={() => acao.mutate({ nome: "contatar" })} disabled={ocupado}>
                  Entrei em contato
                </Button>
              )}
              {lead.status === "CONTACTED" && (
                <Button onClick={() => acao.mutate({ nome: "qualificar" })} disabled={ocupado}>
                  Qualificar
                </Button>
              )}
              {(lead.status === "CONTACTED" || lead.status === "QUALIFIED") && (
                <Button variant="secondary" onClick={() => setConvertendo(true)} disabled={ocupado}>
                  Virou cliente
                </Button>
              )}
              {lead.status === "DISCARDED" && (
                <Button variant="secondary" onClick={() => acao.mutate({ nome: "reabrir" })} disabled={ocupado}>
                  Reabrir
                </Button>
              )}
              {lead.status !== "CONVERTED" && lead.status !== "DISCARDED" && (
                <Button variant="danger" onClick={() => setConfirmandoDescarte(true)} disabled={ocupado}>
                  Descartar
                </Button>
              )}
            </div>
          </>
        )}
      </div>

      {confirmandoDescarte && (
        <ConfirmDialog
          title="Descartar este lead?"
          description={
            <div className="space-y-3">
              <p>Ele sai da fila de atendimento, mas continua no histórico — descarte não apaga nada.</p>
              <Field label="Por quê?">
                <Input
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  placeholder="Ex.: fora da faixa de orçamento"
                  autoFocus
                />
              </Field>
            </div>
          }
          confirmLabel="Descartar"
          danger
          loading={acao.isPending}
          onClose={() => setConfirmandoDescarte(false)}
          onConfirm={() =>
            acao.mutate(
              { nome: "descartar", corpo: { motivo } },
              { onSuccess: () => setConfirmandoDescarte(false) },
            )
          }
        />
      )}

      {convertendo && (
        <ConfirmDialog
          title="Marcar como convertido"
          description={
            <div className="space-y-3">
              {/* O lead não vira cliente sozinho de propósito: cliente exige
                  CPF/CNPJ válido, que o formulário do site não pede. Cadastre
                  em Clientes primeiro e aponte pra ele aqui. */}
              <p>Escolha o cliente já cadastrado que este lead virou.</p>
              <Field label="Cliente">
                <Select value={clienteEscolhido} onChange={(e) => setClienteEscolhido(e.target.value)}>
                  <option value="">Selecione…</option>
                  {Object.entries(clientes ?? {}).map(([id, nome]) => (
                    <option key={id} value={id}>
                      {nome}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          }
          confirmLabel="Confirmar conversão"
          loading={acao.isPending}
          onClose={() => setConvertendo(false)}
          onConfirm={() =>
            acao.mutate(
              { nome: "converter", corpo: { customer: clienteEscolhido } },
              { onSuccess: () => setConvertendo(false) },
            )
          }
        />
      )}
    </Modal>
  )
}

function Dado({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{rotulo}</dt>
      <dd className="text-slate-200">{valor}</dd>
    </div>
  )
}
