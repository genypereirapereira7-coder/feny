import { useQuery } from "@tanstack/react-query"
import { api } from "./api"
import type { PaginatedResponse } from "./types"

/** Busca todas as páginas de um recurso e monta um mapa id -> rótulo, pra
 * telas que só têm o UUID de uma FK (cliente, vendedor...) e precisam
 * mostrar um nome legível. Segue `next` até acabar — em volume baixo (o
 * caso de uso interno da Feny) isso é poucas requisições, não um problema
 * de performance real. */
export function useLookup<T>(
  chave: string,
  caminho: string,
  extrairRotulo: (item: T) => string,
) {
  return useQuery({
    queryKey: ["lookup", chave],
    queryFn: async () => {
      const mapa: Record<string, string> = {}
      let proximo: string | null = caminho
      while (proximo) {
        const resposta: { data: PaginatedResponse<T & { id: string }> } = await api.get(proximo)
        for (const item of resposta.data.results) {
          mapa[item.id] = extrairRotulo(item)
        }
        proximo = resposta.data.next
      }
      return mapa
    },
    staleTime: 60_000,
  })
}

/** Igual a `useLookup`, mas guarda o objeto inteiro em vez de só um rótulo —
 * pra telas que precisam de mais de um campo (ex.: nome E telefone do
 * cliente pro botão de WhatsApp). */
export function useLookupObjects<T extends { id: string }>(chave: string, caminho: string) {
  return useQuery({
    queryKey: ["lookup-objects", chave],
    queryFn: async () => {
      const mapa: Record<string, T> = {}
      let proximo: string | null = caminho
      while (proximo) {
        const resposta: { data: PaginatedResponse<T> } = await api.get(proximo)
        for (const item of resposta.data.results) {
          mapa[item.id] = item
        }
        proximo = resposta.data.next
      }
      return mapa
    },
    staleTime: 60_000,
  })
}
