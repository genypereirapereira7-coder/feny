"""Cria o Group base de cada Role. Idempotente — rodar de novo não duplica.

As permissões (`Permission`) de cada domínio são adicionadas a estes grupos
conforme os apps de negócio (customers, quotations, projects, finance...) vão
sendo construídos — este comando só planta os grupos em si, vazios.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.users.models import Role


class Command(BaseCommand):
    help = "Cria um Group para cada Role, se ainda não existir."

    def handle(self, *args, **options):
        criados = 0
        for role in Role.values:
            _, criado = Group.objects.get_or_create(name=role)
            criados += int(criado)

        self.stdout.write(
            self.style.SUCCESS(f"{criados} grupo(s) criado(s); {len(Role.values) - criados} já existiam.")
        )
