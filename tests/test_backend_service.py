import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema_phishing.backend_service import AnalysisBackendConfig, AnalysisBackendService


class BackendServiceTests(unittest.TestCase):
    def test_backend_service_returns_analysis_result(self):
        root_dir = Path(__file__).resolve().parents[1]
        config = AnalysisBackendConfig(
            threshold=45.0,
            mode="heuristico",
            heur_weight=60,
            neural_weight=40,
            model_path_es=str(root_dir / "modelo_neural_es.joblib"),
            model_path_en=str(root_dir / "modelo_neural_en.joblib"),
        )
        service = AnalysisBackendService(config)

        result = service.analyze_payload(
            {
                "subject": "Verificación de cuenta",
                "from": "soporte@ejemplo.com",
                "body": "Por favor haga clic para confirmar su cuenta.",
            }
        )

        self.assertIn("risk_score", result)
        self.assertIn("is_phishing", result)
        self.assertIn("description", result)
        self.assertIsInstance(result["risk_score"], (int, float))


if __name__ == "__main__":
    unittest.main()
