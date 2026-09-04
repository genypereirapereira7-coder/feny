from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Role, User


class RevenueByMonthApiTests(APITestCase):
    def setUp(self):
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

    def test_gerente_acessa(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/reports/revenue-by-month/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta.data), 6)

    def test_developer_nao_acessa(self):
        self.client.force_authenticate(self.dev)
        resposta = self.client.get("/api/v1/reports/revenue-by-month/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_respeita_parametro_months(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/reports/revenue-by-month/?months=2")
        self.assertEqual(len(resposta.data), 2)

    def test_parametro_invalido_usa_padrao(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/reports/revenue-by-month/?months=abc")
        self.assertEqual(len(resposta.data), 6)

    def test_parametro_acima_do_limite_e_limitado(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/reports/revenue-by-month/?months=999")
        self.assertEqual(len(resposta.data), 24)
