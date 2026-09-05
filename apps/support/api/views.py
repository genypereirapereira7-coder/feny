from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.support import services
from apps.support.api.serializers import AssignTicketSerializer, TicketSerializer
from apps.support.models import Ticket
from apps.support.permissions import TicketPermission
from apps.users.models import User


def _filtrar(qs, params):
    status = params.get("status")
    if status:
        qs = qs.filter(status=status)
    customer = params.get("customer")
    if customer:
        qs = qs.filter(customer_id=customer)
    assigned_to = params.get("assigned_to")
    if assigned_to:
        qs = qs.filter(assigned_to_id=assigned_to)
    return qs


class TicketViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Sem `destroy` — ver `apps/support/permissions.py`."""

    queryset = Ticket.objects.select_related("customer", "assigned_to", "created_by")
    serializer_class = TicketSerializer
    permission_classes = [TicketPermission]

    def get_queryset(self):
        return _filtrar(super().get_queryset(), self.request.query_params)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        entrada = AssignTicketSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            assignee = User.objects.get(pk=entrada.validated_data["assigned_to"])
        except User.DoesNotExist as exc:
            raise ValidationError({"assigned_to": "Usuário não encontrado."}) from exc

        ticket = services.assign_ticket(self.get_object(), request.user, assignee)
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        ticket = services.resolve_ticket(self.get_object(), request.user)
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        ticket = services.close_ticket(self.get_object(), request.user)
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        ticket = services.reopen_ticket(self.get_object(), request.user)
        return Response(self.get_serializer(ticket).data)
