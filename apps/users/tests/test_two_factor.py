import pyotp
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users import two_factor
from apps.users.models import Role, User


class TwoFactorHelpersTests(APITestCase):
    def test_precisa_configurar_2fa_para_papel_obrigatorio_sem_2fa(self):
        gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.assertTrue(two_factor.precisa_configurar_2fa(gerente))

    def test_nao_precisa_configurar_se_ja_tem_2fa_ativo(self):
        gerente = User.objects.create_user(
            username="g1", password="senha-forte-123", role=Role.MANAGER, two_factor_enabled=True,
        )
        self.assertFalse(two_factor.precisa_configurar_2fa(gerente))

    def test_papel_sem_2fa_obrigatorio_nao_precisa(self):
        vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.assertFalse(two_factor.precisa_configurar_2fa(vendedor))

    def test_verificar_codigo_correto(self):
        secret = two_factor.gerar_segredo()
        codigo = pyotp.TOTP(secret).now()
        self.assertTrue(two_factor.verificar_codigo(secret, codigo))

    def test_verificar_codigo_errado(self):
        secret = two_factor.gerar_segredo()
        self.assertFalse(two_factor.verificar_codigo(secret, "000000"))

    def test_verificar_codigo_vazio(self):
        secret = two_factor.gerar_segredo()
        self.assertFalse(two_factor.verificar_codigo(secret, ""))
        self.assertFalse(two_factor.verificar_codigo("", "123456"))


class LoginFlowTests(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)

    def test_papel_sem_2fa_obrigatorio_loga_normalmente(self):
        resposta = self.client.post(
            reverse("token_obtain_pair"), {"username": "v1", "password": "senha-forte-123"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertFalse(resposta.data["requires_2fa_setup"])

    def test_papel_com_2fa_obrigatorio_ainda_nao_configurado_loga_mas_sinaliza(self):
        resposta = self.client.post(
            reverse("token_obtain_pair"), {"username": "g1", "password": "senha-forte-123"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data["requires_2fa_setup"])

    def test_token_com_2fa_pendente_so_acessa_rotas_permitidas(self):
        login = self.client.post(
            reverse("token_obtain_pair"), {"username": "g1", "password": "senha-forte-123"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        bloqueado = self.client.get("/api/v1/quotations/")
        self.assertEqual(bloqueado.status_code, status.HTTP_401_UNAUTHORIZED)

        permitido = self.client.get("/api/v1/users/me/")
        self.assertEqual(permitido.status_code, status.HTTP_200_OK)

    def test_senha_errada_e_recusada(self):
        resposta = self.client.post(
            reverse("token_obtain_pair"), {"username": "v1", "password": "errada"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_com_2fa_ativo_precisa_do_codigo(self):
        secret = two_factor.gerar_segredo()
        self.vendedor.two_factor_secret = secret
        self.vendedor.two_factor_enabled = True
        self.vendedor.save()

        sem_codigo = self.client.post(
            reverse("token_obtain_pair"), {"username": "v1", "password": "senha-forte-123"},
        )
        self.assertEqual(sem_codigo.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(sem_codigo.data["requires_otp"])

        com_codigo = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "v1", "password": "senha-forte-123", "otp_code": pyotp.TOTP(secret).now()},
        )
        self.assertEqual(com_codigo.status_code, status.HTTP_200_OK)
        self.assertFalse(com_codigo.data["requires_2fa_setup"])


class TwoFactorSetupAndConfirmTests(APITestCase):
    def setUp(self):
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)

    def test_fluxo_completo_de_configuracao(self):
        self.client.force_authenticate(self.gerente)

        setup = self.client.post("/api/v1/auth/2fa/setup/")
        self.assertEqual(setup.status_code, status.HTTP_200_OK)
        self.assertIn("secret", setup.data)
        self.assertIn("otpauth_url", setup.data)

        self.gerente.refresh_from_db()
        self.assertFalse(self.gerente.two_factor_enabled)

        codigo = pyotp.TOTP(setup.data["secret"]).now()
        confirmacao = self.client.post("/api/v1/auth/2fa/confirm/", {"code": codigo})
        self.assertEqual(confirmacao.status_code, status.HTTP_200_OK)
        self.assertIn("access", confirmacao.data)

        self.gerente.refresh_from_db()
        self.assertTrue(self.gerente.two_factor_enabled)

    def test_confirmar_com_codigo_errado_nao_ativa(self):
        self.client.force_authenticate(self.gerente)
        self.client.post("/api/v1/auth/2fa/setup/")

        resposta = self.client.post("/api/v1/auth/2fa/confirm/", {"code": "000000"})
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

        self.gerente.refresh_from_db()
        self.assertFalse(self.gerente.two_factor_enabled)

    def test_setup_exige_autenticacao(self):
        resposta = self.client.post("/api/v1/auth/2fa/setup/")
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)


class ResetTwoFactorTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="senha-forte-123", role=Role.ADMIN)
        self.gerente = User.objects.create_user(
            username="g1", password="senha-forte-123", role=Role.MANAGER,
            two_factor_enabled=True, two_factor_secret="ALGUMSEGREDO",
        )

    def test_admin_reseta_2fa_de_outro_usuario(self):
        self.client.force_authenticate(self.admin)
        resposta = self.client.post(f"/api/v1/users/{self.gerente.id}/reset-2fa/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.gerente.refresh_from_db()
        self.assertFalse(self.gerente.two_factor_enabled)
        self.assertEqual(self.gerente.two_factor_secret, "")

    def test_nao_admin_nao_reseta(self):
        self.client.force_authenticate(self.gerente)
        resposta = self.client.post(f"/api/v1/users/{self.gerente.id}/reset-2fa/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_nao_ativa_2fa_via_patch_direto(self):
        """`two_factor_enabled` é read-only no serializer administrativo — só
        um código válido em `TwoFactorConfirmView` liga isso."""
        outro = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.client.force_authenticate(self.admin)

        resposta = self.client.patch(f"/api/v1/users/{outro.id}/", {"two_factor_enabled": True})
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        outro.refresh_from_db()
        self.assertFalse(outro.two_factor_enabled)
