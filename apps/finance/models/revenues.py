from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class RevenueSource(models.TextChoices):
    PROJECT = "PROJECT", "Projeto"
    RECURRING = "RECURRING", "Recorrente"
    OTHER = "OTHER", "Outro"


class Revenue(BaseModel):
    """Lançamento de entrada financeira (ARCHITECTURE.md §6.5).

    Só nasce automaticamente, dentro de `apps.finance.services.confirm_payment`
    — não tem endpoint de criação própria na Fase 5 (o mapa de recursos do
    §12 nem lista `/api/v1/finance/revenues/`); é um livro-razão derivado, não
    um cadastro manual.
    """

    source = models.CharField(max_length=20, choices=RevenueSource.choices)
    payment = models.OneToOneField(
        "finance.Payment", null=True, blank=True, related_name="revenue", on_delete=models.PROTECT
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    description = models.CharField(max_length=200, blank=True)
    received_at = models.DateTimeField()

    class Meta:
        db_table = "finance_revenue"
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"Receita {self.amount} — {self.get_source_display()}"
