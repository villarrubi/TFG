"""Rutas de ejecución separadas entre instalaciones cliente y servidor."""

from __future__ import annotations

import os
from pathlib import Path


def _absolute_path(value: str | os.PathLike[str]) -> Path:
    """Normaliza una ruta configurable sin exigir que ya exista."""
    return Path(value).expanduser().resolve()


def client_data_dir(root_dir: str | os.PathLike[str]) -> Path:
    """Directorio privado de una instalación cliente."""
    configured = os.getenv("PHISHING_CLIENT_DATA_DIR", "").strip()
    return _absolute_path(configured or Path(root_dir) / "runtime" / "client")


def server_data_dir(root_dir: str | os.PathLike[str]) -> Path:
    """Directorio persistente propiedad del backend central."""
    configured = os.getenv("PHISHING_SERVER_DATA_DIR", "").strip()
    return _absolute_path(configured or Path(root_dir) / "runtime" / "server")


def client_env_path(root_dir: str | os.PathLike[str]) -> Path:
    return client_data_dir(root_dir) / ".env.local"


def server_env_path(root_dir: str | os.PathLike[str]) -> Path:
    return server_data_dir(root_dir) / ".env.local"


def gmail_credentials_path(root_dir: str | os.PathLike[str]) -> Path:
    configured = os.getenv("GMAIL_CREDENTIALS_PATH", "").strip()
    return _absolute_path(configured or client_data_dir(root_dir) / "credentials.json")


def gmail_token_path(root_dir: str | os.PathLike[str]) -> Path:
    configured = os.getenv("GMAIL_TOKEN_PATH", "").strip()
    return _absolute_path(configured or client_data_dir(root_dir) / "token.json")


def monitor_state_path(root_dir: str | os.PathLike[str]) -> Path:
    configured = os.getenv("MONITOR_STATE_PATH", "").strip()
    return _absolute_path(configured or client_data_dir(root_dir) / "estado_monitor.json")


def server_models_dir(root_dir: str | os.PathLike[str]) -> Path:
    return server_data_dir(root_dir) / "models"


def server_model_path(root_dir: str | os.PathLike[str], language: str) -> Path:
    """Artefacto ES/EN del backend, con override explícito opcional."""
    normalized = language.strip().lower()
    if normalized not in {"es", "en"}:
        raise ValueError("El idioma del modelo debe ser 'es' o 'en'.")
    configured = os.getenv(f"BACKEND_MODEL_{normalized.upper()}", "").strip()
    return _absolute_path(
        configured or server_models_dir(root_dir) / f"modelo_neural_{normalized}.joblib"
    )


def ensure_runtime_dirs(root_dir: str | os.PathLike[str]) -> None:
    """Crea solo los contenedores; nunca genera secretos ni modelos."""
    client_data_dir(root_dir).mkdir(parents=True, exist_ok=True)
    server_models_dir(root_dir).mkdir(parents=True, exist_ok=True)


__all__ = [
    "client_data_dir",
    "client_env_path",
    "ensure_runtime_dirs",
    "gmail_credentials_path",
    "gmail_token_path",
    "monitor_state_path",
    "server_data_dir",
    "server_env_path",
    "server_model_path",
    "server_models_dir",
]
