class MercadoPagoError(Exception):
    """Falha ao falar com a API do Mercado Pago (rede, HTTP não-2xx, resposta
    inesperada). Não é `DomainError` — não é a regra de negócio que recusou,
    é a integração externa que falhou (ARCHITECTURE.md §21: diferenciar "a
    regra recusou" de "o código/dependência externa quebrou")."""
