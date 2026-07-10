"""Servidor local para la extension de Gmail Web.

La extension del navegador no ejecuta el modelo Python directamente. En su
lugar envia el correo visible en Gmail a este pequeno endpoint local y recibe
la clasificacion en JSON.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple

from sistema_phishing.analysis_service import (
    MODO_COMBINADO,
    MODO_HEURISTICO,
    MODO_NEURAL,
    VALID_MODES,
    EmailAnalysisService,
)
from sistema_phishing.backend_client import BackendAnalysisClient
from sistema_phishing.env_loader import cargar_env_local
from sistema_phishing.gmail_monitor import MonitorConfig


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MODEL_PATH_ES = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
DEFAULT_MODEL_PATH_EN = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")
ALLOWED_ORIGINS = {"https://mail.google.com"}
APP_NAME = "TFG Phishing Guard - Gmail Web"
ASCII_TITLE = r"""
 ____  _   _ ___ ____  _   _ ___ _   _  ____    ____ _   _    _    ____  ____
|  _ \| | | |_ _/ ___|| | | |_ _| \ | |/ ___|  / ___| | | |  / \  |  _ \|  _ \
| |_) | |_| || |\___ \| |_| || ||  \| | |  _  | |  _| | | | / _ \ | |_) | | | |
|  __/|  _  || | ___) |  _  || || |\  | |_| | | |_| | |_| |/ ___ \|  _ <| |_| |
|_|   |_| |_|___|____/|_| |_|___|_| \_|\____|  \____|\___//_/   \_\_| \_\____/
"""


def _hora_actual() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _recortar(texto: str, limite: int = 72) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else f"{texto[: limite - 3]}..."


def _estado_archivo(path: str) -> str:
    return "encontrado" if os.path.exists(path) else "no encontrado"


def _ruta_legible(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT_DIR)
    except ValueError:
        return path


def _linea_clave_valor(clave: str, valor: object) -> str:
    return f"  {clave:<22} {valor}"


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


def mostrar_banner(args: argparse.Namespace) -> None:
    """Muestra una pantalla inicial legible para arrancar el servidor."""
    endpoint = f"http://{args.host}:{args.port}"
    print("")
    print("=" * 72)
    print(ASCII_TITLE.strip("\n"))
    print(APP_NAME)
    print("=" * 72)
    print("Servidor local activo para la extension de Gmail.")
    print("")
    print("Conexion")
    print(_linea_clave_valor("URL local:", endpoint))
    print(_linea_clave_valor("Health check:", f"{endpoint}/health"))
    print(_linea_clave_valor("Endpoint analisis:", f"{endpoint}/analyze"))
    print("")
    print("Analisis")
    print(_linea_clave_valor("Modo:", args.mode))
    print(_linea_clave_valor("Umbral phishing:", f"{args.threshold:.1f}%"))
    print(_linea_clave_valor("Peso heuristico:", f"{args.heur_weight}%"))
    print(_linea_clave_valor("Peso neuronal:", f"{args.neural_weight}%"))
    print("")
    print("Modelos")
    print(_linea_clave_valor("Modelo ES:", f"{_ruta_legible(args.model_es)} ({_estado_archivo(args.model_es)})"))
    print(_linea_clave_valor("Modelo EN:", f"{_ruta_legible(args.model_en)} ({_estado_archivo(args.model_en)})"))
    print("")
    print("Uso rapido")
    print("  1. Recarga la extension en chrome://extensions.")
    print("  2. Abre Gmail y entra en un correo.")
    print("  3. Deja esta ventana abierta mientras uses la extension.")
    print("")
    print("Actividad")
    print("  Esperando solicitudes desde Gmail...")
    print("  Pulsa Ctrl+C para detener el servidor.")
    print("=" * 72)
    print("")


def construir_datos_email(payload: Dict[str, object]) -> Dict[str, object]:
    """Normaliza los datos enviados por la extension al formato del analizador."""
    subject = str(payload.get("subject", "")).strip()
    sender = str(payload.get("from", "") or payload.get("sender", "")).strip()
    body = str(payload.get("body", "")).strip()
    html_body = str(payload.get("html_body", "")).strip()
    urls = [str(url) for url in payload.get("urls", []) if str(url).strip()]
    anchors = [
        {"text": str(anchor.get("text", "")), "href": str(anchor.get("href", ""))}
        for anchor in payload.get("anchors", [])
        if isinstance(anchor, dict) and str(anchor.get("href", "")).strip()
    ]
    headers = {
        "From": sender,
        "Subject": subject,
    }
    full_text = "\n".join(part for part in [f"From: {sender}" if sender else "", f"Subject: {subject}" if subject else "", body] if part)
    return {
        "subject": subject,
        "from": sender,
        "to": "",
        "body": body,
        "html_body": html_body,
        "headers": headers,
        "anchors": anchors,
        "attachments": [],
        "urls": urls,
        "full_text": full_text,
    }


class GmailWebAnalyzer:
    """Analizador reutilizable que delega en el backend centralizado."""

    def __init__(self, config: MonitorConfig):
        self.config = config
        self.client = BackendAnalysisClient(os.getenv("BACKEND_URL", "http://127.0.0.1:8766"))
        self.service = EmailAnalysisService(config)
        self.request_count = 0

    def analyze(self, payload: Dict[str, object]) -> Dict[str, object]:
        datos_email = construir_datos_email(payload)
        try:
            resultado = self.client.analyze(datos_email)
        except Exception:
            resultado = self.service.analyze(datos_email)
        self.request_count += 1
        return resultado


def limpiar_resultado(resultado: Dict[str, object], threshold: float) -> Dict[str, object]:
    """Devuelve solo los campos que necesita la extension."""
    score = float(resultado.get("risk_score", 0))
    return {
        "is_phishing": score >= threshold,
        "risk_score": round(score, 1),
        "label": "Phishing" if score >= threshold else "Seguro",
        "description": resultado.get("description", ""),
        "explanation": resultado.get("explanation", []),
        "signals": resultado.get("signals", {}),
        "urls": resultado.get("urls", []),
    }


def crear_handler(analyzer: GmailWebAnalyzer):
    """Crea un handler HTTP asociado al analizador configurado."""

    class GmailExtensionHandler(BaseHTTPRequestHandler):
        server_version = "GmailPhishingExtension/1.0"

        def _origin_permitido(self) -> str:
            origin = self.headers.get("Origin", "")
            return origin if origin in ALLOWED_ORIGINS else "https://mail.google.com"

        def _send_json(self, status: int, payload: Dict[str, object]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", self._origin_permitido())
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:
            self._send_json(204, {})

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(200, {"ok": True, "mode": analyzer.config.mode})
                return
            self._send_json(404, {"error": "Ruta no encontrada"})

        def do_POST(self) -> None:
            if self.path != "/analyze":
                self._send_json(404, {"error": "Ruta no encontrada"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length)
                payload = json.loads(raw_body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("El cuerpo debe ser un objeto JSON")
                resultado = analyzer.analyze(payload)
                self._log_analisis(payload, resultado)
                self._send_json(200, limpiar_resultado(resultado, analyzer.config.threshold))
            except Exception as exc:
                print(f"[{_hora_actual()}] ERROR analisis: {exc}")
                self._send_json(400, {"error": str(exc)})

        def log_message(self, format: str, *args) -> None:
            return

        def _log_analisis(self, payload: Dict[str, object], resultado: Dict[str, object]) -> None:
            subject = _recortar(str(payload.get("subject", "(sin asunto)")))
            score = float(resultado.get("risk_score", 0))
            label = "PHISHING" if score >= analyzer.config.threshold else "OK"
            print(
                f"[{_hora_actual()}] #{analyzer.request_count:03d} "
                f"{label:<8} {score:5.1f}% | {subject}"
            )

    return GmailExtensionHandler


def parse_args() -> argparse.Namespace:
    cargar_env_local(ROOT_DIR)
    parser = argparse.ArgumentParser(
        description="Servidor local que conecta la extension de Gmail Web con el detector Python.",
        epilog="Ejemplo: python src/gmail_extension_server.py --mode heuristico",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("GMAIL_EXTENSION_HOST", "127.0.0.1"),
        help="Host local donde escuchar peticiones.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_env_int("GMAIL_EXTENSION_PORT", 8765),
        help="Puerto local usado por la extension.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=_env_float("GMAIL_EXTENSION_THRESHOLD", 45.0),
        help="Umbral de riesgo para marcar phishing.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        default=os.getenv("GMAIL_EXTENSION_MODE", MODO_COMBINADO),
        help="Modo de analisis.",
    )
    parser.add_argument(
        "--heur-weight",
        type=int,
        default=_env_int("GMAIL_EXTENSION_HEUR_WEIGHT", 60),
        help="Peso heuristico en modo combinado.",
    )
    parser.add_argument(
        "--neural-weight",
        type=int,
        default=_env_int("GMAIL_EXTENSION_NEURAL_WEIGHT", 40),
        help="Peso neuronal en modo combinado.",
    )
    parser.add_argument(
        "--model-es",
        default=os.getenv("GMAIL_EXTENSION_MODEL_ES", DEFAULT_MODEL_PATH_ES),
        help="Ruta del modelo neuronal en espanol.",
    )
    parser.add_argument(
        "--model-en",
        default=os.getenv("GMAIL_EXTENSION_MODEL_EN", DEFAULT_MODEL_PATH_EN),
        help="Ruta del modelo neuronal en ingles.",
    )
    return parser.parse_args()


def crear_servidor(args: argparse.Namespace) -> Tuple[ThreadingHTTPServer, GmailWebAnalyzer]:
    config = MonitorConfig(
        state_path="",
        threshold=args.threshold,
        mode=args.mode,
        heur_weight=args.heur_weight,
        neural_weight=args.neural_weight,
        model_path_es=args.model_es,
        model_path_en=args.model_en,
    )
    analyzer = GmailWebAnalyzer(config)
    server = ThreadingHTTPServer((args.host, args.port), crear_handler(analyzer))
    return server, analyzer


def main() -> None:
    args = parse_args()
    server, _ = crear_servidor(args)
    mostrar_banner(args)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{_hora_actual()}] Servidor detenido por el usuario.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
