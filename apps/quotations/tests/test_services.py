from django.test import TestCase

from apps.audit.models import AuditLog
from apps.core.choices import PaymentMethod, ProjectType
from apps.core.exceptions import DomainError
from apps.customers.models import Customer, CustomerKind
from apps.quotations import services
from apps.quotations.models import Quotation, QuotationStatus
from apps.users.models import Role, User


class QuotationServicesTestCase(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.outro_vendedor = User.objects.create_user(username="v2", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)

        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )

    def _criar_orcamento(self, **overrides) -> Quotation:
        dados = dict(
            customer=self.cliente, sales_rep=self.vendedor, service_type=ProjectType.WEBSITE,
            description="Site institucional", amount="10000.00",
        )
        dados.update(overrides)
        return Quotation.objects.create(**dados)


class SubmitForApprovalTests(QuotationServicesTestCase):
    def test_rascunho_vai_para_aguardando_aprovacao(self):
        orcamento = self._criar_orcamento()
        services.submit_for_approval(orcamento, self.vendedor)

        orcamento.refresh_from_db()
        self.assertEqual(orcamento.status, QuotationStatus.PENDING_APPROVAL)

    def test_nao_pode_reenviar_o_que_ja_esta_pendente(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)
        with self.assertRaises(DomainError):
            services.submit_for_approval(orcamento, self.vendedor)


class ApproveQuotationTests(QuotationServicesTestCase):
    def test_gerente_aprova_orcamento_de_outro(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)

        services.approve_quotation(orcamento, self.gerente)

        orcamento.refresh_from_db()
        self.assertEqual(orcamento.status, QuotationStatus.APPROVED)
        self.assertEqual(orcamento.decided_by, self.gerente)
        self.assertIsNotNone(orcamento.decided_at)

    def test_vendedor_nao_aprova_o_proprio_orcamento(self):
        """A regra mais importante da Fase 3 — não pode ter jeito de burlar."""
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)

        with self.assertRaises(DomainError):
            services.approve_quotation(orcamento, self.vendedor)

        orcamento.refresh_from_db()
        self.assertEqual(orcamento.status, QuotationStatus.PENDING_APPROVAL)  # nada mudou

    def test_vendedor_pode_aprovar_orcamento_de_outro_vendedor(self):
        """A trava é "é o mesmo vendedor?", não "é vendedor?" — outro vendedor
        também não deveria poder decidir (só ADMIN/MANAGER chegam aqui pela
        API), mas o service em si só protege contra auto-aprovação; quem
        filtra por papel é a permission (ver test_api.py)."""
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)
        services.approve_quotation(orcamento, self.outro_vendedor)

        orcamento.refresh_from_db()
        self.assertEqual(orcamento.status, QuotationStatus.APPROVED)

    def test_nao_aprova_rascunho_direto(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.DRAFT)
        with self.assertRaises(DomainError):
            services.approve_quotation(orcamento, self.gerente)

    def test_aprovacao_grava_auditoria(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)
        services.approve_quotation(orcamento, self.gerente)

        log = AuditLog.objects.get(action="quotation.approved")
        self.assertEqual(log.user, self.gerente)
        self.assertEqual(log.entity_id, str(orcamento.id))
        self.assertEqual(log.before, {"status": QuotationStatus.PENDING_APPROVAL})
        self.assertEqual(log.after, {"status": QuotationStatus.APPROVED})


class RejectQuotationTests(QuotationServicesTestCase):
    def test_gerente_rejeita_com_motivo(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)
        services.reject_quotation(orcamento, self.gerente, reason="Preço fora do orçamento do cliente")

        orcamento.refresh_from_db()
        self.assertEqual(orcamento.status, QuotationStatus.REJECTED)

        log = AuditLog.objects.get(action="quotation.rejected")
        self.assertEqual(log.metadata, {"reason": "Preço fora do orçamento do cliente"})

    def test_vendedor_nao_rejeita_o_proprio_orcamento(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.PENDING_APPROVAL)
        with self.assertRaises(DomainError):
            services.reject_quotation(orcamento, self.vendedor)


class CancelQuotationTests(QuotationServicesTestCase):
    def test_cancela_rascunho(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.DRAFT)
        services.cancel_quotation(orcamento, self.vendedor)

        orcamento.refresh_from_db()
        self.assertEqual(orcamento.status, QuotationStatus.CANCELLED)

    def test_nao_cancela_orcamento_ja_decidido(self):
        orcamento = self._criar_orcamento(status=QuotationStatus.APPROVED)
        with self.assertRaises(DomainError):
            services.cancel_quotation(orcamento, self.vendedor)
