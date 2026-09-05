from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.quotations import services
from apps.quotations.api.serializers import QuotationSerializer
from apps.quotations.models import Quotation
from apps.quotations.permissions import QuotationPermission
from apps.users.models import Role


def _filtrar(qs, params):
    """Filtros de `?query=` pro frontend (spec de frontend §22) — parâmetro
    a parâmetro, sem `django-filter`: mesmo padrão manual já usado em
    `CustomerContactViewSet`, não vale puxar dependência nova pra isto."""
    status = params.get("status")
    if status:
        qs = qs.filter(status=status)
    customer = params.get("customer")
    if customer:
        qs = qs.filter(customer_id=customer)
    sales_rep = params.get("sales_rep")
    if sales_rep:
        qs = qs.filter(sales_rep_id=sales_rep)
    data_de = params.get("date_from")
    if data_de:
        qs = qs.filter(created_at__date__gte=data_de)
    data_ate = params.get("date_to")
    if data_ate:
        qs = qs.filter(created_at__date__lte=data_ate)
    valor_min = params.get("amount_min")
    if valor_min:
        qs = qs.filter(amount__gte=valor_min)
    valor_max = params.get("amount_max")
    if valor_max:
        qs = qs.filter(amount__lte=valor_max)
    return qs


class QuotationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Sem `destroy` — ver `apps/quotations/permissions.py`."""

    queryset = Quotation.objects.select_related("customer", "sales_rep", "decided_by")
    serializer_class = QuotationSerializer
    permission_classes = [QuotationPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.SALES:
            qs = qs.filter(sales_rep=self.request.user)
        return _filtrar(qs, self.request.query_params)

    def perform_create(self, serializer):
        serializer.save(sales_rep=self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        quotation = self.get_object()
        services.submit_for_approval(quotation, request.user)
        return Response(self.get_serializer(quotation).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        quotation = self.get_object()
        services.approve_quotation(quotation, request.user)
        return Response(self.get_serializer(quotation).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        quotation = self.get_object()
        reason = request.data.get("reason", "")
        services.reject_quotation(quotation, request.user, reason=reason)
        return Response(self.get_serializer(quotation).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        quotation = self.get_object()
        services.cancel_quotation(quotation, request.user)
        return Response(self.get_serializer(quotation).data)
