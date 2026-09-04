"""Matriz de permissões de `projects` — ARCHITECTURE.md §9.

| Papel     | Ver                       | Criar (gerar de orçamento) | Editar / avançar etapa    |
|-----------|---------------------------|-----------------------------|---------------------------|
| Admin     | tudo                      | sim                          | qualquer                  |
| Manager   | tudo                      | sim                          | qualquer                  |
| Sales     | só os relacionados (*)    | não                          | não                        |
| Developer | só os designados          | não                          | só os designados          |
| Finance   | tudo                      | não                          | não                        |
| Support   | tudo                      | não                          | não                        |

(*) "relacionado" = o vendedor do orçamento que originou o projeto.

"Avançar etapa" cobre as ações de domínio expostas na API — `start-development`,
`complete-development`, `accept`, `mark-delivered`, `enter-maintenance` — que
seguem a mesma regra de "editar": admin/gerente sempre, desenvolvedor só se
for o responsável. As transições disparadas por cobrança/pagamento
(`request_initial_payment`, `confirm_initial_payment`, `request_final_payment`,
`confirm_final_payment`) não têm rota de API própria — só `apps.finance`
chama, internamente (ver `apps/projects/services.py`).

Sem `destroy`: mesma lógica do orçamento (§48 da spec técnica) — um projeto
carrega valor de auditoria e, a partir da Fase 5, cobranças penduradas nele;
não se apaga, e a máquina de estado ainda nem tem um estado terminal de
cancelamento definido em §7.2.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import Role

_PODE_GERENCIAR = (Role.ADMIN, Role.MANAGER)
_ACOES_DE_AVANCO = (
    "update", "partial_update",
    "start_development", "complete_development", "accept", "mark_delivered", "enter_maintenance",
)


class ProjectPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if view.action in ("list", "retrieve"):
            return True
        if view.action == "create":
            return user.role in _PODE_GERENCIAR
        if view.action in _ACOES_DE_AVANCO:
            return user.role in (*_PODE_GERENCIAR, Role.DEVELOPER)
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.role in _PODE_GERENCIAR:
            return True
        if user.role == Role.DEVELOPER:
            if view.action in _ACOES_DE_AVANCO:
                return obj.responsible_id == user.id
            return view.action in ("list", "retrieve")
        if user.role == Role.SALES:
            if view.action in ("list", "retrieve"):
                return obj.quotation.sales_rep_id == user.id
            return False
        # Finance e Support: só leitura.
        return view.action in ("list", "retrieve")
