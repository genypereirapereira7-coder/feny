from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Payment(BaseModel):
    """O recebimento confirmado de uma `Charge` (ARCHITECTURE.md §6.5).

    Entidade própria, separada de `Charge`, porque "cobrança criada" e
    "dinheiro recebido" são dois eventos, não um. `external_id` é `unique` —
    a segunda notificação do mesmo pagamento nunca cria um segundo `Payment`
    (idempotência, §8.3). Nasce só por `apps.finance.services.confirm_payment`,
    nunca direto via API.
    """

    charge = models.ForeignKey("finance.Charge", related_name="payments", on_delete=models.PROTECT)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    external_id = models.CharField(max_length=100, unique=True)
    method = models.CharField(max_length=20)
    paid_at = models.DateTimeField()
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "finance_payment"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Pagamento {self.amount} — {self.charge}"
