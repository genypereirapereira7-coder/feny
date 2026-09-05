// O backend sempre manda valor monetário como string decimal ("3000.00") —
// nunca number, pra não arredondar por engano em ponto flutuante em
// nenhuma etapa (ARCHITECTURE.md §8.4). Formatar é só exibição.
export function formatBRL(valor: string): string {
  const numero = Number(valor)
  if (Number.isNaN(numero)) return valor
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}
