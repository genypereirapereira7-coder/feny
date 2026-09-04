from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from apps.mercadopago import client
from apps.mercadopago.exceptions import MercadoPagoError


@override_settings(MERCADOPAGO_ACCESS_TOKEN="token-de-teste", MERCADOPAGO_BASE_URL="https://mp.teste")
class CreatePreferenceTests(TestCase):
    @patch("apps.mercadopago.client.requests.post")
    def test_monta_requisicao_correta(self, mock_post):
        mock_post.return_value = Mock(ok=True, json=lambda: {"id": "pref-1", "init_point": "https://pay/1"})

        resultado = client.create_preference(external_reference="charge-1", description="Sinal", amount="3000.00")

        self.assertEqual(resultado["id"], "pref-1")
        url_chamada, kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        self.assertEqual(url_chamada, "https://mp.teste/checkout/preferences")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer token-de-teste")
        self.assertEqual(kwargs["json"]["external_reference"], "charge-1")

    @patch("apps.mercadopago.client.requests.post")
    def test_http_nao_ok_vira_mercadopagoerror(self, mock_post):
        mock_post.return_value = Mock(ok=False, status_code=401, text="unauthorized")
        with self.assertRaises(MercadoPagoError):
            client.create_preference(external_reference="x", description="x", amount="10.00")

    @patch("apps.mercadopago.client.requests.post", side_effect=requests.exceptions.ConnectionError("timeout"))
    def test_falha_de_rede_vira_mercadopagoerror(self, mock_post):
        with self.assertRaises(MercadoPagoError):
            client.create_preference(external_reference="x", description="x", amount="10.00")


@override_settings(MERCADOPAGO_ACCESS_TOKEN="", MERCADOPAGO_BASE_URL="https://mp.teste")
class SemTokenConfiguradoTests(TestCase):
    def test_recusa_sem_token(self):
        with self.assertRaises(MercadoPagoError):
            client.create_preference(external_reference="x", description="x", amount="10.00")


@override_settings(MERCADOPAGO_ACCESS_TOKEN="token-de-teste", MERCADOPAGO_BASE_URL="https://mp.teste")
class GetPaymentTests(TestCase):
    @patch("apps.mercadopago.client.requests.get")
    def test_consulta_pagamento(self, mock_get):
        mock_get.return_value = Mock(ok=True, json=lambda: {"id": 123, "status": "approved"})
        resultado = client.get_payment("123")
        self.assertEqual(resultado["status"], "approved")
        mock_get.assert_called_once()
        self.assertIn("https://mp.teste/v1/payments/123", mock_get.call_args[0][0])
