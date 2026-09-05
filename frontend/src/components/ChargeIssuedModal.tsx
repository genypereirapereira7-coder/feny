import { Copy, Eye, MessageCircle } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { formatBRL } from "../lib/format"
import { useToast } from "../lib/toast"
import type { Charge } from "../lib/types"
import { Button, Modal } from "./ui"

function telefoneParaWhatsApp(telefone: string): string {
  return telefone.replace(/\D/g, "")
}

interface Props {
  charge: Charge
  customerName: string
  customerPhone: string
  onClose: () => void
}

// Frontend §34 — resultado da emissão. O envio automático já foi enfileirado
// pelo backend (issue_charge cria a Notification, ARCHITECTURE.md §11); isto
// aqui é só conveniência pra quem quer agir na hora, não substitui aquilo.
export function ChargeIssuedModal({ charge, customerName, customerPhone, onClose }: Props) {
  const toast = useToast()
  const navigate = useNavigate()
  const numero = telefoneParaWhatsApp(customerPhone)
  const mensagem = `Olá, ${customerName}! Segue o link para pagamento (${formatBRL(charge.amount)}): ${charge.payment_link}`

  return (
    <Modal title="Cobrança emitida" onClose={onClose}>
      <p className="mb-4 text-sm text-slate-400">
        Link de pagamento gerado no Mercado Pago. Uma notificação por WhatsApp também foi enfileirada
        automaticamente — os botões abaixo são só pra agir na hora, se preferir.
      </p>

      <div className="mb-4 break-all rounded-md border border-slate-800 bg-slate-950 p-2 text-xs text-slate-400">
        {charge.payment_link}
      </div>

      <div className="flex flex-col gap-2">
        <Button
          variant="secondary"
          onClick={() => {
            navigator.clipboard.writeText(charge.payment_link)
            toast.success("Link copiado.")
          }}
        >
          <Copy size={14} className="mr-1.5 inline" /> Copiar link
        </Button>

        {numero ? (
          <a
            href={`https://wa.me/${numero}?text=${encodeURIComponent(mensagem)}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
          >
            <MessageCircle size={14} /> Enviar pelo WhatsApp
          </a>
        ) : (
          <p className="text-center text-xs text-slate-600">Cliente sem telefone cadastrado.</p>
        )}

        <Button
          variant="ghost"
          onClick={() => {
            onClose()
            navigate(`/financeiro/cobrancas/${charge.id}`)
          }}
        >
          <Eye size={14} className="mr-1.5 inline" /> Visualizar cobrança
        </Button>
      </div>
    </Modal>
  )
}
