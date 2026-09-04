from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import role_required
from apps.reports import services
from apps.users.models import Role

_MESES_PADRAO = 6
_MESES_MAXIMO = 24


class RevenueByMonthView(APIView):
    """`GET /api/v1/reports/revenue-by-month/?months=6` — só quem tem acesso
    a `finance` (ARCHITECTURE.md §9); Manager vê (não só admin/financeiro),
    igual ao resto do domínio financeiro."""

    permission_classes = [role_required(Role.ADMIN, Role.MANAGER, Role.FINANCE)]

    def get(self, request):
        try:
            months = int(request.query_params.get("months", _MESES_PADRAO))
        except ValueError:
            months = _MESES_PADRAO
        months = max(1, min(months, _MESES_MAXIMO))

        return Response(services.revenue_by_month(months=months))
