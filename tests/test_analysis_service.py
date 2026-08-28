import unittest
from unittest.mock import MagicMock, patch

from sistema_phishing.analysis_service import (
    MODO_HEURISTICO,
    MODO_NEURAL,
    AnalysisConfigurationError,
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

    def test_modo_heuristico_no_requiere_modelo(self):
        service = EmailAnalysisService(MonitorConfig(state_path="", mode=MODO_HEURISTICO))

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

    def test_modo_neural_cachea_un_detector_por_idioma(self):
        config = MonitorConfig(state_path="", mode=MODO_NEURAL)
        idiomas_detectados = ["es", "en", "es"]

        def idioma_falso(_texto):
            return idiomas_detectados.pop(0)

        def detector_falso(_config, _idioma):
            detector = MagicMock()
            detector.analyze.return_value = {"risk_score": 0, "is_phishing": False}
            return detector

        with patch(
            "sistema_phishing.analysis_service.detectar_idioma_correo",
            side_effect=idioma_falso,
        ), patch(
            "sistema_phishing.analysis_service.cargar_detector_neural",
            side_effect=detector_falso,
        ) as mock_cargar:
            service = EmailAnalysisService(config)
            for subject in ("Hola", "Hi", "Adios"):
                service._analyze_neural({"from": "a@a.com", "subject": subject, "body": "Body"})

        self.assertEqual(mock_cargar.call_count, 2)
        self.assertEqual(set(service._detectores), {"es", "en"})

    def test_analyze_all_reutiliza_el_detector_y_devuelve_los_tres_modos(self):
        config = MonitorConfig(
            state_path="",
            mode="combinado",
            threshold=45,
            heur_weight=60,
            neural_weight=40,
        )
        detector = MagicMock()
        detector.analyze.return_value = {"risk_score": 20, "is_phishing": False}
        loader = MagicMock(return_value=detector)
        heuristic = MagicMock(
            return_value={
                "risk_score": 80,
                "is_phishing": True,
                "urls": [],
                "anchors": [],
                "headers": {},
                "explanation": [],
                "signals": {},
            }
        )
        service = EmailAnalysisService(
            config,
            heuristic_analyzer=heuristic,
            detector_loader=loader,
            language_detector=lambda _text: "es",
        )

        resultados = service.analyze_all({"from": "a@example.com", "subject": "Hola", "body": "Texto"})

        self.assertEqual(set(resultados), {"heuristico", "neural", "combinado"})
        self.assertEqual(loader.call_count, 1)
        self.assertEqual(detector.analyze.call_count, 1)
        self.assertEqual(resultados["combinado"]["risk_score"], 80.0)

    def test_combinado_no_diluye_una_senal_de_alta_confianza(self):
        config = MonitorConfig(
            state_path="", threshold=45, heur_weight=20, neural_weight=80
        )

        resultado = construir_resultado_combinado(
            {"risk_score": 84, "urls": [], "anchors": [], "headers": {}},
            {"risk_score": 5},
            config,
        )

        self.assertEqual(resultado["risk_score"], 84.0)
        self.assertTrue(resultado["is_phishing"])

    def test_rechaza_umbral_de_alta_confianza_invalido(self):
        config = MonitorConfig(state_path="")
        config.high_confidence_threshold = 101

        with self.assertRaises(AnalysisConfigurationError):
            EmailAnalysisService(config)


if __name__ == "__main__":
    unittest.main()
