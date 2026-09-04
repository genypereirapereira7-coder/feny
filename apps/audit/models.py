from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class AuditLog(BaseModel):
    """Ação crítica registrada (ARCHITECTURE.md §15).

    Escrito só pelo helper em `apps/audit/services.py::record`, chamado
    explicitamente dentro dos services de domínio — nunca por um signal
    genérico em todo `save()`, que geraria ruído sem contexto de negócio.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name="audit_logs", on_delete=models.SET_NULL,
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=64)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]

    def __str__(self) -> str:
        return f"{self.action} — {self.entity_type}:{self.entity_id}"


class ExternalWebhookEvent(BaseModel):
    """Todo evento recebido de um webhook de provedor externo (ARCHITECTURE.md
    §6.10, §8.3, §10) — não nasceu na Fase 1-5 porque só ganha um disparador
    de verdade agora, com `apps.mercadopago.webhooks`.

    A `UniqueConstraint` em `(provider, external_event_id)` é a primeira das
    três camadas de idempotência (§8.3.1): o mesmo evento reprocessado nunca
    passa daqui — a constraint do banco dispara antes de qualquer lógica.
    """

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Recebido"
        PROCESSED = "PROCESSED", "Processado"
        FAILED = "FAILED", "Falhou"
        IGNORED = "IGNORED", "Ignorado"

    provider = models.CharField(max_length=30)
    external_event_id = models.CharField(max_length=100)
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "audit_externalwebhookevent"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "external_event_id"], name="uq_webhook_event")
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.external_event_id} — {self.get_status_display()}"
