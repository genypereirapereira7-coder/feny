from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id", "user", "action", "entity_type", "entity_id", "before", "after", "metadata", "created_at",
        )
        read_only_fields = fields
