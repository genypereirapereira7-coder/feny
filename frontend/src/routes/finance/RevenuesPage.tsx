import { useQuery } from "@tanstack/react-query"
import { Card, EmptyState, ErrorState, PageHeader, Spinner, Table, Td, Th, Tr } from "../../components/ui"
import { api } from "../../lib/api"
import { formatBRL } from "../../lib/format"
import type { PaginatedResponse, Revenue, RevenueSource } from "../../lib/types"

const ROTULO_ORIGEM: Record<RevenueSource, string> = {
  PROJECT: "Projeto",
  RECURRING: "Recorrente",
  OTHER: "Outro",
}

// Frontend §38 — livro-razão de entradas. Sem criação/edição aqui: cada
// linha nasce sozinha dentro de finance.services.confirm_payment
// (ARCHITECTURE.md, docstring de Revenue) — a tela só lê.
export function RevenuesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["revenues"],
    queryFn: async () => (await api.get<PaginatedResponse<Revenue>>("/finance/revenues/")).data,
  })

  const total = (data?.results.reduce((soma, receita) => soma + Number(receita.amount), 0) ?? 0).toFixed(2)

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Receitas" />

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <>
          <Card className="mb-4 p-4">
            <p className="text-xs text-slate-500">Total nesta página</p>
            <p className="text-xl font-semibold text-slate-100">{formatBRL(total)}</p>
          </Card>

          <Card>
            {data.results.length === 0 ? (
              <EmptyState message="Nenhuma receita registrada ainda." />
            ) : (
              <Table>
                <thead>
                  <tr>
                    <Th>Origem</Th>
                    <Th>Descrição</Th>
                    <Th>Valor</Th>
                    <Th>Recebido em</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((receita) => (
                    <Tr key={receita.id}>
                      <Td>{ROTULO_ORIGEM[receita.source]}</Td>
                      <Td>{receita.description || "—"}</Td>
                      <Td className="font-medium text-slate-100">{formatBRL(receita.amount)}</Td>
                      <Td>{new Date(receita.received_at).toLocaleString("pt-BR")}</Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
