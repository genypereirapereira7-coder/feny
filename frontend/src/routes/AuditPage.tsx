import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Card, EmptyState, ErrorState, Input, PageHeader, Spinner, Table, Td, Th, Tr } from "../components/ui"
import { api } from "../lib/api"
import { useLookup } from "../lib/useLookup"
import type { AuditLog, PaginatedResponse, User } from "../lib/types"

// Frontend Fase 10 — Auditoria. `AuditLog` já existia e já era gravado por
// todo service de domínio crítico (ARCHITECTURE.md §15); só não tinha
// endpoint de leitura. Admin/Manager only (mesma tabela do §9).
export function AuditPage() {
  const [entityType, setEntityType] = useState("")
  const [action, setAction] = useState("")

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-logs", entityType, action],
    queryFn: async () =>
      (
        await api.get<PaginatedResponse<AuditLog>>("/audit/logs/", {
          params: { entity_type: entityType || undefined, action: action || undefined },
        })
      ).data,
  })
  const { data: usuarios } = useLookup<User>("users-lookup", "/users/", (u) => u.username)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Auditoria" />

      <div className="mb-4 flex flex-wrap gap-3">
        <div className="w-56">
          <Input
            placeholder="Filtrar por tipo (ex.: finance.charge)"
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
          />
        </div>
        <div className="w-56">
          <Input
            placeholder="Filtrar por ação (ex.: charge.issued)"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
        </div>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}

      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhum registro de auditoria encontrado." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Quando</Th>
                  <Th>Ação</Th>
                  <Th>Entidade</Th>
                  <Th>Usuário</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((registro) => (
                  <Tr key={registro.id}>
                    <Td>{new Date(registro.created_at).toLocaleString("pt-BR")}</Td>
                    <Td className="font-medium text-slate-100">{registro.action}</Td>
                    <Td className="text-xs text-slate-500">
                      {registro.entity_type}:{registro.entity_id}
                    </Td>
                    <Td>{registro.user ? (usuarios?.[registro.user] ?? "—") : "Sistema"}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}
    </div>
  )
}
