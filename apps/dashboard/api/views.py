from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard import services


class DashboardSummaryView(APIView):
    """`GET /api/v1/dashboard/summary/` (ARCHITECTURE.md §12). Sem
    `role_required` — todo papel autenticado tem alguma seção pra ver;
    `build_summary` decide o quê, nunca o cliente da API."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.build_summary(request.user))
