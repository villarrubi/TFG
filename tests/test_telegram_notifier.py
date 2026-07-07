import unittest

from sistema_phishing.telegram_notifier import TelegramNotifier, construir_mensaje_alerta


class FakeResponse:
    status_code = 200
    text = "OK"


class TestTelegramNotifier(unittest.TestCase):
    def test_enviar_mensaje_usa_api_de_telegram(self):
        llamadas = []

        def fake_post(url, json, timeout):
            llamadas.append((url, json, timeout))
            return FakeResponse()

        notifier = TelegramNotifier("TOKEN", "CHAT", post=fake_post)
        notifier.enviar_mensaje("hola")

        self.assertEqual(len(llamadas), 1)
        self.assertIn("botTOKEN/sendMessage", llamadas[0][0])
        self.assertEqual(llamadas[0][1]["chat_id"], "CHAT")

    def test_construir_mensaje_alerta_incluye_datos_principales(self):
        mensaje = construir_mensaje_alerta(
            {"from": "a@example.com", "subject": "Aviso"},
            {
                "risk_score": 80,
                "urls": ["https://example.com"],
                "explanation": ["URL sospechosa"],
            },
            "heuristico",
        )

        self.assertIn("Posible phishing detectado", mensaje)
        self.assertIn("80.0%", mensaje)
        self.assertIn("a@example.com", mensaje)
