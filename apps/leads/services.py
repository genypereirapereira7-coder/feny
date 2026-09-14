"""Ações de domínio do lead. Mesmo padrão de `apps/support/services.py`:
cada transição confere o estado atual, aplica a mudança e grava auditoria —
nunca uma atribuição de campo solta espalhada pelas views."""

from apps.audit.services import record
from apps.core.exceptions import DomainError
from apps.leads.models import Lead, LeadStatus


def _mudar_status(lead: Lead, *, novo: str, actor, acao: str, extras: dict | None = None) -> Lead:
    anterior = lead.status
    lead.status = novo
    if lead.handled_by_id is None:
        lead.handled_by = actor
    for campo, valor in (extras or {}).items():
        setattr(lead, campo, valor)
    lead.save(update_fields=["status", "handled_by", "updated_at", *(extras or {})])

    record(user=actor, action=acao, entity=lead, before={"status": anterior}, after={"status": novo})
    return lead


def marcar_em_contato(lead: Lead, actor) -> Lead:
    if lead.status != LeadStatus.NEW:
        raise DomainError("Só um lead novo pode entrar em atendimento.")
    return _mudar_status(lead, novo=LeadStatus.CONTACTED, actor=actor, acao="lead.contacted")


def qualificar(lead: Lead, actor) -> Lead:
    if lead.status != LeadStatus.CONTACTED:
        raise DomainError("Fale com o lead antes de qualificá-lo.")
    return _mudar_status(lead, novo=LeadStatus.QUALIFIED, actor=actor, acao="lead.qualified")


def converter_em_cliente(lead: Lead, actor, customer) -> Lead:
    """Não cria o `Customer` sozinho de propósito: cliente exige CPF/CNPJ
    válido (`customers.validators`) e forma de pagamento, e o lead não tem
    nenhum dos dois. Quem converte cadastra o cliente de verdade primeiro e
    aponta pra ele aqui — assim a base de clientes nunca ganha registro
    incompleto por atalho."""
    if lead.status in (LeadStatus.CONVERTED, LeadStatus.DISCARDED):
        raise DomainError("Este lead já foi encerrado.")
    return _mudar_status(
        lead, novo=LeadStatus.CONVERTED, actor=actor, acao="lead.converted",
        extras={"customer": customer},
    )


def descartar(lead: Lead, actor, motivo: str) -> Lead:
    if lead.status == LeadStatus.CONVERTED:
        raise DomainError("Um lead já convertido não pode ser descartado.")
    if not motivo.strip():
        raise DomainError("Diga por que está descartando — é o que explica o número no relatório depois.")

    anotacao = f"[descartado] {motivo.strip()}"
    notas = f"{lead.internal_notes}\n{anotacao}".strip() if lead.internal_notes else anotacao
    return _mudar_status(
        lead, novo=LeadStatus.DISCARDED, actor=actor, acao="lead.discarded",
        extras={"internal_notes": notas},
    )


def reabrir(lead: Lead, actor) -> Lead:
    if lead.status != LeadStatus.DISCARDED:
        raise DomainError("Só um lead descartado pode ser reaberto.")
    return _mudar_status(lead, novo=LeadStatus.NEW, actor=actor, acao="lead.reopened")
