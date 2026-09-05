from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import role_required
from apps.users.models import Role


class IntegrationsStatusView(APIView):
    """`GET /api/v1/settings/integrations/` — tela de Configurações (frontend
    Fase 9). Só leitura: diz se cada integração externa tem credencial
    configurada no ambiente, nunca expõe o valor do segredo em si — editar
    fica no `.env`/variável de ambiente do deploy, não por aqui (ARCHITECTURE.md
    §13: segredo nunca passa pela API). Admin-only, mesmo critério da coluna
    "Settings" da matriz de permissões (§9)."""

    permission_classes = [role_required(Role.ADMIN)]

    def get(self, request):
        return Response({
            "mercadopago": {"configured": bool(settings.MERCADOPAGO_ACCESS_TOKEN)},
            "whatsapp": {
                "configured": bool(settings.EVOLUTION_API_BASE_URL and settings.EVOLUTION_API_KEY),
            },
        })
