"""Quem enxerga e mexe em lead — ARCHITECTURE.md §9.

| Papel     | Ver | Atender (ações) | Editar anotação |
|-----------|-----|-----------------|-----------------|
| Admin     | sim | sim             | sim             |
| Manager   | sim | sim             | sim             |
| Sales     | sim | sim             | sim             |
| Developer | não | não             | não             |
| Finance   | não | não             | não             |
| Support   | sim | não             | não             |

Lead é matéria-prima comercial: quem vende trabalha nele, suporte só consulta
(pra reconhecer um contato que já apareceu antes), e desenvolvimento/financeiro
não têm o que fazer com ele. Excluir não está na tabela porque a API não expõe
`destroy` — lead descartado vira histórico (`LeadStatus.DISCARDED`), não some.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role

_PODE_VER = (Role.ADMIN, Role.MANAGER, Role.SALES, Role.SUPPORT)
_PODE_ATENDER = (Role.ADMIN, Role.MANAGER, Role.SALES)


class LeadPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if view.action in ("list", "retrieve"):
            return user.role in _PODE_VER
        return user.role in _PODE_ATENDER
