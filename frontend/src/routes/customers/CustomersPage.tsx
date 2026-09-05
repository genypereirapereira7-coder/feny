import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowDown, ArrowUp, Search } from "lucide-react"
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
  Table,
  Td,
  Th,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import type { Customer, CustomerKind, PaginatedResponse, PaymentMethod } from "../../lib/types"

const RAZAO_KIND: Record<CustomerKind, string> = { INDIVIDUAL: "Pessoa física", COMPANY: "Pessoa jurídica" }

function IconeOrdenacao({ ordenacao, campo }: { ordenacao: string; campo: string }) {
  if (ordenacao === campo) return <ArrowUp size={12} className="inline" />
  if (ordenacao === `-${campo}`) return <ArrowDown size={12} className="inline" />
  return null
}

export function CustomersPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [modalAberto, setModalAberto] = useState(false)
  const [busca, setBusca] = useState("")
  const [ordenacao, setOrdenacao] = useState("legal_name")

  const { data, isLoading, isError } = useQuery({
    queryKey: ["customers", busca, ordenacao],
    queryFn: async () =>
      (
        await api.get<PaginatedResponse<Customer>>("/customers/", {
          params: { search: busca || undefined, ordering: ordenacao },
        })
      ).data,
  })

  const podeCriar = user && ["ADMIN", "MANAGER", "SALES"].includes(user.role)

  const alternarOrdenacao = (campo: string) => {
    setOrdenacao((atual) => (atual === campo ? `-${campo}` : campo))
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Clientes"
        actions={podeCriar && <Button onClick={() => setModalAberto(true)}>Novo cliente</Button>}
      />

      <div className="mb-4 max-w-xs">
        <div className="relative">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, documento, e-mail…"
            className="pl-9"
          />
        </div>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message={busca ? "Nenhum cliente encontrado." : "Nenhum cliente cadastrado ainda."} />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th className="cursor-pointer hover:text-slate-200" onClick={() => alternarOrdenacao("legal_name")}>
                    Nome <IconeOrdenacao ordenacao={ordenacao} campo="legal_name" />
                  </Th>
                  <Th>Tipo</Th>
                  <Th>Documento</Th>
                  <Th>Contato</Th>
                  <Th className="cursor-pointer hover:text-slate-200" onClick={() => alternarOrdenacao("created_at")}>
                    Criado em <IconeOrdenacao ordenacao={ordenacao} campo="created_at" />
                  </Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((cliente) => (
                  <Tr key={cliente.id}>
                    <Td className="cursor-pointer font-medium text-slate-100" onClick={() => navigate(`/clientes/${cliente.id}`)}>
                      {cliente.legal_name}
                    </Td>
                    <Td>{RAZAO_KIND[cliente.kind]}</Td>
                    <Td className="font-mono text-xs">{cliente.document}</Td>
                    <Td>
                      <div className="text-xs text-slate-400">
                        {cliente.email && <div>{cliente.email}</div>}
                        {cliente.phone && <div>{cliente.phone}</div>}
                      </div>
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {new Date(cliente.created_at).toLocaleDateString("pt-BR")}
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {modalAberto && <NovoClienteModal onClose={() => setModalAberto(false)} />}
    </div>
  )
}

function NovoClienteModal({ onClose }: { onClose: () => void }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [kind, setKind] = useState<CustomerKind>("INDIVIDUAL")
  const [legalName, setLegalName] = useState("")
  const [document, setDocument] = useState("")
  const [email, setEmail] = useState("")
  const [phone, setPhone] = useState("")
  const [preferredPaymentMethod, setPreferredPaymentMethod] = useState<PaymentMethod>("BOLETO")
  const [nomeResponsavel, setNomeResponsavel] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      const resposta = await api.post<Customer>("/customers/", {
        kind,
        legal_name: legalName,
        document,
        email,
        phone,
        preferred_payment_method: preferredPaymentMethod,
      })
      // "Nome do responsável" (spec de frontend §20) não é campo do Customer
      // — é um CustomerContact. Cria um automaticamente quando informado,
      // sem inventar campo nenhum no backend.
      if (nomeResponsavel.trim()) {
        await api.post("/customer-contacts/", { customer: resposta.data.id, name: nomeResponsavel })
      }
      return resposta.data
    },
    onSuccess: (cliente) => {
      queryClient.invalidateQueries({ queryKey: ["customers"] })
      toast.success("Cliente criado com sucesso.")
      onClose()
      navigate(`/clientes/${cliente.id}`)
    },
    onError: (erroRequisicao: unknown) => setErro(extrairMensagemErro(erroRequisicao, "Não foi possível criar o cliente.")),
  })

  const aoSubmeter = (evento: FormEvent) => {
    evento.preventDefault()
    setErro(null)
    mutation.mutate()
  }

  return (
    <Modal title="Novo cliente" onClose={onClose}>
      <form onSubmit={aoSubmeter} className="space-y-3">
        <Field label="Tipo">
          <Select value={kind} onChange={(e) => setKind(e.target.value as CustomerKind)}>
            <option value="INDIVIDUAL">Pessoa física</option>
            <option value="COMPANY">Pessoa jurídica</option>
          </Select>
        </Field>
        <Field label="Nome / Razão social">
          <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} required />
        </Field>
        <Field label={kind === "INDIVIDUAL" ? "CPF" : "CNPJ"}>
          <Input value={document} onChange={(e) => setDocument(e.target.value)} required />
        </Field>
        <Field label="E-mail">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Telefone">
          <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="(11) 99999-9999" />
        </Field>
        <Field label="Forma de pagamento preferida">
          <Select value={preferredPaymentMethod} onChange={(e) => setPreferredPaymentMethod(e.target.value as PaymentMethod)}>
            <option value="BOLETO">Boleto</option>
            <option value="CARD">Cartão</option>
          </Select>
        </Field>
        {kind === "COMPANY" && (
          <Field label="Nome do responsável (opcional)">
            <Input value={nomeResponsavel} onChange={(e) => setNomeResponsavel(e.target.value)} />
          </Field>
        )}

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Criar cliente"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
