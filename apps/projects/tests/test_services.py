from django.test import TestCase

from apps.audit.models import AuditLog
from apps.core.choices import PaymentMethod, ProjectType
from apps.core.exceptions import DomainError
from apps.customers.models import Customer, CustomerKind
from apps.projects import services
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class ProjectServicesTestCase(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )

    def _criar_orcamento(self, **overrides) -> Quotation:
        dados = dict(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="Site institucional", amount="10000.00", status=QuotationStatus.APPROVED,
            decided_by=self.gerente,
        )
        dados.update(overrides)
        return Quotation.objects.create(**dados)

    def _criar_projeto(self, **overrides) -> Project:
        orcamento = self._criar_orcamento()
        dados = dict(
            customer=self.cliente, quotation=orcamento, name="Site institucional", project_type=ProjectType.WEBSITE,
            responsible=self.dev, amount="10000.00", status=ProjectStatus.APPROVED,
        )
        dados.update(overrides)
        return Project.objects.create(**dados)


class GenerateProjectFromQuotationTests(ProjectServicesTestCase):
    def test_gera_projeto_de_orcamento_aprovado(self):
        orcamento = self._criar_orcamento()

        projeto = services.generate_project_from_quotation(
            orcamento, self.gerente, name="Site institucional — Fulano", responsible=self.dev,
        )

        self.assertEqual(projeto.status, ProjectStatus.APPROVED)
        self.assertEqual(projeto.amount, orcamento.amount)
        self.assertEqual(projeto.project_type, orcamento.service_type)
        self.assertEqual(projeto.customer_id, self.cliente.id)
        self.assertEqual(projeto.quotation_id, orcamento.id)

    def test_nao_gera_de_orcamento_nao_aprovado(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.DRAFT, decided_by=None)
        with self.assertRaises(DomainError):
            services.generate_project_from_quotation(
                orcamento, self.gerente, name="x", responsible=self.dev,
            )

    def test_nao_gera_projeto_duplicado(self):
        orcamento = self._criar_orcamento()
        services.generate_project_from_quotation(orcamento, self.gerente, name="x", responsible=self.dev)

        with self.assertRaises(DomainError):
            services.generate_project_from_quotation(orcamento, self.gerente, name="y", responsible=self.dev)

    def test_responsavel_precisa_ter_papel_valido(self):
        orcamento = self._criar_orcamento()
        with self.assertRaises(DomainError):
            services.generate_project_from_quotation(
                orcamento, self.gerente, name="x", responsible=self.vendedor,
            )

    def test_geracao_grava_auditoria(self):
        orcamento = self._criar_orcamento()
        projeto = services.generate_project_from_quotation(
            orcamento, self.gerente, name="x", responsible=self.dev,
        )

        log = AuditLog.objects.get(action="project.created")
        self.assertEqual(log.user, self.gerente)
        self.assertEqual(log.entity_id, str(projeto.id))
        self.assertEqual(log.metadata, {"quotation_id": str(orcamento.id)})


class ProjectTransitionTests(ProjectServicesTestCase):
    """Cobre cada transição isoladamente — o percurso ponta a ponta completo,
    puxado por cobrança/pagamento de verdade, está em `apps.finance.tests`."""

    def test_request_initial_payment(self):
        projeto = self._criar_projeto(status=ProjectStatus.APPROVED)
        services.request_initial_payment(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.AWAITING_INITIAL_PAYMENT)

    def test_request_initial_payment_recusa_fora_de_ordem(self):
        projeto = self._criar_projeto(status=ProjectStatus.IN_DEVELOPMENT)
        with self.assertRaises(DomainError):
            services.request_initial_payment(projeto, self.gerente)

    def test_confirm_initial_payment(self):
        projeto = self._criar_projeto(status=ProjectStatus.AWAITING_INITIAL_PAYMENT)
        services.confirm_initial_payment(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.INITIAL_PAYMENT_CONFIRMED)

    def test_start_development(self):
        projeto = self._criar_projeto(status=ProjectStatus.INITIAL_PAYMENT_CONFIRMED)
        services.start_development(projeto, self.dev)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.IN_DEVELOPMENT)

    def test_complete_development_pula_direto_pra_awaiting_client_acceptance(self):
        projeto = self._criar_projeto(status=ProjectStatus.IN_DEVELOPMENT)
        services.complete_development(projeto, self.dev)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.AWAITING_CLIENT_ACCEPTANCE)

    def test_register_client_acceptance(self):
        projeto = self._criar_projeto(status=ProjectStatus.AWAITING_CLIENT_ACCEPTANCE)
        services.register_client_acceptance(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.ACCEPTED)

    def test_request_final_payment(self):
        projeto = self._criar_projeto(status=ProjectStatus.ACCEPTED)
        services.request_final_payment(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.AWAITING_FINAL_PAYMENT)

    def test_confirm_final_payment(self):
        projeto = self._criar_projeto(status=ProjectStatus.AWAITING_FINAL_PAYMENT)
        services.confirm_final_payment(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.FINAL_PAYMENT_CONFIRMED)

    def test_mark_delivered_grava_delivered_at(self):
        projeto = self._criar_projeto(status=ProjectStatus.FINAL_PAYMENT_CONFIRMED)
        services.mark_delivered(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.DELIVERED)
        self.assertIsNotNone(projeto.delivered_at)

    def test_enter_maintenance(self):
        projeto = self._criar_projeto(status=ProjectStatus.DELIVERED)
        services.enter_maintenance(projeto, self.gerente)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.MAINTENANCE)

    def test_transicao_fora_de_ordem_grava_erro_e_nao_muda_status(self):
        projeto = self._criar_projeto(status=ProjectStatus.APPROVED)
        with self.assertRaises(DomainError):
            services.start_development(projeto, self.dev)
        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.APPROVED)
