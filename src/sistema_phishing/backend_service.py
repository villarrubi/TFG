"""Servicio centralizado para análisis de phishing en modo cliente/servidor."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from .analysis_service import EmailAnalysisService, MODO_COMBINADO


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass
class AnalysisBackendConfig:
    """Configuración compartida por todos los clientes del backend."""

    threshold: float = 45.0
    mode: str = MODO_COMBINADO
    heur_weight: int = 60
    neural_weight: int = 40
    model_path_es: str = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
    model_path_en: str = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")


class AnalysisBackendService:
    """Expone un punto único de análisis para web, Gmail y Telegram."""

    def __init__(self, config: AnalysisBackendConfig | None = None):
        self.config = config or AnalysisBackendConfig()
        self._service = EmailAnalysisService(self.config)

    def build_health_payload(self) -> dict[str, Any]:
        """Devuelve el estado básico del backend."""
        return {
            "ok": True,
            "mode": self.config.mode,
            "threshold": self.config.threshold,
            "heur_weight": self.config.heur_weight,
            "neural_weight": self.config.neural_weight,
            "model_path_es": self.config.model_path_es,
            "model_path_en": self.config.model_path_en,
        }

    def analyze_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Normaliza los datos recibidos y devuelve el resultado de análisis."""
        datos_email = self._normalizar_payload(payload)
        resultado = self._service.analyze(datos_email)
        return self._normalizar_resultado(resultado)

    def _normalizar_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        subject = str(payload.get("subject", "") or payload.get("Subject", "") or "").strip()
        sender = str(payload.get("from", "") or payload.get("sender", "") or payload.get("From", "") or "").strip()
        body = str(payload.get("body", "") or payload.get("text", "") or payload.get("content", "") or "").strip()
        html_body = str(payload.get("html_body", "") or payload.get("html", "") or "").strip()
        urls = [str(url) for url in payload.get("urls", []) if str(url).strip()]
        anchors = [
            {"text": str(anchor.get("text", "")), "href": str(anchor.get("href", ""))}
            for anchor in payload.get("anchors", [])
            if isinstance(anchor, Mapping) and str(anchor.get("href", "")).strip()
        ]
        headers = {
            "From": sender,
            "Subject": subject,
            **{str(k): str(v) for k, v in payload.get("headers", {}).items()},
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
        return {
            "subject": subject,
            "from": sender,
            "to": str(payload.get("to", "") or "").strip(),
            "body": body,
            "html_body": html_body,
            "headers": headers,
            "anchors": anchors,
            "attachments": list(payload.get("attachments", []) or []),
            "urls": urls,
            "full_text": full_text,
        }

    def _normalizar_resultado(self, resultado: Mapping[str, Any]) -> dict[str, Any]:
        """Asegura que el resultado tenga una descripción útil para los clientes."""
        if resultado.get("description"):
            return dict(resultado)

        explanation = resultado.get("explanation")
        if isinstance(explanation, list) and explanation:
            description = str(explanation[0])
        else:
            description = "Resultado generado por el backend centralizado de phishing."

        salida = dict(resultado)
        salida["description"] = description
        return salida
