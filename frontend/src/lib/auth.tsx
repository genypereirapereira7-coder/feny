import axios from "axios"
import * as OTPAuth from "otpauth"
import { type ReactNode, createContext, useContext, useEffect, useState } from "react"
import { api, tokenStorage } from "./api"
import type { LoginResponse, TwoFactorSetupResponse, User } from "./types"

export class LoginError extends Error {
  requiresOtp: boolean
  constructor(message: string, requiresOtp = false) {
    super(message)
    this.requiresOtp = requiresOtp
  }
}

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  /** `requires_2fa_setup` no retorno diz se o próximo passo é configurar 2FA. */
  login: (username: string, password: string, otpCode?: string) => Promise<{ requires2faSetup: boolean }>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

/** Login automático de dev, "por enquanto" (a pedido) — completa a
 * configuração de 2FA sozinho quando o papel exige e ainda não está pronto.
 * O segredo gerado fica em `localStorage` (só deste navegador) pra logins
 * seguintes não precisarem configurar de novo — sem isso, a segunda vez
 * falharia (a conta já tem 2FA ativo, mas ninguém teria o código). Pra
 * tirar isto de vez, apague `VITE_AUTO_LOGIN_USERNAME`/`_PASSWORD` do
 * `.env` e `feny_auto_login_2fa_secret` do localStorage. */
const CHAVE_SEGREDO_2FA_AUTO = "feny_auto_login_2fa_secret"

async function autoLogin(username: string, password: string): Promise<LoginResponse> {
  const segredoSalvo = localStorage.getItem(CHAVE_SEGREDO_2FA_AUTO)
  if (segredoSalvo) {
    try {
      const codigo = new OTPAuth.TOTP({ secret: segredoSalvo }).generate()
      const resposta = await api.post<LoginResponse>("/auth/token/", { username, password, otp_code: codigo })
      return resposta.data
    } catch {
      // Segredo salvo não bate mais (ex.: alguém resetou o 2FA por fora) —
      // esquece e tenta configurar do zero abaixo.
      localStorage.removeItem(CHAVE_SEGREDO_2FA_AUTO)
    }
  }

  const primeiraTentativa = await api.post<LoginResponse>("/auth/token/", { username, password })
  if (!primeiraTentativa.data.requires_2fa_setup) {
    return primeiraTentativa.data
  }

  tokenStorage.set(primeiraTentativa.data.access, primeiraTentativa.data.refresh)
  const setup = await api.post<TwoFactorSetupResponse>("/auth/2fa/setup/")
  localStorage.setItem(CHAVE_SEGREDO_2FA_AUTO, setup.data.secret)
  const totp = new OTPAuth.TOTP({ secret: setup.data.secret })
  const confirmacao = await api.post<LoginResponse>("/auth/2fa/confirm/", { code: totp.generate() })
  return confirmacao.data
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const carregarUsuarioAtual = async () => {
    const resposta = await api.get<User>("/users/me/")
    setUser(resposta.data)
  }

  useEffect(() => {
    if (tokenStorage.getAccess()) {
      carregarUsuarioAtual().finally(() => setIsLoading(false))
      return
    }

    // Login automático temporário ("por enquanto", a pedido) — só entra em
    // ação se as duas variáveis estiverem configuradas em `.env` (nunca
    // commitadas). Tirar depois é só apagar essas duas linhas do `.env`.
    const usernameAuto = import.meta.env.VITE_AUTO_LOGIN_USERNAME
    const passwordAuto = import.meta.env.VITE_AUTO_LOGIN_PASSWORD
    if (usernameAuto && passwordAuto) {
      autoLogin(usernameAuto, passwordAuto)
        .then(async (resposta) => {
          tokenStorage.set(resposta.access, resposta.refresh)
          await carregarUsuarioAtual()
        })
        .catch((erro) => {
          // Nunca trava a tela em branco por causa disto — se o login
          // automático falhar por qualquer motivo, cai de volta pra tela de
          // login normal, como se a variável nem estivesse configurada.
          console.warn("Login automático falhou, mostrando tela de login normal.", erro)
        })
        .finally(() => setIsLoading(false))
      return
    }

    setIsLoading(false)
  }, [])

  useEffect(() => {
    const aoExpirar = () => setUser(null)
    window.addEventListener("feny:auth-expired", aoExpirar)
    return () => window.removeEventListener("feny:auth-expired", aoExpirar)
  }, [])

  const login = async (username: string, password: string, otpCode?: string) => {
    try {
      const resposta = await api.post<LoginResponse>("/auth/token/", {
        username,
        password,
        ...(otpCode ? { otp_code: otpCode } : {}),
      })
      tokenStorage.set(resposta.data.access, resposta.data.refresh)
      await carregarUsuarioAtual()
      return { requires2faSetup: resposta.data.requires_2fa_setup }
    } catch (erro: unknown) {
      const dados = axios.isAxiosError<{ detail?: string; requires_otp?: boolean }>(erro)
        ? erro.response?.data
        : undefined
      if (dados?.requires_otp) {
        throw new LoginError(dados.detail ?? "Código de autenticação em duas etapas necessário.", true)
      }
      throw new LoginError(dados?.detail ?? "Usuário ou senha inválidos.")
    }
  }

  const logout = () => {
    tokenStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser: carregarUsuarioAtual }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth precisa estar dentro de <AuthProvider>")
  return context
}
