from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "category", "customer", "size_bytes", "uploaded_by", "created_at")
    list_filter = ("category",)
    search_fields = ("original_filename",)
