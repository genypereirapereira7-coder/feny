import { useMutation, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import { api } from "../lib/api"
import { useToast } from "../lib/toast"
import { Button, Field, Input, Modal } from "./ui"

interface Props {
  chargeId: string
  amount: string
  onClose: () => void
}

// Correção administrativa auditada (ARCHITECTURE.md §9) — o caminho normal é
// o webhook do Mercado Pago. Usado tanto na lista de cobranças quanto na
// tela de detalhe (§31/§32), por isso vive num componente só.
export function ConfirmPaymentModal({ chargeId, amount, onClose }: Props) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [externalId, setExternalId] = useState("")
  const [valor, setValor] = useState(amount)
  const [method, setMethod] = useState("PIX")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/finance/charges/${chargeId}/confirm-payment/`, { external_id: externalId, amount: valor, method }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["charges"] })
      queryClient.invalidateQueries({ queryKey: ["charge", chargeId] })
      queryClient.invalidateQueries({ queryKey: ["payments", "charge", chargeId] })
      toast.success("Pagamento confirmado.")
      onClose()
    },
    onError: () => setErro("Não foi possível confirmar o pagamento."),
  })

  return (
    <Modal title="Confirmar pagamento manualmente" onClose={onClose}>
      <p className="mb-3 text-xs text-slate-500">
        Correção administrativa auditada (ARCHITECTURE.md §9) — o caminho normal é o webhook do Mercado Pago. Use
        isto só quando o pagamento foi confirmado por outro meio.
      </p>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Identificador externo do pagamento">
          <Input value={externalId} onChange={(e) => setExternalId(e.target.value)} required />
        </Field>
        <Field label="Valor recebido (R$)">
          <Input type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} required />
        </Field>
        <Field label="Método">
          <Input value={method} onChange={(e) => setMethod(e.target.value)} required />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Confirmando…" : "Confirmar pagamento"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
