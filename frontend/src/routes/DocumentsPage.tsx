import { DocumentsPanel } from "../components/DocumentsPanel"
import { PageHeader } from "../components/ui"

// Frontend Fase 9 — Documentos como tela avulsa (§21/§26 já cobriam a versão
// embutida em Cliente/Projeto). Backend já suportava isto por completo desde
// a Fase 6 (DocumentViewSet é `/api/v1/documents/` sem filtro obrigatório) —
// só faltava a tela; sem props, `DocumentsPanel` lista/envia documentos sem
// vínculo de cliente ou projeto.
export function DocumentsPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Documentos" />
      <DocumentsPanel />
    </div>
  )
}
