"""Cliente HTTP único para Streamlit, extensión y monitor."""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .network import es_host_loopback

DEFAULT_BACKEND_URL = "http://127.0.0.1:8766"
DEFAULT_TIMEOUT = 30.0
TRAINING_TIMEOUT = 900.0
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


class BackendClientError(RuntimeError):
    """Error seguro y legible al comunicarse con el backend."""


class BackendUnavailableError(BackendClientError):
    """El servidor central no está disponible."""


def normalize_backend_url(value: str) -> str:
    """Normaliza un origen y exige HTTPS cuando el servidor no es loopback."""
    candidate = str(value or DEFAULT_BACKEND_URL).strip().rstrip("/")
    parsed = urlsplit(candidate)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("El puerto de la URL del backend no es válido.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("La URL del backend debe ser un origen HTTP(S) sin ruta.")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("El puerto de la URL del backend no es válido.")
    if parsed.scheme == "http" and not es_host_loopback(parsed.hostname):
        raise ValueError("HTTP solo se admite en loopback; usa HTTPS para un backend remoto.")
    return candidate


def backend_url_from_env() -> str:
    return normalize_backend_url(
        os.getenv("PHISHING_BACKEND_URL", os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL))
    )


class BackendClient:
    """Implementa el contrato de la API sin ejecutar lógica de detección local."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        admin_token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = normalize_backend_url(base_url or backend_url_from_env())
        self.admin_token = (
            os.getenv("BACKEND_ADMIN_TOKEN", "") if admin_token is None else admin_token
        )
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def models(self) -> dict[str, Any]:
        return self._request("GET", "/models")

    def analyze(
        self,
        email: str | bytes | Mapping[str, Any],
        *,
        mode: str = "combinado",
        threshold: float = 45.0,
        heur_weight: int = 20,
        neural_weight: int = 80,
        include_all: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any]
        if isinstance(email, bytes):
            payload = {"eml_base64": base64.b64encode(email).decode("ascii")}
        elif isinstance(email, str):
            # El servidor interpreta el texto pegado como un mensaje RFC 5322
            # simplificado: así From/Subject no se pierden en el cliente.
            payload = {"raw_text": email}
        elif isinstance(email, Mapping):
            payload = {"email": dict(email)}
        else:
            raise TypeError("El correo debe ser texto, bytes EML u objeto de campos.")
        payload["options"] = {
            "mode": mode,
            "threshold": threshold,
            "heur_weight": heur_weight,
            "neural_weight": neural_weight,
            "include_all": include_all,
        }
        return self._request("POST", "/analyze", payload)

    def summarize(self, datasets: Iterable[Any], *, columns: Mapping[str, str]) -> dict:
        payload = {"datasets": self.serialize_datasets(datasets), "columns": dict(columns)}
        return self._request("POST", "/datasets/summary", payload, admin=True)

    def train(
        self,
        datasets: Iterable[Any],
        *,
        language: str,
        columns: Mapping[str, str],
        hyperparameters: Any = None,
    ) -> dict:
        payload = {
            "datasets": self.serialize_datasets(datasets),
            "language": language,
            "columns": dict(columns),
            "hyperparameters": self._serialize_hyperparameters(hyperparameters),
        }
        return self._request(
            "POST",
            "/train",
            payload,
            admin=True,
            timeout=TRAINING_TIMEOUT,
        )

    def evaluate(
        self,
        datasets: Iterable[Any],
        *,
        language: str,
        columns: Mapping[str, str],
    ) -> dict:
        payload = {
            "datasets": self.serialize_datasets(datasets),
            "language": language,
            "columns": dict(columns),
        }
        return self._request(
            "POST",
            "/evaluate",
            payload,
            admin=True,
            timeout=TRAINING_TIMEOUT,
        )

    def compare(
        self,
        training_datasets: Iterable[Any],
        test_datasets: Iterable[Any],
        *,
        language: str,
        columns: Mapping[str, str],
        models: Iterable[Mapping[str, Any]],
    ) -> dict:
        serialized_models = []
        for model in models:
            serialized_models.append(
                {
                    "name": model.get("name", "Modelo"),
                    "hyperparameters": self._serialize_hyperparameters(
                        model.get("hyperparameters")
                    ),
                }
            )
        payload = {
            "training_datasets": self.serialize_datasets(training_datasets),
            "test_datasets": self.serialize_datasets(test_datasets),
            "language": language,
            "columns": dict(columns),
            "models": serialized_models,
        }
        return self._request(
            "POST",
            "/compare",
            payload,
            admin=True,
            timeout=TRAINING_TIMEOUT,
        )

    def delete_model(self, language: str) -> dict:
        return self._request(
            "POST",
            "/models/delete",
            {"language": language},
            admin=True,
        )

    @staticmethod
    def serialize_datasets(datasets: Iterable[Any]) -> list[dict[str, str]]:
        """Convierte uploads en transporte JSON sin interpretar sus columnas."""
        serialized = []
        for index, source in enumerate(datasets, start=1):
            if isinstance(source, Mapping):
                name = str(source.get("name", f"dataset-{index}.csv"))
                content = source.get("content", "")
            else:
                name = str(getattr(source, "name", f"dataset-{index}.csv"))
                if hasattr(source, "getvalue"):
                    content = source.getvalue()
                elif hasattr(source, "read"):
                    content = source.read()
                else:
                    raise TypeError("El dataset no permite leer su contenido.")
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            if not isinstance(content, str):
                raise TypeError("El contenido del dataset debe ser texto o bytes.")
            serialized.append({"name": name, "content": content})
        return serialized

    @staticmethod
    def _serialize_hyperparameters(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
        if isinstance(value, Mapping):
            return dict(value)
        raise TypeError("Los hiperparámetros deben ser un dataclass o un objeto.")

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        admin: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if admin and self.admin_token:
            headers["Authorization"] = f"Bearer {self.admin_token}"
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=timeout or self.timeout) as response:
                try:
                    content_length = int(
                        response.headers.get("Content-Length", "0") or 0
                    )
                except ValueError as exc:
                    raise BackendClientError(
                        "El backend devolvió un Content-Length no válido."
                    ) from exc
                if content_length > MAX_RESPONSE_BYTES:
                    raise BackendClientError("La respuesta del backend es demasiado grande.")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise BackendClientError("La respuesta del backend es demasiado grande.")
        except HTTPError as exc:
            raw = exc.read(MAX_RESPONSE_BYTES)
            try:
                error_payload = json.loads(raw.decode("utf-8"))
                message = str(error_payload.get("error", f"HTTP {exc.code}"))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                message = f"El backend respondió HTTP {exc.code}."
            raise BackendClientError(message) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise BackendUnavailableError(
                f"No se puede contactar con el backend central en {self.base_url}."
            ) from exc
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackendClientError("El backend no devolvió JSON válido.") from exc
        if not isinstance(parsed, dict):
            raise BackendClientError("El backend devolvió un contrato no válido.")
        return parsed


class RemoteAnalysisService:
    """Adaptador de monitor que conserva ``analyze`` pero usa HTTP."""

    def __init__(self, config: Any, client: BackendClient | None = None):
        self.config = config
        self.client = client or BackendClient(getattr(config, "backend_url", None))

    def analyze(self, datos_email: Mapping[str, Any]) -> dict[str, Any]:
        response = self.client.analyze(
            datos_email,
            mode=self.config.mode,
            threshold=self.config.threshold,
            heur_weight=self.config.heur_weight,
            neural_weight=self.config.neural_weight,
        )
        return dict(response["result"])
