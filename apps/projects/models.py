from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.choices import ProjectType
from apps.core.models import BaseModel


class ProjectStatus(models.TextChoices):
    """ARCHITECTURE.md §7.2 — máquina de estado completa do projeto.

    Só `APPROVED` é alcançável nesta fase (via `services.generate_project_from_quotation`).
    As demais transições dependem de domínios que ainda não existem — `Charge`
    (Fase 5), o webhook do Mercado Pago (Fase 6) e o aceite do cliente — e serão
    implementadas em `apps/projects/services.py` quando esses domínios puderem
    de fato dispará-las (nada de simular um gatilho que ainda não existe).
    """

    APPROVED = "APPROVED", "Aprovado"
    AWAITING_INITIAL_PAYMENT = "AWAITING_INITIAL_PAYMENT", "Aguardando pagamento inicial"
    INITIAL_PAYMENT_CONFIRMED = "INITIAL_PAYMENT_CONFIRMED", "Pagamento inicial confirmado"
    IN_DEVELOPMENT = "IN_DEVELOPMENT", "Em desenvolvimento"
    DEVELOPMENT_COMPLETED = "DEVELOPMENT_COMPLETED", "Desenvolvimento concluído"
    AWAITING_CLIENT_ACCEPTANCE = "AWAITING_CLIENT_ACCEPTANCE", "Aguardando aceite do cliente"
    ACCEPTED = "ACCEPTED", "Aceito"
    AWAITING_FINAL_PAYMENT = "AWAITING_FINAL_PAYMENT", "Aguardando pagamento final"
    FINAL_PAYMENT_CONFIRMED = "FINAL_PAYMENT_CONFIRMED", "Pagamento final confirmado"
    DELIVERED = "DELIVERED", "Entregue"
    MAINTENANCE = "MAINTENANCE", "Manutenção"


class Project(BaseModel):
    """Projeto (ARCHITECTURE.md §6.4, §7.2).

    Nasce sempre de um `Quotation` aprovado (`quotation` é `OneToOneField` —
    impossível, a nível de banco, um orçamento gerar dois projetos ou um
    projeto existir sem orçamento por trás). `amount` é um snapshot do valor
    aprovado no momento da criação — não recalcula do orçamento depois, pelo
    mesmo motivo do `Charge` FINAL em §8.1 (evita divergência se o orçamento
    mudasse, mesmo que hoje ele já esteja imutável fora de DRAFT).
    """

    customer = models.ForeignKey("customers.Customer", related_name="projects", on_delete=models.PROTECT)
    quotation = models.OneToOneField("quotations.Quotation", related_name="project", on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    project_type = models.CharField(max_length=20, choices=ProjectType.choices)
    description = models.TextField(blank=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="projects_responsible", on_delete=models.PROTECT
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    # `db_index`: agregado no dashboard por status e filtrado por papel toda
    # hora (Fase 10 — performance).
    status = models.CharField(
        max_length=30, choices=ProjectStatus.choices, default=ProjectStatus.APPROVED, db_index=True,
    )
    expected_delivery_at = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "projects_project"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} — {self.get_status_display()}"
