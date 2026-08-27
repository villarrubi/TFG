"""Servidor HTTP común del backend central de phishing."""

from __future__ import annotations

import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from .backend_service import API_VERSION, AnalysisBackendService

LOGGER = logging.getLogger(__name__)
MAX_ANALYSIS_REQUEST_BYTES = 16 * 1024 * 1024
MAX_TRAINING_REQUEST_BYTES = 256 * 1024 * 1024
DEFAULT_ALLOWED_ORIGINS = {"https://mail.google.com"}
ADMIN_PATHS = {
    "/datasets/summary",
    "/train",
    "/evaluate",
    "/compare",
    "/models/delete",
}


class _LocalThreadingHTTPServer(ThreadingHTTPServer):
    """Servidor con hilos que no impiden cerrar el proceso local."""

    daemon_threads = True
    allow_reuse_address = True


class APIRequestError(ValueError):
    """Error de entrada que se puede comunicar al cliente de forma segura."""

    status_code = 400


def _origen_permitido(origen: str, allowed_origins: set[str]) -> bool:
    """Valida CORS sin abrir el endpoint a cualquier web."""
    return (
        not origen
        or origen in allowed_origins
        or re.fullmatch(r"chrome-extension://[a-p]{32}", origen) is not None
    )


def crear_handler(
    service: AnalysisBackendService,
    *,
    allowed_origins: set[str] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Crea el handler versionado para todos los clientes."""
    allowed = DEFAULT_ALLOWED_ORIGINS if allowed_origins is None else allowed_origins

    class AnalysisRequestHandler(BaseHTTPRequestHandler):
        server_version = f"TFGPhishingAPI/{API_VERSION}"

        def version_string(self) -> str:
            """No expone la versión del intérprete en la cabecera Server."""
            return self.server_version

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/health":
                self._send_json(200, service.build_health_payload())
                return
            if path == "/models":
                models_payload = getattr(service, "models_payload", None)
                if models_payload is None:
                    self._send_json(404, {"error": "Ruta no disponible."})
                else:
                    self._send_json(200, models_payload())
                return
            self._send_json(404, {"error": "Ruta no encontrada."})

        def do_OPTIONS(self) -> None:
            if not self._check_origin():
                return
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            handlers = {
                "/analyze": ("analyze_payload", MAX_ANALYSIS_REQUEST_BYTES),
                "/datasets/summary": ("summarize_payload", MAX_TRAINING_REQUEST_BYTES),
                "/train": ("train_payload", MAX_TRAINING_REQUEST_BYTES),
                "/evaluate": ("evaluate_payload", MAX_TRAINING_REQUEST_BYTES),
                "/compare": ("compare_payload", MAX_TRAINING_REQUEST_BYTES),
                "/models/delete": ("delete_model_payload", MAX_ANALYSIS_REQUEST_BYTES),
            }
            route = handlers.get(path)
            if route is None:
                self._send_json(404, {"error": "Ruta no encontrada."})
                return
            if not self._check_origin() or not self._check_admin(path):
                return

            method_name, max_bytes = route
            method = getattr(service, method_name, None)
            if method is None:
                self._send_json(404, {"error": "Ruta no disponible."})
                return
            try:
                payload = self._read_payload(max_bytes=max_bytes)
                result = method(payload)
            except (APIRequestError, TypeError, ValueError) as exc:
                self._send_json(getattr(exc, "status_code", 400), {"error": str(exc)})
                return
            except Exception:
                LOGGER.exception("Fallo interno procesando %s", path)
                self._send_json(500, {"error": "No se pudo completar la operación."})
                return
            self._send_json(200, result)

        def _read_payload(self, *, max_bytes: int) -> dict[str, Any]:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.lower().startswith("application/json"):
                raise APIRequestError("Content-Type debe ser application/json.")
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError as exc:
                raise APIRequestError("Content-Length no es válido.") from exc
            if length < 1 or length > max_bytes:
                raise APIRequestError(
                    f"El cuerpo debe tener entre 1 byte y {max_bytes // (1024 * 1024)} MiB."
                )
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise APIRequestError("El cuerpo no contiene JSON UTF-8 válido.") from exc
            if not isinstance(payload, dict):
                raise APIRequestError("El cuerpo debe ser un objeto JSON.")
            return payload

        def _check_origin(self) -> bool:
            origin = self.headers.get("Origin", "")
            if _origen_permitido(origin, allowed):
                return True
            self._send_json(403, {"error": "Origen no permitido."}, include_cors=False)
            return False

        def _check_admin(self, path: str) -> bool:
            if path not in ADMIN_PATHS:
                return True
            if self.headers.get("Origin"):
                self._send_json(
                    403,
                    {"error": "Las operaciones administrativas no se aceptan desde páginas web."},
                )
                return False
            authorizer = getattr(service, "is_admin_authorized", None)
            if authorizer is None or authorizer(self.headers.get("Authorization", "")):
                return True
            self._send_json(401, {"error": "Autorización de administración requerida."})
            return False

        def _send_json(
            self,
            status: int,
            payload: dict[str, Any],
            *,
            include_cors: bool = True,
        ) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            if include_cors:
                self._send_cors_headers()
            self.end_headers()
            self.wfile.write(data)

        def _send_cors_headers(self) -> None:
            origin = self.headers.get("Origin", "")
            if origin and _origen_permitido(origin, allowed):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def log_message(self, format: str, *args: Any) -> None:
            LOGGER.info("%s - %s", self.address_string(), format % args)

    return AnalysisRequestHandler


def crear_servidor_http(
    host: str,
    port: int,
    service: AnalysisBackendService,
    *,
    allowed_origins: set[str] | None = None,
) -> ThreadingHTTPServer:
    """Construye el servidor sin arrancar el bucle, facilitando pruebas."""
    return _LocalThreadingHTTPServer(
        (host, port),
        crear_handler(service, allowed_origins=allowed_origins),
    )
