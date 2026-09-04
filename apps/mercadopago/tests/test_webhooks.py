from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.audit.models import AuditLog, ExternalWebhookEvent
from apps.core.choices import PaymentMethod, ProjectType
from apps.customers.models import Customer, CustomerKind
from apps.finance import services as finance_services
from apps.finance.models import ChargeStatus, Commission, Payment
from apps.mercadopago.exceptions import MercadoPagoError
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User

_URL = "/api/webhooks/mercadopago/"


class MercadoPagoWebhookTestCase(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.financeiro = User.objects.create_user(username="f1", password="senha-forte-123", role=Role.FINANCE)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )
        self.orcamento = Quotation.objects.create(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="Site institucional", amount="10000.00",
            status=QuotationStatus.APPROVED, decided_by=self.gerente,
        )
        self.projeto = Project.objects.create(
            customer=self.cliente, quotation=self.orcamento, name="Site institucional",
            project_type=ProjectType.WEBSITE, responsible=self.dev, amount=Decimal("10000.00"),
            status=ProjectStatus.APPROVED,
        )
        self.cobranca = finance_services.create_initial_charge(self.projeto, self.financeiro)

    def _payload(self, mp_id="mp-payment-1"):
        return {"type": "payment", "data": {"id": mp_id}}

    def _pagamento_aprovado(self, **overrides):
        base = {
            "id": "mp-payment-1", "status": "approved", "external_reference": str(self.cobranca.id),
            "transaction_amount": 3000.00, "payment_method_id": "pix",
            "date_approved": "2026-09-01T10:00:00.000-03:00",
        }
        base.update(overrides)
        return base


class RelevanceAndIdempotencyTests(MercadoPagoWebhookTestCase):
    def test_evento_sem_data_id_e_ignorado_sem_criar_registro(self):
        resposta = self.client.post(_URL, {}, format="json")
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(ExternalWebhookEvent.objects.exists())

    def test_tipo_diferente_de_payment_e_marcado_ignored(self):
        resposta = self.client.post(_URL, {"type": "merchant_order", "data": {"id": "1"}}, format="json")
        self.assertEqual(resposta.status_code, 200)
        evento = ExternalWebhookEvent.objects.get(external_event_id="1")
        self.assertEqual(evento.status, ExternalWebhookEvent.Status.IGNORED)

    @patch("apps.mercadopago.webhooks.client.get_payment")
    def test_evento_duplicado_nao_reprocessa(self, mock_get_payment):
        mock_get_payment.return_value = self._pagamento_aprovado()

        self.client.post(_URL, self._payload(), format="json")
        self.client.post(_URL, self._payload(), format="json")

        self.assertEqual(ExternalWebhookEvent.objects.filter(external_event_id="mp-payment-1").count(), 1)
        self.assertEqual(Payment.objects.filter(external_id="mp-payment-1").count(), 1)
        self.assertEqual(mock_get_payment.call_count, 1)


class PaymentConfirmationTests(MercadoPagoWebhookTestCase):
    @patch("apps.mercadopago.webhooks.client.get_payment")
    def test_pagamento_aprovado_confirma_cobranca_e_avanca_projeto(self, mock_get_payment):
        mock_get_payment.return_value = self._pagamento_aprovado()

        resposta = self.client.post(_URL, self._payload(), format="json")
        self.assertEqual(resposta.status_code, 200)

        self.cobranca.refresh_from_db()
        self.assertEqual(self.cobranca.status, ChargeStatus.PAID)

        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjectStatus.INITIAL_PAYMENT_CONFIRMED)

        pagamento = Payment.objects.get(external_id="mp-payment-1")
        self.assertEqual(pagamento.amount, Decimal("3000.00"))
        self.assertTrue(Commission.objects.filter(payment=pagamento).exists())

        evento = ExternalWebhookEvent.objects.get(external_event_id="mp-payment-1")
        self.assertEqual(evento.status, ExternalWebhookEvent.Status.PROCESSED)
        self.assertIsNotNone(evento.processed_at)

    @patch("apps.mercadopago.webhooks.client.get_payment")
    def test_confirmacao_via_webhook_registra_auditoria_como_sistema(self, mock_get_payment):
        mock_get_payment.return_value = self._pagamento_aprovado()
        self.client.post(_URL, self._payload(), format="json")

        log = AuditLog.objects.get(action="payment.confirmed")
        self.assertIsNone(log.user)

    @patch("apps.mercadopago.webhooks.client.get_payment")
    def test_pagamento_pendente_nao_confirma_nada(self, mock_get_payment):
        mock_get_payment.return_value = self._pagamento_aprovado(status="pending")

        self.client.post(_URL, self._payload(), format="json")

        self.cobranca.refresh_from_db()
        self.assertEqual(self.cobranca.status, ChargeStatus.PENDING)
        self.assertFalse(Payment.objects.exists())

        evento = ExternalWebhookEvent.objects.get(external_event_id="mp-payment-1")
        self.assertEqual(evento.status, ExternalWebhookEvent.Status.PROCESSED)

    @patch("apps.mercadopago.webhooks.client.get_payment")
    def test_external_reference_desconhecida_marca_evento_como_failed(self, mock_get_payment):
        mock_get_payment.return_value = self._pagamento_aprovado(external_reference="00000000-0000-0000-0000-000000000000")

        self.client.post(_URL, self._payload(), format="json")

        evento = ExternalWebhookEvent.objects.get(external_event_id="mp-payment-1")
        self.assertEqual(evento.status, ExternalWebhookEvent.Status.FAILED)
        self.assertFalse(Payment.objects.exists())

    @patch("apps.mercadopago.webhooks.client.get_payment", side_effect=MercadoPagoError("timeout"))
    def test_falha_ao_consultar_mercado_pago_marca_evento_como_failed(self, mock_get_payment):
        resposta = self.client.post(_URL, self._payload(), format="json")
        self.assertEqual(resposta.status_code, 200)

        evento = ExternalWebhookEvent.objects.get(external_event_id="mp-payment-1")
        self.assertEqual(evento.status, ExternalWebhookEvent.Status.FAILED)
        self.assertIn("timeout", evento.error)

    @patch("apps.mercadopago.webhooks.client.get_payment")
    def test_pagamento_de_cobranca_ja_paga_marca_evento_failed_sem_duplicar(self, mock_get_payment):
        """Segunda notificação real (`payment_id` diferente) pra uma cobrança
        que outro caminho já pagou — o service recusa (`DomainError`), o
        webhook não deixa isso virar 500, só registra e segue."""
        finance_services.confirm_payment(
            self.cobranca, self.financeiro, external_id="outro-pagamento", amount=Decimal("3000.00"), method="PIX",
        )
        mock_get_payment.return_value = self._pagamento_aprovado(id="mp-payment-2")

        resposta = self.client.post(_URL, self._payload(mp_id="mp-payment-2"), format="json")
        self.assertEqual(resposta.status_code, 200)

        evento = ExternalWebhookEvent.objects.get(external_event_id="mp-payment-2")
        self.assertEqual(evento.status, ExternalWebhookEvent.Status.FAILED)
        self.assertEqual(Payment.objects.count(), 1)
