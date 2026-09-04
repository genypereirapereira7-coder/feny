"""Ações de domínio do orçamento.

Nenhuma delas é "mudar um campo" — cada uma valida a transição, aplica a
mudança e grava auditoria, na ordem certa. A regra mais importante daqui —
quem vendeu não decide o próprio orçamento — vive só aqui, não em
serializer nem em permissão de view, porque é regra de negócio, não controle
de acesso (ARCHITECTURE.md §7.1, §11, §75).
"""

from django.utils import timezone

from apps.audit.services import record
from apps.core.exceptions import DomainError
from apps.quotations.models import Quotation, QuotationStatus


def submit_for_approval(quotation: Quotation, actor) -> Quotation:
    if quotation.status != QuotationStatus.DRAFT:
        raise DomainError("Só um orçamento em rascunho pode ser enviado para aprovação.")

    estado_anterior = quotation.status
    quotation.status = QuotationStatus.PENDING_APPROVAL
    quotation.save(update_fields=["status", "updated_at"])

    record(
        user=actor, action="quotation.submitted", entity=quotation,
        before={"status": estado_anterior}, after={"status": quotation.status},
    )
    return quotation


def approve_quotation(quotation: Quotation, actor) -> Quotation:
    if quotation.status != QuotationStatus.PENDING_APPROVAL:
        raise DomainError("Só um orçamento aguardando aprovação pode ser aprovado.")
    if quotation.sales_rep_id == actor.id:
        raise DomainError("Quem vendeu não pode aprovar o próprio orçamento.")

    estado_anterior = quotation.status
    quotation.status = QuotationStatus.APPROVED
    quotation.decided_by = actor
    quotation.decided_at = timezone.now()
    quotation.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])

    record(
        user=actor, action="quotation.approved", entity=quotation,
        before={"status": estado_anterior}, after={"status": quotation.status},
    )
    return quotation


def reject_quotation(quotation: Quotation, actor, reason: str = "") -> Quotation:
    if quotation.status != QuotationStatus.PENDING_APPROVAL:
        raise DomainError("Só um orçamento aguardando aprovação pode ser rejeitado.")
    if quotation.sales_rep_id == actor.id:
        raise DomainError("Quem vendeu não pode rejeitar o próprio orçamento.")

    estado_anterior = quotation.status
    quotation.status = QuotationStatus.REJECTED
    quotation.decided_by = actor
    quotation.decided_at = timezone.now()
    quotation.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])

    record(
        user=actor, action="quotation.rejected", entity=quotation,
        before={"status": estado_anterior}, after={"status": quotation.status},
        metadata={"reason": reason} if reason else None,
    )
    return quotation


def cancel_quotation(quotation: Quotation, actor) -> Quotation:
    if quotation.status not in (QuotationStatus.DRAFT, QuotationStatus.PENDING_APPROVAL):
        raise DomainError("Só um orçamento em rascunho ou aguardando aprovação pode ser cancelado.")

    estado_anterior = quotation.status
    quotation.status = QuotationStatus.CANCELLED
    quotation.save(update_fields=["status", "updated_at"])

    record(
        user=actor, action="quotation.cancelled", entity=quotation,
        before={"status": estado_anterior}, after={"status": quotation.status},
    )
    return quotation
