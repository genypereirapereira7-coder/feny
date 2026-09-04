from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Expense(BaseModel):
    """Despesa da empresa — infra, software, fornecedor, funcionário...
    (ARCHITECTURE.md §6.5)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        PAID = "PAID", "Paga"
        OVERDUE = "OVERDUE", "Vencida"
        CANCELLED = "CANCELLED", "Cancelada"

    category = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    # `db_index`: dashboard filtra "pago no mês" toda consulta (Fase 10).
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    document = models.ForeignKey(
        "documents.Document", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_expense"
        ordering = ["-due_date"]

    def __str__(self) -> str:
        return f"{self.description} — {self.get_status_display()}"
