"""Proxy opcional entre la extensión Gmail y el backend central.

La extensión puede llamar directamente al backend en el puerto 8766. Este
proceso conserva el puerto histórico 8765, pero ya no carga ningún modelo:
solo reenvía las solicitudes al servidor central.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

from sistema_phishing.analysis_service import (
    MODO_COMBINADO,
    VALID_MODES,
)
from sistema_phishing.backend_client import BackendClient, backend_url_from_env
from sistema_phishing.backend_service import MAX_LIST_ITEMS, MAX_TEXT_CHARS
from sistema_phishing.env_loader import cargar_env_local, env_float, env_int
from sistema_phishing.gmail_monitor import MonitorConfig
from sistema_phishing.http_api import crear_handler as crear_handler_http
from sistema_phishing.http_api import crear_servidor_http
from sistema_phishing.network import validar_host_local

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
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
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


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


def mostrar_banner(args: argparse.Namespace) -> None:
    """Muestra una pantalla inicial legible para arrancar el servidor."""
    endpoint = f"http://{args.host}:{args.port}"
    print()
    print("=" * 72)
    print(ASCII_TITLE.strip("\n"))
    print(APP_NAME)
    print("=" * 72)
    print("Proxy local activo para la extension de Gmail.")
    print()
    print("Conexion")
    print(_linea_clave_valor("URL local:", endpoint))
    print(_linea_clave_valor("Health check:", f"{endpoint}/health"))
    print(_linea_clave_valor("Endpoint analisis:", f"{endpoint}/analyze"))
    print(_linea_clave_valor("Backend destino:", args.backend_url))
    print()
    print("Analisis")
    print(_linea_clave_valor("Modo:", args.mode))
    print(_linea_clave_valor("Umbral phishing:", f"{args.threshold:.1f}%"))
    print(_linea_clave_valor("Peso heuristico:", f"{args.heur_weight}%"))
    print(_linea_clave_valor("Peso neuronal:", f"{args.neural_weight}%"))
    print()
    print("Uso rapido")
    print("  1. Recarga la extension en chrome://extensions.")
    print("  2. Abre Gmail y entra en un correo.")
    print("  3. Deja esta ventana abierta mientras uses la extension.")
    print()
    print("Actividad")
    print("  Esperando solicitudes desde Gmail...")
    print("  Pulsa Ctrl+C para detener el servidor.")
    print("=" * 72)
    print()


def construir_datos_email(payload: dict[str, object]) -> dict[str, object]:
    """Normaliza los datos enviados por la extension al formato del analizador."""
    if not isinstance(payload, dict):
        raise TypeError("El cuerpo debe ser un objeto JSON.")

    def texto(nombre: str, *alternativos: str) -> str:
        for clave in (nombre, *alternativos):
            valor = payload.get(clave)
            if valor not in (None, ""):
                if isinstance(valor, (dict, list, tuple, set)):
                    raise ValueError(f"El campo {clave} debe ser texto.")
                resultado = str(valor).strip()
                if len(resultado) > MAX_TEXT_CHARS:
                    raise ValueError(f"El campo {clave} supera el límite permitido.")
                return resultado
        return ""

    def lista(nombre: str) -> list[object]:
        valores = payload.get(nombre, [])
        if valores in (None, ""):
            return []
        if not isinstance(valores, list):
            raise TypeError(f"El campo {nombre} debe ser una lista.")
        if len(valores) > MAX_LIST_ITEMS:
            raise ValueError(f"El campo {nombre} contiene demasiados elementos.")
        return valores

    subject = texto("subject")
    sender = texto("from", "sender")
    body = texto("body", "text", "content")
    html_body = texto("html_body", "html")
    urls = [str(url).strip() for url in lista("urls") if str(url).strip()]
    if any(len(url) > MAX_TEXT_CHARS for url in urls):
        raise ValueError("Una URL supera el límite permitido.")
    raw_anchors = lista("anchors")
    for anchor in raw_anchors:
        if not isinstance(anchor, dict):
            raise TypeError("Cada anchor debe ser un objeto JSON.")
    anchors = [
        {"text": str(anchor.get("text", "")), "href": str(anchor.get("href", ""))}
        for anchor in raw_anchors
        if str(anchor.get("href", "")).strip()
    ]
    headers = {
        "From": sender,
        "Subject": subject,
    }
    full_text = "\n".join(
        part
        for part in [
            f"From: {sender}" if sender else "",
            f"Subject: {subject}" if subject else "",
            body,
        ]
        if part
    )
    if len(full_text) > MAX_TEXT_CHARS:
        raise ValueError("El contenido del correo supera el límite permitido.")
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
    """Cliente reutilizable que nunca carga modelos en el proceso proxy."""

    def __init__(self, config: MonitorConfig, client: BackendClient | None = None):
        self.config = config
        self.client = client or BackendClient(config.backend_url)
        self.request_count = 0

    def analyze(self, payload: dict[str, object]) -> dict[str, object]:
        datos_email = construir_datos_email(payload)
        response = self.client.analyze(
            datos_email,
            mode=self.config.mode,
            threshold=self.config.threshold,
            heur_weight=self.config.heur_weight,
            neural_weight=self.config.neural_weight,
        )
        self.request_count += 1
        return dict(response["result"])


def limpiar_resultado(resultado: dict[str, object], threshold: float) -> dict[str, object]:
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
    """Crea el handler común con el adaptador específico de la extensión."""
    return crear_handler_http(_ExtensionBackendAdapter(analyzer), allowed_origins=ALLOWED_ORIGINS)


class _ExtensionBackendAdapter:
    """Adapta la salida histórica de la extensión al contrato HTTP común."""

    def __init__(self, analyzer: GmailWebAnalyzer):
        self.analyzer = analyzer
        self.config = analyzer.config

    def build_health_payload(self) -> dict[str, object]:
        health = dict(self.analyzer.client.health())
        health["proxy"] = True
        health["requests"] = self.analyzer.request_count
        return health

    def analyze_payload(self, payload: dict[str, object]) -> dict[str, object]:
        resultado = self.analyzer.analyze(payload)
        subject = _recortar(str(payload.get("subject", "(sin asunto)")))
        score = float(resultado.get("risk_score", 0))
        label = "PHISHING" if score >= self.config.threshold else "OK"
        print(
            f"[{_hora_actual()}] #{self.analyzer.request_count:03d} "
            f"{label:<8} {score:5.1f}% | {subject}"
        )
        return limpiar_resultado(resultado, self.config.threshold)


def parse_args() -> argparse.Namespace:
    cargar_env_local(ROOT_DIR)
    parser = argparse.ArgumentParser(
        description="Proxy opcional entre la extensión antigua y el backend central.",
        epilog="Ejemplo: python src/gmail_extension_server.py --backend-url http://127.0.0.1:8766",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("GMAIL_EXTENSION_HOST", "127.0.0.1"),
        help="Host local donde escuchar peticiones.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=env_int("GMAIL_EXTENSION_PORT", 8765),
        help="Puerto local usado por la extension.",
    )
    parser.add_argument(
        "--backend-url",
        default=backend_url_from_env(),
        help="URL del backend central al que se reenvían los correos.",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Permite escuchar fuera de loopback bajo responsabilidad del operador.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=env_float("GMAIL_EXTENSION_THRESHOLD", 45.0),
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
        default=env_int("GMAIL_EXTENSION_HEUR_WEIGHT", 60),
        help="Peso heuristico en modo combinado.",
    )
    parser.add_argument(
        "--neural-weight",
        type=int,
        default=env_int("GMAIL_EXTENSION_NEURAL_WEIGHT", 40),
        help="Peso neuronal en modo combinado.",
    )
    return parser.parse_args()


def crear_servidor(args: argparse.Namespace) -> tuple[ThreadingHTTPServer, GmailWebAnalyzer]:
    args.host = validar_host_local(
        args.host,
        allow_remote=getattr(args, "allow_remote", False),
    )
    config = MonitorConfig(
        state_path="",
        threshold=args.threshold,
        mode=args.mode,
        heur_weight=args.heur_weight,
        neural_weight=args.neural_weight,
        backend_url=args.backend_url,
    )
    analyzer = GmailWebAnalyzer(config)
    server = crear_servidor_http(
        args.host,
        args.port,
        _ExtensionBackendAdapter(analyzer),
        allowed_origins=ALLOWED_ORIGINS,
    )
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
