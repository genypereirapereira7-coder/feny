from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.choices import ProjectType
from apps.core.models import BaseModel


class QuotationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Aguardando aprovação"
    APPROVED = "APPROVED", "Aprovado"
    REJECTED = "REJECTED", "Rejeitado"
    CANCELLED = "CANCELLED", "Cancelado"


class Quotation(BaseModel):
    """Orçamento (ARCHITECTURE.md §6.3, §7.1, §11).

    Nunca muda de `status` por atribuição direta de campo fora de
    `apps/quotations/services.py` — toda transição é uma ação de domínio,
    auditada (ARCHITECTURE.md §21).
    """

    customer = models.ForeignKey("customers.Customer", related_name="quotations", on_delete=models.PROTECT)
    sales_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="quotations", on_delete=models.PROTECT
    )
    service_type = models.CharField(max_length=20, choices=ProjectType.choices)
    description = models.TextField()
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    deadline_days = models.PositiveIntegerField(null=True, blank=True)
    # `db_index`: filtrado a cada agregação do dashboard (Fase 9) e em toda
    # listagem por status (ARCHITECTURE.md §19, Fase 10 — performance).
    status = models.CharField(
        max_length=20, choices=QuotationStatus.choices, default=QuotationStatus.DRAFT, db_index=True,
    )
    notes = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "quotations_quotation"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.customer.legal_name} — {self.get_status_display()}"
