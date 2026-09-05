from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.services import record
from apps.core.choices import PaymentMethod
from apps.customers.models import Customer, CustomerKind
from apps.users.models import Role, User


class AuditLogApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="a1", password="senha-forte-123", role=Role.ADMIN)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )
        record(user=self.vendedor, action="customer.created", entity=self.cliente, before=None, after={"x": 1})

    def test_admin_ve_auditoria(self):
        self.client.force_authenticate(self.admin)
        resposta = self.client.get("/api/v1/audit/logs/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resposta.data["count"], 1)

    def test_gerente_ve_auditoria(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/audit/logs/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_vendedor_nao_ve_auditoria(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/audit/logs/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_filtra_por_entity_type(self):
        self.client.force_authenticate(self.admin)
        resposta = self.client.get("/api/v1/audit/logs/?entity_type=customers.customer")
        self.assertEqual(len(resposta.data["results"]), 1)

        resposta_vazia = self.client.get("/api/v1/audit/logs/?entity_type=finance.charge")
        self.assertEqual(len(resposta_vazia.data["results"]), 0)
