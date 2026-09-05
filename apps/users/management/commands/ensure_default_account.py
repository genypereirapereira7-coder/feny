"""Garante que a conta única do sistema (frontend/src/routes/LoginPage.tsx —
tela de login só com senha, usuário fixo) existe com a senha configurada no
ambiente. Idempotente, como `create_default_groups`: rodar de novo não quebra
nada, só confirma o estado.

Existe porque um deploy novo (Railway, ou qualquer ambiente novo) sobe um
banco Postgres vazio — sem isto, a senha só existiria em bancos onde alguém
rodou `manage.py shell` manualmente, o que já causou login não funcionar em
produção depois de funcionar local (bancos diferentes, um só tinha a conta).

Também zera `two_factor_enabled`/`two_factor_secret` a cada deploy — o dono
do sistema pediu acesso direto só com senha (ver `two_factor.py`,
`PAPEIS_COM_2FA_OBRIGATORIO` vazio); sem isto, um 2FA configurado numa sessão
de navegador anterior continuaria pedindo código numa conta que não deveria
mais exigir isso, travando o próprio dono pra fora (foi exatamente isso que
aconteceu: a obrigatoriedade por papel foi desligada, mas a conta já tinha
`two_factor_enabled=True` de antes — LoginView pede o código de qualquer
jeito quando isso está ligado, não só quando o papel exige).

A senha nunca mora no código — só em `DEFAULT_ACCOUNT_PASSWORD`, variável de
ambiente (ARCHITECTURE.md §13: segredo nunca no repositório).
"""

import os

from django.core.management.base import BaseCommand

from apps.users.models import Role, User


class Command(BaseCommand):
    help = "Garante a conta única do sistema (usuário fixo, senha do ambiente, sem 2FA pendente)."

    def handle(self, *args, **options):
        username = os.getenv("DEFAULT_ACCOUNT_USERNAME", "gerente")
        password = os.getenv("DEFAULT_ACCOUNT_PASSWORD")

        if not password:
            self.stdout.write(self.style.WARNING(
                "DEFAULT_ACCOUNT_PASSWORD não definida — nada a fazer (login continua com o estado já existente)."
            ))
            return

        usuario, criado = User.objects.get_or_create(
            username=username, defaults={"role": Role.MANAGER, "is_active": True},
        )
        usuario.set_password(password)
        usuario.is_active = True
        usuario.two_factor_enabled = False
        usuario.two_factor_secret = ""
        usuario.save()

        acao = "criada" if criado else "senha atualizada e 2FA zerado"
        self.stdout.write(self.style.SUCCESS(f"Conta '{username}' {acao}."))
