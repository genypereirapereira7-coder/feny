from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.finance.models import ChargeStatus
from apps.mercadopago import adapter


class MapStatusTests(TestCase):
    def test_mapa_conhecido(self):
        casos = {
            "approved": ChargeStatus.PAID,
            "pending": ChargeStatus.PENDING,
            "in_process": ChargeStatus.PROCESSING,
            "authorized": ChargeStatus.PROCESSING,
            "cancelled": ChargeStatus.CANCELLED,
            "refunded": ChargeStatus.FAILED,
            "charged_back": ChargeStatus.FAILED,
            "rejected": ChargeStatus.FAILED,
        }
        for status_mp, esperado in casos.items():
            self.assertEqual(adapter.map_status(status_mp), esperado)

    def test_status_desconhecido_vira_failed(self):
        """Nunca confirma pagamento por omissão — um status novo do Mercado
        Pago que a gente ainda não mapeou cai no lado seguro."""
        self.assertEqual(adapter.map_status("um-status-que-nao-existe-ainda"), ChargeStatus.FAILED)


class CreateChargePreferenceTests(TestCase):
    @patch("apps.mercadopago.adapter.client.create_preference")
    def test_chama_client_com_os_dados_certos(self, mock_create):
        mock_create.return_value = {"id": "pref-123", "init_point": "https://pay/123"}
        cobranca_fake = Mock(id="charge-uuid", amount=Decimal("3000.00"))
        cobranca_fake.get_charge_type_display.return_value = "Sinal (30%)"
        cobranca_fake.customer.legal_name = "Fulano"

        resultado = adapter.create_charge_preference(cobranca_fake)

        self.assertEqual(resultado, {"external_id": "pref-123", "payment_link": "https://pay/123"})
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs["external_reference"], "charge-uuid")
        self.assertEqual(kwargs["amount"], Decimal("3000.00"))
        self.assertIn("Fulano", kwargs["description"])


class VerifySignatureTests(TestCase):
    def test_assinatura_valida(self):
        import hashlib
        import hmac

        manifesto = "id:123;request-id:req-1;ts:1700000000;"
        v1 = hmac.new(b"segredo", manifesto.encode(), hashlib.sha256).hexdigest()

        self.assertTrue(adapter.verify_signature(
            data_id="123", x_signature=f"ts=1700000000,v1={v1}", x_request_id="req-1", secret="segredo",
        ))

    def test_assinatura_invalida(self):
        self.assertFalse(adapter.verify_signature(
            data_id="123", x_signature="ts=1700000000,v1=lixo", x_request_id="req-1", secret="segredo",
        ))

    def test_header_mal_formado(self):
        self.assertFalse(adapter.verify_signature(
            data_id="123", x_signature="sem-formato-certo", x_request_id="req-1", secret="segredo",
        ))
