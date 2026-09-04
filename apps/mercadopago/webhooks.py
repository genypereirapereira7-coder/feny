"""Recebe e valida eventos do Mercado Pago (ARCHITECTURE.md §6.8, §10).

Fluxo, na ordem (spec técnica): receber → validar → registrar
(`ExternalWebhookEvent`) → checar duplicata → confirmar com o provedor →
atualizar estado → auditar → responder. Fora de `/api/v1/` de propósito —
webhook de provedor externo tem o contrato do provedor, não o nosso (§12).
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.models import ExternalWebhookEvent
from apps.core.exceptions import DomainError
from apps.finance import services as finance_services
from apps.finance.models import Charge, ChargeStatus
from apps.mercadopago import adapter, client
from apps.mercadopago.exceptions import MercadoPagoError

_TIPOS_RELEVANTES = {"payment"}


class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    # Rate limiting (§13) — por IP, já que não há usuário autenticado aqui.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mercadopago-webhook"

    def post(self, request):
        tipo = request.data.get("type") or request.query_params.get("type", "")
        data_id = (request.data.get("data") or {}).get("id") or request.query_params.get("data.id", "")

        if not data_id:
            return Response(status=200)

        try:
            with transaction.atomic():
                evento = ExternalWebhookEvent.objects.create(
                    provider="mercadopago", external_event_id=str(data_id),
                    event_type=tipo or "unknown", payload=request.data,
                )
        except IntegrityError:
            # Já existe — o mesmo evento sendo reprocessado. Idempotência de
            # banco (§8.3.1), encerra sem tratar isso como erro.
            return Response(status=200)

        if tipo not in _TIPOS_RELEVANTES:
            evento.status = ExternalWebhookEvent.Status.IGNORED
            evento.save(update_fields=["status", "updated_at"])
            return Response(status=200)

        self._processar_pagamento(evento, data_id)
        return Response(status=200)

    def _processar_pagamento(self, evento: ExternalWebhookEvent, payment_id) -> None:
        evento.attempts += 1
        try:
            pagamento_mp = client.get_payment(payment_id)
        except MercadoPagoError as exc:
            evento.status = ExternalWebhookEvent.Status.FAILED
            evento.error = str(exc)
            evento.save(update_fields=["status", "error", "attempts", "updated_at"])
            return

        referencia = pagamento_mp.get("external_reference")
        charge = Charge.objects.filter(id=referencia).first() if referencia else None
        if charge is None:
            evento.status = ExternalWebhookEvent.Status.FAILED
            evento.error = f"Nenhuma Charge encontrada para external_reference={referencia!r}."
            evento.save(update_fields=["status", "error", "attempts", "updated_at"])
            return

        status_mapeado = adapter.map_status(pagamento_mp.get("status", ""))

        if status_mapeado == ChargeStatus.PAID:
            data_aprovacao = parse_datetime(pagamento_mp.get("date_approved") or "") or timezone.now()
            try:
                with transaction.atomic():
                    finance_services.confirm_payment(
                        charge, None,
                        external_id=str(pagamento_mp["id"]),
                        amount=Decimal(str(pagamento_mp.get("transaction_amount", charge.amount))),
                        method=pagamento_mp.get("payment_method_id", ""),
                        paid_at=data_aprovacao,
                        raw_payload=pagamento_mp,
                    )
            except DomainError as exc:
                evento.status = ExternalWebhookEvent.Status.FAILED
                evento.error = str(exc)
                evento.save(update_fields=["status", "error", "attempts", "updated_at"])
                return

        evento.status = ExternalWebhookEvent.Status.PROCESSED
        evento.processed_at = timezone.now()
        evento.save(update_fields=["status", "processed_at", "attempts", "updated_at"])
