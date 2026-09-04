from django.contrib import admin

from apps.finance.models import Charge, Commission, Expense, Payment, RecurringSubscription, Revenue


@admin.register(Charge)
class ChargeAdmin(admin.ModelAdmin):
    list_display = ("charge_type", "customer", "project", "amount", "status", "due_date")
    list_filter = ("charge_type", "status")
    search_fields = ("customer__legal_name", "external_id")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("charge", "amount", "method", "paid_at")
    search_fields = ("external_id",)
    readonly_fields = ("external_id", "raw_payload")


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ("source", "amount", "received_at")
    list_filter = ("source",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "category", "amount", "status", "due_date")
    list_filter = ("status", "category")


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("sales_rep", "project", "amount", "status", "created_at")
    list_filter = ("status",)
    readonly_fields = ("payment",)


@admin.register(RecurringSubscription)
class RecurringSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("service_description", "customer", "amount", "status", "next_billing_date")
    list_filter = ("status", "frequency")
    search_fields = ("customer__legal_name", "service_description")
