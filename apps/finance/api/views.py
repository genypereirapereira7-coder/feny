from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.finance import services
from apps.finance.api.serializers import (
    ChargeCreateSerializer,
    ChargeSerializer,
    CommissionSerializer,
    ConfirmPaymentSerializer,
    ExpenseSerializer,
    PaymentSerializer,
    RevenueSerializer,
    SubscriptionSerializer,
)
from apps.finance.models import Charge, Commission, Expense, Payment, RecurringSubscription, Revenue
from apps.finance.permissions import (
    ChargePermission,
    CommissionPermission,
    ExpensePermission,
    SubscriptionPermission,
)
from apps.users.models import Role


class ChargeViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Sem `create`/`update`/`destroy` genéricos — uma cobrança só nasce por
    `create-initial`/`create-final` (o valor é sempre calculado, nunca
    informado) e só muda de estado por `confirm-payment`/`cancel`."""

    queryset = Charge.objects.select_related("project", "customer")
    serializer_class = ChargeSerializer
    permission_classes = [ChargePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        # `?project=`/`?customer=`/`?status=` — frontend §22/§26/§30.
        for campo in ("project", "customer", "status"):
            valor = self.request.query_params.get(campo)
            if valor:
                qs = qs.filter(**{campo if campo == "status" else f"{campo}_id": valor})
        return qs

    @action(detail=False, methods=["post"], url_path="create-initial")
    def create_initial(self, request):
        entrada = ChargeCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        charge = services.create_initial_charge(actor=request.user, **entrada.validated_data)
        return Response(ChargeSerializer(charge).data, status=201)

    @action(detail=False, methods=["post"], url_path="create-final")
    def create_final(self, request):
        entrada = ChargeCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        charge = services.create_final_charge(actor=request.user, **entrada.validated_data)
        return Response(ChargeSerializer(charge).data, status=201)

    @action(detail=True, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        entrada = ConfirmPaymentSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        charge = services.confirm_payment(self.get_object(), request.user, **entrada.validated_data)
        return Response(self.get_serializer(charge).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        charge = services.cancel_charge(self.get_object(), request.user)
        return Response(self.get_serializer(charge).data)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        charge = services.issue_charge(self.get_object(), request.user)
        return Response(self.get_serializer(charge).data)


class PaymentViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Só leitura — `Payment` nasce exclusivamente dentro de
    `finance.services.confirm_payment`."""

    queryset = Payment.objects.select_related("charge")
    serializer_class = PaymentSerializer
    permission_classes = [ChargePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        charge_id = self.request.query_params.get("charge")
        if charge_id:
            qs = qs.filter(charge_id=charge_id)
        return qs


class RevenueViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Só leitura — livro-razão derivado de `finance.services.confirm_payment`,
    nunca um cadastro manual (ver docstring de `Revenue`)."""

    queryset = Revenue.objects.select_related("payment")
    serializer_class = RevenueSerializer
    permission_classes = [ChargePermission]


class ExpenseViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Sem `destroy` — despesa se cancela (`cancel`), não se apaga."""

    queryset = Expense.objects.select_related("created_by", "document")
    serializer_class = ExpenseSerializer
    permission_classes = [ExpensePermission]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        expense = services.pay_expense(self.get_object(), request.user)
        return Response(self.get_serializer(expense).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        expense = services.cancel_expense(self.get_object(), request.user)
        return Response(self.get_serializer(expense).data)


class SubscriptionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Sem `destroy` — assinatura se cancela (`cancel`), não se apaga."""

    queryset = RecurringSubscription.objects.select_related("customer", "project")
    serializer_class = SubscriptionSerializer
    permission_classes = [SubscriptionPermission]

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        subscription = services.pause_subscription(self.get_object(), request.user)
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        subscription = services.resume_subscription(self.get_object(), request.user)
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        subscription = services.cancel_subscription(self.get_object(), request.user)
        return Response(self.get_serializer(subscription).data)


class CommissionViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Commission.objects.select_related("sales_rep", "project")
    serializer_class = CommissionSerializer
    permission_classes = [CommissionPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.SALES:
            qs = qs.filter(sales_rep=self.request.user)
        return qs

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        commission = services.pay_commission(self.get_object(), request.user)
        return Response(self.get_serializer(commission).data)
