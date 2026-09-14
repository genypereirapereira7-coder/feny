from django.contrib import admin

from apps.leads.models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "email", "phone", "service_type", "status", "created_at")
    list_filter = ("status", "service_type", "budget_range")
    search_fields = ("name", "company", "email", "phone", "message")
    # Status só muda por ação de domínio (`apps/leads/services.py`, que grava
    # auditoria) — editar direto no admin pularia esse registro.
    readonly_fields = ("status", "created_at", "updated_at")
