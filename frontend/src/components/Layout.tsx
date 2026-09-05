import {
  Banknote,
  Briefcase,
  ChevronDown,
  FileStack,
  FileText,
  History,
  LayoutDashboard,
  LifeBuoy,
  LineChart,
  LogOut,
  Percent,
  Receipt,
  Repeat,
  Settings,
  TrendingUp,
  UserCog,
  Users,
} from "lucide-react"
import { useState } from "react"
import { NavLink, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "../lib/auth"
import type { Role } from "../lib/types"

const NOME_PAPEL: Record<Role, string> = {
  ADMIN: "Administrador",
  MANAGER: "Gerente/Dono",
  SALES: "Vendedor",
  DEVELOPER: "Desenvolvedor",
  FINANCE: "Financeiro",
  SUPPORT: "Suporte",
}

const TITULO_ROTA: Record<string, string> = {
  "/": "Dashboard",
  "/clientes": "Clientes",
  "/orcamentos": "Orçamentos",
  "/projetos": "Projetos",
  "/financeiro/cobrancas": "Contas a receber",
  "/financeiro/receitas": "Receitas",
  "/financeiro/fluxo-de-caixa": "Fluxo de caixa",
  "/financeiro/despesas": "Despesas",
  "/financeiro/assinaturas": "Recorrências",
  "/financeiro/comissoes": "Comissões",
  "/documentos": "Documentos",
  "/suporte": "Suporte",
  "/equipe": "Equipe",
  "/configuracoes": "Configurações",
  "/auditoria": "Auditoria",
}

interface ItemNav {
  to: string
  label: string
  icon: typeof Users
  roles?: Role[]
}
interface GrupoNav {
  label: string
  itens: ItemNav[]
}

// Espelha a matriz de permissões da ARCHITECTURE.md §9 — quem não tem acesso
// a um domínio nem vê o link (a proteção de verdade é sempre o backend).
// Só entram aqui telas que existem de verdade — nada de link morto (spec de
// frontend §93).
const GRUPOS_NAV: GrupoNav[] = [
  { label: "", itens: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }] },
  {
    label: "Comercial",
    itens: [
      { to: "/clientes", label: "Clientes", icon: Users },
      { to: "/orcamentos", label: "Orçamentos", icon: FileText },
    ],
  },
  { label: "Projetos", itens: [{ to: "/projetos", label: "Projetos", icon: Briefcase }] },
  {
    label: "Financeiro",
    itens: [
      { to: "/financeiro/cobrancas", label: "Contas a receber", icon: Receipt, roles: ["ADMIN", "MANAGER", "FINANCE"] },
      { to: "/financeiro/receitas", label: "Receitas", icon: TrendingUp, roles: ["ADMIN", "MANAGER", "FINANCE"] },
      { to: "/financeiro/fluxo-de-caixa", label: "Fluxo de caixa", icon: LineChart, roles: ["ADMIN", "MANAGER", "FINANCE"] },
      { to: "/financeiro/despesas", label: "Despesas", icon: Banknote, roles: ["ADMIN", "MANAGER", "FINANCE"] },
      { to: "/financeiro/assinaturas", label: "Recorrências", icon: Repeat, roles: ["ADMIN", "MANAGER", "FINANCE"] },
      {
        to: "/financeiro/comissoes",
        label: "Comissões",
        icon: Percent,
        roles: ["ADMIN", "MANAGER", "FINANCE", "SALES"],
      },
    ],
  },
  {
    label: "Sistema",
    itens: [
      { to: "/documentos", label: "Documentos", icon: FileStack },
      { to: "/suporte", label: "Suporte", icon: LifeBuoy, roles: ["ADMIN", "MANAGER", "SUPPORT"] },
      { to: "/equipe", label: "Equipe", icon: UserCog, roles: ["ADMIN", "MANAGER"] },
      { to: "/auditoria", label: "Auditoria", icon: History, roles: ["ADMIN", "MANAGER"] },
      { to: "/configuracoes", label: "Configurações", icon: Settings, roles: ["ADMIN"] },
    ],
  },
]

export function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [menuAberto, setMenuAberto] = useState(false)

  const grupos = GRUPOS_NAV.map((grupo) => ({
    ...grupo,
    itens: grupo.itens.filter((item) => !item.roles || (user && item.roles.includes(user.role))),
  })).filter((grupo) => grupo.itens.length > 0)

  const tituloPagina = TITULO_ROTA[location.pathname] ?? "Feny"

  return (
    <div className="flex min-h-screen bg-slate-950">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-900/40 px-3 py-4">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
            F
          </div>
          <span className="text-base font-semibold text-slate-100">Feny</span>
        </div>

        <nav className="flex-1 space-y-4">
          {grupos.map((grupo) => (
            <div key={grupo.label || "root"}>
              {grupo.label && (
                <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                  {grupo.label}
                </p>
              )}
              <div className="space-y-0.5">
                {grupo.itens.map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === "/"}
                      className={({ isActive }) =>
                        `flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                          isActive ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800"
                        }`
                      }
                    >
                      <Icon size={16} strokeWidth={2} />
                      {item.label}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
          <h1 className="text-sm font-medium text-slate-300">{tituloPagina}</h1>

          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuAberto((atual) => !atual)}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            >
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-700 text-xs font-medium text-slate-200">
                {(user?.first_name || user?.username || "?").charAt(0).toUpperCase()}
              </div>
              {user?.first_name || user?.username}
              <ChevronDown size={14} />
            </button>

            {menuAberto && (
              <>
                <button
                  type="button"
                  className="fixed inset-0 z-10 cursor-default"
                  aria-label="Fechar menu"
                  onClick={() => setMenuAberto(false)}
                />
                <div className="absolute right-0 z-20 mt-1 w-56 rounded-md border border-slate-800 bg-slate-900 py-1 shadow-lg">
                  <div className="border-b border-slate-800 px-3 py-2">
                    <p className="text-sm text-slate-100">{user?.first_name || user?.username}</p>
                    <p className="text-xs text-slate-500">{user?.email || "—"}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{user && NOME_PAPEL[user.role]}</p>
                  </div>
                  <button
                    type="button"
                    onClick={logout}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-400 hover:bg-slate-800"
                  >
                    <LogOut size={15} /> Sair
                  </button>
                </div>
              </>
            )}
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}