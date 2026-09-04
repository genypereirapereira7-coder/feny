"""ARCHITECTURE.md §11: qualquer domínio cria uma `Notification` e termina
ali — o envio é responsabilidade de outro processo (`dispatch_pending`,
chamado por `manage.py dispatch_notifications`, agendado por cron). Nunca
Celery aqui: §17 só pede isso quando volume ou necessidade de retry robusto
justificar, e uma plataforma interna de uso próprio começando do zero ainda
não tem esse volume — o comando de management resolve por enquanto.
"""

from django.utils import timezone

from apps.notifications.models import Notification, NotificationChannel, NotificationStatus

_MAX_TENTATIVAS = 5


def _carregar_remetente_whatsapp():
    """Import tardio: evita que `apps.notifications` (uma dependência de
    domínios como `finance`) precise carregar `apps.whatsapp` só pra criar
    uma notificação que talvez nem seja WhatsApp."""
    from apps.whatsapp import service as whatsapp_service

    return whatsapp_service.send


def notify(*, channel: str, recipient: str, template: str, context: dict | None = None) -> Notification | None:
    """Ponto único de criação de aviso. `recipient` vazio (ex.: cliente sem
    telefone cadastrado) não é erro — só não há pra quem avisar, então nem
    cria o registro."""
    if not recipient:
        return None

    return Notification.objects.create(
        channel=channel, recipient=recipient, template=template, context=context or {},
    )


def dispatch_pending(limit: int = 100) -> dict:
    """Roda pelo `manage.py dispatch_notifications`. Reprocessa `PENDING` e
    `FAILED` com menos de `_MAX_TENTATIVAS` — o diagrama do §11 é explícito
    que uma falha "reprocessa depois", não é definitiva na primeira tentativa.
    """
    candidatas = Notification.objects.filter(
        channel=NotificationChannel.WHATSAPP,
        status__in=(NotificationStatus.PENDING, NotificationStatus.FAILED),
        attempts__lt=_MAX_TENTATIVAS,
    ).order_by("created_at")[:limit]

    enviadas = falharam = 0
    for notification in candidatas:
        if _enviar_uma(notification):
            enviadas += 1
        else:
            falharam += 1

    return {"enviadas": enviadas, "falharam": falharam, "total": enviadas + falharam}


def _enviar_uma(notification: Notification) -> bool:
    enviar = _carregar_remetente_whatsapp()
    try:
        enviar(notification)
    except Exception as exc:  # noqa: BLE001 — qualquer falha do canal é "não enviou", nunca propaga
        notification.attempts += 1
        notification.status = NotificationStatus.FAILED
        notification.last_error = str(exc)
        notification.save(update_fields=["attempts", "status", "last_error", "updated_at"])
        return False

    notification.status = NotificationStatus.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at", "updated_at"])
    return True
