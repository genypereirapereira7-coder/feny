from django.contrib import admin

from apps.projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "customer", "responsible", "amount", "status", "created_at")
    list_filter = ("status", "project_type")
    search_fields = ("name", "customer__legal_name")
    readonly_fields = ("quotation", "amount")
