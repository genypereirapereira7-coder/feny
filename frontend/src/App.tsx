import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Suspense, lazy } from "react"
import { BrowserRouter, Navigate, Route, Routes, useLocation, useParams } from "react-router-dom"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { AuthProvider } from "./lib/auth"
import { PAINEL } from "./lib/rotas"
import { ToastProvider } from "./lib/toast"
import { LoginPage } from "./routes/LoginPage"

/** O painel interno da Feny.
 *
 * Este bundle é só o sistema, atrás de login. O site público (`/`) é uma
 * página estática separada — `landing/`, HTML e CSS puros, servida pelo
 * Django antes do React existir na conversa. Essa separação é o motivo de a
 * vitrine carregar rápido: quem chega pelo Google não baixa uma linha do
 * JavaScript de cobranças, auditoria e configurações.
 *
 * As telas entram por `lazy()` pelo mesmo motivo de sempre: o login é a
 * primeira tela, e ela não precisa do código do financeiro junto.
 *
 * Links antigos (`/clientes`, `/financeiro/cobrancas`) são redirecionados no
 * fim deste arquivo — bookmark salvo continua funcionando.
 */
const queryClient = new QueryClient()

const Layout = lazy(() => import("./components/Layout").then((m) => ({ default: m.Layout })))
const TwoFactorSetupPage = lazy(() =>
  import("./routes/TwoFactorSetupPage").then((m) => ({ default: m.TwoFactorSetupPage })),
)
const DashboardPage = lazy(() => import("./routes/DashboardPage").then((m) => ({ default: m.DashboardPage })))
const CustomersPage = lazy(() =>
  import("./routes/customers/CustomersPage").then((m) => ({ default: m.CustomersPage })),
)
const CustomerDetailPage = lazy(() =>
  import("./routes/customers/CustomerDetailPage").then((m) => ({ default: m.CustomerDetailPage })),
)
const LeadsPage = lazy(() => import("./routes/leads/LeadsPage").then((m) => ({ default: m.LeadsPage })))
const QuotationsPage = lazy(() =>
  import("./routes/quotations/QuotationsPage").then((m) => ({ default: m.QuotationsPage })),
)
const QuotationDetailPage = lazy(() =>
  import("./routes/quotations/QuotationDetailPage").then((m) => ({ default: m.QuotationDetailPage })),
)
const ProjectsPage = lazy(() => import("./routes/projects/ProjectsPage").then((m) => ({ default: m.ProjectsPage })))
const ProjectDetailPage = lazy(() =>
  import("./routes/projects/ProjectDetailPage").then((m) => ({ default: m.ProjectDetailPage })),
)
const ChargesPage = lazy(() => import("./routes/finance/ChargesPage").then((m) => ({ default: m.ChargesPage })))
const ChargeDetailPage = lazy(() =>
  import("./routes/finance/ChargeDetailPage").then((m) => ({ default: m.ChargeDetailPage })),
)
const RevenuesPage = lazy(() => import("./routes/finance/RevenuesPage").then((m) => ({ default: m.RevenuesPage })))
const CashFlowPage = lazy(() => import("./routes/finance/CashFlowPage").then((m) => ({ default: m.CashFlowPage })))
const ExpensesPage = lazy(() => import("./routes/finance/ExpensesPage").then((m) => ({ default: m.ExpensesPage })))
const SubscriptionsPage = lazy(() =>
  import("./routes/finance/SubscriptionsPage").then((m) => ({ default: m.SubscriptionsPage })),
)
const CommissionsPage = lazy(() =>
  import("./routes/finance/CommissionsPage").then((m) => ({ default: m.CommissionsPage })),
)
const DocumentsPage = lazy(() => import("./routes/DocumentsPage").then((m) => ({ default: m.DocumentsPage })))
const SupportPage = lazy(() => import("./routes/support/SupportPage").then((m) => ({ default: m.SupportPage })))
const TeamPage = lazy(() => import("./routes/team/TeamPage").then((m) => ({ default: m.TeamPage })))
const SettingsPage = lazy(() => import("./routes/SettingsPage").then((m) => ({ default: m.SettingsPage })))
const AuditPage = lazy(() => import("./routes/AuditPage").then((m) => ({ default: m.AuditPage })))

// Rotas do painel que existiam na raiz antes do site — mantidas como
// redirecionamento pra não quebrar bookmark nem link colado em conversa.
const ROTAS_ANTIGAS = [
  "clientes",
  "orcamentos",
  "projetos",
  "financeiro",
  "documentos",
  "suporte",
  "equipe",
  "configuracoes",
  "auditoria",
]

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <Suspense fallback={<CarregandoPainel />}>
              <Routes>
                <Route path="/login" element={<LoginPage />} />

                <Route element={<ProtectedRoute />}>
                  <Route path="/2fa/configurar" element={<TwoFactorSetupPage />} />

                  <Route path={PAINEL} element={<Layout />}>
                    <Route index element={<DashboardPage />} />
                    <Route path="clientes" element={<CustomersPage />} />
                    <Route path="clientes/:id" element={<CustomerDetailPage />} />
                    <Route path="leads" element={<LeadsPage />} />
                    <Route path="orcamentos" element={<QuotationsPage />} />
                    <Route path="orcamentos/:id" element={<QuotationDetailPage />} />
                    <Route path="projetos" element={<ProjectsPage />} />
                    <Route path="projetos/:id" element={<ProjectDetailPage />} />
                    <Route path="financeiro/cobrancas" element={<ChargesPage />} />
                    <Route path="financeiro/cobrancas/:id" element={<ChargeDetailPage />} />
                    <Route path="financeiro/receitas" element={<RevenuesPage />} />
                    <Route path="financeiro/fluxo-de-caixa" element={<CashFlowPage />} />
                    <Route path="financeiro/despesas" element={<ExpensesPage />} />
                    <Route path="financeiro/assinaturas" element={<SubscriptionsPage />} />
                    <Route path="financeiro/comissoes" element={<CommissionsPage />} />
                    <Route path="documentos" element={<DocumentsPage />} />
                    <Route path="suporte" element={<SupportPage />} />
                    <Route path="equipe" element={<TeamPage />} />
                    <Route path="configuracoes" element={<SettingsPage />} />
                    <Route path="auditoria" element={<AuditPage />} />

                    {/* Rota inexistente dentro do painel volta pro dashboard —
                        jogar quem está trabalhando no site institucional seria
                        desorientador. */}
                    <Route path="*" element={<Navigate to={PAINEL} replace />} />
                  </Route>
                </Route>

                {ROTAS_ANTIGAS.map((rota) => (
                  <Route key={rota} path={`/${rota}/*`} element={<RedirecionaParaPainel base={rota} />} />
                ))}

                {/* Qualquer rota desconhecida que chegue neste bundle vai
                    pro painel: a vitrine (`/`) é outra página, servida pelo
                    Django antes do React entrar em cena. */}
                <Route path="*" element={<Navigate to={PAINEL} replace />} />
              </Routes>
            </Suspense>
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

function CarregandoPainel() {
  return <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-500">Carregando…</div>
}

function RedirecionaParaPainel({ base }: { base: string }) {
  const location = useLocation()
  const resto = useParams()["*"]
  const caminho = `${PAINEL}/${base}${resto ? `/${resto}` : ""}`
  return <Navigate to={`${caminho}${location.search}`} replace />
}
