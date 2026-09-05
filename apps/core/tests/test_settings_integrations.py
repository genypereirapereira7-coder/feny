from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Role, User


class IntegrationsStatusApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="a1", password="senha-forte-123", role=Role.ADMIN)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)

    def test_admin_ve_status_das_integracoes(self):
        self.client.force_authenticate(self.admin)
        resposta = self.client.get("/api/v1/settings/integrations/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("mercadopago", resposta.data)
        self.assertIn("whatsapp", resposta.data)
        self.assertIn("configured", resposta.data["mercadopago"])

    def test_gerente_nao_ve_configuracoes(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/settings/integrations/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
