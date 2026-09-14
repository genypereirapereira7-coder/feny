import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"

const ACCESS_KEY = "feny_access"
const REFRESH_KEY = "feny_refresh"

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  setAccess: (access: string) => localStorage.setItem(ACCESS_KEY, access),
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api = axios.create({ baseURL: API_BASE_URL })

/** Cliente sem token e sem interceptador, pro site institucional (público).
 * O `api` acima anexa o Bearer e, num 401, tenta renovar a sessão e dispara
 * `feny:auth-expired` — comportamento certo dentro do painel e errado numa
 * página que qualquer visitante abre: um erro no formulário de contato não
 * pode derrubar a sessão de quem por acaso esteja logado na mesma aba. */
export const apiPublica = axios.create({ baseURL: API_BASE_URL })

api.interceptors.request.use((config) => {
  const access = tokenStorage.getAccess()
  if (access) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

// Um 401 que não seja do próprio /auth/token/ tenta renovar o access token
// uma vez (refresh nunca é gasto duas vezes pra mesma falha — ver
// SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] no backend). Se o refresh também
// falhar, avisa o resto do app que a sessão morreu, sem tentar de novo.
let refreshing: Promise<string | null> | null = null

async function renovarToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) return null

  if (!refreshing) {
    refreshing = axios
      .post(`${API_BASE_URL}/auth/token/refresh/`, { refresh })
      .then((resposta) => {
        tokenStorage.setAccess(resposta.data.access)
        return resposta.data.access as string
      })
      .catch(() => null)
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

api.interceptors.response.use(
  (resposta) => resposta,
  async (erro: AxiosError) => {
    const original = erro.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const ehLogin = original?.url?.includes("/auth/token/")

    if (erro.response?.status === 401 && original && !original._retry && !ehLogin) {
      original._retry = true
      const novoAccess = await renovarToken()
      if (novoAccess) {
        original.headers.Authorization = `Bearer ${novoAccess}`
        return api(original)
      }
      tokenStorage.clear()
      window.dispatchEvent(new Event("feny:auth-expired"))
    }

    return Promise.reject(erro)
  },
)
