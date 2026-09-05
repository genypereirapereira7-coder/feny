from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class TicketStatus(models.TextChoices):
    OPEN = "OPEN", "Aberto"
    IN_PROGRESS = "IN_PROGRESS", "Em atendimento"
    RESOLVED = "RESOLVED", "Resolvido"
    CLOSED = "CLOSED", "Fechado"


class TicketPriority(models.TextChoices):
    LOW = "LOW", "Baixa"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "Alta"


class Ticket(BaseModel):
    """Chamado de suporte (domínio novo, criado na Fase 9 do frontend —
    não existia em nenhuma das 10 fases originais do backend).

    Mesma disciplina do resto do projeto: nunca muda de `status` por
    atribuição direta de campo fora de `apps/support/services.py` — toda
    transição é uma ação de domínio, auditada.
    """

    customer = models.ForeignKey("customers.Customer", related_name="tickets", on_delete=models.PROTECT)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=TicketPriority.choices, default=TicketPriority.NORMAL)
    status = models.CharField(
        max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN, db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="assigned_tickets", on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="tickets_created", on_delete=models.PROTECT,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "support_ticket"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.subject} — {self.get_status_display()}"
