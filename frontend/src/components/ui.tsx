import { CheckCircle2, Circle, Clock, XCircle } from "lucide-react"
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TdHTMLAttributes,
  TextareaHTMLAttributes,
  ThHTMLAttributes,
} from "react"

/** Kit de componentes visuais compartilhado — tema escuro único (não
 * alternável) usado em todas as telas. Centralizar aqui evita repetir a
 * mesma classe Tailwind em cada tela nova. */

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  const estilos = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-indigo-400",
    secondary: "border border-slate-700 text-slate-200 hover:bg-slate-800 disabled:opacity-40",
    danger: "bg-red-600 text-white hover:bg-red-500 disabled:bg-red-900 disabled:text-red-400",
    ghost: "text-slate-300 hover:bg-slate-800 disabled:opacity-40",
  }
  return (
    <button
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${estilos[variant]} ${className}`}
      {...props}
    />
  )
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50 ${props.className ?? ""}`}
    />
  )
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50 ${props.className ?? ""}`}
    />
  )
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none disabled:opacity-50 ${props.className ?? ""}`}
    />
  )
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-xs font-medium text-slate-400">
      {children}
    </label>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
    </div>
  )
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-800 bg-slate-900 ${className}`}>{children}</div>
}

export function PageHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
      {actions}
    </div>
  )
}

export function Spinner() {
  return <p className="text-sm text-slate-500">Carregando…</p>
}

export function ErrorState({ message }: { message?: string }) {
  return <p className="text-sm text-red-400">{message ?? "Algo deu errado."}</p>
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-8 text-center text-sm text-slate-500">{message}</p>
}

// Nunca só cor (spec de frontend §57/§58) — cada categoria também tem um
// ícone e o texto do próprio status continua sempre visível.
type CategoriaStatus = "sucesso" | "espera" | "erro" | "neutro"

const CATEGORIA_POR_STATUS: Record<string, CategoriaStatus> = {
  APPROVED: "sucesso",
  PAID: "sucesso",
  SENT: "sucesso",
  ACCEPTED: "sucesso",
  DELIVERED: "sucesso",
  ACTIVE: "sucesso",
  PROCESSED: "sucesso",
  MAINTENANCE: "sucesso",
  RESOLVED: "sucesso",
  OPEN: "espera",
  IN_PROGRESS: "espera",
  PENDING: "espera",
  PENDING_APPROVAL: "espera",
  PROCESSING: "espera",
  AWAITING_INITIAL_PAYMENT: "espera",
  AWAITING_FINAL_PAYMENT: "espera",
  AWAITING_CLIENT_ACCEPTANCE: "espera",
  PAUSED: "espera",
  RECEIVED: "espera",
  IN_DEVELOPMENT: "espera",
  REJECTED: "erro",
  CANCELLED: "erro",
  FAILED: "erro",
  OVERDUE: "erro",
  IGNORED: "neutro",
  DRAFT: "neutro",
}

const ESTILO_POR_CATEGORIA: Record<CategoriaStatus, string> = {
  sucesso: "bg-emerald-500/15 text-emerald-400",
  espera: "bg-amber-500/15 text-amber-400",
  erro: "bg-red-500/15 text-red-400",
  neutro: "bg-slate-700/40 text-slate-300",
}

function IconeStatus({ categoria }: { categoria: CategoriaStatus }) {
  const tamanho = 12
  if (categoria === "sucesso") return <CheckCircle2 size={tamanho} />
  if (categoria === "espera") return <Clock size={tamanho} />
  if (categoria === "erro") return <XCircle size={tamanho} />
  return <Circle size={tamanho} />
}

export function StatusBadge({ status }: { status: string }) {
  const categoria = CATEGORIA_POR_STATUS[status] ?? "neutro"
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${ESTILO_POR_CATEGORIA[categoria]}`}
    >
      <IconeStatus categoria={categoria} />
      {status.replaceAll("_", " ").toLowerCase()}
    </span>
  )
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-left text-sm">{children}</table>
    </div>
  )
}

export function Th({ children, className = "", ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th className={`border-b border-slate-800 bg-slate-900 px-4 py-2 font-medium text-slate-400 ${className}`} {...props}>
      {children}
    </th>
  )
}

export function Td({ children, className = "", ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={`border-b border-slate-800 px-4 py-2.5 text-slate-200 ${className}`} {...props}>
      {children}
    </td>
  )
}

export function Tr({ children }: { children: ReactNode }) {
  return <tr className="hover:bg-slate-900/60">{children}</tr>
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-200">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

/** Confirmação pra operação crítica (spec de frontend §51) — título,
 * consequência, cancelar/confirmar. Usar pra aprovar orçamento, cancelar
 * cobrança/recorrência, remover usuário e afins; não pra toda ação. */
export function ConfirmDialog({
  title,
  description,
  confirmLabel = "Confirmar",
  danger = false,
  onConfirm,
  onClose,
  loading = false,
}: {
  title: string
  description: ReactNode
  confirmLabel?: string
  danger?: boolean
  onConfirm: () => void
  onClose: () => void
  loading?: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-800 bg-slate-900 p-6">
        <h2 className="mb-2 text-base font-semibold text-slate-100">{title}</h2>
        <div className="mb-5 text-sm text-slate-400">{description}</div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} disabled={loading}>
            {loading ? "Processando…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
