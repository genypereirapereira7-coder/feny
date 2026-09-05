"""Matriz de permissões de `support` — domínio novo (não está na tabela
original de ARCHITECTURE.md §9, que nem previa esta app).

| Papel     | Ver  | Criar/editar/agir |
|-----------|------|--------------------|
| Admin     | tudo | sim                |
| Manager   | tudo | sim                |
| Support   | tudo | sim                |
| demais    | não  | não                |

Sem `destroy` — chamado se fecha, nunca se apaga.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role

_PODE_GERENCIAR = (Role.ADMIN, Role.MANAGER, Role.SUPPORT)


class TicketPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.role in _PODE_GERENCIAR
