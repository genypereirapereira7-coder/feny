"""Expõe `send(notification)` pro domínio `notifications` — nada mais daqui
é chamado de fora (ARCHITECTURE.md §6.9)."""

from apps.whatsapp import client
from apps.whatsapp.exceptions import EvolutionApiError

# Só os dois gatilhos que `apps.finance` já dispara nesta fase (emissão de
# cobrança e confirmação de pagamento — ARCHITECTURE.md §10). Novos templates
# entram aqui conforme o domínio que os dispara for escrito, não antes.
_TEMPLATES = {
    "charge.issued": (
        "Olá, {customer_name}! Segue o link para pagamento do seu {charge_label} "
        "({charge_amount}): {payment_link}"
    ),
    "payment.received": (
        "Olá, {customer_name}! Confirmamos o recebimento do seu pagamento de "
        "{payment_amount}. Obrigado!"
    ),
}


def send(notification) -> None:
    modelo = _TEMPLATES.get(notification.template)
    if modelo is None:
        raise EvolutionApiError(f"Sem modelo de mensagem cadastrado para o template {notification.template!r}.")

    try:
        texto = modelo.format(**notification.context)
    except KeyError as exc:
        raise EvolutionApiError(f"Contexto incompleto pro template {notification.template!r}: falta {exc}.") from exc

    client.send_text(notification.recipient, texto)
