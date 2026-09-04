from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Só leitura — o estado de envio muda exclusivamente por
    `dispatch_pending`, nunca por edição manual."""

    list_display = ("template", "channel", "recipient", "status", "attempts", "created_at", "sent_at")
    list_filter = ("channel", "status", "template")
    search_fields = ("recipient",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
