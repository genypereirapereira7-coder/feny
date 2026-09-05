import { type ReactNode, createContext, useCallback, useContext, useState } from "react"

/** Sistema de toast (ARCHITECTURE de frontend §17, §52, §63) — feedback
 * explícito depois de qualquer operação, nunca "sucesso silencioso". */

interface Toast {
  id: number
  kind: "success" | "error"
  message: string
}

interface ToastContextValue {
  success: (message: string) => void
  error: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let proximoId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const empurrar = useCallback((kind: Toast["kind"], message: string) => {
    const id = proximoId++
    setToasts((atual) => [...atual, { id, kind, message }])
    setTimeout(() => setToasts((atual) => atual.filter((t) => t.id !== id)), 5000)
  }, [])

  const success = useCallback((message: string) => empurrar("success", message), [empurrar])
  const error = useCallback((message: string) => empurrar("error", message), [empurrar])

  return (
    <ToastContext.Provider value={{ success, error }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`rounded-md border px-4 py-2.5 text-sm shadow-lg ${
              toast.kind === "success"
                ? "border-emerald-800 bg-emerald-950 text-emerald-300"
                : "border-red-800 bg-red-950 text-red-300"
            }`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error("useToast precisa estar dentro de <ToastProvider>")
  return context
}

/** Extrai uma mensagem legível de um erro de API do DRF — nunca mostra
 * stack trace pro usuário (regra explícita da especificação de frontend §53). */
export function extrairMensagemErro(erro: unknown, padrao: string): string {
  const dados = (erro as { response?: { data?: unknown } })?.response?.data
  if (!dados || typeof dados !== "object") return padrao
  if ("detail" in dados && typeof (dados as { detail?: unknown }).detail === "string") {
    return (dados as { detail: string }).detail
  }
  const primeiroValor = Object.values(dados as Record<string, unknown>)[0]
  if (Array.isArray(primeiroValor) && typeof primeiroValor[0] === "string") return primeiroValor[0]
  if (typeof primeiroValor === "string") return primeiroValor
  return padrao
}
