import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sistema_phishing.http_api import crear_servidor_http


class _FakeService:
    def build_health_payload(self):
        return {"ok": True, "mode": "heuristico"}

    def analyze_payload(self, payload):
        return {"ok": True, "risk_score": 12.5, "is_phishing": False}


class _ProtectedFakeService(_FakeService):
    def is_admin_authorized(self, authorization):
        return authorization == "Bearer secreto"

    def summarize_payload(self, payload):
        return {"ok": True, "datasets": len(payload.get("datasets", []))}


class TestHTTPApi(unittest.TestCase):
    def setUp(self):
        self.server = crear_servidor_http("127.0.0.1", 0, _FakeService())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_health_no_expone_rutas_y_analisis_usa_json(self):
        with urlopen(f"{self.base_url}/health") as response:
            health = json.loads(response.read())
            self.assertEqual(response.headers["Server"], "TFGPhishingAPI/1.0")
        self.assertTrue(health["ok"])
        self.assertNotIn("model_path_es", health)

        request = Request(
            f"{self.base_url}/analyze",
            data=b'{"subject":"Hola"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            result = json.loads(response.read())
        self.assertEqual(result["risk_score"], 12.5)

    def test_rechaza_content_type_origen_y_cuerpo_no_validos(self):
        request = Request(
            f"{self.base_url}/analyze",
            data=b"{}",
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 400)

        request = Request(
            f"{self.base_url}/analyze",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://sitio-no-autorizado.example",
            },
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)

        request = Request(
            f"{self.base_url}/analyze",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Origin": "chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
            method="POST",
        )
        with urlopen(request) as response:
            self.assertEqual(response.status, 200)

    def test_lista_cors_vacia_no_recupera_origenes_predeterminados(self):
        server = crear_servidor_http(
            "127.0.0.1",
            0,
            _FakeService(),
            allowed_origins=set(),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(
                f"http://127.0.0.1:{server.server_port}/analyze",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://mail.google.com",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_operaciones_de_administracion_exigen_token_si_esta_configurado(self):
        server = crear_servidor_http("127.0.0.1", 0, _ProtectedFakeService())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/datasets/summary"
        try:
            body = b'{"datasets":[]}'
            request = Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)

            authorized = Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer secreto",
                },
                method="POST",
            )
            with urlopen(authorized) as response:
                result = json.loads(response.read())
            self.assertTrue(result["ok"])

            browser_request = Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer secreto",
                    "Origin": "https://mail.google.com",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as error:
                urlopen(browser_request)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
