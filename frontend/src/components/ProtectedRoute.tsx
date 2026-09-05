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

  // Tela de login desligada "por enquanto" (a pedido) — sem isto, qualquer
  // falha do auto-login (backend fora do ar, credencial errada no `.env`)
  // caía de volta pro formulário de usuário/senha, que é exatamente o que
  // não deve aparecer agora. Pra religar a tela de login: descomente a rota
  // `/login` em `App.tsx` e troque este bloco de volta por
  // `<Navigate to="/login" replace />`.
  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-center text-slate-500">
        <p>Não foi possível entrar automaticamente.</p>
        <p className="max-w-sm text-xs text-slate-600">
          Confira se o backend está no ar e se `VITE_AUTO_LOGIN_USERNAME`/`_PASSWORD` em `frontend/.env` apontam pra
          uma conta válida.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
        >
          Tentar de novo
        </button>
      </div>
    )
  }

  const precisaConfigurar2fa = requiresTwoFactorSetup(tokenStorage.getAccess())
  if (precisaConfigurar2fa && location.pathname !== "/2fa/configurar") {
    return <Navigate to="/2fa/configurar" replace />
  }

  return <Outlet />
}
