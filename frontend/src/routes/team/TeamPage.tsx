import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import {
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
  Tr,
} from "../../components/ui"
import { api } from "../../lib/api"
import { useAuth } from "../../lib/auth"
import { extrairMensagemErro, useToast } from "../../lib/toast"
import type { PaginatedResponse, Role, User } from "../../lib/types"

const NOME_PAPEL: Record<Role, string> = {
  ADMIN: "Administrador",
  MANAGER: "Gerente/Dono",
  SALES: "Vendedor",
  DEVELOPER: "Desenvolvedor",
  FINANCE: "Financeiro",
  SUPPORT: "Suporte",
}

// Frontend Fase 9 — administração de contas (apps/users, já existia por
// completo desde a Fase 1 do backend: create/update/reset-2fa). Escrita é
// ADMIN-only (UserPermission); Manager só vê, o resto não chega aqui.
export function TeamPage() {
  const { user } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [modalNovo, setModalNovo] = useState(false)
  const [modalEditar, setModalEditar] = useState<User | null>(null)
  const [confirmReset, setConfirmReset] = useState<User | null>(null)

  const podeAdministrar = user?.role === "ADMIN"

  const { data, isLoading, isError } = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get<PaginatedResponse<User>>("/users/")).data,
  })

  const alternarAtivo = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/users/${id}/`, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      toast.success("Conta atualizada.")
    },
    onError: (erro: unknown) => toast.error(extrairMensagemErro(erro, "Não foi possível atualizar a conta.")),
  })

  const resetar2fa = useMutation({
    mutationFn: (id: string) => api.post(`/users/${id}/reset-2fa/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      toast.success("2FA resetado — a pessoa configura de novo no próximo login.")
    },
    onError: () => toast.error("Não foi possível resetar o 2FA."),
  })

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Equipe"
        actions={podeAdministrar && <Button onClick={() => setModalNovo(true)}>Nova conta</Button>}
      />

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhuma conta ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Usuário</Th>
                  <Th>Papel</Th>
                  <Th>2FA</Th>
                  <Th>Status</Th>
                  {podeAdministrar && <Th>Ações</Th>}
                </tr>
              </thead>
              <tbody>
                {data.results.map((pessoa) => (
                  <Tr key={pessoa.id}>
                    <Td className="font-medium text-slate-100">
                      {pessoa.first_name || pessoa.last_name ? `${pessoa.first_name} ${pessoa.last_name}`.trim() : pessoa.username}
                      <p className="text-xs text-slate-500">{pessoa.email || pessoa.username}</p>
                    </Td>
                    <Td>{NOME_PAPEL[pessoa.role]}</Td>
                    <Td>{pessoa.two_factor_enabled ? "Ativo" : "Não configurado"}</Td>
                    <Td>
                      <span className={pessoa.is_active ? "text-emerald-400" : "text-slate-500"}>
                        {pessoa.is_active ? "Ativo" : "Inativo"}
                      </span>
                    </Td>
                    {podeAdministrar && (
                      <Td>
                        <div className="flex flex-wrap gap-2">
                          <Button variant="secondary" onClick={() => setModalEditar(pessoa)}>
                            Editar
                          </Button>
                          <Button
                            variant="ghost"
                            disabled={alternarAtivo.isPending}
                            onClick={() => alternarAtivo.mutate({ id: pessoa.id, is_active: !pessoa.is_active })}
                          >
                            {pessoa.is_active ? "Desativar" : "Reativar"}
                          </Button>
                          {pessoa.two_factor_enabled && (
                            <Button variant="ghost" onClick={() => setConfirmReset(pessoa)}>
                              Resetar 2FA
                            </Button>
                          )}
                        </div>
                      </Td>
                    )}
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {modalNovo && <ContaModal onClose={() => setModalNovo(false)} />}
      {modalEditar && <ContaModal usuario={modalEditar} onClose={() => setModalEditar(null)} />}
      {confirmReset && (
        <ConfirmDialog
          title="Resetar o 2FA desta conta?"
          description={
            <>
              {confirmReset.username} vai precisar configurar o autenticador de novo no próximo login. Use isto só
              se a pessoa perdeu o dispositivo.
            </>
          }
          confirmLabel="Resetar 2FA"
          danger
          loading={resetar2fa.isPending}
          onClose={() => setConfirmReset(null)}
          onConfirm={() => {
            resetar2fa.mutate(confirmReset.id)
            setConfirmReset(null)
          }}
        />
      )}
    </div>
  )
}

function ContaModal({ usuario, onClose }: { usuario?: User; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [username, setUsername] = useState(usuario?.username ?? "")
  const [email, setEmail] = useState(usuario?.email ?? "")
  const [firstName, setFirstName] = useState(usuario?.first_name ?? "")
  const [lastName, setLastName] = useState(usuario?.last_name ?? "")
  const [role, setRole] = useState<Role>(usuario?.role ?? "SALES")
  const [password, setPassword] = useState("")
  const [erro, setErro] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => {
      const dados: Record<string, unknown> = {
        username, email, first_name: firstName, last_name: lastName, role,
      }
      if (password) dados.password = password
      return usuario ? api.patch(`/users/${usuario.id}/`, dados) : api.post("/users/", dados)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      onClose()
    },
    onError: (erroRequisicao: unknown) => {
      const dados = (erroRequisicao as { response?: { data?: Record<string, unknown> } })?.response?.data
      setErro(dados ? String(Object.values(dados).flat()[0]) : "Não foi possível salvar a conta.")
    },
  })

  return (
    <Modal title={usuario ? "Editar conta" : "Nova conta"} onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          setErro(null)
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <Field label="Usuário">
          <Input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </Field>
        <Field label="E-mail">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Nome">
            <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </Field>
          <Field label="Sobrenome">
            <Input value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </Field>
        </div>
        <Field label="Papel">
          <Select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {Object.entries({
              ADMIN: "Administrador", MANAGER: "Gerente/Dono", SALES: "Vendedor",
              DEVELOPER: "Desenvolvedor", FINANCE: "Financeiro", SUPPORT: "Suporte",
            }).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={usuario ? "Nova senha (deixe em branco pra manter)" : "Senha"}>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={10}
            required={!usuario}
          />
        </Field>

        {erro && <p className="text-sm text-red-400">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
