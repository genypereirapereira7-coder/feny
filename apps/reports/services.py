"""Relatórios agregados (ARCHITECTURE.md §19, Fase 9). Só um relatório nesta
fase — receita/despesa por mês — porque é o único que a especificação de
negócio já justifica sem inventar métrica nova: visão de caixa ao longo do
tempo é o pedido mais básico e recorrente de qualquer dono de empresa.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.finance.models import Expense, Revenue

_ZERO = Decimal("0.00")


def revenue_by_month(months: int = 6) -> list[dict]:
    """Uma consulta agregada por mês (`aggregate`, nunca soma em Python linha
    a linha) — pra `months` pequeno (o parâmetro é limitado na view) isso é
    simples e correto; não vale a complexidade extra de agrupar tudo numa
    query só com `TruncMonth` pra um relatório deste tamanho."""
    hoje = timezone.now().date()
    ano, mes = hoje.year, hoje.month
    ciclos = []
    for _ in range(months):
        ciclos.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    ciclos.reverse()

    resultado = []
    for ano, mes in ciclos:
        inicio = date(ano, mes, 1)
        fim = date(ano, mes, calendar.monthrange(ano, mes)[1])

        receita = Revenue.objects.filter(received_at__date__range=(inicio, fim)).aggregate(
            total=Sum("amount"),
        )["total"] or _ZERO
        despesa = Expense.objects.filter(
            status=Expense.Status.PAID, paid_at__date__range=(inicio, fim),
        ).aggregate(total=Sum("amount"))["total"] or _ZERO

        resultado.append({
            "month": f"{ano:04d}-{mes:02d}",
            "revenue": str(receita),
            "expenses": str(despesa),
            "net": str(receita - despesa),
        })
    return resultado
