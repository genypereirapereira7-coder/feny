from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.choices import PaymentMethod, ProjectType
from apps.customers.models import Customer, CustomerKind
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class QuotationApiTestCase(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.outro_vendedor = User.objects.create_user(username="v2", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )
        self.payload = {
            "customer": str(self.cliente.id), "service_type": ProjectType.WEBSITE,
            "description": "Site institucional", "amount": "10000.00",
        }


class QuotationCrudTests(QuotationApiTestCase):
    def test_vendedor_cria_orcamento(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post("/api/v1/quotations/", self.payload)

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        # `resposta.data` é o dict pré-render do DRF — o campo UUID ainda não
        # virou string (isso só acontece na hora de serializar pra JSON).
        self.assertEqual(resposta.data["sales_rep"], self.vendedor.id)
        self.assertEqual(resposta.data["status"], QuotationStatus.DRAFT)

    def test_desenvolvedor_nao_cria_orcamento(self):
        self.client.force_authenticate(self.dev)
        resposta = self.client.post("/api/v1/quotations/", self.payload)
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendedor_so_ve_os_proprios_orcamentos(self):
        self.client.force_authenticate(self.vendedor)
        meu = self.client.post("/api/v1/quotations/", self.payload).data

        self.client.force_authenticate(self.outro_vendedor)
        self.client.post("/api/v1/quotations/", self.payload)

        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/quotations/")

        ids = [item["id"] for item in resposta.data["results"]]
        self.assertEqual(ids, [meu["id"]])

    def test_gerente_ve_todos_os_orcamentos(self):
        self.client.force_authenticate(self.vendedor)
        self.client.post("/api/v1/quotations/", self.payload)
        self.client.force_authenticate(self.outro_vendedor)
        self.client.post("/api/v1/quotations/", self.payload)

        self.client.force_authenticate(self.gerente)
        resposta = self.client.get("/api/v1/quotations/")
        self.assertEqual(len(resposta.data["results"]), 2)

    def test_edita_rascunho(self):
        self.client.force_authenticate(self.vendedor)
        criado = self.client.post("/api/v1/quotations/", self.payload).data

        resposta = self.client.patch(f"/api/v1/quotations/{criado['id']}/", {"amount": "12000.00"})
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["amount"], "12000.00")

    def test_nao_edita_orcamento_ja_enviado(self):
        self.client.force_authenticate(self.vendedor)
        criado = self.client.post("/api/v1/quotations/", self.payload).data
        self.client.post(f"/api/v1/quotations/{criado['id']}/submit/")

        resposta = self.client.patch(f"/api/v1/quotations/{criado['id']}/", {"amount": "12000.00"})
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sem_rota_de_exclusao(self):
        """`QuotationViewSet` não tem `destroy` — o router nem mapeia DELETE
        pra nenhuma action, então `view.action` chega `None` na permission, que
        nega por padrão (403). Um 405 também seria uma resposta aceitável;
        o que importa é que DELETE nunca apaga um orçamento."""
        self.client.force_authenticate(self.gerente)
        criado_por_vendedor = Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="x", amount="1000.00",
        )
        resposta = self.client.delete(f"/api/v1/quotations/{criado_por_vendedor.id}/")
        self.assertIn(resposta.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))
        self.assertTrue(Quotation.objects.filter(id=criado_por_vendedor.id).exists())


class QuotationApprovalFlowTests(QuotationApiTestCase):
    def _criar_e_enviar(self, autenticado_como) -> dict:
        self.client.force_authenticate(autenticado_como)
        criado = self.client.post("/api/v1/quotations/", self.payload).data
        self.client.post(f"/api/v1/quotations/{criado['id']}/submit/")
        return criado

    def test_gerente_aprova(self):
        orcamento = self._criar_e_enviar(self.vendedor)

        self.client.force_authenticate(self.gerente)
        resposta = self.client.post(f"/api/v1/quotations/{orcamento['id']}/approve/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], QuotationStatus.APPROVED)

    def test_vendedor_nao_aprova_via_api_mesmo_tentando_a_propria_rota(self):
        orcamento = self._criar_e_enviar(self.vendedor)

        # Mesmo usuário que criou tentando aprovar — barrado na permissão
        # (papel errado) antes mesmo de chegar no service.
        resposta = self.client.post(f"/api/v1/quotations/{orcamento['id']}/approve/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_tambem_vendedor_nao_aprova_o_proprio(self):
        """Mesmo um papel com permissão de aprovar é barrado pelo service se
        for o autor do orçamento — a checagem final é sempre 'é o mesmo
        usuário', não 'tem o cargo certo'."""
        gerente_vendedor = User.objects.create_user(
            username="gv1", password="senha-forte-123", role=Role.MANAGER
        )
        self.client.force_authenticate(gerente_vendedor)
        criado = self.client.post("/api/v1/quotations/", self.payload).data
        self.client.post(f"/api/v1/quotations/{criado['id']}/submit/")

        resposta = self.client.post(f"/api/v1/quotations/{criado['id']}/approve/")
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("não pode aprovar", resposta.data["detail"])

    def test_rejeitar_aceita_motivo(self):
        orcamento = self._criar_e_enviar(self.vendedor)

        self.client.force_authenticate(self.gerente)
        resposta = self.client.post(
            f"/api/v1/quotations/{orcamento['id']}/reject/", {"reason": "Fora do escopo"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], QuotationStatus.REJECTED)

    def test_vendedor_cancela_o_proprio_rascunho(self):
        self.client.force_authenticate(self.vendedor)
        criado = self.client.post("/api/v1/quotations/", self.payload).data

        resposta = self.client.post(f"/api/v1/quotations/{criado['id']}/cancel/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], QuotationStatus.CANCELLED)


class QuotationFilterTests(QuotationApiTestCase):
    """Frontend §22 — filtros por status/cliente/valor."""

    def test_filtra_por_status(self):
        self.client.force_authenticate(self.gerente)
        self.client.post("/api/v1/quotations/", self.payload)

        resposta = self.client.get("/api/v1/quotations/?status=APPROVED")
        self.assertEqual(len(resposta.data["results"]), 0)

        resposta = self.client.get("/api/v1/quotations/?status=DRAFT")
        self.assertEqual(len(resposta.data["results"]), 1)

    def test_filtra_por_faixa_de_valor(self):
        self.client.force_authenticate(self.gerente)
        self.client.post("/api/v1/quotations/", {**self.payload, "amount": "500.00"})
        self.client.post("/api/v1/quotations/", {**self.payload, "amount": "50000.00"})

        resposta = self.client.get("/api/v1/quotations/?amount_min=1000")
        self.assertEqual(len(resposta.data["results"]), 1)
        self.assertEqual(resposta.data["results"][0]["amount"], "50000.00")
