import unittest

from sistema_phishing.analysis_service import (
    MODO_HEURISTICO,
    EmailAnalysisService,
    construir_resultado_combinado,
)
from sistema_phishing.gmail_monitor import MonitorConfig


class TestAnalysisService(unittest.TestCase):
    def test_construir_resultado_combinado_respeta_pesos_y_umbral(self):
        config = MonitorConfig(state_path="", threshold=45, heur_weight=60, neural_weight=40)
        resultado = construir_resultado_combinado(
            {"risk_score": 50, "urls": ["https://example.com"], "anchors": [], "headers": {}},
            {"risk_score": 20},
            config,
        )

        self.assertEqual(resultado["risk_score"], 38.0)
        self.assertFalse(resultado["is_phishing"])
        self.assertEqual(resultado["urls"], ["https://example.com"])

    def test_email_analysis_service_modo_heuristico_no_requiere_modelo(self):
        config = MonitorConfig(state_path="", mode=MODO_HEURISTICO)
        service = EmailAnalysisService(config)

        resultado = service.analyze(
            {
                "from": "Banco <alerta@example.com>",
                "subject": "Verifica tu cuenta",
                "body": "Estimado cliente, actualice sus credenciales.",
                "full_text": "Subject: Verifica tu cuenta\nEstimado cliente, actualice sus credenciales.",
                "urls": [],
            }
        )

        self.assertIn("risk_score", resultado)
        self.assertIn("signals", resultado)


if __name__ == "__main__":
    unittest.main()
