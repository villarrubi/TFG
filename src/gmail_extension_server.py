"""Servidor local para la extension de Gmail Web.

La extension del navegador no ejecuta el modelo Python directamente. En su
lugar envia el correo visible en Gmail a este pequeno endpoint local y recibe
la clasificacion en JSON.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple

from sistema_phishing.analizador_email import construir_texto_para_analisis
from sistema_phishing.gmail_monitor import (
    MODO_COMBINADO,
    MODO_HEURISTICO,
    MODO_NEURAL,
    MonitorConfig,
    construir_resultado_combinado,
    cargar_detector_neural,
)
from sistema_phishing.heuristicas import analizar_correo


ALLOWED_ORIGINS = {"https://mail.google.com"}
VALID_MODES = {MODO_HEURISTICO, MODO_NEURAL, MODO_COMBINADO}


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
    """Analizador reutilizable para no recargar el modelo neuronal en cada peticion."""

    def __init__(self, config: MonitorConfig):
        self.config = config
        self._detector = None

    def analyze(self, payload: Dict[str, object]) -> Dict[str, object]:
        datos_email = construir_datos_email(payload)
        resultado_heur = analizar_correo(datos_email)

        if self.config.mode == MODO_HEURISTICO:
            return resultado_heur

        if self._detector is None:
            self._detector = cargar_detector_neural(self.config)

        resultado_neural = self._detector.analyze(
            construir_texto_para_analisis(datos_email),
            datos_email.get("from", ""),
            datos_email.get("subject", ""),
        )
        if self.config.mode == MODO_NEURAL:
            return resultado_neural
        return construir_resultado_combinado(resultado_heur, resultado_neural, self.config)


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
                self._send_json(200, limpiar_resultado(resultado, analyzer.config.threshold))
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def log_message(self, format: str, *args) -> None:
            return

    return GmailExtensionHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor local para la extension de Gmail Web.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--threshold", type=float, default=45.0)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default=MODO_COMBINADO)
    parser.add_argument("--heur-weight", type=int, default=60)
    parser.add_argument("--neural-weight", type=int, default=40)
    parser.add_argument("--model-es", default="modelo_neural_es.joblib")
    parser.add_argument("--model-en", default="modelo_neural_en.joblib")
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
    print(f"Servidor de extension Gmail activo en http://{args.host}:{args.port}")
    print("Pulsa Ctrl+C para detenerlo.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
