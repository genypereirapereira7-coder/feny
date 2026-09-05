from rest_framework import serializers

from apps.core.choices import PaymentMethod
from apps.finance import services
from apps.finance.models import Charge, Commission, Expense, Payment, RecurringSubscription, Revenue
from apps.projects.models import Project


class ChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charge
        fields = (
            "id", "project", "customer", "charge_type", "percentage", "amount", "due_date",
            "status", "payment_method", "external_provider", "external_id", "payment_link",
            "paid_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class ChargeCreateSerializer(serializers.Serializer):
    """Entrada de `create-initial`/`create-final` — não é a cobrança em si
    (essa é sempre calculada pelo service, nunca informada pelo cliente da
    API); só o projeto e, opcionalmente, o vencimento/forma de pagamento."""

    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    due_date = serializers.DateField(required=False)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, required=False)


class ConfirmPaymentSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    method = serializers.CharField(max_length=20)
    paid_at = serializers.DateTimeField(required=False)
    raw_payload = serializers.JSONField(required=False)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "charge", "amount", "external_id", "method", "paid_at", "created_at")
        read_only_fields = fields


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = (
            "id", "category", "description", "amount", "due_date", "paid_at", "status",
            "document", "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "paid_at", "status", "created_by", "created_at", "updated_at")


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringSubscription
        fields = (
            "id", "customer", "project", "service_description", "amount", "frequency",
            "start_date", "next_billing_date", "status", "external_id", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "next_billing_date", "status", "external_id", "created_at", "updated_at",
        )

    def create(self, validated_data):
        """Nunca `RecurringSubscription.objects.create()` direto — sempre por
        `services.create_subscription`, que fixa `next_billing_date` a partir
        de `start_date` num único lugar (ARCHITECTURE.md §6.5)."""
        return services.create_subscription(
            validated_data.pop("customer"), self.context["request"].user, **validated_data,
        )

    def update(self, instance, validated_data):
        """Só os campos descritivos são editáveis. `amount`/`frequency`
        mudarem no meio de uma assinatura ativa não é uma edição de campo,
        seria uma decisão de negócio (reajuste) que esta fase não define —
        cancelar e criar de novo é o caminho por enquanto."""
        campos_nao_editaveis = set(validated_data) - {"service_description", "project"}
        if campos_nao_editaveis:
            raise serializers.ValidationError(
                {campo: "Não é possível editar este campo de uma assinatura existente." for campo in campos_nao_editaveis}
            )
        return super().update(instance, validated_data)


class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = ("id", "source", "payment", "amount", "description", "received_at", "created_at")
        read_only_fields = fields


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = (
            "id", "sales_rep", "project", "payment", "percentage", "amount", "status",
            "created_at", "paid_at",
        )
        read_only_fields = fields
