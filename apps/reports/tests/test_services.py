from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.finance.models import Expense, Revenue, RevenueSource
from apps.reports import services
from apps.users.models import Role, User


class RevenueByMonthTests(TestCase):
    def setUp(self):
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)

    def test_meses_vem_em_ordem_do_mais_antigo_pro_mais_recente(self):
        resultado = services.revenue_by_month(months=3)
        meses = [item["month"] for item in resultado]
        self.assertEqual(meses, sorted(meses))
        self.assertEqual(len(resultado), 3)

    def test_mes_sem_movimento_devolve_zero(self):
        resultado = services.revenue_by_month(months=1)
        self.assertEqual(resultado[0]["revenue"], "0.00")
        self.assertEqual(resultado[0]["expenses"], "0.00")
        self.assertEqual(resultado[0]["net"], "0.00")

    def test_soma_receita_e_despesa_paga_do_mes_atual(self):
        agora = timezone.now()
        Revenue.objects.create(source=RevenueSource.OTHER, amount=Decimal("500.00"), received_at=agora)
        Revenue.objects.create(source=RevenueSource.OTHER, amount=Decimal("250.00"), received_at=agora)
        Expense.objects.create(
            category="infra", description="x", amount=Decimal("100.00"), due_date=agora.date(),
            status=Expense.Status.PAID, paid_at=agora, created_by=self.gerente,
        )
        # Despesa pendente (não paga) não deve entrar.
        Expense.objects.create(
            category="infra", description="y", amount=Decimal("999.00"), due_date=agora.date(),
            created_by=self.gerente,
        )

        resultado = services.revenue_by_month(months=1)[0]
        self.assertEqual(resultado["revenue"], "750.00")
        self.assertEqual(resultado["expenses"], "100.00")
        self.assertEqual(resultado["net"], "650.00")

    def test_mes_atual_e_o_ultimo_da_lista(self):
        mes_atual = timezone.now().strftime("%Y-%m")
        resultado = services.revenue_by_month(months=4)
        self.assertEqual(resultado[-1]["month"], mes_atual)
