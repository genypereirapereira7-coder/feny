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
  Td,
  Textarea,
  Th,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import { useLookup } from "../../lib/useLookup"
import type { Customer, PaginatedResponse, Ticket, TicketPriority, TicketStatus, User } from "../../lib/types"

const ROTULO_PRIORIDADE: Record<TicketPriority, string> = { LOW: "Baixa", NORMAL: "Normal", HIGH: "Alta" }
const TODOS_STATUS: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]

// Frontend Fase 9 — domínio novo (não existia em nenhuma das 10 fases do
// backend original; criado exatamente pra esta tela, com o mínimo que um
// chamado precisa: cliente, assunto, status, responsável).
export function SupportPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [modalNovo, setModalNovo] = useState(false)
  const [modalAtribuir, setModalAtribuir] = useState<Ticket | null>(null)
  const [filtroStatus, setFiltroStatus] = useState("")

  const { data, isLoading, isError } = useQuery({
    queryKey: ["tickets", filtroStatus],
    queryFn: async () =>
      (await api.get<PaginatedResponse<Ticket>>("/support/tickets/", { params: { status: filtroStatus || undefined } }))
        .data,
  })
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const { data: usuarios } = useLookup<User>("users-lookup", "/users/", (u) => u.username)

  const acao = useMutation({
    mutationFn: ({ id, rota }: { id: string; rota: string }) => api.post(`/support/tickets/${id}/${rota}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets"] })
      toast.success("Chamado atualizado.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível atualizar o chamado.")),
  })

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Suporte" actions={<Button onClick={() => setModalNovo(true)}>Novo chamado</Button>} />

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
            <EmptyState message="Nenhum chamado ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Assunto</Th>
                  <Th>Cliente</Th>
                  <Th>Prioridade</Th>
                  <Th>Responsável</Th>
                  <Th>Status</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((chamado) => (
                  <Tr key={chamado.id}>
                    <Td className="font-medium text-slate-100">{chamado.subject}</Td>
                    <Td>{clientes?.[chamado.customer] ?? chamado.customer}</Td>
                    <Td>{ROTULO_PRIORIDADE[chamado.priority]}</Td>
                    <Td>{chamado.assigned_to ? (usuarios?.[chamado.assigned_to] ?? "—") : "—"}</Td>
                    <Td>
                      <StatusBadge status={chamado.status} />
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-2">
                        {chamado.status === "OPEN" && (
                          <Button variant="secondary" onClick={() => setModalAtribuir(chamado)}>
                            Atribuir
                          </Button>
                        )}
                        {chamado.status === "IN_PROGRESS" && (
                          <Button disabled={acao.isPending} onClick={() => acao.mutate({ id: chamado.id, rota: "resolve" })}>
                            Resolver
                          </Button>
                        )}
                        {chamado.status === "RESOLVED" && (
                          <Button disabled={acao.isPending} onClick={() => acao.mutate({ id: chamado.id, rota: "close" })}>
                            Fechar
                          </Button>
                        )}
                        {(chamado.status === "RESOLVED" || chamado.status === "CLOSED") && (
                          <Button
                            variant="ghost"
                            disabled={acao.isPending}
                            onClick={() => acao.mutate({ id: chamado.id, rota: "reopen" })}
                          >
                            Reabrir
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

      {modalNovo && <NovoChamadoModal onClose={() => setModalNovo(false)} />}
      {modalAtribuir && <AtribuirModal ticket={modalAtribuir} onClose={() => setModalAtribuir(null)} />}
    </div>
  )
}

function NovoChamadoModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data: clientes } = useLookup<Customer>("customers", "/customers/", (c) => c.legal_name)
  const [customer, setCustomer] = useState("")
  const [subject, setSubject] = useState("")
  const [description, setDescription] = useState("")
  const [priority, setPriority] = useState<TicketPriority>("NORMAL")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => api.post("/support/tickets/", { customer, subject, description, priority }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets"] })
      onClose()
    },
    onError: (erroRequisicao: unknown) => {
      const dados = (erroRequisicao as { response?: { data?: Record<string, string[]> } })?.response?.data
      setErro(dados ? String(Object.values(dados).flat()[0]) : "Não foi possível abrir o chamado.")
    },
  })

  return (
    <Modal title="Novo chamado" onClose={onClose}>
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
        <Field label="Assunto">
          <Input value={subject} onChange={(e) => setSubject(e.target.value)} required />
        </Field>
        <Field label="Descrição">
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} required />
        </Field>
        <Field label="Prioridade">
          <Select value={priority} onChange={(e) => setPriority(e.target.value as TicketPriority)}>
            {Object.entries(ROTULO_PRIORIDADE).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
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
            {mutation.isPending ? "Abrindo…" : "Abrir chamado"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function AtribuirModal({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const { data: usuarios } = useQuery({
    queryKey: ["users-for-assign"],
    queryFn: async () => (await api.get<PaginatedResponse<User>>("/users/")).data,
  })
  const [assignedTo, setAssignedTo] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => api.post(`/support/tickets/${ticket.id}/assign/`, { assigned_to: assignedTo }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets"] })
      toast.success("Chamado atribuído.")
      onClose()
    },
    onError: () => setErro("Não foi possível atribuir o chamado."),
  })

  return (
    <Modal title="Atribuir chamado" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Responsável">
          <Select value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)} required>
            <option value="">Selecione…</option>
            {usuarios?.results.map((u) => (
              <option key={u.id} value={u.id}>
                {u.username}
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
            {mutation.isPending ? "Atribuindo…" : "Atribuir"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
