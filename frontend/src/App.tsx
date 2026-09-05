import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { AuthProvider } from "./lib/auth"
import { ToastProvider } from "./lib/toast"
import { AuditPage } from "./routes/AuditPage"
import { CustomerDetailPage } from "./routes/customers/CustomerDetailPage"
import { CustomersPage } from "./routes/customers/CustomersPage"
import { DashboardPage } from "./routes/DashboardPage"
import { DocumentsPage } from "./routes/DocumentsPage"
import { CashFlowPage } from "./routes/finance/CashFlowPage"
import { ChargeDetailPage } from "./routes/finance/ChargeDetailPage"
import { ChargesPage } from "./routes/finance/ChargesPage"
import { CommissionsPage } from "./routes/finance/CommissionsPage"
import { ExpensesPage } from "./routes/finance/ExpensesPage"
import { RevenuesPage } from "./routes/finance/RevenuesPage"
import { SubscriptionsPage } from "./routes/finance/SubscriptionsPage"
import { LoginPage } from "./routes/LoginPage"
import { ProjectDetailPage } from "./routes/projects/ProjectDetailPage"
import { ProjectsPage } from "./routes/projects/ProjectsPage"
import { QuotationDetailPage } from "./routes/quotations/QuotationDetailPage"
import { QuotationsPage } from "./routes/quotations/QuotationsPage"
import { SettingsPage } from "./routes/SettingsPage"
import { SupportPage } from "./routes/support/SupportPage"
import { TeamPage } from "./routes/team/TeamPage"
import { TwoFactorSetupPage } from "./routes/TwoFactorSetupPage"

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />

              <Route element={<ProtectedRoute />}>
                <Route path="/2fa/configurar" element={<TwoFactorSetupPage />} />

                <Route element={<Layout />}>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/clientes" element={<CustomersPage />} />
                  <Route path="/clientes/:id" element={<CustomerDetailPage />} />
                  <Route path="/orcamentos" element={<QuotationsPage />} />
                  <Route path="/orcamentos/:id" element={<QuotationDetailPage />} />
                  <Route path="/projetos" element={<ProjectsPage />} />
                  <Route path="/projetos/:id" element={<ProjectDetailPage />} />
                  <Route path="/financeiro/cobrancas" element={<ChargesPage />} />
                  <Route path="/financeiro/cobrancas/:id" element={<ChargeDetailPage />} />
                  <Route path="/financeiro/receitas" element={<RevenuesPage />} />
                  <Route path="/financeiro/fluxo-de-caixa" element={<CashFlowPage />} />
                  <Route path="/financeiro/despesas" element={<ExpensesPage />} />
                  <Route path="/financeiro/assinaturas" element={<SubscriptionsPage />} />
                  <Route path="/financeiro/comissoes" element={<CommissionsPage />} />
                  <Route path="/documentos" element={<DocumentsPage />} />
                  <Route path="/suporte" element={<SupportPage />} />
                  <Route path="/equipe" element={<TeamPage />} />
                  <Route path="/configuracoes" element={<SettingsPage />} />
                  <Route path="/auditoria" element={<AuditPage />} />
                </Route>
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
