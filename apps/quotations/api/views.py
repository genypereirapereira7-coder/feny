from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.quotations import services
from apps.quotations.api.serializers import QuotationSerializer
from apps.quotations.models import Quotation
from apps.quotations.permissions import QuotationPermission
from apps.users.models import Role


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
        return qs

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
