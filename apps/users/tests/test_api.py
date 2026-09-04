from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Role, User


class TokenAuthTests(APITestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="adriano", password="senha-forte-123", role=Role.MANAGER
        )

    def test_login_com_credencial_valida_devolve_tokens(self):
        resposta = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "adriano", "password": "senha-forte-123"},
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("access", resposta.data)
        self.assertIn("refresh", resposta.data)

    def test_login_com_senha_errada_e_recusado(self):
        resposta = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "adriano", "password": "senha-errada"},
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)


class MeEndpointTests(APITestCase):
    def test_usuario_autenticado_ve_a_propria_identidade(self):
        usuario = User.objects.create_user(
            username="vendedor1", password="senha-forte-123", role=Role.SALES
        )
        self.client.force_authenticate(usuario)

        resposta = self.client.get("/api/v1/users/me/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["username"], "vendedor1")
        self.assertEqual(resposta.data["role"], Role.SALES)

    def test_anonimo_nao_acessa(self):
        resposta = self.client.get("/api/v1/users/me/")
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)


class UserViewSetPermissionTests(APITestCase):
    """Só ADMIN administra contas — ver apps/core/permissions.py."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="senha-forte-123", role=Role.ADMIN)
        self.vendedor = User.objects.create_user(username="vendedor2", password="senha-forte-123", role=Role.SALES)

    def test_admin_lista_usuarios(self):
        self.client.force_authenticate(self.admin)
        resposta = self.client.get("/api/v1/users/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_vendedor_nao_lista_usuarios(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get("/api/v1/users/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
