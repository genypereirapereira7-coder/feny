import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Card, ErrorState, PageHeader, Select, Spinner, Table, Td, Th, Tr } from "../../components/ui"
import { api } from "../../lib/api"
import { formatBRL } from "../../lib/format"

interface LinhaFluxo {
  month: string
  revenue: string
  expenses: string
  net: string
}

// Frontend §39 — fluxo de caixa mensal. `revenue_by_month` já existe em
// apps/reports (Fase 9 original) e devolve exatamente receita/despesa/líquido
// por mês, então esta tela só consome — sem endpoint novo (§93).
export function CashFlowPage() {
  const [meses, setMeses] = useState(6)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["cash-flow", meses],
    queryFn: async () => (await api.get<LinhaFluxo[]>("/reports/revenue-by-month/", { params: { months: meses } })).data,
  })

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Fluxo de caixa" />

      <div className="mb-4 w-52">
        <Select value={meses} onChange={(e) => setMeses(Number(e.target.value))}>
          <option value={3}>Últimos 3 meses</option>
          <option value={6}>Últimos 6 meses</option>
          <option value={12}>Últimos 12 meses</option>
          <option value={24}>Últimos 24 meses</option>
        </Select>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          <Table>
            <thead>
              <tr>
                <Th>Mês</Th>
                <Th>Receita</Th>
                <Th>Despesas pagas</Th>
                <Th>Líquido</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((linha) => {
                const liquido = Number(linha.net)
                return (
                  <Tr key={linha.month}>
                    <Td className="font-medium text-slate-100">{linha.month}</Td>
                    <Td className="text-emerald-400">{formatBRL(linha.revenue)}</Td>
                    <Td className="text-red-400">{formatBRL(linha.expenses)}</Td>
                    <Td className={liquido >= 0 ? "text-slate-100" : "text-red-400"}>{formatBRL(linha.net)}</Td>
                  </Tr>
                )
              })}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  )
}
