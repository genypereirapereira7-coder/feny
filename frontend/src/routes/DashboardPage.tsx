import { useQuery } from "@tanstack/react-query"
import { StatCard, StatusBreakdown } from "../components/StatCard"
import { api } from "../lib/api"
import { formatBRL } from "../lib/format"
import type { DashboardSummary } from "../lib/types"

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => (await api.get<DashboardSummary>("/dashboard/summary/")).data,
  })

  if (isLoading) return <p className="text-sm text-slate-500">Carregando…</p>
  if (isError || !data) return <p className="text-sm text-red-400">Não foi possível carregar o dashboard.</p>

  const semNadaAinda =
    !data.finance && !data.quotations && !data.projects && !data.projects_by_status && !data.customers && !data.sales

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>

      {semNadaAinda && <p className="text-sm text-slate-500">Nenhuma informação disponível pro seu papel ainda.</p>}

      {data.finance && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-slate-500 uppercase tracking-wide">Financeiro</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatCard label="A receber" value={formatBRL(data.finance.receivable_pending)} />
            <StatCard label="Vencido" value={formatBRL(data.finance.overdue_total)} />
            <StatCard label="Qtd. vencida" value={data.finance.overdue_count} />
            <StatCard label="Receita no mês" value={formatBRL(data.finance.revenue_this_month)} />
            <StatCard label="Despesas pagas no mês" value={formatBRL(data.finance.expenses_paid_this_month)} />
            <StatCard label="Líquido no mês" value={formatBRL(data.finance.net_this_month)} />
            <StatCard label="Comissões pendentes" value={formatBRL(data.finance.commissions_pending)} />
          </div>
        </section>
      )}

      {data.customers && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-slate-500 uppercase tracking-wide">Clientes</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatCard label="Total" value={data.customers.total} />
            <StatCard label="Novos no mês" value={data.customers.new_this_month} />
          </div>
        </section>
      )}

      {(data.quotations || data.projects) && (
        <section className="grid gap-4 sm:grid-cols-2">
          {data.quotations && <StatusBreakdown title="Orçamentos" counts={data.quotations} />}
          {data.projects && <StatusBreakdown title="Projetos" counts={data.projects} />}
        </section>
      )}

      {data.sales && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-slate-500 uppercase tracking-wide">Minhas vendas</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <StatusBreakdown title="Meus orçamentos" counts={data.sales.quotations_by_status} />
            <div className="grid grid-cols-2 gap-4">
              <StatCard label="Comissão pendente" value={formatBRL(data.sales.commissions_pending)} />
              <StatCard label="Comissão paga" value={formatBRL(data.sales.commissions_paid)} />
            </div>
          </div>
        </section>
      )}

      {data.projects_by_status && (
        <section>
          <StatusBreakdown title="Meus projetos" counts={data.projects_by_status} />
        </section>
      )}
    </div>
  )
}
