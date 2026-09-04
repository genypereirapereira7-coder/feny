from django.contrib import admin

from apps.audit.models import AuditLog, ExternalWebhookEvent


class _SomenteLeituraAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(_SomenteLeituraAdmin):
    """Só leitura — um log de auditoria que pode ser editado pelo admin não é
    auditoria de verdade."""

    list_display = ("created_at", "action", "entity_type", "entity_id", "user")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "action")


@admin.register(ExternalWebhookEvent)
class ExternalWebhookEventAdmin(_SomenteLeituraAdmin):
    list_display = ("created_at", "provider", "event_type", "external_event_id", "status", "attempts")
    list_filter = ("provider", "status", "event_type")
    search_fields = ("external_event_id",)
