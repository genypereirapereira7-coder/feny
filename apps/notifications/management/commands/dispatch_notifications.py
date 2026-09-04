"""Chamado por cron simples (ARCHITECTURE.md §17) — não é Celery de propósito:
não há, ainda, volume ou necessidade de retry robusto que justifique a
complexidade extra."""

from django.core.management.base import BaseCommand

from apps.notifications import services


class Command(BaseCommand):
    help = "Envia as notificações pendentes (e as que falharam e ainda podem tentar de novo)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        resultado = services.dispatch_pending(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(
            f"{resultado['enviadas']} enviada(s), {resultado['falharam']} falharam "
            f"(de {resultado['total']} processada(s))."
        ))
