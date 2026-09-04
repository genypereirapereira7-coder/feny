from rest_framework import serializers

from apps.projects import services
from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "id", "customer", "quotation", "name", "project_type", "description",
            "responsible", "amount", "status", "expected_delivery_at", "delivered_at",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "customer", "project_type", "amount", "status", "delivered_at",
            "created_at", "updated_at",
        )

    def create(self, validated_data):
        """Um projeto nunca nasce de um `Project.objects.create()` direto —
        sempre de `services.generate_project_from_quotation`, que valida o
        orçamento e grava auditoria (ARCHITECTURE.md §6.4)."""
        quotation = validated_data.pop("quotation")
        return services.generate_project_from_quotation(
            quotation,
            self.context["request"].user,
            name=validated_data["name"],
            responsible=validated_data["responsible"],
            description=validated_data.get("description", ""),
            expected_delivery_at=validated_data.get("expected_delivery_at"),
        )
