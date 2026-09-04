from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Role, User


class DashboardSummaryApiTests(APITestCase):
    def setUp(self):
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)

    def test_exige_autenticacao(self):
        resposta = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_gerente_ve_secoes_completas(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(set(resposta.data), {"quotations", "projects", "finance", "customers"})

    def test_vendedor_ve_so_sales(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(set(resposta.data), {"sales"})
