import unittest
from unittest.mock import MagicMock, patch

from sistema_phishing.analysis_service import (
    MODO_HEURISTICO,
    MODO_NEURAL,
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

    def test_modo_neural_detecta_idioma_por_correo_no_por_sesion(self):
        """Antes, el detector se cacheaba una sola vez para toda la sesión del
        monitor: el primer correo analizado fijaba el idioma (normalmente
        español) para todos los siguientes, aunque llegara un correo en
        inglés después. Este test comprueba que ahora cada correo usa el
        idioma que le corresponde, aunque se analicen en la misma sesión."""
        config = MonitorConfig(state_path="", mode=MODO_NEURAL)
        service = EmailAnalysisService(config)

        idiomas_detectados = ["es", "en"]

        def idioma_falso(_texto):
            return idiomas_detectados.pop(0)

        def detector_falso(config, idioma):
            detector = MagicMock()
            detector.analyze.return_value = {"risk_score": 0, "is_phishing": False}
            return detector

        with patch("sistema_phishing.analysis_service.detectar_idioma_correo", side_effect=idioma_falso), \
             patch("sistema_phishing.analysis_service.cargar_detector_neural") as mock_cargar:
            mock_cargar.side_effect = detector_falso

            # Primer correo: "es" -> debe pedir un detector para español.
            service._analyze_neural({"from": "a@a.com", "subject": "Hola", "body": "Cuerpo"})
            # Segundo correo: "en" -> debe pedir uno distinto para inglés,
            # no reutilizar el de español ya cacheado.
            service._analyze_neural({"from": "b@b.com", "subject": "Hi", "body": "Body"})

        self.assertEqual(
            [llamada.args[1] for llamada in mock_cargar.call_args_list],
            ["es", "en"],
        )
        self.assertEqual(set(service._detectores.keys()), {"es", "en"})


if __name__ == "__main__":
    unittest.main()
