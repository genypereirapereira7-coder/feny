from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Commission(BaseModel):
    """Comissão de venda — 10% sobre o que foi **recebido**, nunca sobre o
    contratado (ARCHITECTURE.md §8.2). `payment` é `OneToOneField`
    obrigatório (não `null`) de propósito: a nível de banco, é impossível
    existir uma `Commission` sem um `Payment` real por trás — a comissão
    nunca é "prometida", só gerada sobre dinheiro que já entrou.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        PAID = "PAID", "Paga"

    sales_rep = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="commissions", on_delete=models.PROTECT)
    project = models.ForeignKey("projects.Project", related_name="commissions", on_delete=models.PROTECT)
    payment = models.OneToOneField("finance.Payment", related_name="commission", on_delete=models.PROTECT)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    # `db_index`: dashboard soma comissão pendente toda consulta (Fase 10).
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_commission"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Comissão {self.amount} — {self.sales_rep} — {self.get_status_display()}"
