from unittest.mock import Mock, patch

from django.test import TestCase

from apps.whatsapp import service
from apps.whatsapp.exceptions import EvolutionApiError


class SendTests(TestCase):
    @patch("apps.whatsapp.service.client.send_text")
    def test_renderiza_template_e_envia(self, mock_send_text):
        notification = Mock(
            recipient="11999999999", template="charge.issued",
            context={
                "customer_name": "Fulano", "charge_label": "Sinal (30%)",
                "charge_amount": "R$ 3000.00", "payment_link": "https://pay/1",
            },
        )

        service.send(notification)

        mock_send_text.assert_called_once()
        numero, texto = mock_send_text.call_args[0]
        self.assertEqual(numero, "11999999999")
        self.assertIn("Fulano", texto)
        self.assertIn("https://pay/1", texto)

    def test_template_desconhecido_levanta_erro(self):
        notification = Mock(recipient="11999999999", template="algo.inexistente", context={})
        with self.assertRaises(EvolutionApiError):
            service.send(notification)

    def test_contexto_incompleto_levanta_erro(self):
        notification = Mock(recipient="11999999999", template="payment.received", context={})
        with self.assertRaises(EvolutionApiError):
            service.send(notification)
