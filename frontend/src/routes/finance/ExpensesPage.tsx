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
import type { Expense, PaginatedResponse } from "../../lib/types"

export function ExpensesPage() {
  const { user } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [modalAberto, setModalAberto] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["expenses"],
    queryFn: async () => (await api.get<PaginatedResponse<Expense>>("/finance/expenses/")).data,
  })

  const pagar = useMutation({
    mutationFn: (id: string) => api.post(`/finance/expenses/${id}/pay/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] })
      toast.success("Despesa marcada como paga.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível marcar a despesa como paga.")),
  })
  const cancelar = useMutation({
    mutationFn: (id: string) => api.post(`/finance/expenses/${id}/cancel/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] })
      toast.success("Despesa cancelada.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível cancelar a despesa.")),
  })

  // ExpensePermission no backend: só ADMIN/FINANCE criam ou agem — MANAGER
  // só vê (ARCHITECTURE.md §9). Esconder o que ia dar 403 é só clareza de
  // UX; quem garante isso de verdade é sempre o backend.
  const podeGerenciar = user && ["ADMIN", "FINANCE"].includes(user.role)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Despesas"
        actions={podeGerenciar && <Button onClick={() => setModalAberto(true)}>Nova despesa</Button>}
      />

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhuma despesa ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Descrição</Th>
                  <Th>Categoria</Th>
                  <Th>Valor</Th>
                  <Th>Vencimento</Th>
                  <Th>Status</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((despesa) => (
                  <Tr key={despesa.id}>
                    <Td className="font-medium text-slate-100">{despesa.description}</Td>
                    <Td>{despesa.category}</Td>
                    <Td>{formatBRL(despesa.amount)}</Td>
                    <Td>{despesa.due_date}</Td>
                    <Td>
                      <StatusBadge status={despesa.status} />
                    </Td>
                    <Td>
                      {podeGerenciar && despesa.status === "PENDING" && (
                        <div className="flex gap-2">
                          <Button disabled={pagar.isPending} onClick={() => pagar.mutate(despesa.id)}>
                            Marcar como paga
                          </Button>
                          <Button variant="ghost" disabled={cancelar.isPending} onClick={() => cancelar.mutate(despesa.id)}>
                            Cancelar
                          </Button>
                        </div>
                      )}
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {modalAberto && <NovaDespesaModal onClose={() => setModalAberto(false)} />}
    </div>
  )
}

function NovaDespesaModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [category, setCategory] = useState("")
  const [description, setDescription] = useState("")
  const [amount, setAmount] = useState("")
  const [dueDate, setDueDate] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => api.post("/finance/expenses/", { category, description, amount, due_date: dueDate }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] })
      onClose()
    },
    onError: () => setErro("Não foi possível criar a despesa."),
  })

  return (
    <Modal title="Nova despesa" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Categoria">
          <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="infra, software..." required />
        </Field>
        <Field label="Descrição">
          <Input value={description} onChange={(e) => setDescription(e.target.value)} required />
        </Field>
        <Field label="Valor (R$)">
          <Input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </Field>
        <Field label="Vencimento">
          <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Criar despesa"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
