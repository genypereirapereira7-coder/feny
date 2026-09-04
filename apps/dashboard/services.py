"""Agregações de leitura pra `GET /api/v1/dashboard/summary/` (ARCHITECTURE.md
§5, §19 Fase 9). Cada seção é uma função própria — cada uma usa `annotate`/
`aggregate` do ORM, nunca soma linha por linha em Python (evita N+1: um
projeto com mil orçamentos não deve custar mil consultas).

O que cada papel vê é decidido aqui, no backend, igual a qualquer outra
autorização da plataforma (§9) — nunca é o frontend que esconde uma seção.
"""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.customers.models import Customer
from apps.finance.models import Charge, ChargeStatus, Commission, Expense, Revenue
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role

_ZERO = Decimal("0.00")


def _inicio_do_mes():
    return timezone.now().date().replace(day=1)


def _contagem_por_status(queryset, todos_os_status) -> dict:
    contagens = dict(queryset.values_list("status").annotate(total=Count("id")))
    return {status: contagens.get(status, 0) for status in todos_os_status}


def quotations_summary(queryset=None) -> dict:
    qs = queryset if queryset is not None else Quotation.objects.all()
    return _contagem_por_status(qs, QuotationStatus.values)


def projects_summary(queryset=None) -> dict:
    qs = queryset if queryset is not None else Project.objects.all()
    return _contagem_por_status(qs, ProjectStatus.values)


def customers_summary() -> dict:
    inicio_mes = _inicio_do_mes()
    return {
        "total": Customer.objects.count(),
        "new_this_month": Customer.objects.filter(created_at__date__gte=inicio_mes).count(),
    }


def finance_summary() -> dict:
    hoje = timezone.now().date()
    inicio_mes = _inicio_do_mes()

    a_receber = Charge.objects.filter(status__in=(ChargeStatus.PENDING, ChargeStatus.PROCESSING)).aggregate(
        total=Sum("amount"),
    )["total"] or _ZERO

    # "Vencido" aqui é calculado na hora (PENDING com due_date no passado),
    # não um status persistido — nenhuma fase anterior criou um job que marca
    # `Charge.status = OVERDUE` automaticamente, e o dashboard não precisa
    # disso pra mostrar o número certo agora.
    vencidas = Charge.objects.filter(status=ChargeStatus.PENDING, due_date__lt=hoje)
    vencidas_agregado = vencidas.aggregate(total=Sum("amount"), quantidade=Count("id"))

    receita_no_mes = Revenue.objects.filter(received_at__date__gte=inicio_mes).aggregate(
        total=Sum("amount"),
    )["total"] or _ZERO

    despesas_pagas_no_mes = Expense.objects.filter(
        status=Expense.Status.PAID, paid_at__date__gte=inicio_mes,
    ).aggregate(total=Sum("amount"))["total"] or _ZERO

    comissoes_pendentes = Commission.objects.filter(status=Commission.Status.PENDING).aggregate(
        total=Sum("amount"),
    )["total"] or _ZERO

    return {
        "receivable_pending": str(a_receber),
        "overdue_total": str(vencidas_agregado["total"] or _ZERO),
        "overdue_count": vencidas_agregado["quantidade"],
        "revenue_this_month": str(receita_no_mes),
        "expenses_paid_this_month": str(despesas_pagas_no_mes),
        "net_this_month": str(receita_no_mes - despesas_pagas_no_mes),
        "commissions_pending": str(comissoes_pendentes),
    }


def sales_summary(user) -> dict:
    comissoes = Commission.objects.filter(sales_rep=user).aggregate(
        pending=Sum("amount", filter=Q(status=Commission.Status.PENDING)),
        paid=Sum("amount", filter=Q(status=Commission.Status.PAID)),
    )
    return {
        "quotations_by_status": quotations_summary(Quotation.objects.filter(sales_rep=user)),
        "commissions_pending": str(comissoes["pending"] or _ZERO),
        "commissions_paid": str(comissoes["paid"] or _ZERO),
    }


def developer_summary(user) -> dict:
    return {"projects_by_status": projects_summary(Project.objects.filter(responsible=user))}


def build_summary(user) -> dict:
    if user.role in (Role.ADMIN, Role.MANAGER):
        return {
            "quotations": quotations_summary(),
            "projects": projects_summary(),
            "finance": finance_summary(),
            "customers": customers_summary(),
        }
    if user.role == Role.FINANCE:
        return {"finance": finance_summary(), "customers": customers_summary()}
    if user.role == Role.SALES:
        return {"sales": sales_summary(user)}
    if user.role == Role.DEVELOPER:
        return developer_summary(user)
    if user.role == Role.SUPPORT:
        return {"quotations": quotations_summary(), "projects": projects_summary()}
    return {}
