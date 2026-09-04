from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.core.choices import PaymentMethod, ProjectType
from apps.customers.models import Customer, CustomerKind
from apps.dashboard import services
from apps.finance.models import Charge, ChargeStatus, ChargeType, Expense, Revenue, RevenueSource
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class DashboardServicesTestCase(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )


class QuotationsSummaryTests(DashboardServicesTestCase):
    def test_conta_por_status_incluindo_zerados(self):
        Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="x", amount="1000.00", status=QuotationStatus.DRAFT,
        )
        Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="y", amount="2000.00", status=QuotationStatus.APPROVED, decided_by=self.gerente,
        )

        resultado = services.quotations_summary()

        self.assertEqual(resultado[QuotationStatus.DRAFT], 1)
        self.assertEqual(resultado[QuotationStatus.APPROVED], 1)
        self.assertEqual(resultado[QuotationStatus.REJECTED], 0)


class FinanceSummaryTests(DashboardServicesTestCase):
    def test_a_receber_soma_pending_e_processing(self):
        Charge.objects.create(
            customer=self.cliente, charge_type=ChargeType.SCOPE_CHANGE, amount=Decimal("500.00"),
            due_date=date.today(), payment_method=PaymentMethod.BOLETO, status=ChargeStatus.PENDING,
        )
        Charge.objects.create(
            customer=self.cliente, charge_type=ChargeType.SCOPE_CHANGE, amount=Decimal("300.00"),
            due_date=date.today(), payment_method=PaymentMethod.BOLETO, status=ChargeStatus.PROCESSING,
        )
        Charge.objects.create(
            customer=self.cliente, charge_type=ChargeType.SCOPE_CHANGE, amount=Decimal("999.00"),
            due_date=date.today(), payment_method=PaymentMethod.BOLETO, status=ChargeStatus.CANCELLED,
        )

        resultado = services.finance_summary()
        self.assertEqual(resultado["receivable_pending"], "800.00")

    def test_vencida_e_pending_com_due_date_no_passado(self):
        Charge.objects.create(
            customer=self.cliente, charge_type=ChargeType.SCOPE_CHANGE, amount=Decimal("500.00"),
            due_date=date(2020, 1, 1), payment_method=PaymentMethod.BOLETO, status=ChargeStatus.PENDING,
        )
        # Pendente mas ainda não venceu — não deve contar como vencida.
        Charge.objects.create(
            customer=self.cliente, charge_type=ChargeType.SCOPE_CHANGE, amount=Decimal("100.00"),
            due_date=date(2099, 1, 1), payment_method=PaymentMethod.BOLETO, status=ChargeStatus.PENDING,
        )

        resultado = services.finance_summary()
        self.assertEqual(resultado["overdue_total"], "500.00")
        self.assertEqual(resultado["overdue_count"], 1)

    def test_receita_e_despesa_do_mes(self):
        agora = timezone.now()
        Revenue.objects.create(source=RevenueSource.OTHER, amount=Decimal("1000.00"), received_at=agora)
        Expense.objects.create(
            category="infra", description="Servidor", amount=Decimal("200.00"), due_date=date.today(),
            status=Expense.Status.PAID, paid_at=agora, created_by=self.gerente,
        )
        # Despesa pendente não deve entrar no "pago no mês".
        Expense.objects.create(
            category="infra", description="Outro", amount=Decimal("999.00"), due_date=date.today(),
            created_by=self.gerente,
        )

        resultado = services.finance_summary()
        self.assertEqual(resultado["revenue_this_month"], "1000.00")
        self.assertEqual(resultado["expenses_paid_this_month"], "200.00")
        self.assertEqual(resultado["net_this_month"], "800.00")

    def test_sem_dados_devolve_zero_nao_none(self):
        resultado = services.finance_summary()
        self.assertEqual(resultado["receivable_pending"], "0.00")
        self.assertEqual(resultado["overdue_total"], "0.00")
        self.assertEqual(resultado["commissions_pending"], "0.00")


class SalesAndDeveloperSummaryTests(DashboardServicesTestCase):
    def test_sales_summary_e_escopado_ao_proprio_vendedor(self):
        outro_vendedor = User.objects.create_user(username="v2", password="senha-forte-123", role=Role.SALES)
        Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="x", amount="1000.00", status=QuotationStatus.DRAFT,
        )
        Quotation.objects.create(
            customer=self.cliente, sales_rep=outro_vendedor, service_type=ProjectType.WEBSITE,
            description="y", amount="2000.00", status=QuotationStatus.DRAFT,
        )

        resultado = services.sales_summary(self.vendedor)
        self.assertEqual(resultado["quotations_by_status"][QuotationStatus.DRAFT], 1)

    def test_developer_summary_e_escopado_ao_proprio_responsavel(self):
        outro_dev = User.objects.create_user(username="dev2", password="senha-forte-123", role=Role.DEVELOPER)
        orcamento = Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="x", amount="1000.00", status=QuotationStatus.APPROVED, decided_by=self.gerente,
        )
        Project.objects.create(
            customer=self.cliente, quotation=orcamento, name="x", project_type=ProjectType.WEBSITE,
            responsible=self.dev, amount="1000.00", status=ProjectStatus.APPROVED,
        )

        resultado_dev = services.developer_summary(self.dev)
        resultado_outro = services.developer_summary(outro_dev)
        self.assertEqual(resultado_dev["projects_by_status"][ProjectStatus.APPROVED], 1)
        self.assertEqual(resultado_outro["projects_by_status"][ProjectStatus.APPROVED], 0)


class BuildSummaryRoleDispatchTests(DashboardServicesTestCase):
    def test_admin_e_gerente_veem_tudo(self):
        resultado = services.build_summary(self.gerente)
        self.assertIn("quotations", resultado)
        self.assertIn("projects", resultado)
        self.assertIn("finance", resultado)
        self.assertIn("customers", resultado)

    def test_financeiro_ve_so_finance_e_customers(self):
        financeiro = User.objects.create_user(username="f1", password="senha-forte-123", role=Role.FINANCE)
        resultado = services.build_summary(financeiro)
        self.assertEqual(set(resultado), {"finance", "customers"})

    def test_vendedor_ve_so_sales(self):
        resultado = services.build_summary(self.vendedor)
        self.assertEqual(set(resultado), {"sales"})

    def test_developer_ve_so_projects_by_status(self):
        resultado = services.build_summary(self.dev)
        self.assertEqual(set(resultado), {"projects_by_status"})

    def test_support_ve_quotations_e_projects_sem_finance(self):
        suporte = User.objects.create_user(username="s1", password="senha-forte-123", role=Role.SUPPORT)
        resultado = services.build_summary(suporte)
        self.assertEqual(set(resultado), {"quotations", "projects"})
