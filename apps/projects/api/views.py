from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects import services
from apps.projects.api.serializers import ProjectSerializer
from apps.projects.models import Project
from apps.projects.permissions import ProjectPermission
from apps.users.models import Role


class ProjectViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Sem `destroy` — ver `apps/projects/permissions.py`.

    As ações abaixo cobrem só as transições de estado disparadas por gente
    (§7.2) — as disparadas por cobrança/pagamento vivem em `apps.finance`."""

    queryset = Project.objects.select_related("customer", "quotation", "responsible")
    serializer_class = ProjectSerializer
    permission_classes = [ProjectPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == Role.SALES:
            qs = qs.filter(quotation__sales_rep=user)
        elif user.role == Role.DEVELOPER:
            qs = qs.filter(responsible=user)
        return qs

    @action(detail=True, methods=["post"], url_path="start-development")
    def start_development(self, request, pk=None):
        project = services.start_development(self.get_object(), request.user)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"], url_path="complete-development")
    def complete_development(self, request, pk=None):
        project = services.complete_development(self.get_object(), request.user)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        project = services.register_client_acceptance(self.get_object(), request.user)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"], url_path="mark-delivered")
    def mark_delivered(self, request, pk=None):
        project = services.mark_delivered(self.get_object(), request.user)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"], url_path="enter-maintenance")
    def enter_maintenance(self, request, pk=None):
        project = services.enter_maintenance(self.get_object(), request.user)
        return Response(self.get_serializer(project).data)
