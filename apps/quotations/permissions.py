"""Matriz de permissões de `quotations` — ARCHITECTURE.md §9.

| Papel     | Ver              | Criar | Editar (só DRAFT) | Aprovar/Rejeitar |
|-----------|------------------|-------|--------------------|-------------------|
| Admin     | tudo             | sim   | qualquer           | sim               |
| Manager   | tudo             | sim   | qualquer           | sim               |
| Sales     | só os que criou  | sim   | só os que criou    | não               |
| Developer | tudo             | não   | não                | não               |
| Finance   | tudo             | não   | não                | não               |
| Support   | tudo             | não   | não                | não               |

Sem `destroy`: orçamento não se apaga, se cancela (§48 da spec técnica).
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role

_PODE_CRIAR = (Role.ADMIN, Role.MANAGER, Role.SALES)
_PODE_EDITAR = (Role.ADMIN, Role.MANAGER, Role.SALES)
_PODE_DECIDIR = (Role.ADMIN, Role.MANAGER)


class QuotationPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if view.action in ("list", "retrieve"):
            return True
        if view.action == "create":
            return user.role in _PODE_CRIAR
        if view.action in ("update", "partial_update", "submit", "cancel"):
            return user.role in _PODE_EDITAR
        if view.action in ("approve", "reject"):
            return user.role in _PODE_DECIDIR
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.role in (Role.ADMIN, Role.MANAGER):
            return True
        if user.role == Role.SALES:
            if view.action in ("update", "partial_update", "submit", "cancel"):
                return obj.sales_rep_id == user.id
            return view.action in ("list", "retrieve")
        return view.action in ("list", "retrieve")
