from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from apps.whatsapp import client
from apps.whatsapp.exceptions import EvolutionApiError

_CONFIGURADO = {
    "EVOLUTION_API_BASE_URL": "https://evo.teste",
    "EVOLUTION_API_KEY": "chave-de-teste",
    "EVOLUTION_API_INSTANCE": "feny",
}


@override_settings(**_CONFIGURADO)
class SendTextTests(TestCase):
    @patch("apps.whatsapp.client.requests.post")
    def test_monta_requisicao_correta(self, mock_post):
        mock_post.return_value = Mock(ok=True, json=lambda: {"status": "sent"})

        client.send_text("(11) 99999-9999", "Olá!")

        url_chamada, kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        self.assertEqual(url_chamada, "https://evo.teste/message/sendText/feny")
        self.assertEqual(kwargs["headers"]["apikey"], "chave-de-teste")
        self.assertEqual(kwargs["json"]["number"], "11999999999")
        self.assertEqual(kwargs["json"]["text"], "Olá!")

    @patch("apps.whatsapp.client.requests.post")
    def test_http_nao_ok_vira_evolutionapierror(self, mock_post):
        mock_post.return_value = Mock(ok=False, status_code=500, text="erro interno")
        with self.assertRaises(EvolutionApiError):
            client.send_text("11999999999", "x")

    @patch("apps.whatsapp.client.requests.post", side_effect=requests.exceptions.ConnectionError("timeout"))
    def test_falha_de_rede_vira_evolutionapierror(self, mock_post):
        with self.assertRaises(EvolutionApiError):
            client.send_text("11999999999", "x")


@override_settings(EVOLUTION_API_BASE_URL="", EVOLUTION_API_KEY="", EVOLUTION_API_INSTANCE="")
class SemConfiguracaoTests(TestCase):
    def test_recusa_sem_configuracao(self):
        with self.assertRaises(EvolutionApiError):
            client.send_text("11999999999", "x")
