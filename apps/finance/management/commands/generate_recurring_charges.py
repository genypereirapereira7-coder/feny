"""Chamado por cron simples, uma vez por dia (ARCHITECTURE.md §17, mesma
disciplina de `dispatch_notifications` da Fase 7 — sem Celery, sem volume
que justifique)."""

from django.core.management.base import BaseCommand

from apps.finance import services


class Command(BaseCommand):
    help = "Gera as cobranças recorrentes vencidas hoje e emite no Mercado Pago quando possível."

    def handle(self, *args, **options):
        resultado = services.generate_recurring_charges()
        self.stdout.write(self.style.SUCCESS(
            f"{resultado['geradas']} cobrança(s) gerada(s); "
            f"{resultado['falhas_emissao']} não conseguiram emitir no Mercado Pago (continuam válidas)."
        ))
