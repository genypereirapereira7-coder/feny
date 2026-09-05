import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner, StatusBadge, Table, Th, Td, Tr } from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { formatBRL } from "../../lib/format"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import type { Commission, PaginatedResponse } from "../../lib/types"

export function CommissionsPage() {
  const { user } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ["commissions"],
    queryFn: async () => (await api.get<PaginatedResponse<Commission>>("/finance/commissions/")).data,
  })

  const pagar = useMutation({
    mutationFn: (id: string) => api.post(`/finance/commissions/${id}/pay/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commissions"] })
      toast.success("Comissão marcada como paga.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível marcar a comissão como paga.")),
  })

  const podeMarcarPaga = user && ["ADMIN", "FINANCE"].includes(user.role)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Comissões" />

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhuma comissão ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Valor</Th>
                  <Th>Percentual</Th>
                  <Th>Status</Th>
                  <Th>Gerada em</Th>
                  {podeMarcarPaga && <Th>Ações</Th>}
                </tr>
              </thead>
              <tbody>
                {data.results.map((comissao) => (
                  <Tr key={comissao.id}>
                    <Td className="font-medium text-slate-100">{formatBRL(comissao.amount)}</Td>
                    <Td>{comissao.percentage}%</Td>
                    <Td>
                      <StatusBadge status={comissao.status} />
                    </Td>
                    <Td>{new Date(comissao.created_at).toLocaleDateString("pt-BR")}</Td>
                    {podeMarcarPaga && (
                      <Td>
                        {comissao.status === "PENDING" && (
                          <Button disabled={pagar.isPending} onClick={() => pagar.mutate(comissao.id)}>
                            Marcar como paga
                          </Button>
                        )}
                      </Td>
                    )}
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}
    </div>
  )
}
