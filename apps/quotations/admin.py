from django.contrib import admin

from apps.quotations.models import Quotation


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("customer", "sales_rep", "amount", "status", "decided_by", "created_at")
    list_filter = ("status", "service_type")
    search_fields = ("customer__legal_name",)
    readonly_fields = ("decided_at", "decided_by")
