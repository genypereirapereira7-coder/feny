from unittest.mock import patch

from django.test import TestCase

from apps.notifications import services
from apps.notifications.models import Notification, NotificationChannel, NotificationStatus


class NotifyTests(TestCase):
    def test_cria_notification_pending(self):
        notification = services.notify(
            channel=NotificationChannel.WHATSAPP, recipient="11999999999",
            template="charge.issued", context={"x": "1"},
        )
        self.assertIsNotNone(notification)
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertEqual(notification.attempts, 0)

    def test_sem_recipient_nao_cria_nada(self):
        resultado = services.notify(channel=NotificationChannel.WHATSAPP, recipient="", template="x")
        self.assertIsNone(resultado)
        self.assertFalse(Notification.objects.exists())


class DispatchPendingTests(TestCase):
    def _criar_pendente(self, **overrides):
        dados = dict(channel=NotificationChannel.WHATSAPP, recipient="11999999999", template="charge.issued", context={})
        dados.update(overrides)
        return Notification.objects.create(**dados)

    @patch("apps.whatsapp.service.send")
    def test_envia_com_sucesso(self, mock_send):
        notification = self._criar_pendente()

        resultado = services.dispatch_pending()

        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.SENT)
        self.assertIsNotNone(notification.sent_at)
        self.assertEqual(resultado, {"enviadas": 1, "falharam": 0, "total": 1})
        mock_send.assert_called_once_with(notification)

    @patch("apps.whatsapp.service.send", side_effect=Exception("Evolution API fora do ar"))
    def test_falha_marca_failed_e_incrementa_attempts(self, mock_send):
        notification = self._criar_pendente()

        services.dispatch_pending()

        notification.refresh_from_db()
        self.assertEqual(notification.status, NotificationStatus.FAILED)
        self.assertEqual(notification.attempts, 1)
        self.assertIn("Evolution API fora do ar", notification.last_error)

    @patch("apps.whatsapp.service.send", side_effect=Exception("falhou de novo"))
    def test_reprocessa_failed_ate_o_limite_de_tentativas(self, mock_send):
        notification = self._criar_pendente(status=NotificationStatus.FAILED, attempts=4)

        services.dispatch_pending()
        notification.refresh_from_db()
        self.assertEqual(notification.attempts, 5)

        # Na 5ª tentativa esgotada, a próxima rodada não pega mais esta notificação.
        resultado = services.dispatch_pending()
        self.assertEqual(resultado["total"], 0)

    @patch("apps.whatsapp.service.send")
    def test_nao_processa_canal_diferente_de_whatsapp(self, mock_send):
        self._criar_pendente(channel=NotificationChannel.EMAIL, recipient="a@b.com")

        resultado = services.dispatch_pending()

        self.assertEqual(resultado["total"], 0)
        mock_send.assert_not_called()

    @patch("apps.whatsapp.service.send")
    def test_nao_reprocessa_notification_ja_enviada(self, mock_send):
        self._criar_pendente(status=NotificationStatus.SENT)

        resultado = services.dispatch_pending()

        self.assertEqual(resultado["total"], 0)
        mock_send.assert_not_called()
