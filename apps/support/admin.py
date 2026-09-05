from django.contrib import admin

from apps.support.models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("subject", "customer", "status", "priority", "assigned_to", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("subject", "customer__legal_name")
