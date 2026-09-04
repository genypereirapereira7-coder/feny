from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.audit.models import AuditLog
from apps.core.choices import PaymentMethod, ProjectType
from apps.core.exceptions import DomainError
from apps.customers.models import Customer, CustomerKind
from apps.finance import services
from apps.finance.models import (
    Charge,
    ChargeStatus,
    ChargeType,
    Commission,
    Expense,
    Payment,
    RecurringSubscription,
    Revenue,
    SubscriptionStatus,
)
from apps.notifications.models import Notification, NotificationChannel, NotificationStatus
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class FinanceServicesTestCase(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.financeiro = User.objects.create_user(username="f1", password="senha-forte-123", role=Role.FINANCE)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
            phone="11999999999",
        )
        self.orcamento = Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="Site institucional", amount="10000.00",
            status=QuotationStatus.APPROVED, decided_by=self.gerente,
        )

    def _criar_projeto(self, **overrides) -> Project:
        dados = dict(
            customer=self.cliente, quotation=self.orcamento, name="Site institucional",
            project_type=ProjectType.WEBSITE, responsible=self.dev, amount=Decimal("10000.00"),
            status=ProjectStatus.APPROVED,
        )
        dados.update(overrides)
        return Project.objects.create(**dados)


class CreateInitialChargeTests(FinanceServicesTestCase):
    def test_cria_cobranca_de_30_por_cento_e_avanca_projeto(self):
        projeto = self._criar_projeto()

        cobranca = services.create_initial_charge(projeto, self.financeiro)

        self.assertEqual(cobranca.charge_type, ChargeType.INITIAL)
        self.assertEqual(cobranca.amount, Decimal("3000.00"))
        self.assertEqual(cobranca.percentage, Decimal("30.00"))
        self.assertEqual(cobranca.status, ChargeStatus.PENDING)
        self.assertEqual(cobranca.payment_method, self.cliente.preferred_payment_method)

        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.AWAITING_INITIAL_PAYMENT)

    def test_nao_cria_cobranca_inicial_duas_vezes(self):
        projeto = self._criar_projeto()
        services.create_initial_charge(projeto, self.financeiro)

        with self.assertRaises(DomainError):
            services.create_initial_charge(projeto, self.financeiro)

    def test_nao_cria_de_projeto_fora_de_ordem(self):
        projeto = self._criar_projeto(status=ProjectStatus.IN_DEVELOPMENT)
        with self.assertRaises(DomainError):
            services.create_initial_charge(projeto, self.financeiro)


class CreateFinalChargeTests(FinanceServicesTestCase):
    def test_cria_cobranca_final_por_subtracao_do_ja_cobrado(self):
        projeto = self._criar_projeto(status=ProjectStatus.ACCEPTED)
        Charge.objects.create(
            project=projeto, customer=self.cliente, charge_type=ChargeType.INITIAL,
            percentage=Decimal("30.00"), amount=Decimal("3000.00"), due_date="2026-01-01",
            payment_method=PaymentMethod.BOLETO, status=ChargeStatus.PAID,
        )

        cobranca = services.create_final_charge(projeto, self.financeiro)

        self.assertEqual(cobranca.charge_type, ChargeType.FINAL)
        self.assertEqual(cobranca.amount, Decimal("7000.00"))

        projeto.refresh_from_db()
        self.assertEqual(projeto.status, ProjectStatus.AWAITING_FINAL_PAYMENT)

    def test_ignora_cobranca_cancelada_no_calculo(self):
        """Uma `Charge` cancelada não conta como "já cobrado" — senão o saldo
        final ficaria errado pra menos."""
        projeto = self._criar_projeto(status=ProjectStatus.ACCEPTED)
        Charge.objects.create(
            project=projeto, customer=self.cliente, charge_type=ChargeType.INITIAL,
            percentage=Decimal("30.00"), amount=Decimal("3000.00"), due_date="2026-01-01",
            payment_method=PaymentMethod.BOLETO, status=ChargeStatus.CANCELLED,
        )

        cobranca = services.create_final_charge(projeto, self.financeiro)
        self.assertEqual(cobranca.amount, Decimal("10000.00"))

    def test_nao_cria_de_projeto_fora_de_ordem(self):
        projeto = self._criar_projeto(status=ProjectStatus.IN_DEVELOPMENT)
        with self.assertRaises(DomainError):
            services.create_final_charge(projeto, self.financeiro)


class ConfirmPaymentTests(FinanceServicesTestCase):
    def _cobranca_inicial_pendente(self) -> Charge:
        projeto = self._criar_projeto()
        return services.create_initial_charge(projeto, self.financeiro)

    def test_confirma_pagamento_gera_payment_revenue_e_comissao(self):
        cobranca = self._cobranca_inicial_pendente()

        services.confirm_payment(
            cobranca, self.financeiro, external_id="mp-123", amount=Decimal("3000.00"),
            method="PIX",
        )

        cobranca.refresh_from_db()
        self.assertEqual(cobranca.status, ChargeStatus.PAID)
        self.assertIsNotNone(cobranca.paid_at)

        pagamento = Payment.objects.get(external_id="mp-123")
        self.assertEqual(pagamento.amount, Decimal("3000.00"))

        receita = Revenue.objects.get(payment=pagamento)
        self.assertEqual(receita.amount, Decimal("3000.00"))

        comissao = Commission.objects.get(payment=pagamento)
        self.assertEqual(comissao.sales_rep, self.vendedor)
        self.assertEqual(comissao.percentage, Decimal("10.00"))
        self.assertEqual(comissao.amount, Decimal("300.00"))
        self.assertEqual(comissao.status, Commission.Status.PENDING)

        cobranca.project.refresh_from_db()
        self.assertEqual(cobranca.project.status, ProjectStatus.INITIAL_PAYMENT_CONFIRMED)

    def test_segunda_notificacao_do_mesmo_external_id_e_ignorada(self):
        """Idempotência (§8.3): reprocessar o mesmo `external_id` não gera um
        segundo `Payment` nem uma segunda `Commission`."""
        cobranca = self._cobranca_inicial_pendente()
        services.confirm_payment(cobranca, self.financeiro, external_id="mp-123", amount=Decimal("3000.00"), method="PIX")

        services.confirm_payment(cobranca, self.financeiro, external_id="mp-123", amount=Decimal("3000.00"), method="PIX")

        self.assertEqual(Payment.objects.filter(external_id="mp-123").count(), 1)
        self.assertEqual(Commission.objects.count(), 1)

    def test_nao_confirma_cobranca_ja_paga(self):
        cobranca = self._cobranca_inicial_pendente()
        cobranca.status = ChargeStatus.CANCELLED
        cobranca.save(update_fields=["status"])

        with self.assertRaises(DomainError):
            services.confirm_payment(cobranca, self.financeiro, external_id="mp-999", amount=Decimal("3000.00"), method="PIX")

    def test_confirmacao_grava_auditoria(self):
        cobranca = self._cobranca_inicial_pendente()
        services.confirm_payment(cobranca, self.financeiro, external_id="mp-123", amount=Decimal("3000.00"), method="PIX")

        self.assertTrue(AuditLog.objects.filter(action="payment.confirmed").exists())
        self.assertTrue(AuditLog.objects.filter(action="commission.generated").exists())

    def test_confirmacao_cria_notification_whatsapp_pendente(self):
        cobranca = self._cobranca_inicial_pendente()
        services.confirm_payment(cobranca, self.financeiro, external_id="mp-123", amount=Decimal("3000.00"), method="PIX")

        notification = Notification.objects.get(template="payment.received")
        self.assertEqual(notification.channel, NotificationChannel.WHATSAPP)
        self.assertEqual(notification.recipient, self.cliente.phone)
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertIn("R$ 3000.00", notification.context["payment_amount"])

    def test_sem_telefone_cadastrado_nao_cria_notification(self):
        self.cliente.phone = ""
        self.cliente.save(update_fields=["phone"])
        cobranca = self._cobranca_inicial_pendente()

        services.confirm_payment(cobranca, self.financeiro, external_id="mp-123", amount=Decimal("3000.00"), method="PIX")

        self.assertFalse(Notification.objects.exists())


class IssueChargeTests(FinanceServicesTestCase):
    @patch("apps.finance.services.mercadopago_adapter.create_charge_preference")
    def test_emite_cobranca_grava_external_id_e_link(self, mock_create_preference):
        mock_create_preference.return_value = {"external_id": "pref-1", "payment_link": "https://pay/1"}
        projeto = self._criar_projeto()
        cobranca = services.create_initial_charge(projeto, self.financeiro)

        emitida = services.issue_charge(cobranca, self.financeiro)

        self.assertEqual(emitida.external_id, "pref-1")
        self.assertEqual(emitida.payment_link, "https://pay/1")
        mock_create_preference.assert_called_once_with(cobranca)

        notification = Notification.objects.get(template="charge.issued")
        self.assertEqual(notification.recipient, self.cliente.phone)
        self.assertEqual(notification.context["payment_link"], "https://pay/1")

    @patch("apps.finance.services.mercadopago_adapter.create_charge_preference")
    def test_nao_emite_duas_vezes(self, mock_create_preference):
        mock_create_preference.return_value = {"external_id": "pref-1", "payment_link": "https://pay/1"}
        projeto = self._criar_projeto()
        cobranca = services.create_initial_charge(projeto, self.financeiro)
        services.issue_charge(cobranca, self.financeiro)

        with self.assertRaises(DomainError):
            services.issue_charge(cobranca, self.financeiro)

    def test_erro_do_mercado_pago_vira_domainerror(self):
        """Sem `MERCADOPAGO_ACCESS_TOKEN` configurado (like num ambiente de
        dev sem credencial real), o erro chega como `DomainError` — 400
        arrumado, não uma 500 vazando de dentro de `client.py`."""
        projeto = self._criar_projeto()
        cobranca = services.create_initial_charge(projeto, self.financeiro)

        with self.assertRaises(DomainError):
            services.issue_charge(cobranca, self.financeiro)


class CancelChargeTests(FinanceServicesTestCase):
    def test_cancela_cobranca_pendente(self):
        projeto = self._criar_projeto()
        cobranca = services.create_initial_charge(projeto, self.financeiro)

        services.cancel_charge(cobranca, self.financeiro)
        cobranca.refresh_from_db()
        self.assertEqual(cobranca.status, ChargeStatus.CANCELLED)

    def test_nao_cancela_cobranca_paga(self):
        projeto = self._criar_projeto()
        cobranca = services.create_initial_charge(projeto, self.financeiro)
        services.confirm_payment(cobranca, self.financeiro, external_id="mp-1", amount=Decimal("3000.00"), method="PIX")

        with self.assertRaises(DomainError):
            services.cancel_charge(cobranca, self.financeiro)


class ExpenseAndCommissionServiceTests(FinanceServicesTestCase):
    def test_paga_despesa_pendente(self):
        despesa = Expense.objects.create(
            category="infra", description="Servidor", amount=Decimal("150.00"),
            due_date="2026-09-10", created_by=self.financeiro,
        )
        services.pay_expense(despesa, self.financeiro)
        despesa.refresh_from_db()
        self.assertEqual(despesa.status, Expense.Status.PAID)
        self.assertIsNotNone(despesa.paid_at)

    def test_nao_paga_despesa_ja_cancelada(self):
        despesa = Expense.objects.create(
            category="infra", description="Servidor", amount=Decimal("150.00"),
            due_date="2026-09-10", created_by=self.financeiro, status=Expense.Status.CANCELLED,
        )
        with self.assertRaises(DomainError):
            services.pay_expense(despesa, self.financeiro)

    def test_paga_comissao_pendente(self):
        projeto = self._criar_projeto()
        cobranca = services.create_initial_charge(projeto, self.financeiro)
        services.confirm_payment(cobranca, self.financeiro, external_id="mp-1", amount=Decimal("3000.00"), method="PIX")
        comissao = Commission.objects.get(project=projeto)

        services.pay_commission(comissao, self.financeiro)
        comissao.refresh_from_db()
        self.assertEqual(comissao.status, Commission.Status.PAID)
        self.assertIsNotNone(comissao.paid_at)


class SomarUmMesTests(TestCase):
    def test_meio_do_mes(self):
        self.assertEqual(services._somar_um_mes(date(2026, 3, 15)), date(2026, 4, 15))

    def test_vira_o_ano(self):
        self.assertEqual(services._somar_um_mes(date(2026, 12, 10)), date(2027, 1, 10))

    def test_dia_31_em_mes_mais_curto_nao_estoura(self):
        self.assertEqual(services._somar_um_mes(date(2026, 1, 31)), date(2026, 2, 28))


class CreateSubscriptionTests(FinanceServicesTestCase):
    def test_cria_assinatura_com_next_billing_igual_ao_start(self):
        subscription = services.create_subscription(
            self.cliente, self.financeiro, service_description="Hospedagem mensal",
            amount=Decimal("150.00"), start_date=date(2026, 9, 10),
        )
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.next_billing_date, date(2026, 9, 10))

    def test_criacao_grava_auditoria(self):
        services.create_subscription(
            self.cliente, self.financeiro, service_description="Hospedagem mensal",
            amount=Decimal("150.00"), start_date=date(2026, 9, 10),
        )
        self.assertTrue(AuditLog.objects.filter(action="subscription.created").exists())


class SubscriptionTransitionTests(FinanceServicesTestCase):
    def _criar(self, **overrides) -> RecurringSubscription:
        dados = dict(
            customer=self.cliente, service_description="Hospedagem mensal",
            amount=Decimal("150.00"), start_date=date(2026, 9, 10), next_billing_date=date(2026, 9, 10),
        )
        dados.update(overrides)
        return RecurringSubscription.objects.create(**dados)

    def test_pausa_assinatura_ativa(self):
        subscription = self._criar()
        services.pause_subscription(subscription, self.financeiro)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.PAUSED)

    def test_nao_pausa_assinatura_ja_pausada(self):
        subscription = self._criar(status=SubscriptionStatus.PAUSED)
        with self.assertRaises(DomainError):
            services.pause_subscription(subscription, self.financeiro)

    def test_retoma_assinatura_pausada(self):
        subscription = self._criar(status=SubscriptionStatus.PAUSED)
        services.resume_subscription(subscription, self.financeiro)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)

    def test_nao_retoma_assinatura_ativa(self):
        subscription = self._criar()
        with self.assertRaises(DomainError):
            services.resume_subscription(subscription, self.financeiro)

    def test_cancela_assinatura(self):
        subscription = self._criar()
        services.cancel_subscription(subscription, self.financeiro)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.CANCELLED)

    def test_nao_cancela_assinatura_ja_cancelada(self):
        subscription = self._criar(status=SubscriptionStatus.CANCELLED)
        with self.assertRaises(DomainError):
            services.cancel_subscription(subscription, self.financeiro)


class GenerateRecurringChargesTests(FinanceServicesTestCase):
    def _criar(self, **overrides) -> RecurringSubscription:
        dados = dict(
            customer=self.cliente, service_description="Hospedagem mensal",
            amount=Decimal("150.00"), start_date=date(2026, 9, 1), next_billing_date=date(2026, 9, 1),
        )
        dados.update(overrides)
        return RecurringSubscription.objects.create(**dados)

    def test_gera_cobranca_para_assinatura_vencida_e_avanca_ciclo(self):
        subscription = self._criar()

        resultado = services.generate_recurring_charges(reference_date=date(2026, 9, 1))

        self.assertEqual(resultado["geradas"], 1)
        cobranca = Charge.objects.get(recurring_subscription=subscription)
        self.assertEqual(cobranca.charge_type, ChargeType.RECURRING)
        self.assertEqual(cobranca.amount, Decimal("150.00"))
        self.assertEqual(cobranca.customer, self.cliente)

        subscription.refresh_from_db()
        self.assertEqual(subscription.next_billing_date, date(2026, 10, 1))

    def test_nao_gera_para_assinatura_ainda_nao_vencida(self):
        self._criar(next_billing_date=date(2026, 10, 1))
        resultado = services.generate_recurring_charges(reference_date=date(2026, 9, 1))
        self.assertEqual(resultado["geradas"], 0)

    def test_nao_gera_para_assinatura_pausada(self):
        self._criar(status=SubscriptionStatus.PAUSED)
        resultado = services.generate_recurring_charges(reference_date=date(2026, 9, 1))
        self.assertEqual(resultado["geradas"], 0)

    def test_falha_de_emissao_nao_impede_geracao_da_cobranca(self):
        """Sem `MERCADOPAGO_ACCESS_TOKEN` configurado no ambiente de teste,
        `issue_charge` recusa — mas a cobrança em si já existe e é válida."""
        self._criar()
        resultado = services.generate_recurring_charges(reference_date=date(2026, 9, 1))
        self.assertEqual(resultado["geradas"], 1)
        self.assertEqual(resultado["falhas_emissao"], 1)
        self.assertTrue(Charge.objects.filter(charge_type=ChargeType.RECURRING).exists())

    def test_gera_uma_cobranca_por_assinatura_vencida(self):
        self._criar(service_description="Hospedagem")
        self._criar(service_description="Manutenção", next_billing_date=date(2026, 8, 15))

        resultado = services.generate_recurring_charges(reference_date=date(2026, 9, 1))
        self.assertEqual(resultado["geradas"], 2)
