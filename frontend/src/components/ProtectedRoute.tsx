import { Navigate, Outlet, useLocation } from "react-router-dom"
import { tokenStorage } from "../lib/api"
import { useAuth } from "../lib/auth"
import { requiresTwoFactorSetup } from "../lib/jwt"

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">Carregando…</div>
  }

  // Tela de login de verdade pra quem não está autenticado. `VITE_AUTO_LOGIN_*`
  // (só em `frontend/.env`, nunca commitado) continua funcionando — nesse
  // caso `user` já chega preenchido antes de cair aqui, então quem tem essa
  // variável configurada (dev, sua própria máquina) nunca vê este formulário;
  // qualquer outra pessoa/ambiente sem essa variável vê a tela normal.
  if (!user) {
    return <Navigate to="/login" replace />
  }

  const precisaConfigurar2fa = requiresTwoFactorSetup(tokenStorage.getAccess())
  if (precisaConfigurar2fa && location.pathname !== "/2fa/configurar") {
    return <Navigate to="/2fa/configurar" replace />
  }

  return <Outlet />
}
