import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Download, Upload } from "lucide-react"
import { type FormEvent, useState } from "react"
import { api } from "../lib/api"
import { extrairMensagemErro, useToast } from "../lib/toast"
import type { DocumentCategory, DocumentFile, PaginatedResponse } from "../lib/types"
import { Button, Card, EmptyState, ErrorState, Field, Select, Spinner, Table, Td, Th, Tr } from "./ui"

const ROTULO_CATEGORIA: Record<DocumentCategory, string> = {
  CONTRACT: "Contrato",
  INVOICE: "Nota fiscal",
  RECEIPT: "Comprovante",
  PROJECT_FILE: "Arquivo de projeto",
  OTHER: "Outro",
}

function formatarTamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Aba/painel de documentos (spec de frontend §21, §26, §42-44) — reusado na
 * tela de cliente e na de projeto, só troca qual FK é enviada/filtrada. */
export function DocumentsPanel({ customerId, projectId }: { customerId?: string; projectId?: string }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [categoria, setCategoria] = useState<DocumentCategory>("OTHER")
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const chaveConsulta = ["documents", customerId, projectId]

  const { data, isLoading, isError } = useQuery({
    queryKey: chaveConsulta,
    queryFn: async () =>
      (
        await api.get<PaginatedResponse<DocumentFile>>("/documents/", {
          params: { customer: customerId, project: projectId },
        })
      ).data,
  })

  const upload = useMutation({
    mutationFn: () => {
      const formData = new FormData()
      if (customerId) formData.append("customer", customerId)
      if (projectId) formData.append("project", projectId)
      formData.append("category", categoria)
      formData.append("file", arquivo as File)
      return api.post("/documents/", formData, { headers: { "Content-Type": "multipart/form-data" } })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chaveConsulta })
      toast.success("Documento enviado.")
      setArquivo(null)
    },
    onError: (erro: unknown) => setErro(extrairMensagemErro(erro, "Não foi possível enviar o arquivo.")),
  })

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            setErro(null)
            if (arquivo) upload.mutate()
          }}
          className="flex flex-wrap items-end gap-3"
        >
          <div className="w-48">
            <Field label="Categoria">
              <Select value={categoria} onChange={(e) => setCategoria(e.target.value as DocumentCategory)}>
                {Object.entries(ROTULO_CATEGORIA).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="flex-1">
            <Field label="Arquivo">
              <input
                type="file"
                onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-1.5 file:text-sm file:text-slate-200"
              />
            </Field>
          </div>
          <Button type="submit" disabled={!arquivo || upload.isPending}>
            <Upload size={14} className="mr-1 inline" />
            {upload.isPending ? "Enviando…" : "Enviar"}
          </Button>
        </form>
        {erro && <p className="mt-2 text-sm text-red-400">{erro}</p>}
      </Card>

      {isLoading && <Spinner />}
      {isError && <ErrorState />}
      {data && (
        <Card>
          {data.results.length === 0 ? (
            <EmptyState message="Nenhum documento enviado ainda." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Arquivo</Th>
                  <Th>Categoria</Th>
                  <Th>Tamanho</Th>
                  <Th>Enviado em</Th>
                  <Th>Ações</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((documento) => (
                  <Tr key={documento.id}>
                    <Td className="font-medium text-slate-100">{documento.original_filename}</Td>
                    <Td>{ROTULO_CATEGORIA[documento.category]}</Td>
                    <Td>{formatarTamanho(documento.size_bytes)}</Td>
                    <Td>{new Date(documento.created_at).toLocaleDateString("pt-BR")}</Td>
                    <Td>
                      <a
                        href={documento.file}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-xs text-indigo-400 hover:underline"
                      >
                        <Download size={12} /> Baixar
                      </a>
                    </Td>
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
