import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema_phishing.backend_client import (
    BackendClient,
    BackendClientError,
    normalize_backend_url,
)
from sistema_phishing.http_api import crear_servidor_http


class _ContractService:
    def __init__(self):
        self.last_payload = None

    def build_health_payload(self):
        return {"ok": True, "architecture": "client-server"}

    def models_payload(self):
        return {"models": {"es": {"version": "abc123"}}}

    def analyze_payload(self, payload):
        self.last_payload = payload
        return {
            "result": {"risk_score": 9.0, "is_phishing": False},
            "selected_mode": payload["options"]["mode"],
        }

    def is_admin_authorized(self, authorization):
        return authorization == "Bearer secreto"

    def summarize_payload(self, payload):
        self.last_payload = payload
        return {"datasets": [{"rows": 2}]}

    def settings_payload(self):
        return {
            "analysis_defaults": {"mode": "combinado"},
            "training_defaults": {"tfidf_max_features": 3000},
        }

    def update_settings_payload(self, payload):
        self.last_payload = payload
        return payload


class BackendClientTests(unittest.TestCase):
    def setUp(self):
        self.service = _ContractService()
        self.server = crear_servidor_http("127.0.0.1", 0, self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_transfiere_eml_y_opciones_al_backend(self):
        client = BackendClient(self.url)

        health = client.health()
        result = client.analyze(
            b"Subject: Prueba\n\nContenido",
            mode="heuristico",
            threshold=61,
        )

        self.assertEqual(health["architecture"], "client-server")
        self.assertEqual(result["selected_mode"], "heuristico")
        self.assertIn("eml_base64", self.service.last_payload)
        self.assertEqual(self.service.last_payload["options"]["threshold"], 61)

    def test_token_se_envia_solo_en_operaciones_administrativas(self):
        unauthorized = BackendClient(self.url)
        with self.assertRaises(BackendClientError):
            unauthorized.summarize(
                [{"name": "datos.csv", "content": "label,text\n0,hola"}],
                columns={"label": "label", "text": "text"},
            )

        authorized = BackendClient(self.url, admin_token="secreto")
        result = authorized.summarize(
            [{"name": "datos.csv", "content": "label,text\n0,hola"}],
            columns={"label": "label", "text": "text"},
        )
        self.assertEqual(result["datasets"][0]["rows"], 2)

    def test_ajustes_del_servidor_viajan_por_la_api_administrativa(self):
        client = BackendClient(self.url, admin_token="secreto")

        settings = client.settings()
        updated = client.update_settings(
            analysis_defaults={"mode": "neural"},
            training_defaults={"tfidf_max_features": 1500},
        )

        self.assertEqual(settings["analysis_defaults"]["mode"], "combinado")
        self.assertEqual(updated["analysis_defaults"]["mode"], "neural")
        self.assertEqual(updated["training_defaults"]["tfidf_max_features"], 1500)

    def test_http_remoto_se_rechaza_y_https_remoto_se_admite(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            normalize_backend_url("http://192.168.1.20:8766")
        self.assertEqual(
            normalize_backend_url("https://phishing.example"),
            "https://phishing.example",
        )

    def test_puerto_invalido_se_rechaza_al_configurar(self):
        with self.assertRaisesRegex(ValueError, "puerto"):
            normalize_backend_url("http://127.0.0.1:99999")


if __name__ == "__main__":
    unittest.main()
