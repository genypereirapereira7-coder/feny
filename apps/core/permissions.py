"""Permissões de domínio, baseadas em papel (ARCHITECTURE.md §9).

Autorização é sempre decidida aqui, no backend — nunca inferida do frontend.
Cada app de domínio (customers, quotations, projects, finance...) define suas
próprias regras de escopo (ex.: "vendedor só vê os próprios orçamentos") nos
`get_queryset()` dos seus ViewSets; esta classe cobre só o portão de entrada
por papel, comum a todos.
"""

from rest_framework.permissions import BasePermission


def role_required(*roles: str) -> type[BasePermission]:
    """Fábrica de permissão DRF: `permission_classes = [role_required(Role.ADMIN)]`."""

    class _HasRole(BasePermission):
        def has_permission(self, request, view) -> bool:
            user = request.user
            return bool(user and user.is_authenticated and user.role in roles)

    return _HasRole
