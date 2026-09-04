"""Ações de domínio do projeto (ARCHITECTURE.md §7.2).

Cada função corresponde a uma transição da máquina de estado. Duas delas —
`confirm_initial_payment` e `confirm_final_payment` — não têm `@action` na
API: a tabela de guardas do §7.2 é explícita que essa transição "só via
ConfirmPayment, disparado pelo webhook do Mercado Pago — nunca por um
funcionário marcando manualmente". Na Fase 5, sem Mercado Pago ainda, quem
chama essas duas é `apps.finance.services.confirm_payment` (a correção
administrativa auditada que o §9 já antecipa) — nunca uma view chamada
diretamente por um `role_required` de funcionário comum.
"""

from django.utils import timezone

from apps.audit.services import record
from apps.core.exceptions import DomainError
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role

_PODE_SER_RESPONSAVEL = (Role.ADMIN, Role.MANAGER, Role.DEVELOPER)


def generate_project_from_quotation(
    quotation: Quotation,
    actor,
    *,
    name: str,
    responsible,
    description: str = "",
    expected_delivery_at=None,
) -> Project:
    """ARCHITECTURE.md §6.4: "Um Project nasce de um Quotation aprovado —
    nunca é criado solto." `quotation` sendo `OneToOneField` já impede duas
    gerações a nível de banco; a checagem de status aqui dá o erro de domínio
    correto (400) em vez de deixar estourar um `IntegrityError` (500)."""
    if quotation.status != QuotationStatus.APPROVED:
        raise DomainError("Só um orçamento aprovado pode gerar um projeto.")
    if hasattr(quotation, "project"):
        raise DomainError("Este orçamento já gerou um projeto.")
    if responsible.role not in _PODE_SER_RESPONSAVEL:
        raise DomainError("O responsável pelo projeto precisa ser admin, gerente ou desenvolvedor.")

    project = Project.objects.create(
        customer=quotation.customer,
        quotation=quotation,
        name=name,
        project_type=quotation.service_type,
        description=description,
        responsible=responsible,
        amount=quotation.amount,
        status=ProjectStatus.APPROVED,
        expected_delivery_at=expected_delivery_at,
    )

    record(
        user=actor, action="project.created", entity=project,
        before=None, after={"status": project.status},
        metadata={"quotation_id": str(quotation.id)},
    )
    return project


def _transicionar(project: Project, actor, *, de, para, acao: str, extra_fields: dict | None = None) -> Project:
    if project.status != de:
        raise DomainError(f"Projeto precisa estar em {de} para esta ação (está em {project.status}).")

    estado_anterior = project.status
    project.status = para
    update_fields = ["status", "updated_at"]
    for campo, valor in (extra_fields or {}).items():
        setattr(project, campo, valor)
        update_fields.append(campo)
    project.save(update_fields=update_fields)

    record(
        user=actor, action=acao, entity=project,
        before={"status": estado_anterior}, after={"status": project.status},
    )
    return project


def request_initial_payment(project: Project, actor) -> Project:
    """Disparado só por `finance.services.create_initial_charge` — nunca
    diretamente por uma view de funcionário."""
    return _transicionar(
        project, actor, de=ProjectStatus.APPROVED, para=ProjectStatus.AWAITING_INITIAL_PAYMENT,
        acao="project.awaiting_initial_payment",
    )


def confirm_initial_payment(project: Project, actor) -> Project:
    """Disparado só por `finance.services.confirm_payment` — ver docstring do módulo."""
    return _transicionar(
        project, actor, de=ProjectStatus.AWAITING_INITIAL_PAYMENT, para=ProjectStatus.INITIAL_PAYMENT_CONFIRMED,
        acao="project.initial_payment_confirmed",
    )


def start_development(project: Project, actor) -> Project:
    return _transicionar(
        project, actor, de=ProjectStatus.INITIAL_PAYMENT_CONFIRMED, para=ProjectStatus.IN_DEVELOPMENT,
        acao="project.development_started",
    )


def complete_development(project: Project, actor) -> Project:
    """§7.2: "Automática ao marcar desenvolvimento concluído" — os dois nós do
    diagrama (`DEVELOPMENT_COMPLETED` e `AWAITING_CLIENT_ACCEPTANCE`) viram um
    único passo aqui; não existe uma ação separada pra sair de
    `DEVELOPMENT_COMPLETED`, então não faria sentido parar nele."""
    return _transicionar(
        project, actor, de=ProjectStatus.IN_DEVELOPMENT, para=ProjectStatus.AWAITING_CLIENT_ACCEPTANCE,
        acao="project.development_completed",
    )


def register_client_acceptance(project: Project, actor) -> Project:
    """§7.2: "Evento explícito de aceite — nunca inferido." Por isso é uma
    ação separada, e não algo que acontece sozinho a partir de outro evento."""
    return _transicionar(
        project, actor, de=ProjectStatus.AWAITING_CLIENT_ACCEPTANCE, para=ProjectStatus.ACCEPTED,
        acao="project.client_accepted",
    )


def request_final_payment(project: Project, actor) -> Project:
    """Disparado só por `finance.services.create_final_charge`."""
    return _transicionar(
        project, actor, de=ProjectStatus.ACCEPTED, para=ProjectStatus.AWAITING_FINAL_PAYMENT,
        acao="project.awaiting_final_payment",
    )


def confirm_final_payment(project: Project, actor) -> Project:
    """Disparado só por `finance.services.confirm_payment`."""
    return _transicionar(
        project, actor, de=ProjectStatus.AWAITING_FINAL_PAYMENT, para=ProjectStatus.FINAL_PAYMENT_CONFIRMED,
        acao="project.final_payment_confirmed",
    )


def mark_delivered(project: Project, actor) -> Project:
    return _transicionar(
        project, actor, de=ProjectStatus.FINAL_PAYMENT_CONFIRMED, para=ProjectStatus.DELIVERED,
        acao="project.delivered", extra_fields={"delivered_at": timezone.now()},
    )


def enter_maintenance(project: Project, actor) -> Project:
    return _transicionar(
        project, actor, de=ProjectStatus.DELIVERED, para=ProjectStatus.MAINTENANCE,
        acao="project.entered_maintenance",
    )
