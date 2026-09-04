from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.choices import PaymentMethod
from apps.core.models import BaseModel


class ChargeType(models.TextChoices):
    INITIAL = "INITIAL", "Sinal (30%)"
    FINAL = "FINAL", "Saldo (70%)"
    RECURRING = "RECURRING", "Recorrente"
    SCOPE_CHANGE = "SCOPE_CHANGE", "Alteração de escopo"


class ChargeStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    PROCESSING = "PROCESSING", "Em processamento"
    PAID = "PAID", "Pago"
    OVERDUE = "OVERDUE", "Vencido"
    CANCELLED = "CANCELLED", "Cancelado"
    FAILED = "FAILED", "Falhou"


class Charge(BaseModel):
    """Uma obrigação financeira cobrável — o "contas a receber" (ARCHITECTURE.md
    §6.5, §7.3, §8.1).

    Uma vez com `external_id` (cobrança emitida no Mercado Pago, Fase 6),
    `amount` é imutável na prática — mas isso só se torna uma trava de
    verdade (bloqueando update) quando a Fase 6 escrever o serializer de
    edição; nesta fase `Charge` não tem update exposto na API de jeito
    nenhum, então a imutabilidade já vale por outro motivo (ver `api/views.py`).
    """

    project = models.ForeignKey(
        "projects.Project", null=True, blank=True, related_name="charges", on_delete=models.PROTECT
    )
    recurring_subscription = models.ForeignKey(
        "finance.RecurringSubscription", null=True, blank=True, related_name="charges", on_delete=models.PROTECT
    )
    customer = models.ForeignKey("customers.Customer", related_name="charges", on_delete=models.PROTECT)
    charge_type = models.CharField(max_length=20, choices=ChargeType.choices)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=ChargeStatus.choices, default=ChargeStatus.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    external_provider = models.CharField(max_length=30, default="mercadopago")
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_link = models.URLField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_charge"
        ordering = ["-created_at"]
        # Cobre a consulta de "a receber"/"vencido" do dashboard (Fase 9) —
        # `status` sozinho já ajuda a maioria dos filtros, mas essa combinação
        # é a exata do WHERE mais pesado (ARCHITECTURE.md §19, Fase 10).
        indexes = [models.Index(fields=["status", "due_date"], name="idx_charge_status_due_date")]

    def __str__(self) -> str:
        return f"{self.get_charge_type_display()} — {self.customer.legal_name} — {self.get_status_display()}"
