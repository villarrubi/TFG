"""Cliente para consumir el backend centralizado de análisis."""

from __future__ import annotations

import os
from typing import Any, Callable, Mapping

import requests


class BackendAnalysisClient:
    """Envía peticiones al backend HTTP de análisis."""

    def __init__(self, base_url: str | None = None, api_token: str | None = None):
        configured = base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8766")
        self.base_url = configured.rstrip("/")
        self.api_token = api_token if api_token is not None else os.getenv("BACKEND_API_TOKEN", "")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
            headers["X-API-Key"] = self.api_token
        return headers

    def analyze(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Envía un payload al backend y devuelve el resultado JSON."""
        response = requests.post(f"{self.base_url}/analyze", json=dict(payload), headers=self._headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        """Consulta el estado del backend."""
        response = requests.get(f"{self.base_url}/health", headers=self._headers(), timeout=5)
        response.raise_for_status()
        return response.json()


def analyze_via_backend(payload: Mapping[str, Any], fallback: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Prueba el backend y cae al fallback si no está disponible."""
    client = BackendAnalysisClient()
    try:
        return client.analyze(payload)
    except Exception as exc:  # noqa: BLE001
        if fallback is None:
            return {"backend_available": False, "error": f"Backend no disponible: {exc}"}
        return fallback(payload)
