import base64
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema_phishing.backend_service import (
    AnalysisBackendConfig,
    AnalysisBackendService,
)


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
        self.assertIsNone(result["model"])

    def test_modo_heuristico_no_carga_detector_neuronal(self):
        service = AnalysisBackendService(AnalysisBackendConfig(mode="heuristico"))
        service._service._detector_loader = mock.MagicMock(
            side_effect=AssertionError("No debe cargar un modelo")
        )

        response = service.analyze_payload(
            {
                "email": {"subject": "Reunión", "body": "Nos vemos el jueves."},
                "options": {"mode": "heuristico", "include_all": False},
            }
        )

        self.assertEqual(response["selected_mode"], "heuristico")
        self.assertIsNone(response["model"])
        service._service._detector_loader.assert_not_called()

    def test_include_all_debe_ser_booleano(self):
        service = AnalysisBackendService(AnalysisBackendConfig(mode="heuristico"))

        with self.assertRaisesRegex(TypeError, "include_all debe ser booleano"):
            service.analyze_payload(
                {
                    "email": {"subject": "Reunión", "body": "Nos vemos."},
                    "options": {"mode": "heuristico", "include_all": "false"},
                }
            )

    def test_acepta_eml_y_devuelve_los_tres_modos_sin_logica_en_el_cliente(self):
        service = AnalysisBackendService(
            AnalysisBackendConfig(mode="combinado", threshold=45.0)
        )
        raw_eml = (
            b"From: soporte@ejemplo.com\n"
            b"To: persona@example.com\n"
            b"Subject: Verifica tu cuenta\n\n"
            b"Accede urgentemente a http://192.168.1.1/login"
        )

        response = service.analyze_payload(
            {
                "eml_base64": base64.b64encode(raw_eml).decode("ascii"),
                "options": {"mode": "combinado", "include_all": True},
            }
        )

        self.assertEqual(response["email"]["subject"], "Verifica tu cuenta")
        self.assertEqual(response["selected_mode"], "combinado")
        self.assertEqual(set(response["results"]), {"heuristico", "neural", "combinado"})
        self.assertEqual(response["result"], response["results"]["combinado"])

    def test_texto_pegado_se_parsea_en_el_servidor(self):
        service = AnalysisBackendService(AnalysisBackendConfig(mode="heuristico"))

        response = service.analyze_payload(
            {
                "raw_text": (
                    "From: equipo@empresa.com\n"
                    "Subject: Reunión semanal\n\n"
                    "La reunión será el jueves."
                ),
                "options": {"mode": "heuristico"},
            }
        )

        self.assertEqual(response["email"]["subject"], "Reunión semanal")
        self.assertEqual(response["email"]["from"], "equipo@empresa.com")

    def test_entrenamiento_activa_una_version_central_compartida(self):
        dataset = """label,text
1,verifica tu cuenta bancaria urgentemente
1,confirma ahora tu usuario y contrasena
1,pago retenido pulsa el enlace de acceso
1,cuenta bloqueada introduce tus credenciales
0,reunion del equipo el jueves a las diez
0,confirmacion del pedido enviado correctamente
0,boletin mensual con novedades del proyecto
0,cafe el viernes por la tarde
"""
        test_dir = Path(__file__).resolve().parent
        model_paths = [
            test_dir / ".backend-central-es-test.joblib",
            test_dir / ".backend-central-en-test.joblib",
        ]
        for path in model_paths:
            path.unlink(missing_ok=True)
        try:
            model_es, model_en = map(str, model_paths)
            service = AnalysisBackendService(
                AnalysisBackendConfig(
                    mode="combinado",
                    model_path_es=model_es,
                    model_path_en=model_en,
                )
            )
            before = service.models_payload()["models"]["es"]

            trained = service.train_payload(
                {
                    "language": "es",
                    "datasets": [{"name": "central.csv", "content": dataset}],
                    "columns": {"label": "label", "text": "text"},
                    "hyperparameters": {
                        "tfidf_ngram_range": [1, 1],
                        "tfidf_max_features": 100,
                        "tfidf_min_df": 1,
                        "mlp_hidden_layer_sizes": [4],
                        "mlp_max_iter": 20,
                        "mlp_random_state": 42,
                    },
                }
            )
            after = service.models_payload()["models"]["es"]
            analyzed = service.analyze_payload(
                {"email": {"text": "reunion ordinaria del equipo"}}
            )

            self.assertFalse(before["available"])
            self.assertTrue(trained["model"]["available"])
            self.assertTrue(after["valid"])
            self.assertEqual(after["version"], trained["model"]["version"])
            self.assertEqual(analyzed["model"]["version"], after["version"])
            self.assertEqual(trained["training"]["n_samples"], 8)
        finally:
            for path in model_paths:
                path.unlink(missing_ok=True)

    def test_artefacto_corrupto_declara_fallback_en_la_respuesta(self):
        invalid_path = Path(__file__).resolve().parent / ".invalid-model.joblib"
        invalid_path.write_bytes(b"no es un modelo joblib")
        try:
            service = AnalysisBackendService(
                AnalysisBackendConfig(
                    mode="neural",
                    model_path_es=str(invalid_path),
                    model_path_en=str(invalid_path),
                )
            )
            models = service.models_payload()["models"]
            response = service.analyze_payload(
                {
                    "email": {
                        "subject": "Verifica tu cuenta",
                        "body": "Introduce ahora tus credenciales.",
                    },
                    "options": {"mode": "neural"},
                }
            )

            self.assertFalse(models["es"]["valid"])
            self.assertTrue(models["es"]["fallback"])
            self.assertEqual(response["model"]["active_source"], "synthetic_fallback")
            self.assertTrue(response["model"]["fallback"])
            self.assertIsNone(response["model"]["version"])
            self.assertIsNotNone(response["model"]["artifact_version"])
        finally:
            invalid_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
