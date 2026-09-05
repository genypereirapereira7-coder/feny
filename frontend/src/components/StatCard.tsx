import { Card } from "./ui"

export function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-100">{value}</p>
    </Card>
  )
}

export function StatusBreakdown({ title, counts }: { title: string; counts: Record<string, number> }) {
  const entradas = Object.entries(counts)
  const total = entradas.reduce((soma, [, quantidade]) => soma + quantidade, 0)

  return (
    <Card className="p-4">
      <p className="mb-3 text-sm font-medium text-slate-300">{title}</p>
      {total === 0 ? (
        <p className="text-sm text-slate-500">Nada por aqui ainda.</p>
      ) : (
        <ul className="space-y-1.5">
          {entradas
            .filter(([, quantidade]) => quantidade > 0)
            .map(([status, quantidade]) => (
              <li key={status} className="flex items-center justify-between text-sm">
                <span className="text-slate-400">{status.replaceAll("_", " ").toLowerCase()}</span>
                <span className="font-medium text-slate-100">{quantidade}</span>
              </li>
            ))}
        </ul>
      )}
    </Card>
  )
}
