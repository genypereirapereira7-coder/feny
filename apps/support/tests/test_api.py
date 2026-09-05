from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.choices import PaymentMethod
from apps.customers.models import Customer, CustomerKind
from apps.support.models import TicketStatus
from apps.users.models import Role, User


class SupportApiTestCase(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.suporte = User.objects.create_user(username="s1", password="senha-forte-123", role=Role.SUPPORT)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )


class TicketPermissionTests(SupportApiTestCase):
    def test_suporte_cria_chamado(self):
        self.client.force_authenticate(self.suporte)
        resposta = self.client.post(
            "/api/v1/support/tickets/",
            {"customer": str(self.cliente.id), "subject": "Site fora do ar", "description": "Erro 500 na home"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["status"], TicketStatus.OPEN)
        self.assertEqual(resposta.data["created_by"], self.suporte.id)

    def test_vendedor_nao_acessa_suporte(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/support/tickets/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_dev_nao_acessa_suporte(self):
        self.client.force_authenticate(self.dev)
        resposta = self.client.post(
            "/api/v1/support/tickets/", {"customer": str(self.cliente.id), "subject": "x", "description": "y"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_filtra_por_status_e_cliente(self):
        self.client.force_authenticate(self.suporte)
        self.client.post(
            "/api/v1/support/tickets/",
            {"customer": str(self.cliente.id), "subject": "Chamado 1", "description": "..."},
        )
        resposta = self.client.get(f"/api/v1/support/tickets/?status=OPEN&customer={self.cliente.id}")
        self.assertEqual(len(resposta.data["results"]), 1)

        resposta_vazia = self.client.get("/api/v1/support/tickets/?status=CLOSED")
        self.assertEqual(len(resposta_vazia.data["results"]), 0)


class TicketLifecycleTests(SupportApiTestCase):
    def _criar_chamado(self):
        self.client.force_authenticate(self.suporte)
        return self.client.post(
            "/api/v1/support/tickets/",
            {"customer": str(self.cliente.id), "subject": "Dúvida sobre fatura", "description": "..."},
        ).data

    def test_fluxo_completo(self):
        chamado = self._criar_chamado()

        resposta_assign = self.client.post(
            f"/api/v1/support/tickets/{chamado['id']}/assign/", {"assigned_to": str(self.suporte.id)},
        )
        self.assertEqual(resposta_assign.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_assign.data["status"], TicketStatus.IN_PROGRESS)
        self.assertEqual(resposta_assign.data["assigned_to"], self.suporte.id)

        resposta_resolve = self.client.post(f"/api/v1/support/tickets/{chamado['id']}/resolve/")
        self.assertEqual(resposta_resolve.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_resolve.data["status"], TicketStatus.RESOLVED)
        self.assertIsNotNone(resposta_resolve.data["resolved_at"])

        resposta_close = self.client.post(f"/api/v1/support/tickets/{chamado['id']}/close/")
        self.assertEqual(resposta_close.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_close.data["status"], TicketStatus.CLOSED)

        resposta_reopen = self.client.post(f"/api/v1/support/tickets/{chamado['id']}/reopen/")
        self.assertEqual(resposta_reopen.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_reopen.data["status"], TicketStatus.OPEN)
        self.assertIsNone(resposta_reopen.data["resolved_at"])

    def test_nao_resolve_chamado_ainda_aberto(self):
        chamado = self._criar_chamado()
        resposta = self.client.post(f"/api/v1/support/tickets/{chamado['id']}/resolve/")
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nao_reatribui_chamado_fechado(self):
        chamado = self._criar_chamado()
        self.client.post(f"/api/v1/support/tickets/{chamado['id']}/assign/", {"assigned_to": str(self.suporte.id)})
        self.client.post(f"/api/v1/support/tickets/{chamado['id']}/resolve/")
        self.client.post(f"/api/v1/support/tickets/{chamado['id']}/close/")

        resposta = self.client.post(
            f"/api/v1/support/tickets/{chamado['id']}/assign/", {"assigned_to": str(self.suporte.id)},
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
