import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { type FormEvent, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { DocumentsPanel } from "../../components/DocumentsPanel"
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  Spinner,
  StatusBadge,
  Table,
  Td,
  Th,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import type { Charge, Customer, CustomerContact, PaginatedResponse, Project } from "../../lib/types"

const RAZAO_KIND: Record<string, string> = { INDIVIDUAL: "Pessoa física", COMPANY: "Pessoa jurídica" }
type Aba = "resumo" | "projetos" | "financeiro" | "documentos"

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [aba, setAba] = useState<Aba>("resumo")

  const { data: cliente, isLoading, isError } = useQuery({
    queryKey: ["customer", id],
    queryFn: async () => (await api.get<Customer>(`/customers/${id}/`)).data,
  })

  // Financeiro é ChargePermission no backend: só ADMIN/MANAGER/FINANCE veem
  // — nem oferece a aba pra quem bateria 403 (§47).
  const vePainelFinanceiro = user && ["ADMIN", "MANAGER", "FINANCE"].includes(user.role)

  if (isLoading) return <Spinner />
  if (isError || !cliente) return <ErrorState message="Não foi possível carregar este cliente." />

  const abas: { id: Aba; label: string }[] = [
    { id: "resumo", label: "Resumo" },
    { id: "projetos", label: "Projetos" },
    ...(vePainelFinanceiro ? ([{ id: "financeiro", label: "Financeiro" }] as const) : []),
    { id: "documentos", label: "Documentos" },
  ]

  return (
    <div className="mx-auto max-w-5xl">
      <button
        type="button"
        onClick={() => navigate("/clientes")}
        className="mb-4 flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft size={14} /> Clientes
      </button>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">{cliente.legal_name}</h1>
          <p className="mt-1 font-mono text-sm text-slate-500">{cliente.document}</p>
        </div>
        <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-medium text-slate-300">
          {RAZAO_KIND[cliente.kind]}
        </span>
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

      {aba === "resumo" && <AbaResumo cliente={cliente} />}
      {aba === "projetos" && <AbaProjetos customerId={cliente.id} />}
      {aba === "financeiro" && vePainelFinanceiro && <AbaFinanceiro customerId={cliente.id} />}
      {aba === "documentos" && <DocumentsPanel customerId={cliente.id} />}
    </div>
  )
}

function AbaResumo({ cliente }: { cliente: Customer }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [modalContato, setModalContato] = useState(false)

  const excluirContato = useMutation({
    mutationFn: (contatoId: string) => api.delete(`/customer-contacts/${contatoId}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer", cliente.id] })
      toast.success("Contato removido.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível remover o contato.")),
  })

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card className="space-y-3 p-4">
        <p className="text-sm font-medium text-slate-300">Dados de contato</p>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">E-mail</dt>
            <dd className="text-slate-200">{cliente.email || "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Telefone</dt>
            <dd className="text-slate-200">{cliente.phone || "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Pagamento preferido</dt>
            <dd className="text-slate-200">{cliente.preferred_payment_method === "BOLETO" ? "Boleto" : "Cartão"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Cliente desde</dt>
            <dd className="text-slate-200">{new Date(cliente.created_at).toLocaleDateString("pt-BR")}</dd>
          </div>
        </dl>
      </Card>

      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-300">Responsáveis / contatos</p>
          <Button variant="secondary" onClick={() => setModalContato(true)}>
            Adicionar
          </Button>
        </div>
        {cliente.contacts.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum contato cadastrado.</p>
        ) : (
          <ul className="space-y-2">
            {cliente.contacts.map((contato: CustomerContact) => (
              <li key={contato.id} className="flex items-center justify-between rounded-md border border-slate-800 px-3 py-2 text-sm">
                <div>
                  <p className="text-slate-200">{contato.name}</p>
                  <p className="text-xs text-slate-500">
                    {[contato.role, contato.email, contato.phone].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => excluirContato.mutate(contato.id)}
                  className="text-xs text-red-400 hover:underline"
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {modalContato && <NovoContatoModal customerId={cliente.id} onClose={() => setModalContato(false)} />}
    </div>
  )
}

function NovoContatoModal({ customerId, onClose }: { customerId: string; onClose: () => void }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [role, setRole] = useState("")
  const [email, setEmail] = useState("")
  const [phone, setPhone] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => api.post("/customer-contacts/", { customer: customerId, name, role, email, phone }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer", customerId] })
      toast.success("Contato adicionado.")
      onClose()
    },
    onError: (erro: unknown) => setErro(extrairMensagemErro(erro, "Não foi possível adicionar o contato.")),
  })

  return (
    <Modal title="Novo contato" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Nome">
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Cargo (opcional)">
          <Input value={role} onChange={(e) => setRole(e.target.value)} />
        </Field>
        <Field label="E-mail (opcional)">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Telefone (opcional)">
          <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Adicionar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function AbaProjetos({ customerId }: { customerId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["projects"],
    queryFn: async () => (await api.get<PaginatedResponse<Project>>("/projects/")).data,
  })

  if (isLoading) return <Spinner />
  if (isError) return <ErrorState />

  const projetos = data?.results.filter((p) => p.customer === customerId) ?? []

  return (
    <Card>
      {projetos.length === 0 ? (
        <EmptyState message="Nenhum projeto relacionado a este cliente." />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Projeto</Th>
              <Th>Valor</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {projetos.map((projeto) => (
              <Tr key={projeto.id}>
                <Td className="font-medium text-slate-100">{projeto.name}</Td>
                <Td>{formatBRL(projeto.amount)}</Td>
                <Td>
                  <StatusBadge status={projeto.status} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  )
}

function AbaFinanceiro({ customerId }: { customerId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["charges"],
    queryFn: async () => (await api.get<PaginatedResponse<Charge>>("/finance/charges/")).data,
  })

  if (isLoading) return <Spinner />
  if (isError) return <ErrorState />

  const cobrancas = data?.results.filter((c) => c.customer === customerId) ?? []

  return (
    <Card>
      {cobrancas.length === 0 ? (
        <EmptyState message="Nenhuma cobrança relacionada a este cliente." />
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
            {cobrancas.map((cobranca) => (
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
