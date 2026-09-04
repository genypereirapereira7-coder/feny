import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """Cargo do usuário — a base do RBAC (ARCHITECTURE.md §9).

    Cada papel mapeia 1:1 para um Django Group do mesmo nome (ver signals.py).
    Permissões finas por domínio (ex.: "vendedor só vê os próprios orçamentos")
    não vivem aqui — são filtro de queryset nos apps que ainda serão
    construídos nas próximas fases.
    """

    ADMIN = "ADMIN", "Administrador"
    MANAGER = "MANAGER", "Gerente/Dono"
    SALES = "SALES", "Vendedor"
    DEVELOPER = "DEVELOPER", "Desenvolvedor"
    FINANCE = "FINANCE", "Financeiro"
    SUPPORT = "SUPPORT", "Suporte"


class User(AbstractUser):
    """Usuário da Feny (ARCHITECTURE.md §6.1).

    UUID como chave primária. `date_joined`/`last_login` já vêm do
    `AbstractUser` — não duplicar como `created_at`/`last_login_at` seria
    redundância sem motivo (ver ARCHITECTURE.md §21).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices)
    two_factor_enabled = models.BooleanField(default=False)
    # Segredo TOTP (ARCHITECTURE.md §13, Fase 10). Nunca exposto por nenhum
    # serializer — só `apps/users/two_factor.py` lê/escreve este campo.
    # `two_factor_enabled` só vira `True` depois de um código válido
    # confirmar a posse do segredo (`TwoFactorConfirmView`); setar os dois
    # direto no banco é o único jeito de burlar isso, e nenhum serializer
    # de escrita expõe `two_factor_secret` pra alguém fazer isso pela API.
    two_factor_secret = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "users_user"

    def __str__(self) -> str:
        return self.get_full_name() or self.username
