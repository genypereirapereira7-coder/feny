import { QRCodeSVG } from "qrcode.react"
import { type FormEvent, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { PAINEL } from "../lib/rotas"
import { Button, Field, Input, Spinner } from "../components/ui"
import { api, tokenStorage } from "../lib/api"
import { useAuth } from "../lib/auth"
import type { LoginResponse, TwoFactorSetupResponse } from "../lib/types"

/** ARCHITECTURE.md §13: obrigatório pra ADMIN/MANAGER/FINANCE. Chega aqui
 * tanto por ser forçado no primeiro login quanto por escolha, então não
 * assume de onde veio. */
export function TwoFactorSetupPage() {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()

  const [dados, setDados] = useState<TwoFactorSetupResponse | null>(null)
  const [codigo, setCodigo] = useState("")
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api.post<TwoFactorSetupResponse>("/auth/2fa/setup/").then((resposta) => setDados(resposta.data))
  }, [])

  const aoConfirmar = async (evento: FormEvent) => {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const resposta = await api.post<LoginResponse>("/auth/2fa/confirm/", { code: codigo })
      tokenStorage.set(resposta.data.access, resposta.data.refresh)
      await refreshUser()
      navigate(PAINEL, { replace: true })
    } catch {
      setErro("Código inválido. Confira o horário do celular e tente de novo.")
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm rounded-lg border border-slate-800 bg-slate-900 p-8">
        <h1 className="mb-2 text-xl font-semibold text-slate-100">Configurar autenticação em duas etapas</h1>
        <p className="mb-6 text-sm text-slate-400">
          Obrigatório pro seu papel. Escaneie o QR code com um app autenticador (Google Authenticator, Authy...).
        </p>

        {!dados ? (
          <Spinner />
        ) : (
          <>
            <div className="mb-4 flex justify-center rounded-md bg-white p-3">
              <QRCodeSVG value={dados.otpauth_url} size={180} />
            </div>
            <p className="mb-6 break-all text-center text-xs text-slate-500">
              Não consegue escanear? Digite manualmente: <span className="font-mono text-slate-400">{dados.secret}</span>
            </p>

            <form onSubmit={aoConfirmar}>
              <div className="mb-4">
                <Field label="Código de 6 dígitos do app">
                  <Input
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value)}
                    inputMode="numeric"
                    maxLength={6}
                    className="tracking-widest"
                    autoFocus
                    required
                  />
                </Field>
              </div>
              {erro && <p className="mb-4 text-sm text-red-400">{erro}</p>}
              <Button type="submit" disabled={enviando} className="w-full">
                {enviando ? "Confirmando…" : "Confirmar e ativar"}
              </Button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
