"""Servidor HTTP simple para exponer el backend de análisis de phishing."""

from __future__ import annotations

import argparse
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from sistema_phishing.analysis_service import MODO_COMBINADO, VALID_MODES
from sistema_phishing.backend_service import AnalysisBackendConfig, AnalysisBackendService
from sistema_phishing.env_loader import cargar_env_local


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MODEL_PATH_ES = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
DEFAULT_MODEL_PATH_EN = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _allowed_origins() -> set[str]:
    raw = os.getenv("BACKEND_ALLOWED_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return {"*"}
    return {origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()}


def build_backend_config() -> AnalysisBackendConfig:
    """Construye la configuración del backend desde variables de entorno."""
    mode = os.getenv("BACKEND_ANALYSIS_MODE", os.getenv("MONITOR_ANALYSIS_MODE", MODO_COMBINADO)).lower()
    if mode not in VALID_MODES:
        mode = MODO_COMBINADO
    heur_weight = _env_int("BACKEND_HEUR_WEIGHT", _env_int("MONITOR_HEUR_WEIGHT", 60))
    neural_weight = _env_int("BACKEND_NEURAL_WEIGHT", 100 - heur_weight)
    if heur_weight + neural_weight <= 0:
        heur_weight, neural_weight = 60, 40
    return AnalysisBackendConfig(
        threshold=_env_float("BACKEND_PHISHING_THRESHOLD", _env_float("PHISHING_THRESHOLD", 45.0)),
        mode=mode,
        heur_weight=heur_weight,
        neural_weight=neural_weight,
        model_path_es=os.getenv("BACKEND_MODEL_ES", DEFAULT_MODEL_PATH_ES),
        model_path_en=os.getenv("BACKEND_MODEL_EN", DEFAULT_MODEL_PATH_EN),
    )


class BackendRequestHandler(BaseHTTPRequestHandler):
    server_version = "PhishingBackend/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send_json(401, {"error": "No autorizado"})
            return
        if self.path == "/health":
            self._send_json(200, self.server.service.build_health_payload())
            return
        self._send_json(404, {"error": "Ruta no encontrada"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send_json(401, {"error": "No autorizado"})
            return
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
            logging.info(
                "analyze status=200 score=%.1f phishing=%s subject=%r",
                float(result.get("risk_score", 0.0)),
                bool(result.get("is_phishing", False)),
                str(payload.get("subject", ""))[:120],
            )
            self._send_json(200, result)
        except Exception as exc:  # noqa: BLE001
            logging.exception("analyze status=400 error=%s", exc)
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _authorized(self) -> bool:
        token = getattr(self.server, "api_token", "")
        if not token:
            return True
        auth_header = self.headers.get("Authorization", "")
        api_key = self.headers.get("X-API-Key", "")
        return auth_header == f"Bearer {token}" or api_key == token

    def _cors_origin(self) -> str:
        allowed = getattr(self.server, "allowed_origins", {"*"})
        request_origin = self.headers.get("Origin", "").rstrip("/")
        if "*" in allowed:
            return "*"
        if request_origin in allowed:
            return request_origin
        return next(iter(allowed), "")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        cors_origin = self._cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(204, {})


class BackendHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_cls: type[BaseHTTPRequestHandler],
        service: AnalysisBackendService,
        api_token: str = "",
        allowed_origins: set[str] | None = None,
    ):
        super().__init__(server_address, handler_cls)
        self.service = service
        self.api_token = api_token
        self.allowed_origins = allowed_origins or {"*"}


def parse_args() -> argparse.Namespace:
    cargar_env_local(ROOT_DIR)
    parser = argparse.ArgumentParser(description="Servidor HTTP para centralizar el análisis de phishing.")
    parser.add_argument("--host", default=os.getenv("BACKEND_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("BACKEND_PORT", "8766")))
    parser.add_argument("--token", default=os.getenv("BACKEND_API_TOKEN", ""), help="Token opcional para proteger /health y /analyze.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=os.getenv("BACKEND_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    service = AnalysisBackendService(build_backend_config())
    server = BackendHTTPServer(
        (args.host, args.port),
        BackendRequestHandler,
        service,
        api_token=args.token,
        allowed_origins=_allowed_origins(),
    )
    print(f"Backend escuchando en http://{args.host}:{args.port}")
    if args.token:
        print("Control de acceso activo: los clientes deben enviar BACKEND_API_TOKEN.")
    server.serve_forever()


if __name__ == "__main__":
    main()
