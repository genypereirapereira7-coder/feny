from django.contrib import admin

from apps.leads.models import ClientePotencial, Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "email", "phone", "service_type", "status", "created_at")
    list_filter = ("status", "service_type", "budget_range")
    search_fields = ("name", "company", "email", "phone", "message")
    # Status só muda por ação de domínio (`apps/leads/services.py`, que grava
    # auditoria) — editar direto no admin pularia esse registro.
    readonly_fields = ("status", "created_at", "updated_at")


@admin.register(ClientePotencial)
class ClientePotencialAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "valor_estimado", "created_at")
    search_fields = ("nome", "telefone", "descricao_projeto")
    date_hierarchy = "created_at"
    # Tudo que veio da conversa é somente-leitura: o registro é o que o agente
    # apurou no WhatsApp, e editar aqui apagaria a única versão do que foi
    # combinado com a pessoa sem deixar rastro de quem mudou.
    readonly_fields = ("nome", "telefone", "descricao_projeto", "valor_estimado", "created_at", "updated_at")
