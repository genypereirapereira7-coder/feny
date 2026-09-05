import { Check } from "lucide-react"
import type { ProjectStatus } from "../lib/types"

/** Componente de domínio (spec de frontend §27, §64) — a sequência espelha
 * ARCHITECTURE.md §7.2. `DEVELOPMENT_COMPLETED` existe no enum mas nunca é
 * um `status` persistido de verdade: `complete_development` no backend pula
 * direto pra `AWAITING_CLIENT_ACCEPTANCE` (transição "automática", por
 * design) — mostrar aqui um estágio que nunca aparece na prática seria
 * confundir, não ajudar. */
const SEQUENCIA: { status: ProjectStatus; label: string }[] = [
  { status: "APPROVED", label: "Orçamento aprovado" },
  { status: "AWAITING_INITIAL_PAYMENT", label: "Sinal (30%) cobrado" },
  { status: "INITIAL_PAYMENT_CONFIRMED", label: "Sinal pago" },
  { status: "IN_DEVELOPMENT", label: "Em desenvolvimento" },
  { status: "AWAITING_CLIENT_ACCEPTANCE", label: "Aguardando aceite" },
  { status: "ACCEPTED", label: "Aceite do cliente" },
  { status: "AWAITING_FINAL_PAYMENT", label: "Saldo (70%) cobrado" },
  { status: "FINAL_PAYMENT_CONFIRMED", label: "Saldo pago" },
  { status: "DELIVERED", label: "Projeto entregue" },
  { status: "MAINTENANCE", label: "Em manutenção" },
]

export function ProjectTimeline({ status }: { status: ProjectStatus }) {
  const indiceAtual = SEQUENCIA.findIndex((etapa) => etapa.status === status)

  return (
    <ol className="space-y-0">
      {SEQUENCIA.map((etapa, indice) => {
        const concluida = indiceAtual >= 0 && indice < indiceAtual
        const atual = indice === indiceAtual
        const ultima = indice === SEQUENCIA.length - 1

        return (
          <li key={etapa.status} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
                  concluida
                    ? "bg-emerald-500/20 text-emerald-400"
                    : atual
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-800 text-slate-600"
                }`}
              >
                {concluida ? <Check size={13} /> : indice + 1}
              </div>
              {!ultima && <div className={`w-px flex-1 ${concluida ? "bg-emerald-500/30" : "bg-slate-800"}`} />}
            </div>
            <div className={`pb-5 text-sm ${atual ? "font-medium text-slate-100" : concluida ? "text-slate-300" : "text-slate-600"}`}>
              {etapa.label}
              {atual && <span className="ml-2 text-xs text-indigo-400">(etapa atual)</span>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
