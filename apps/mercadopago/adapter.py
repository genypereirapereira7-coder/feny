"""Traduz `Charge`/`ChargeStatus` internos ↔ formato do Mercado Pago
(ARCHITECTURE.md §6.8, §10). Quem sabe o que é um "Mercado Pago payment_id"
é só aqui — `apps.finance` só enxerga `external_id`/`payment_link` genéricos."""

import hashlib
import hmac

from apps.finance.models import ChargeStatus
from apps.mercadopago import client

# Status reais que a API do Mercado Pago devolve pra um `payment`
# (https://www.mercadopago.com.br/developers — não é lista inventada).
_MAPA_STATUS = {
    "approved": ChargeStatus.PAID,
    "pending": ChargeStatus.PENDING,
    "in_process": ChargeStatus.PROCESSING,
    "authorized": ChargeStatus.PROCESSING,
    "cancelled": ChargeStatus.CANCELLED,
    "refunded": ChargeStatus.FAILED,
    "charged_back": ChargeStatus.FAILED,
    "rejected": ChargeStatus.FAILED,
}


def map_status(mp_status: str) -> ChargeStatus:
    """Nunca copia o status do provedor direto pro domínio (§10) — passa por
    esta tabela, então o domínio preserva a própria semântica mesmo se o
    Mercado Pago adicionar um status novo (cai em `FAILED`, o mais seguro:
    não confirma pagamento por omissão)."""
    return _MAPA_STATUS.get(mp_status, ChargeStatus.FAILED)


def create_charge_preference(charge) -> dict:
    """Cria a preferência de pagamento pra uma `Charge` já existente e devolve
    `{"external_id": ..., "payment_link": ...}` — quem persiste isso na
    `Charge` é `apps.finance.services.issue_charge`, não aqui."""
    resposta = client.create_preference(
        external_reference=str(charge.id),
        description=f"{charge.get_charge_type_display()} — {charge.customer.legal_name}",
        amount=charge.amount,
    )
    return {"external_id": resposta["id"], "payment_link": resposta.get("init_point", "")}


def verify_signature(*, data_id: str, x_signature: str, x_request_id: str, secret: str) -> bool:
    """Esquema `x-signature` do Mercado Pago: `ts=<epoch>,v1=<hmac-sha256>`
    sobre o manifesto `id:<data_id>;request-id:<x_request_id>;ts:<ts>;`.

    Camada extra, opcional (só roda se `MERCADOPAGO_WEBHOOK_SECRET` estiver
    configurado) — a proteção que não é opcional é `client.get_payment` no
    processador do webhook: mesmo uma assinatura válida nunca é motivo pra
    dar baixa financeira sem confirmar direto na API (§10)."""
    partes = dict(par.split("=", 1) for par in x_signature.split(",") if "=" in par)
    ts, v1 = partes.get("ts"), partes.get("v1")
    if not ts or not v1:
        return False

    manifesto = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    esperado = hmac.new(secret.encode(), manifesto.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, v1)
