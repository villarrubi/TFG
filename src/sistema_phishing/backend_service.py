"""Servicio centralizado para análisis de phishing en modo cliente/servidor."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .analysis_service import MODO_COMBINADO, EmailAnalysisService

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAX_TEXT_CHARS = 200_000
MAX_LIST_ITEMS = 100


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
            # No se exponen rutas absolutas del equipo en una respuesta HTTP.
            "model_es_available": os.path.exists(self.config.model_path_es),
            "model_en_available": os.path.exists(self.config.model_path_en),
        }

    def analyze_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Normaliza los datos recibidos y devuelve el resultado de análisis."""
        datos_email = self._normalizar_payload(payload)
        resultado = self._service.analyze(datos_email)
        return self._normalizar_resultado(resultado)

    def _normalizar_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("El cuerpo debe ser un objeto JSON.")

        subject = self._texto(payload, ("subject", "Subject"))
        sender = self._texto(payload, ("from", "sender", "From"))
        recipient = self._texto(payload, ("to", "recipient", "To"))
        body = self._texto(payload, ("body", "text", "content"))
        html_body = self._texto(payload, ("html_body", "html"))

        urls = self._lista_textos(payload.get("urls", []), "urls", max_items=MAX_LIST_ITEMS)
        anchors = self._normalizar_anclas(payload.get("anchors", []))
        raw_headers = payload.get("headers", {})
        if not isinstance(raw_headers, Mapping):
            raise TypeError("headers debe ser un objeto JSON.")
        headers = {
            "From": sender,
            "To": recipient,
            "Subject": subject,
            **{
                self._limitar_texto(str(k), "nombre de cabecera"): self._limitar_texto(
                    str(v), "valor de cabecera"
                )
                for k, v in list(raw_headers.items())[:MAX_LIST_ITEMS]
            },
        }
        full_text = "\n".join(
            part for part in [
                *(f"{key}: {value}" for key, value in headers.items() if value),
                body,
            ] if part
        )
        full_text = self._limitar_texto(full_text, "contenido del correo")
        return {
            "subject": subject,
            "from": sender,
            "to": recipient,
            "body": body,
            "html_body": html_body,
            "headers": headers,
            "anchors": anchors,
            "attachments": self._lista_textos(
                payload.get("attachments", []), "attachments", max_items=50
            ),
            "urls": urls,
            "full_text": full_text,
        }

    @staticmethod
    def _limitar_texto(value: str, field_name: str) -> str:
        if len(value) > MAX_TEXT_CHARS:
            raise ValueError(f"El campo {field_name} supera el límite permitido.")
        return value.strip()

    @classmethod
    def _texto(cls, payload: Mapping[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                if isinstance(value, (Mapping, list, tuple, set)):
                    raise ValueError(f"El campo {key} debe ser texto.")
                return cls._limitar_texto(str(value), key)
        return ""

    @classmethod
    def _lista_textos(
        cls,
        values: Any,
        field_name: str,
        *,
        max_items: int,
    ) -> list[str]:
        if values in (None, ""):
            return []
        if not isinstance(values, list):
            raise TypeError(f"El campo {field_name} debe ser una lista.")
        if len(values) > max_items:
            raise ValueError(f"El campo {field_name} contiene demasiados elementos.")
        return [cls._limitar_texto(str(value), field_name) for value in values if str(value).strip()]

    @classmethod
    def _normalizar_anclas(cls, values: Any) -> list[dict[str, str]]:
        if values in (None, ""):
            return []
        if not isinstance(values, list) or len(values) > MAX_LIST_ITEMS:
            raise ValueError("anchors debe ser una lista de tamaño válido.")
        anclas = []
        for anchor in values:
            if not isinstance(anchor, Mapping):
                raise TypeError("Cada anchor debe ser un objeto JSON.")
            href = cls._limitar_texto(str(anchor.get("href", "")), "href")
            if href:
                anclas.append(
                    {
                        "text": cls._limitar_texto(str(anchor.get("text", "")), "anchor.text"),
                        "href": href,
                    }
                )
        return anclas

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
