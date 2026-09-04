from django.db import models

from apps.core.models import BaseModel


class NotificationChannel(models.TextChoices):
    WHATSAPP = "WHATSAPP", "WhatsApp"
    EMAIL = "EMAIL", "E-mail"
    INTERNAL = "INTERNAL", "Interna"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    SENT = "SENT", "Enviada"
    FAILED = "FAILED", "Falhou"


class Notification(BaseModel):
    """Aviso agnóstico de canal (ARCHITECTURE.md §6.7, §11).

    Quem cria isto (`finance`, `projects`...) não sabe nem precisa saber que
    existe Evolution API por trás — só descreve *o quê* avisar (`template` +
    `context`) e *pra quem* (`recipient`). Quem entende `channel=WHATSAPP` e
    de fato envia é `apps.whatsapp`, só quando `dispatch_notifications` roda
    — nunca na mesma requisição que criou a notificação (§17: envio não pode
    bloquear a resposta HTTP, e uma falha de envio nunca desfaz a transação
    que originou o aviso).
    """

    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    recipient = models.CharField(max_length=100)
    template = models.CharField(max_length=100)
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        # Exatamente o WHERE de `dispatch_pending` (Fase 7), que também roda
        # via cron (Fase 10 — performance).
        indexes = [models.Index(fields=["channel", "status"], name="idx_notif_channel_status")]

    def __str__(self) -> str:
        return f"{self.template} → {self.recipient} ({self.get_status_display()})"
