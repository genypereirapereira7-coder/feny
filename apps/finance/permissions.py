"""Matriz de permissões de `finance` — ARCHITECTURE.md §9.

| Papel     | Charges/Payments/Expenses/Subscriptions | Commissions              |
|-----------|-------------------------------------------|---------------------------|
| Admin     | CRUD + ações de domínio                    | vê tudo, marca como paga |
| Manager   | só vê                                      | vê tudo                  |
| Finance   | CRUD + ações de domínio                    | vê tudo, marca como paga |
| Sales     | sem acesso                                 | só as próprias, só vê    |
| Developer | sem acesso                                 | sem acesso                |
| Support   | sem acesso                                 | sem acesso                |

`can_confirm_manual_payment` (§9) não é uma permissão solta — é só
admin/finance chegando em `confirm-payment`, e o service ainda audita cada
chamada. Sem `destroy` em nenhum recurso financeiro (§ soft-delete restraint):
cobrança e despesa se cancelam, nunca se apagam.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role

_PODE_GERENCIAR = (Role.ADMIN, Role.FINANCE)


class ChargePermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("list", "retrieve"):
            return user.role in (*_PODE_GERENCIAR, Role.MANAGER)
        return user.role in _PODE_GERENCIAR


class ExpensePermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("list", "retrieve"):
            return user.role in (*_PODE_GERENCIAR, Role.MANAGER)
        return user.role in _PODE_GERENCIAR


class SubscriptionPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("list", "retrieve"):
            return user.role in (*_PODE_GERENCIAR, Role.MANAGER)
        return user.role in _PODE_GERENCIAR


class CommissionPermission(BasePermission):
    """Só leitura pra todo mundo autorizado — `pay` é a única ação de escrita,
    e só admin/financeiro chega nela."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action == "pay":
            return user.role in _PODE_GERENCIAR
        return user.role in (*_PODE_GERENCIAR, Role.MANAGER, Role.SALES)

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.role in (*_PODE_GERENCIAR, Role.MANAGER):
            return True
        if user.role == Role.SALES:
            return obj.sales_rep_id == user.id
        return False
