from django.contrib import admin

from apps.customers.models import Customer, CustomerContact


class CustomerContactInline(admin.TabularInline):
    model = CustomerContact
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "kind", "document", "email", "preferred_payment_method", "created_by")
    list_filter = ("kind", "preferred_payment_method")
    search_fields = ("legal_name", "document", "email")
    inlines = [CustomerContactInline]
