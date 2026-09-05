from rest_framework import serializers

from apps.support.models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            "id", "customer", "subject", "description", "priority", "status",
            "assigned_to", "created_by", "resolved_at", "created_at", "updated_at",
        )
        read_only_fields = ("id", "status", "assigned_to", "created_by", "resolved_at", "created_at", "updated_at")


class AssignTicketSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()
