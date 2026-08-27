import unittest

from gmail_extension_server import (
    GmailWebAnalyzer,
    construir_datos_email,
    limpiar_resultado,
)
from sistema_phishing.gmail_monitor import MODO_HEURISTICO, MonitorConfig


class TestGmailExtensionServer(unittest.TestCase):
    def test_construir_datos_email_normaliza_payload_de_extension(self):
        payload = {
            "subject": "Verifica tu cuenta",
            "from": "Soporte <soporte@example.com>",
            "body": "Pulsa https://example.com/login para continuar.",
            "anchors": [{"text": "Acceder", "href": "https://example.com/login"}],
            "urls": ["https://example.com/login"],
        }

        datos = construir_datos_email(payload)

        self.assertEqual(datos["subject"], "Verifica tu cuenta")
        self.assertEqual(datos["from"], "Soporte <soporte@example.com>")
        self.assertIn("Subject: Verifica tu cuenta", datos["full_text"])
        self.assertEqual(datos["anchors"][0]["href"], "https://example.com/login")

    def test_analyzer_heuristico_devuelve_resultado_limpiable(self):
        class FakeBackendClient:
            def analyze(self, email, **options):
                self.email = email
                self.options = options
                return {
                    "result": {
                        "risk_score": 82.5,
                        "is_phishing": True,
                        "description": "Resultado del backend central.",
                        "signals": {"urgency": True},
                    }
                }

        config = MonitorConfig(state_path="", mode=MODO_HEURISTICO, threshold=45)
        client = FakeBackendClient()
        analyzer = GmailWebAnalyzer(config, client=client)

        resultado = analyzer.analyze(
            {
                "subject": "Cuenta suspendida",
                "from": "seguridad@banco-secure.example",
                "body": "Urgente, confirme sus credenciales en http://192.168.1.1/login",
                "urls": ["http://192.168.1.1/login"],
            }
        )
        respuesta = limpiar_resultado(resultado, threshold=45)

        self.assertIn("risk_score", respuesta)
        self.assertIn("label", respuesta)
        self.assertIn("signals", respuesta)
        self.assertEqual(client.options["mode"], MODO_HEURISTICO)
        self.assertEqual(client.email["subject"], "Cuenta suspendida")


if __name__ == "__main__":
    unittest.main()
