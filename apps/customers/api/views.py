from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.customers.api.serializers import CustomerContactSerializer, CustomerSerializer
from apps.customers.models import Customer, CustomerContact
from apps.customers.permissions import CustomerPermission


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.select_related("created_by").prefetch_related("contacts")
    serializer_class = CustomerSerializer
    permission_classes = [CustomerPermission]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CustomerContactViewSet(viewsets.ModelViewSet):
    """`/api/v1/customer-contacts/?customer=<id>` — sem router aninhado de
    propósito: um parâmetro de query resolve sem puxar dependência nova."""

    serializer_class = CustomerContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = CustomerContact.objects.select_related("customer")
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs
