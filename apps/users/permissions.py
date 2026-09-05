"""Permissões de `users` (ARCHITECTURE.md §9).

`Settings` no §9 é `ADMIN`-only, mas "ver a lista de usuários" não é a mesma
coisa que administrar conta — `MANAGER` já pode gerar projeto e escolher o
responsável (`apps.projects`), e pra isso precisa enxergar quem existe.
`list`/`retrieve` abrem pra `MANAGER` por esse motivo concreto; criar,
editar, desativar conta e resetar 2FA continuam só `ADMIN`.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role


class UserPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("list", "retrieve"):
            return user.role in (Role.ADMIN, Role.MANAGER)
        return user.role == Role.ADMIN
