from rest_framework import serializers

from apps.quotations.models import Quotation, QuotationStatus


class QuotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quotation
        fields = (
            "id", "customer", "sales_rep", "service_type", "description",
            "amount", "deadline_days", "status", "notes",
            "decided_at", "decided_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "sales_rep", "status", "decided_at", "decided_by",
            "created_at", "updated_at",
        )

    def update(self, instance, validated_data):
        """Editar campos do orçamento (valor, descrição...) só faz sentido
        enquanto ele ainda é rascunho — depois de enviado, a única forma de
        mudar é cancelar e criar de novo (não existe transição de volta pra
        DRAFT no estado da máquina, ARCHITECTURE.md §7.1)."""
        if instance.status != QuotationStatus.DRAFT:
            raise serializers.ValidationError("Só é possível editar um orçamento em rascunho.")
        return super().update(instance, validated_data)
