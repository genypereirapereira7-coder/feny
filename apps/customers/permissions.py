"""Matriz de permissões de `customers` — ARCHITECTURE.md §9.

| Papel     | Ver | Criar | Editar                  | Excluir |
|-----------|-----|-------|-------------------------|---------|
| Admin     | sim | sim   | qualquer                | sim     |
| Manager   | sim | sim   | qualquer                | sim     |
| Sales     | sim | sim   | só os que criou         | não     |
| Developer | sim | não   | não                     | não     |
| Finance   | sim | não   | não                     | não     |
| Support   | sim | não   | qualquer (sem excluir)  | não     |

"Support edita qualquer cliente" é a leitura mais razoável de "acesso
limitado" da spec de negócio até o negócio precisar de algo mais fino — sem
um exemplo concreto do que fica de fora, restringir por campo seria
adivinhação.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role

_PODE_CRIAR = (Role.ADMIN, Role.MANAGER, Role.SALES)
_PODE_EDITAR = (Role.ADMIN, Role.MANAGER, Role.SALES, Role.SUPPORT)
_PODE_EXCLUIR = (Role.ADMIN, Role.MANAGER)


class CustomerPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if view.action in ("list", "retrieve"):
            return True
        if view.action == "create":
            return user.role in _PODE_CRIAR
        if view.action in ("update", "partial_update"):
            return user.role in _PODE_EDITAR
        if view.action == "destroy":
            return user.role in _PODE_EXCLUIR
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.role in (Role.ADMIN, Role.MANAGER):
            return True
        if view.action in ("update", "partial_update") and user.role == Role.SALES:
            return obj.created_by_id == user.id
        if view.action in ("update", "partial_update") and user.role == Role.SUPPORT:
            return True
        return view.action in ("list", "retrieve")
