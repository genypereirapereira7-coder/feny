"""Ações de domínio do chamado de suporte. Mesmo padrão de
`apps/quotations/services.py`: cada transição valida o estado atual, aplica
a mudança e grava auditoria — nunca uma atribuição de campo solta."""

from django.utils import timezone

from apps.audit.services import record
from apps.core.exceptions import DomainError
from apps.support.models import Ticket, TicketStatus


def assign_ticket(ticket: Ticket, actor, assignee) -> Ticket:
    if ticket.status == TicketStatus.CLOSED:
        raise DomainError("Um chamado fechado não pode ser reatribuído — reabra primeiro.")

    estado_anterior = ticket.status
    ticket.assigned_to = assignee
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS
    ticket.save(update_fields=["assigned_to", "status", "updated_at"])

    record(
        user=actor, action="ticket.assigned", entity=ticket,
        before={"status": estado_anterior}, after={"status": ticket.status},
        metadata={"assigned_to": str(assignee.id)},
    )
    return ticket


def resolve_ticket(ticket: Ticket, actor) -> Ticket:
    if ticket.status != TicketStatus.IN_PROGRESS:
        raise DomainError("Só um chamado em atendimento pode ser marcado como resolvido.")

    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = timezone.now()
    ticket.save(update_fields=["status", "resolved_at", "updated_at"])

    record(
        user=actor, action="ticket.resolved", entity=ticket,
        before={"status": TicketStatus.IN_PROGRESS}, after={"status": ticket.status},
    )
    return ticket


def close_ticket(ticket: Ticket, actor) -> Ticket:
    if ticket.status != TicketStatus.RESOLVED:
        raise DomainError("Só um chamado resolvido pode ser fechado.")

    ticket.status = TicketStatus.CLOSED
    ticket.save(update_fields=["status", "updated_at"])

    record(
        user=actor, action="ticket.closed", entity=ticket,
        before={"status": TicketStatus.RESOLVED}, after={"status": ticket.status},
    )
    return ticket


def reopen_ticket(ticket: Ticket, actor) -> Ticket:
    if ticket.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        raise DomainError("Só um chamado resolvido ou fechado pode ser reaberto.")

    estado_anterior = ticket.status
    ticket.status = TicketStatus.OPEN
    ticket.resolved_at = None
    ticket.save(update_fields=["status", "resolved_at", "updated_at"])

    record(
        user=actor, action="ticket.reopened", entity=ticket,
        before={"status": estado_anterior}, after={"status": ticket.status},
    )
    return ticket
