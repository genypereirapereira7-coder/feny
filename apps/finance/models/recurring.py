from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class SubscriptionFrequency(models.TextChoices):
    MONTHLY = "MONTHLY", "Mensal"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativa"
    PAUSED = "PAUSED", "Pausada"
    CANCELLED = "CANCELLED", "Cancelada"


class RecurringSubscription(BaseModel):
    """Serviço contínuo cobrado periodicamente — hospedagem, manutenção, SaaS
    (ARCHITECTURE.md §6.5, Fase 8). Não gera `Charge` sozinha: só descreve o
    contrato. Quem cria a `Charge RECURRING` a cada ciclo é
    `services.generate_recurring_charges`, chamado por
    `manage.py generate_recurring_charges` — mesma disciplina do
    `dispatch_notifications` da Fase 7 (cron simples, sem Celery, porque
    ainda não há volume que justifique a complexidade extra, §17).
    """

    customer = models.ForeignKey("customers.Customer", related_name="subscriptions", on_delete=models.PROTECT)
    project = models.ForeignKey(
        "projects.Project", null=True, blank=True, related_name="subscriptions", on_delete=models.PROTECT
    )
    service_description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    frequency = models.CharField(
        max_length=20, choices=SubscriptionFrequency.choices, default=SubscriptionFrequency.MONTHLY
    )
    start_date = models.DateField()
    next_billing_date = models.DateField()
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    external_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "finance_recurringsubscription"
        ordering = ["-created_at"]
        # Exatamente o WHERE de `generate_recurring_charges` (Fase 8) — a
        # consulta mais sensível a ficar lenta com o tempo, porque roda todo
        # dia via cron sobre a tabela inteira (Fase 10 — performance).
        indexes = [models.Index(fields=["status", "next_billing_date"], name="idx_sub_status_next_billing")]

    def __str__(self) -> str:
        return f"{self.service_description} — {self.customer.legal_name} ({self.get_status_display()})"
