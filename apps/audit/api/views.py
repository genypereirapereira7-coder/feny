from rest_framework import mixins, viewsets

from apps.audit.api.serializers import AuditLogSerializer
from apps.audit.models import AuditLog
from apps.core.permissions import role_required
from apps.users.models import Role


def _filtrar(qs, params):
    entity_type = params.get("entity_type")
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    entity_id = params.get("entity_id")
    if entity_id:
        qs = qs.filter(entity_id=entity_id)
    action = params.get("action")
    if action:
        qs = qs.filter(action=action)
    user_id = params.get("user")
    if user_id:
        qs = qs.filter(user_id=user_id)
    return qs


class AuditLogViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Só leitura — `AuditLog` nasce exclusivamente de `apps.audit.services.record`,
    chamado pelos services de domínio (ARCHITECTURE.md §15). Frontend §9: só
    Admin/Manager veem auditoria."""

    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = [role_required(Role.ADMIN, Role.MANAGER)]

    def get_queryset(self):
        return _filtrar(super().get_queryset(), self.request.query_params)
