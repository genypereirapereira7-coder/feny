from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.choices import PaymentMethod, ProjectType
from apps.customers.models import Customer, CustomerKind
from apps.finance.models import Charge, ChargeStatus, ChargeType, Commission, Expense
from apps.projects.models import Project, ProjectStatus
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class FinanceApiTestCase(APITestCase):
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
            project_type=ProjectType.WEBSITE, responsible=self.dev, amount="10000.00",
            status=ProjectStatus.APPROVED,
        )


class ChargePermissionTests(FinanceApiTestCase):
    def test_financeiro_cria_cobranca_inicial(self):
        self.client.force_authenticate(self.financeiro)
        resposta = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)})
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["amount"], "3000.00")

    def test_vendedor_nao_acessa_finance(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/finance/charges/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_dev_nao_acessa_finance(self):
        self.client.force_authenticate(self.dev)
        resposta = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)})
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_gerente_so_ve_nao_cria(self):
        self.client.force_authenticate(self.gerente)
        resposta_leitura = self.client.get("/api/v1/finance/charges/")
        self.assertEqual(resposta_leitura.status_code, status.HTTP_200_OK)

        resposta_escrita = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)})
        self.assertEqual(resposta_escrita.status_code, status.HTTP_403_FORBIDDEN)

    def test_confirma_pagamento_e_cancela_via_api(self):
        self.client.force_authenticate(self.financeiro)
        cobranca = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)}).data

        resposta = self.client.post(
            f"/api/v1/finance/charges/{cobranca['id']}/confirm-payment/",
            {"external_id": "mp-abc", "amount": "3000.00", "method": "PIX"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], ChargeStatus.PAID)

        outra_cobranca_pendente = Charge.objects.create(
            project=self.projeto, customer=self.cliente, charge_type=ChargeType.SCOPE_CHANGE,
            amount=Decimal("500.00"), due_date="2026-10-01", payment_method=PaymentMethod.BOLETO,
        )
        resposta_cancela = self.client.post(f"/api/v1/finance/charges/{outra_cobranca_pendente.id}/cancel/")
        self.assertEqual(resposta_cancela.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_cancela.data["status"], ChargeStatus.CANCELLED)


class IssueChargeApiTests(FinanceApiTestCase):
    @patch("apps.finance.services.mercadopago_adapter.create_charge_preference")
    def test_financeiro_emite_cobranca_no_mercado_pago(self, mock_create_preference):
        mock_create_preference.return_value = {"external_id": "pref-1", "payment_link": "https://pay/1"}
        self.client.force_authenticate(self.financeiro)
        cobranca = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)}).data

        resposta = self.client.post(f"/api/v1/finance/charges/{cobranca['id']}/issue/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["external_id"], "pref-1")
        self.assertEqual(resposta.data["payment_link"], "https://pay/1")

    def test_sem_mercado_pago_configurado_devolve_400_nao_500(self):
        self.client.force_authenticate(self.financeiro)
        cobranca = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)}).data

        resposta = self.client.post(f"/api/v1/finance/charges/{cobranca['id']}/issue/")
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)


class ExpenseApiTests(FinanceApiTestCase):
    def test_financeiro_cria_e_paga_despesa(self):
        self.client.force_authenticate(self.financeiro)
        criada = self.client.post(
            "/api/v1/finance/expenses/",
            {"category": "infra", "description": "Servidor", "amount": "150.00", "due_date": "2026-09-10"},
        ).data
        self.assertEqual(criada["status"], Expense.Status.PENDING)

        paga = self.client.post(f"/api/v1/finance/expenses/{criada['id']}/pay/")
        self.assertEqual(paga.status_code, status.HTTP_200_OK)
        self.assertEqual(paga.data["status"], Expense.Status.PAID)

    def test_vendedor_nao_cria_despesa(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post(
            "/api/v1/finance/expenses/",
            {"category": "infra", "description": "x", "amount": "10.00", "due_date": "2026-09-10"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)


class CommissionApiTests(FinanceApiTestCase):
    def _gerar_comissao(self) -> dict:
        self.client.force_authenticate(self.financeiro)
        cobranca = self.client.post("/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)}).data
        self.client.post(
            f"/api/v1/finance/charges/{cobranca['id']}/confirm-payment/",
            {"external_id": "mp-abc", "amount": "3000.00", "method": "PIX"},
        )
        return Commission.objects.get(project=self.projeto)

    def test_vendedor_ve_so_a_propria_comissao(self):
        comissao = self._gerar_comissao()
        outro_vendedor = User.objects.create_user(username="v2", password="senha-forte-123", role=Role.SALES)

        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/finance/commissions/")
        self.assertEqual(len(resposta.data["results"]), 1)
        self.assertEqual(resposta.data["results"][0]["id"], str(comissao.id))

        self.client.force_authenticate(outro_vendedor)
        resposta_outro = self.client.get("/api/v1/finance/commissions/")
        self.assertEqual(len(resposta_outro.data["results"]), 0)

    def test_vendedor_nao_marca_a_propria_comissao_como_paga(self):
        comissao = self._gerar_comissao()
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post(f"/api/v1/finance/commissions/{comissao.id}/pay/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_financeiro_marca_comissao_como_paga(self):
        comissao = self._gerar_comissao()
        self.client.force_authenticate(self.financeiro)
        resposta = self.client.post(f"/api/v1/finance/commissions/{comissao.id}/pay/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], Commission.Status.PAID)


class FullProjectLifecycleIntegrationTest(FinanceApiTestCase):
    """ARCHITECTURE.md §16, prioridade 4: "Fluxo completo orçamento → projeto
    → 30% → desenvolvimento → 70% → entregue" ponta a ponta, via API."""

    def test_fluxo_completo(self):
        self.client.force_authenticate(self.financeiro)
        inicial = self.client.post(
            "/api/v1/finance/charges/create-initial/", {"project": str(self.projeto.id)}
        ).data
        self.assertEqual(inicial["amount"], "3000.00")

        self.client.post(
            f"/api/v1/finance/charges/{inicial['id']}/confirm-payment/",
            {"external_id": "mp-inicial", "amount": "3000.00", "method": "PIX"},
        )
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjectStatus.INITIAL_PAYMENT_CONFIRMED)

        self.client.force_authenticate(self.dev)
        self.client.post(f"/api/v1/projects/{self.projeto.id}/start-development/")
        self.client.post(f"/api/v1/projects/{self.projeto.id}/complete-development/")
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjectStatus.AWAITING_CLIENT_ACCEPTANCE)

        self.client.force_authenticate(self.gerente)
        self.client.post(f"/api/v1/projects/{self.projeto.id}/accept/")
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjectStatus.ACCEPTED)

        self.client.force_authenticate(self.financeiro)
        final = self.client.post(
            "/api/v1/finance/charges/create-final/", {"project": str(self.projeto.id)}
        ).data
        self.assertEqual(final["amount"], "7000.00")

        self.client.post(
            f"/api/v1/finance/charges/{final['id']}/confirm-payment/",
            {"external_id": "mp-final", "amount": "7000.00", "method": "PIX"},
        )
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjectStatus.FINAL_PAYMENT_CONFIRMED)

        self.client.force_authenticate(self.gerente)
        self.client.post(f"/api/v1/projects/{self.projeto.id}/mark-delivered/")
        self.client.post(f"/api/v1/projects/{self.projeto.id}/enter-maintenance/")
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjectStatus.MAINTENANCE)
        self.assertIsNotNone(self.projeto.delivered_at)

        comissoes = Commission.objects.filter(project=self.projeto).order_by("amount")
        self.assertEqual(list(comissoes.values_list("amount", flat=True)), [Decimal("300.00"), Decimal("700.00")])
        self.assertEqual(sum(c.amount for c in comissoes), Decimal("1000.00"))


class SubscriptionApiTests(FinanceApiTestCase):
    def _payload(self, **overrides):
        payload = {
            "customer": str(self.cliente.id), "service_description": "Hospedagem mensal",
            "amount": "150.00", "start_date": "2026-09-10",
        }
        payload.update(overrides)
        return payload

    def test_financeiro_cria_assinatura(self):
        self.client.force_authenticate(self.financeiro)
        resposta = self.client.post("/api/v1/finance/subscriptions/", self._payload())

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["status"], "ACTIVE")
        self.assertEqual(resposta.data["next_billing_date"], "2026-09-10")

    def test_vendedor_nao_cria_assinatura(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post("/api/v1/finance/subscriptions/", self._payload())
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_gerente_so_ve_nao_cria(self):
        self.client.force_authenticate(self.gerente)
        resposta_leitura = self.client.get("/api/v1/finance/subscriptions/")
        self.assertEqual(resposta_leitura.status_code, status.HTTP_200_OK)

        resposta_escrita = self.client.post("/api/v1/finance/subscriptions/", self._payload())
        self.assertEqual(resposta_escrita.status_code, status.HTTP_403_FORBIDDEN)

    def test_pausa_retoma_e_cancela_via_api(self):
        self.client.force_authenticate(self.financeiro)
        criada = self.client.post("/api/v1/finance/subscriptions/", self._payload()).data

        pausada = self.client.post(f"/api/v1/finance/subscriptions/{criada['id']}/pause/")
        self.assertEqual(pausada.data["status"], "PAUSED")

        retomada = self.client.post(f"/api/v1/finance/subscriptions/{criada['id']}/resume/")
        self.assertEqual(retomada.data["status"], "ACTIVE")

        cancelada = self.client.post(f"/api/v1/finance/subscriptions/{criada['id']}/cancel/")
        self.assertEqual(cancelada.data["status"], "CANCELLED")

    def test_nao_edita_valor_de_assinatura_existente(self):
        self.client.force_authenticate(self.financeiro)
        criada = self.client.post("/api/v1/finance/subscriptions/", self._payload()).data

        resposta = self.client.patch(f"/api/v1/finance/subscriptions/{criada['id']}/", {"amount": "999.00"})
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edita_descricao_do_servico(self):
        self.client.force_authenticate(self.financeiro)
        criada = self.client.post("/api/v1/finance/subscriptions/", self._payload()).data

        resposta = self.client.patch(
            f"/api/v1/finance/subscriptions/{criada['id']}/", {"service_description": "Hospedagem + manutenção"}
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["service_description"], "Hospedagem + manutenção")

    def test_sem_rota_de_exclusao(self):
        self.client.force_authenticate(self.financeiro)
        criada = self.client.post("/api/v1/finance/subscriptions/", self._payload()).data

        resposta = self.client.delete(f"/api/v1/finance/subscriptions/{criada['id']}/")
        self.assertIn(resposta.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))
