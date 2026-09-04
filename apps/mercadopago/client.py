"""Única camada que fala HTTP com o Mercado Pago de verdade
(ARCHITECTURE.md §10: "Nenhuma chamada HTTP ao Mercado Pago fora de
`apps/mercadopago/`"). Não sabe nada de `Charge`/`Payment` — isso é trabalho
de `adapter.py`."""

import requests
from django.conf import settings

from apps.mercadopago.exceptions import MercadoPagoError

_TIMEOUT_SEGUNDOS = 10


def _access_token() -> str:
    token = settings.MERCADOPAGO_ACCESS_TOKEN
    if not token:
        raise MercadoPagoError("MERCADOPAGO_ACCESS_TOKEN não está configurado neste ambiente.")
    return token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"}


def create_preference(*, external_reference: str, description: str, amount, back_urls: dict | None = None) -> dict:
    """POST /checkout/preferences — devolve o payload cru do Mercado Pago
    (tem `id` da preferência e `init_point`, o link de pagamento)."""
    corpo = {
        "external_reference": external_reference,
        "items": [{"title": description, "quantity": 1, "unit_price": float(amount), "currency_id": "BRL"}],
    }
    if back_urls:
        corpo["back_urls"] = back_urls

    try:
        resposta = requests.post(
            f"{settings.MERCADOPAGO_BASE_URL}/checkout/preferences",
            json=corpo, headers=_headers(), timeout=_TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.RequestException as exc:
        raise MercadoPagoError(f"Falha de rede ao criar preferência no Mercado Pago: {exc}") from exc

    if not resposta.ok:
        raise MercadoPagoError(f"Mercado Pago recusou a criação da preferência: {resposta.status_code} {resposta.text}")
    return resposta.json()


def get_payment(payment_id: str) -> dict:
    """GET /v1/payments/{id} — a única fonte de verdade sobre o status real
    de um pagamento; o webhook nunca confia no que o payload dele mesmo diz."""
    try:
        resposta = requests.get(
            f"{settings.MERCADOPAGO_BASE_URL}/v1/payments/{payment_id}",
            headers=_headers(), timeout=_TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.RequestException as exc:
        raise MercadoPagoError(f"Falha de rede ao consultar pagamento {payment_id} no Mercado Pago: {exc}") from exc

    if not resposta.ok:
        raise MercadoPagoError(f"Mercado Pago recusou a consulta do pagamento {payment_id}: {resposta.status_code} {resposta.text}")
    return resposta.json()
