from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.choices import PaymentMethod, ProjectType
from apps.customers.models import Customer, CustomerKind
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class ProjectApiTestCase(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)
        self.outro_dev = User.objects.create_user(username="dev2", password="senha-forte-123", role=Role.DEVELOPER)
        self.financeiro = User.objects.create_user(username="f1", password="senha-forte-123", role=Role.FINANCE)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )
        self.orcamento = Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="Site institucional", amount="10000.00",
            status=QuotationStatus.APPROVED, decided_by=self.gerente,
        )
        self.payload = {
            "quotation": str(self.orcamento.id), "name": "Site institucional — Fulano",
            "responsible": str(self.dev.id),
        }


class ProjectCreateTests(ProjectApiTestCase):
    def test_gerente_gera_projeto_de_orcamento_aprovado(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.post("/api/v1/projects/", self.payload)

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["status"], ProjectStatus.APPROVED)
        self.assertEqual(resposta.data["amount"], "10000.00")

    def test_vendedor_nao_gera_projeto(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post("/api/v1/projects/", self.payload)
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_nao_gera_projeto_duplicado(self):
        self.client.force_authenticate(self.gerente)
        self.client.post("/api/v1/projects/", self.payload)

        resposta = self.client.post("/api/v1/projects/", self.payload)
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nao_gera_de_orcamento_ainda_nao_aprovado(self):
        outro_orcamento = Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="x", amount="500.00", status=QuotationStatus.DRAFT,
        )
        self.client.force_authenticate(self.gerente)
        resposta = self.client.post(
            "/api/v1/projects/",
            {"quotation": str(outro_orcamento.id), "name": "x", "responsible": str(self.dev.id)},
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)


class ProjectVisibilityTests(ProjectApiTestCase):
    def _criar_projeto(self, responsible=None) -> dict:
        self.client.force_authenticate(self.gerente)
        payload = dict(self.payload)
        if responsible is not None:
            payload["responsible"] = str(responsible.id)
        return self.client.post("/api/v1/projects/", payload).data

    def test_vendedor_ve_projeto_do_proprio_orcamento(self):
        self._criar_projeto()
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/projects/")
        self.assertEqual(len(resposta.data["results"]), 1)

    def test_outro_vendedor_nao_ve(self):
        self._criar_projeto()
        outro_vendedor = User.objects.create_user(username="v2", password="senha-forte-123", role=Role.SALES)
        self.client.force_authenticate(outro_vendedor)
        resposta = self.client.get("/api/v1/projects/")
        self.assertEqual(len(resposta.data["results"]), 0)

    def test_dev_designado_ve_seu_projeto(self):
        self._criar_projeto(responsible=self.dev)
        self.client.force_authenticate(self.dev)
        resposta = self.client.get("/api/v1/projects/")
        self.assertEqual(len(resposta.data["results"]), 1)

    def test_outro_dev_nao_ve(self):
        self._criar_projeto(responsible=self.dev)
        self.client.force_authenticate(self.outro_dev)
        resposta = self.client.get("/api/v1/projects/")
        self.assertEqual(len(resposta.data["results"]), 0)

    def test_financeiro_ve_tudo(self):
        self._criar_projeto()
        self.client.force_authenticate(self.financeiro)
        resposta = self.client.get("/api/v1/projects/")
        self.assertEqual(len(resposta.data["results"]), 1)


class ProjectUpdateTests(ProjectApiTestCase):
    def test_dev_designado_edita_o_proprio_projeto(self):
        self.client.force_authenticate(self.gerente)
        criado = self.client.post("/api/v1/projects/", self.payload).data

        self.client.force_authenticate(self.dev)
        resposta = self.client.patch(f"/api/v1/projects/{criado['id']}/", {"description": "Ajustado"})
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_dev_nao_designado_nao_edita(self):
        """`outro_dev` nem aparece na queryset dele (filtrada por `responsible`
        em `get_queryset`), então o objeto nunca chega em `get_object()` — dá
        404, não 403. Isso é intencional: não vaza nem a existência de um
        projeto de outro desenvolvedor."""
        self.client.force_authenticate(self.gerente)
        criado = self.client.post("/api/v1/projects/", self.payload).data

        self.client.force_authenticate(self.outro_dev)
        resposta = self.client.patch(f"/api/v1/projects/{criado['id']}/", {"description": "Ajustado"})
        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendedor_nao_edita(self):
        self.client.force_authenticate(self.gerente)
        criado = self.client.post("/api/v1/projects/", self.payload).data

        self.client.force_authenticate(self.vendedor)
        resposta = self.client.patch(f"/api/v1/projects/{criado['id']}/", {"description": "Ajustado"})
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_sem_rota_de_exclusao(self):
        self.client.force_authenticate(self.gerente)
        criado = self.client.post("/api/v1/projects/", self.payload).data

        resposta = self.client.delete(f"/api/v1/projects/{criado['id']}/")
        self.assertIn(resposta.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))
        self.assertTrue(Project.objects.filter(id=criado["id"]).exists())


class ProjectTransitionActionTests(ProjectApiTestCase):
    """As transições disparadas por cobrança (`confirm-initial-payment` etc.)
    não têm rota — só as de gente têm. Ver `apps.finance.tests` pro percurso
    completo puxado por pagamento real."""

    def _criar_projeto(self, status_inicial=ProjectStatus.IN_DEVELOPMENT) -> dict:
        self.client.force_authenticate(self.gerente)
        criado = self.client.post("/api/v1/projects/", self.payload).data
        Project.objects.filter(id=criado["id"]).update(status=status_inicial)
        return criado

    def test_dev_designado_avanca_desenvolvimento(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.INITIAL_PAYMENT_CONFIRMED)
        self.client.force_authenticate(self.dev)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/start-development/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], ProjectStatus.IN_DEVELOPMENT)

    def test_outro_dev_nao_avanca_projeto_que_nao_e_dele(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.INITIAL_PAYMENT_CONFIRMED)
        self.client.force_authenticate(self.outro_dev)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/start-development/")
        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_completa_desenvolvimento_vai_direto_pra_awaiting_client_acceptance(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.IN_DEVELOPMENT)
        self.client.force_authenticate(self.dev)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/complete-development/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], ProjectStatus.AWAITING_CLIENT_ACCEPTANCE)

    def test_registra_aceite_do_cliente(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.AWAITING_CLIENT_ACCEPTANCE)
        self.client.force_authenticate(self.gerente)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/accept/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], ProjectStatus.ACCEPTED)

    def test_marca_entregue_grava_delivered_at(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.FINAL_PAYMENT_CONFIRMED)
        self.client.force_authenticate(self.gerente)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/mark-delivered/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], ProjectStatus.DELIVERED)
        self.assertIsNotNone(resposta.data["delivered_at"])

    def test_entra_em_manutencao(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.DELIVERED)
        self.client.force_authenticate(self.gerente)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/enter-maintenance/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], ProjectStatus.MAINTENANCE)

    def test_transicao_fora_de_ordem_devolve_400(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.APPROVED)
        self.client.force_authenticate(self.gerente)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/start-development/")
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vendedor_nao_avanca_etapa(self):
        criado = self._criar_projeto(status_inicial=ProjectStatus.INITIAL_PAYMENT_CONFIRMED)
        self.client.force_authenticate(self.vendedor)

        resposta = self.client.post(f"/api/v1/projects/{criado['id']}/start-development/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)


class ProjectFilterTests(ProjectApiTestCase):
    """Frontend §25 — filtros por status/responsável."""

    def _criar_projeto(self, status_inicial=ProjectStatus.IN_DEVELOPMENT) -> dict:
        self.client.force_authenticate(self.gerente)
        criado = self.client.post("/api/v1/projects/", self.payload).data
        Project.objects.filter(id=criado["id"]).update(status=status_inicial)
        return criado

    def test_filtra_por_status(self):
        self._criar_projeto(status_inicial=ProjectStatus.IN_DEVELOPMENT)
        self.client.force_authenticate(self.gerente)

        resposta = self.client.get("/api/v1/projects/?status=IN_DEVELOPMENT")
        self.assertEqual(len(resposta.data["results"]), 1)

        resposta = self.client.get("/api/v1/projects/?status=DELIVERED")
        self.assertEqual(len(resposta.data["results"]), 0)

    def test_filtra_por_responsavel(self):
        self._criar_projeto()
        self.client.force_authenticate(self.gerente)

        resposta = self.client.get(f"/api/v1/projects/?responsible={self.dev.id}")
        self.assertEqual(len(resposta.data["results"]), 1)

        resposta = self.client.get(f"/api/v1/projects/?responsible={self.outro_dev.id}")
        self.assertEqual(len(resposta.data["results"]), 0)
