/** Raiz do sistema interno. O site institucional ocupa `/`, então todas as
 * telas do painel vivem sob este prefixo (ver `App.tsx`).
 *
 * Mora num módulo próprio, e não dentro de `App.tsx`, de propósito: `Layout`
 * precisa da constante pra montar o menu e o `App` importa o `Layout` — se a
 * constante ficasse lá, as duas se importariam em círculo e `PAINEL` seria
 * `undefined` na hora em que o menu é construído (o módulo do `App` ainda não
 * teria terminado de executar).
 */
export const PAINEL = "/painel"
