from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.users.models import Role, User


class EnsureDefaultAccountTests(TestCase):
    """`ensure_default_account` — existe pra bancos novos (deploy do zero,
    ex.: Railway) nunca ficarem sem a conta única do sistema, mesmo que
    ninguém rode nada manual (ver docker-entrypoint.sh)."""

    @mock.patch.dict("os.environ", {"DEFAULT_ACCOUNT_PASSWORD": ""})
    def test_sem_variavel_de_ambiente_nao_faz_nada(self):
        call_command("ensure_default_account", stdout=StringIO())
        self.assertFalse(User.objects.filter(username="gerente").exists())

    def test_cria_conta_quando_nao_existe(self):
        with mock.patch.dict("os.environ", {"DEFAULT_ACCOUNT_PASSWORD": "senha-forte-123"}):
            call_command("ensure_default_account", stdout=StringIO())

        usuario = User.objects.get(username="gerente")
        self.assertEqual(usuario.role, Role.MANAGER)
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.two_factor_enabled)
        self.assertTrue(usuario.check_password("senha-forte-123"))

    def test_atualiza_senha_quando_ja_existe(self):
        User.objects.create_user(username="gerente", password="senha-antiga-123", role=Role.MANAGER)

        with mock.patch.dict("os.environ", {"DEFAULT_ACCOUNT_PASSWORD": "senha-nova-456"}):
            call_command("ensure_default_account", stdout=StringIO())

        usuario = User.objects.get(username="gerente")
        self.assertTrue(usuario.check_password("senha-nova-456"))
        self.assertFalse(usuario.check_password("senha-antiga-123"))

    def test_usuario_customizavel_via_variavel(self):
        with mock.patch.dict(
            "os.environ", {"DEFAULT_ACCOUNT_USERNAME": "outra-conta", "DEFAULT_ACCOUNT_PASSWORD": "senha-forte-123"},
        ):
            call_command("ensure_default_account", stdout=StringIO())

        self.assertTrue(User.objects.filter(username="outra-conta").exists())
        self.assertFalse(User.objects.filter(username="gerente").exists())

    def test_zera_2fa_de_uma_conta_que_ja_tinha_configurado(self):
        """Cenário real que travou o dono do sistema: a conta tinha 2FA
        configurado de uma sessão de navegador anterior, e continuava
        pedindo código mesmo depois da obrigatoriedade por papel ter sido
        desligada — `LoginView` olha `two_factor_enabled` na conta, não a
        regra de papel."""
        User.objects.create_user(
            username="gerente", password="senha-antiga-123", role=Role.MANAGER,
            two_factor_enabled=True, two_factor_secret="ALGUMSEGREDO",
        )

        with mock.patch.dict("os.environ", {"DEFAULT_ACCOUNT_PASSWORD": "senha-nova-456"}):
            call_command("ensure_default_account", stdout=StringIO())

        usuario = User.objects.get(username="gerente")
        self.assertFalse(usuario.two_factor_enabled)
        self.assertEqual(usuario.two_factor_secret, "")
