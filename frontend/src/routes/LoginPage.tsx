import { Eye, EyeOff } from "lucide-react"
import { type FormEvent, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button, Field, Input } from "../components/ui"
import { LoginError, useAuth } from "../lib/auth"

// Conta única deste sistema — sem tela de escolher usuário, só senha
// (a pedido). Se um dia mais de uma pessoa precisar de conta própria, é só
// voltar a pedir usuário aqui; o backend já suporta isso sem mudança nenhuma.
const USUARIO_UNICO = "gerente"

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [password, setPassword] = useState("")
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [otpCode, setOtpCode] = useState("")
  const [precisaDeOtp, setPrecisaDeOtp] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const aoSubmeter = async (evento: FormEvent) => {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const { requires2faSetup } = await login(USUARIO_UNICO, password, precisaDeOtp ? otpCode : undefined)
      navigate(requires2faSetup ? "/2fa/configurar" : "/", { replace: true })
    } catch (e) {
      if (e instanceof LoginError) {
        setErro(e.message)
        if (e.requiresOtp) setPrecisaDeOtp(true)
      } else {
        setErro("Não foi possível entrar. Tente de novo.")
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <form onSubmit={aoSubmeter} className="w-full max-w-sm rounded-lg border border-slate-800 bg-slate-900 p-8">
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
            F
          </div>
          <h1 className="text-xl font-semibold text-slate-100">Feny</h1>
        </div>

        <div className="mb-4">
          <Field label="Senha">
            <div className="relative">
              <Input
                type={mostrarSenha ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                disabled={precisaDeOtp}
                className="pr-10"
                autoFocus
                required
              />
              <button
                type="button"
                onClick={() => setMostrarSenha((atual) => !atual)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 hover:text-slate-300"
                tabIndex={-1}
                aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
              >
                {mostrarSenha ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </Field>
        </div>

        {precisaDeOtp && (
          <div className="mb-4">
            <Field label="Código do app autenticador">
              <Input
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                inputMode="numeric"
                maxLength={6}
                className="tracking-widest"
                autoFocus
                required
              />
            </Field>
          </div>
        )}

        {erro && <p className="mb-4 text-sm text-red-400">{erro}</p>}

        <Button type="submit" disabled={enviando} className="w-full">
          {enviando ? "Entrando…" : "Entrar"}
        </Button>

        <p className="mt-4 text-center text-xs text-slate-500">
          Esqueceu a senha? A redefinição ainda não é self-service.
        </p>
      </form>
    </div>
  )
}
