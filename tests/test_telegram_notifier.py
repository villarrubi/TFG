import unittest

import requests

from sistema_phishing.telegram_notifier import (
    TelegramNotificationError,
    TelegramNotifier,
    construir_mensaje_alerta,
)


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
                "signals": {"enlaces_sospechosos": True},
            },
            "heuristico",
        )

        self.assertIn("ALERTA DE PHISHING", mensaje)
        self.assertIn("80.0%", mensaje)
        self.assertIn("a@example.com", mensaje)
        self.assertIn("Primeros enlaces", mensaje)

    def test_error_de_red_no_filtra_el_token(self):
        def failing_post(url, json, timeout):
            raise requests.ConnectionError(f"fallo al conectar con {url}")

        notifier = TelegramNotifier("TOKEN_SECRETO", "CHAT", post=failing_post)
        with self.assertRaises(TelegramNotificationError) as error:
            notifier.enviar_mensaje("hola")

        self.assertNotIn("TOKEN_SECRETO", str(error.exception))
        self.assertIn("Telegram", str(error.exception))

    def test_construir_mensaje_alerta_escapa_remitente_html(self):
        mensaje = construir_mensaje_alerta(
            {"from": "Nombre <correo@example.com>", "subject": "Aviso <urgente>"},
            {
                "risk_score": 80,
                "urls": [],
                "signals": {"solicitud_credenciales": True},
            },
            "heuristico",
        )

        self.assertIn("Nombre &lt;correo@example.com&gt;", mensaje)
        self.assertIn("Aviso &lt;urgente&gt;", mensaje)

    def test_construir_mensaje_alerta_solo_muestra_senales_activas(self):
        mensaje = construir_mensaje_alerta(
            {"from": "a@example.com", "subject": "Aviso"},
            {
                "risk_score": 40,
                "urls": [],
                "signals": {
                    "reply_to_diferente": False,
                    "lenguaje_urgente": True,
                },
                "explanation": [
                    "No se encontró un Reply-To claramente diferente al From.",
                    "El cuerpo del mensaje contiene lenguaje urgente o de alta presión.",
                ],
            },
            "combinado",
        )

        self.assertIn("Lenguaje urgente", mensaje)
        self.assertNotIn("No se encontró", mensaje)
