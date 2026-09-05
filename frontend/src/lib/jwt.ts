/** Só lê o payload (não confere assinatura — o backend já validou isso; aqui
 * é só pra decidir navegação no cliente, nunca pra decisão de autorização de
 * verdade). JWT não é criptografado, só assinado — ler o payload no cliente
 * é seguro e comum. */
export function requiresTwoFactorSetup(accessToken: string | null): boolean {
  if (!accessToken) return false
  try {
    const payloadBase64 = accessToken.split(".")[1]
    const payload = JSON.parse(atob(payloadBase64.replace(/-/g, "+").replace(/_/g, "/")))
    return Boolean(payload.requires_2fa_setup)
  } catch {
    return false
  }
}
