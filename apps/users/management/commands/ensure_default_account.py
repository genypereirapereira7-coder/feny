"""Garante que a conta única do sistema (frontend/src/routes/LoginPage.tsx —
tela de login só com senha, usuário fixo) existe com a senha configurada no
ambiente. Idempotente, como `create_default_groups`: rodar de novo não quebra
nada, só confirma o estado.

Existe porque um deploy novo (Railway, ou qualquer ambiente novo) sobe um
banco Postgres vazio — sem isto, a senha só existiria em bancos onde alguém
rodou `manage.py shell` manualmente, o que já causou login não funcionar em
produção depois de funcionar local (bancos diferentes, um só tinha a conta).

A senha nunca mora no código — só em `DEFAULT_ACCOUNT_PASSWORD`, variável de
ambiente (ARCHITECTURE.md §13: segredo nunca no repositório).
"""

import os

from django.core.management.base import BaseCommand

from apps.users.models import Role, User


class Command(BaseCommand):
    help = "Garante a conta única do sistema (usuário fixo, senha do ambiente)."

    def handle(self, *args, **options):
        username = os.getenv("DEFAULT_ACCOUNT_USERNAME", "gerente")
        password = os.getenv("DEFAULT_ACCOUNT_PASSWORD")

        if not password:
            self.stdout.write(self.style.WARNING(
                "DEFAULT_ACCOUNT_PASSWORD não definida — nada a fazer (login continua com a senha já existente)."
            ))
            return

        usuario, criado = User.objects.get_or_create(
            username=username, defaults={"role": Role.MANAGER, "is_active": True},
        )
        usuario.set_password(password)
        usuario.is_active = True
        usuario.save()

        acao = "criada" if criado else "senha atualizada"
        self.stdout.write(self.style.SUCCESS(f"Conta '{username}' {acao}."))
