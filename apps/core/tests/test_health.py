from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import Client, TestCase


class HealthCheckTests(TestCase):
    def test_health_responde_ok_com_banco_de_verdade(self):
        resposta = Client().get("/health/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok", "database": "ok"})

    @patch("apps.core.views.connection.cursor", side_effect=OperationalError("banco fora do ar"))
    def test_health_reporta_erro_se_banco_estiver_fora_do_ar(self, mock_cursor):
        resposta = Client().get("/health/")
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.json()["database"], "unreachable")
