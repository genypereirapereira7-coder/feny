"""Ações de domínio do financeiro (ARCHITECTURE.md §6.5, §8, §9, §10).

`confirm_payment` é a "correção administrativa auditada" que o §9 já prevê
como forma de dar baixa manual num pagamento (`can_confirm_manual_payment`).
Até a Fase 5 era o único caminho possível (sem Mercado Pago ainda); a partir
da Fase 6, `apps.mercadopago.webhooks` também chama esta mesma função — o
service não sabe nem precisa saber se quem chamou foi um humano ou um
webhook, só que alguém confirmou um pagamento (por isso `actor` aceita
`None`: "ação do sistema", já previsto em `AuditLog.user`). `issue_charge` é
a única função daqui que fala com `apps.mercadopago` — nenhuma outra função
deste módulo sabe que Mercado Pago existe. `issue_charge` e `confirm_payment`
também criam uma `Notification` (§11) pra avisar o cliente por WhatsApp —
mas só criam o registro `PENDING`; quem entende WhatsApp e envia de verdade é
`apps.notifications`/`apps.whatsapp`, nunca este módulo. Dinheiro é sempre
`Decimal` (§8.4) — nenhum `float` em nenhuma linha aqui.
"""

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.core.exceptions import DomainError
from apps.finance.models import (
    Charge,
    ChargeStatus,
    ChargeType,
    Commission,
    Expense,
    Payment,
    RecurringSubscription,
    Revenue,
    RevenueSource,
    SubscriptionStatus,
)
from apps.mercadopago import adapter as mercadopago_adapter
from apps.mercadopago.exceptions import MercadoPagoError
from apps.notifications import services as notifications_services
from apps.notifications.models import NotificationChannel
from apps.projects import services as project_services
from apps.projects.models import Project

_DUAS_CASAS = Decimal("0.01")


def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)


def create_initial_charge(project: Project, actor, *, due_date=None, payment_method=None) -> Charge:
    """Cria a cobrança do sinal (30%) e avança o projeto pra
    `AWAITING_INITIAL_PAYMENT` (ARCHITECTURE.md §8.1). A própria transição de
    projeto (`request_initial_payment`) já recusa se o projeto não estiver em
    `APPROVED` — inclusive numa segunda tentativa, o que evita gerar duas
    cobranças iniciais para o mesmo projeto sem precisar de outra checagem."""
    with transaction.atomic():
        project_services.request_initial_payment(project, actor)

        valor = _arredondar(project.amount * Decimal("0.30"))
        charge = Charge.objects.create(
            project=project,
            customer=project.customer,
            charge_type=ChargeType.INITIAL,
            percentage=Decimal("30.00"),
            amount=valor,
            due_date=due_date or timezone.now().date(),
            payment_method=payment_method or project.customer.preferred_payment_method,
        )

        record(
            user=actor, action="charge.created", entity=charge,
            before=None, after={"charge_type": charge.charge_type, "amount": str(charge.amount)},
            metadata={"project_id": str(project.id)},
        )
        return charge


def create_final_charge(project: Project, actor, *, due_date=None, payment_method=None) -> Charge:
    """Cria a cobrança do saldo (70%) e avança o projeto pra
    `AWAITING_FINAL_PAYMENT`. O valor é `amount - já cobrado`, não
    `0.70 * amount` de novo — evita divergência de centavos por
    arredondamento se algum `SCOPE_CHANGE` tiver mexido no total (§8.1)."""
    with transaction.atomic():
        project_services.request_final_payment(project, actor)

        ja_cobrado = sum(
            (c.amount for c in project.charges.exclude(status=ChargeStatus.CANCELLED)),
            Decimal("0.00"),
        )
        valor = _arredondar(project.amount - ja_cobrado)
        if valor <= Decimal("0.00"):
            raise DomainError("Não há saldo restante a cobrar neste projeto.")

        charge = Charge.objects.create(
            project=project,
            customer=project.customer,
            charge_type=ChargeType.FINAL,
            percentage=Decimal("70.00"),
            amount=valor,
            due_date=due_date or timezone.now().date(),
            payment_method=payment_method or project.customer.preferred_payment_method,
        )

        record(
            user=actor, action="charge.created", entity=charge,
            before=None, after={"charge_type": charge.charge_type, "amount": str(charge.amount)},
            metadata={"project_id": str(project.id)},
        )
        return charge


def cancel_charge(charge: Charge, actor) -> Charge:
    if charge.status != ChargeStatus.PENDING:
        raise DomainError("Só uma cobrança pendente pode ser cancelada.")

    estado_anterior = charge.status
    charge.status = ChargeStatus.CANCELLED
    charge.save(update_fields=["status", "updated_at"])

    record(
        user=actor, action="charge.cancelled", entity=charge,
        before={"status": estado_anterior}, after={"status": charge.status},
    )
    return charge


def issue_charge(charge: Charge, actor) -> Charge:
    """Emite a cobrança no Mercado Pago (ARCHITECTURE.md §10): cria a
    preferência de pagamento e grava `external_id`/`payment_link` na `Charge`.

    Separado de `create_initial_charge`/`create_final_charge` de propósito —
    a obrigação financeira já existe e é válida sem isso (é o que a Fase 5
    testou), emitir no Mercado Pago é um passo seguinte, não uma condição
    pra a cobrança existir. Também mantém `MERCADOPAGO_ACCESS_TOKEN` ausente
    (ambiente sem a integração configurada) como um erro de domínio recusado
    aqui, não uma 500 vazando lá de dentro do `client.py`.
    """
    if charge.status != ChargeStatus.PENDING:
        raise DomainError("Só uma cobrança pendente pode ser emitida no Mercado Pago.")
    if charge.external_id:
        raise DomainError("Esta cobrança já foi emitida no Mercado Pago.")

    try:
        preferencia = mercadopago_adapter.create_charge_preference(charge)
    except MercadoPagoError as exc:
        raise DomainError(str(exc)) from exc

    charge.external_id = preferencia["external_id"]
    charge.payment_link = preferencia["payment_link"]
    charge.save(update_fields=["external_id", "payment_link", "updated_at"])

    record(
        user=actor, action="charge.issued", entity=charge,
        before=None, after={"external_id": charge.external_id},
    )

    notifications_services.notify(
        channel=NotificationChannel.WHATSAPP, recipient=charge.customer.phone, template="charge.issued",
        context={
            "customer_name": charge.customer.legal_name,
            "charge_label": charge.get_charge_type_display(),
            "charge_amount": f"R$ {charge.amount}",
            "payment_link": charge.payment_link,
        },
    )
    return charge


def confirm_payment(
    charge: Charge, actor, *, external_id: str, amount: Decimal, method: str, paid_at=None, raw_payload=None
) -> Charge:
    """"ConfirmPayment" (§7.2, §8.3). Na Fase 6 isto passa a ser chamado pelo
    processador de webhook do Mercado Pago; por enquanto é uma ação
    administrativa auditada — a permissão de API restringe quem chega aqui
    (ver `apps/finance/permissions.py`), não este service.

    Idempotência (§8.3.1-2): se já existe um `Payment` com este `external_id`,
    o evento já foi processado — encerra sem reprocessar, sem tratar isso
    como erro."""
    pagamento_existente = Payment.objects.filter(external_id=external_id).first()
    if pagamento_existente is not None:
        return charge

    if charge.status not in (ChargeStatus.PENDING, ChargeStatus.PROCESSING):
        raise DomainError("Só uma cobrança pendente ou em processamento pode ser confirmada como paga.")

    momento_pagamento = paid_at or timezone.now()

    with transaction.atomic():
        payment = Payment.objects.create(
            charge=charge, amount=amount, external_id=external_id, method=method,
            paid_at=momento_pagamento, raw_payload=raw_payload or {},
        )

        charge.status = ChargeStatus.PAID
        charge.paid_at = momento_pagamento
        charge.save(update_fields=["status", "paid_at", "updated_at"])

        Revenue.objects.create(
            source=RevenueSource.PROJECT if charge.project_id else RevenueSource.OTHER,
            payment=payment, amount=payment.amount, received_at=momento_pagamento,
        )

        record(
            user=actor, action="payment.confirmed", entity=payment,
            before=None, after={"amount": str(payment.amount), "method": payment.method},
            metadata={"charge_id": str(charge.id)},
        )

        notifications_services.notify(
            channel=NotificationChannel.WHATSAPP, recipient=charge.customer.phone, template="payment.received",
            context={"customer_name": charge.customer.legal_name, "payment_amount": f"R$ {payment.amount}"},
        )

        if charge.project_id:
            if charge.charge_type == ChargeType.INITIAL:
                project_services.confirm_initial_payment(charge.project, actor)
            elif charge.charge_type == ChargeType.FINAL:
                project_services.confirm_final_payment(charge.project, actor)

            _generate_commission(payment, actor)

    return charge


def _generate_commission(payment: Payment, actor) -> Commission:
    """§8.2: 10% sobre o que foi **recebido**, gerada só depois do `Payment`
    existir — nunca antes, nunca sobre valor contratado."""
    project = payment.charge.project
    sales_rep = project.quotation.sales_rep

    commission = Commission.objects.create(
        sales_rep=sales_rep, project=project, payment=payment,
        percentage=Decimal("10.00"), amount=_arredondar(payment.amount * Decimal("0.10")),
    )

    record(
        user=actor, action="commission.generated", entity=commission,
        before=None, after={"amount": str(commission.amount), "status": commission.status},
    )
    return commission


def pay_commission(commission: Commission, actor) -> Commission:
    if commission.status != Commission.Status.PENDING:
        raise DomainError("Só uma comissão pendente pode ser marcada como paga.")

    commission.status = Commission.Status.PAID
    commission.paid_at = timezone.now()
    commission.save(update_fields=["status", "paid_at", "updated_at"])

    record(
        user=actor, action="commission.paid", entity=commission,
        before={"status": Commission.Status.PENDING}, after={"status": commission.status},
    )
    return commission


def pay_expense(expense: Expense, actor) -> Expense:
    if expense.status != Expense.Status.PENDING:
        raise DomainError("Só uma despesa pendente pode ser marcada como paga.")

    expense.status = Expense.Status.PAID
    expense.paid_at = timezone.now()
    expense.save(update_fields=["status", "paid_at", "updated_at"])

    record(
        user=actor, action="expense.paid", entity=expense,
        before={"status": Expense.Status.PENDING}, after={"status": expense.status},
    )
    return expense


def cancel_expense(expense: Expense, actor) -> Expense:
    if expense.status != Expense.Status.PENDING:
        raise DomainError("Só uma despesa pendente pode ser cancelada.")

    expense.status = Expense.Status.CANCELLED
    expense.save(update_fields=["status", "updated_at"])

    record(
        user=actor, action="expense.cancelled", entity=expense,
        before={"status": Expense.Status.PENDING}, after={"status": expense.status},
    )
    return expense


def _somar_um_mes(data: date) -> date:
    """Só `MONTHLY` existe em `SubscriptionFrequency` por enquanto (§6.5) —
    sem lib nova só pra isso. Trata o caso de dia 29-31 num mês mais curto
    (dia 31 + 1 mês em fevereiro vira o último dia de fevereiro, não estoura)."""
    mes, ano = (data.month % 12) + 1, data.year + (data.month // 12)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return data.replace(year=ano, month=mes, day=min(data.day, ultimo_dia))


def create_subscription(
    customer, actor, *, service_description: str, amount: Decimal, start_date: date, project=None,
) -> RecurringSubscription:
    """Só registra o contrato (ARCHITECTURE.md §6.5) — não gera nenhuma
    `Charge` aqui. Quem cobra é sempre `generate_recurring_charges`, pra não
    ter duas rotas que criam `Charge RECURRING` de jeitos diferentes."""
    subscription = RecurringSubscription.objects.create(
        customer=customer, project=project, service_description=service_description,
        amount=amount, start_date=start_date, next_billing_date=start_date,
    )
    record(
        user=actor, action="subscription.created", entity=subscription,
        before=None, after={"status": subscription.status, "amount": str(subscription.amount)},
    )
    return subscription


def pause_subscription(subscription: RecurringSubscription, actor) -> RecurringSubscription:
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise DomainError("Só uma assinatura ativa pode ser pausada.")
    return _transicionar_assinatura(subscription, actor, SubscriptionStatus.PAUSED, "subscription.paused")


def resume_subscription(subscription: RecurringSubscription, actor) -> RecurringSubscription:
    if subscription.status != SubscriptionStatus.PAUSED:
        raise DomainError("Só uma assinatura pausada pode ser retomada.")
    return _transicionar_assinatura(subscription, actor, SubscriptionStatus.ACTIVE, "subscription.resumed")


def cancel_subscription(subscription: RecurringSubscription, actor) -> RecurringSubscription:
    if subscription.status == SubscriptionStatus.CANCELLED:
        raise DomainError("Esta assinatura já está cancelada.")
    return _transicionar_assinatura(subscription, actor, SubscriptionStatus.CANCELLED, "subscription.cancelled")


def _transicionar_assinatura(subscription, actor, novo_status, acao) -> RecurringSubscription:
    estado_anterior = subscription.status
    subscription.status = novo_status
    subscription.save(update_fields=["status", "updated_at"])
    record(
        user=actor, action=acao, entity=subscription,
        before={"status": estado_anterior}, after={"status": subscription.status},
    )
    return subscription


def generate_recurring_charges(actor=None, reference_date: date | None = None) -> dict:
    """Roda por `manage.py generate_recurring_charges` (cron). Pra cada
    assinatura `ACTIVE` com `next_billing_date <= hoje`: cria a `Charge
    RECURRING`, avança `next_billing_date` um ciclo, e tenta emitir no
    Mercado Pago (§10) — se a emissão falhar (ex.: ambiente sem
    `MERCADOPAGO_ACCESS_TOKEN`), a cobrança continua existindo e válida,
    só sem link automático ainda; não é motivo pra não cobrar."""
    hoje = reference_date or timezone.now().date()
    subscriptions = RecurringSubscription.objects.filter(
        status=SubscriptionStatus.ACTIVE, next_billing_date__lte=hoje,
    )

    geradas = falhas_emissao = 0
    for subscription in subscriptions:
        with transaction.atomic():
            charge = Charge.objects.create(
                project=subscription.project,
                recurring_subscription=subscription,
                customer=subscription.customer,
                charge_type=ChargeType.RECURRING,
                amount=subscription.amount,
                due_date=subscription.next_billing_date,
                payment_method=subscription.customer.preferred_payment_method,
            )
            record(
                user=actor, action="charge.created", entity=charge,
                before=None, after={"charge_type": charge.charge_type, "amount": str(charge.amount)},
                metadata={"subscription_id": str(subscription.id)},
            )

            subscription.next_billing_date = _somar_um_mes(subscription.next_billing_date)
            subscription.save(update_fields=["next_billing_date", "updated_at"])

        geradas += 1
        try:
            issue_charge(charge, actor)
        except DomainError:
            falhas_emissao += 1

    return {"geradas": geradas, "falhas_emissao": falhas_emissao}
