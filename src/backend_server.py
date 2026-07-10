"""Servidor HTTP simple para exponer el backend de análisis de phishing."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from sistema_phishing.backend_service import AnalysisBackendConfig, AnalysisBackendService


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class BackendRequestHandler(BaseHTTPRequestHandler):
    server_version = "PhishingBackend/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, self.server.service.build_health_payload())
            return
        self._send_json(404, {"error": "Ruta no encontrada"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/analyze":
            self._send_json(404, {"error": "Ruta no encontrada"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body) if body else {}
            if not isinstance(payload, dict):
                raise ValueError("El cuerpo debe ser un objeto JSON")
            result = self.server.service.analyze_payload(payload)
            self._send_json(200, result)
        except Exception as exc:  # noqa: BLE001
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(204, {})


class BackendHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], service: AnalysisBackendService):
        super().__init__(server_address, handler_cls)
        self.service = service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor HTTP para centralizar el análisis de phishing.")
    parser.add_argument("--host", default=os.getenv("BACKEND_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("BACKEND_PORT", "8766")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = AnalysisBackendService(AnalysisBackendConfig())
    server = BackendHTTPServer((args.host, args.port), BackendRequestHandler, service)
    print(f"Backend escuchando en http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
