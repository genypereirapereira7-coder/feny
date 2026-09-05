import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, XCircle } from "lucide-react"
import { Card, ErrorState, PageHeader, Spinner } from "../components/ui"
import { api } from "../lib/api"
import type { IntegrationsStatus } from "../lib/types"

// Frontend Fase 9 — Configurações. Escopo decidido com o usuário: só status
// das integrações externas (Mercado Pago/WhatsApp), somente leitura — o
// segredo em si nunca passa pela API (ARCHITECTURE.md §13), então não tem
// campo pra editar aqui, só pra saber se o ambiente já tem credencial.
export function SettingsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["settings-integrations"],
    queryFn: async () => (await api.get<IntegrationsStatus>("/settings/integrations/")).data,
  })

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Configurações" />

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card className="divide-y divide-slate-800">
          <LinhaIntegracao nome="Mercado Pago" descricao="Emissão de cobranças e recebimento de webhooks de pagamento." configurado={data.mercadopago.configured} />
          <LinhaIntegracao nome="WhatsApp (Evolution API)" descricao="Envio de notificações automáticas por WhatsApp." configurado={data.whatsapp.configured} />
        </Card>
      )}

      <p className="mt-4 text-xs text-slate-600">
        Credenciais são configuradas por variável de ambiente no servidor, não por aqui — esta tela só mostra se
        cada integração já está pronta pra uso.
      </p>
    </div>
  )
}

function LinhaIntegracao({ nome, descricao, configurado }: { nome: string; descricao: string; configurado: boolean }) {
  return (
    <div className="flex items-center justify-between p-4">
      <div>
        <p className="text-sm font-medium text-slate-100">{nome}</p>
        <p className="text-xs text-slate-500">{descricao}</p>
      </div>
      {configurado ? (
        <span className="flex items-center gap-1.5 text-sm text-emerald-400">
          <CheckCircle2 size={16} /> Configurado
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-sm text-slate-500">
          <XCircle size={16} /> Não configurado
        </span>
      )}
    </div>
  )
}
