"""Monitor de Gmail para analizar correos nuevos y generar alertas."""

import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from .analizador_email import parsear_eml_bytes
from .analysis_service import (
    MODO_COMBINADO,
    MODO_HEURISTICO,
    MODO_NEURAL,
)
from .backend_client import DEFAULT_BACKEND_URL, RemoteAnalysisService
from .defaults import (
    DEFAULT_HEUR_WEIGHT,
    DEFAULT_NEURAL_WEIGHT,
    DEFAULT_PHISHING_THRESHOLD,
)
from .telegram_notifier import TelegramNotifier, construir_mensaje_alerta

__all__ = [
    "MODO_COMBINADO",
    "MODO_HEURISTICO",
    "MODO_NEURAL",
    "MonitorConfig",
    "MonitorResult",
    "analizar_correos_nuevos",
    "analizar_email_monitor",
    "cargar_estado",
    "guardar_estado",
]


@dataclass
class MonitorConfig:
    """Configuración del monitor de correos."""

    state_path: str
    threshold: float = DEFAULT_PHISHING_THRESHOLD
    mode: str = MODO_COMBINADO
    heur_weight: int = DEFAULT_HEUR_WEIGHT
    neural_weight: int = DEFAULT_NEURAL_WEIGHT
    backend_url: str = DEFAULT_BACKEND_URL
    mark_existing_as_seen: bool = True


@dataclass
class MonitorResult:
    """Resultado de analizar un correo nuevo."""

    gmail_id: str
    subject: str
    sender: str
    risk_score: float
    is_phishing: bool
    notified: bool
    error: str | None = None


class MonitorStateError(RuntimeError):
    """Indica que el estado persistente del monitor no es válido."""


class AnalysisClient(Protocol):
    """Contrato mínimo del cliente remoto utilizado por el monitor."""

    def analyze(self, datos_email: dict) -> dict: ...


def cargar_estado(path: str) -> set[str]:
    """Carga los identificadores de Gmail ya revisados."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as state_file:
            data = json.load(state_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise MonitorStateError(f"No se pudo leer el estado del monitor: {path}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("seen_ids", []), list):
        raise MonitorStateError("El estado del monitor no contiene una lista 'seen_ids'.")
    return {str(gmail_id) for gmail_id in data.get("seen_ids", [])}


def guardar_estado(path: str, seen_ids: Iterable[str]) -> None:
    """Guarda el estado de forma atómica para no dejar JSON a medias."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    state_directory = directory or "."
    descriptor, temp_path = tempfile.mkstemp(
        dir=state_directory,
        prefix=".monitor-",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as state_file:
            json.dump(
                {"seen_ids": sorted(set(seen_ids))},
                state_file,
                indent=2,
                ensure_ascii=False,
            )
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def analizar_email_monitor(
    datos_email: dict,
    config: MonitorConfig,
    service: AnalysisClient | None = None,
) -> dict:
    """Envía un correo al backend central con la configuración del monitor."""
    return (service or RemoteAnalysisService(config)).analyze(datos_email)


def analizar_correos_nuevos(
    correos_gmail: Iterable,
    config: MonitorConfig,
    notifier: TelegramNotifier | None = None,
    analysis_service: AnalysisClient | None = None,
) -> list[MonitorResult]:
    """Analiza correos no vistos sin interrumpir el lote por un mensaje defectuoso."""
    correos_gmail = list(correos_gmail)
    state_exists = os.path.exists(config.state_path)
    seen_ids = cargar_estado(config.state_path)
    if not state_exists and config.mark_existing_as_seen:
        seen_ids.update(correo.gmail_id for correo in correos_gmail)
        guardar_estado(config.state_path, seen_ids)
        return []

    service = analysis_service or RemoteAnalysisService(config)
    resultados: list[MonitorResult] = []
    for correo in correos_gmail:
        if correo.gmail_id in seen_ids:
            continue

        try:
            datos_email = parsear_eml_bytes(correo.raw_bytes)
            resultado = analizar_email_monitor(datos_email, config, service)
        except Exception as exc:  # noqa: BLE001
            # Un EML corrupto o un fallo puntual del modelo no debe impedir que
            # el resto del lote se procese. El ID queda pendiente para reintento.
            resultados.append(
                MonitorResult(
                    gmail_id=correo.gmail_id,
                    subject="",
                    sender="",
                    risk_score=0.0,
                    is_phishing=False,
                    notified=False,
                    error=str(exc),
                )
            )
            continue

        is_phishing = bool(resultado["is_phishing"])
        notified = False
        notification_error = None

        if is_phishing and notifier is not None:
            try:
                notifier.enviar_mensaje(
                    construir_mensaje_alerta(datos_email, resultado, config.mode)
                )
                notified = True
            except Exception as exc:  # noqa: BLE001
                # Se conserva el correo como pendiente para reintentar la alerta.
                notification_error = str(exc)

        resultados.append(
            MonitorResult(
                gmail_id=correo.gmail_id,
                subject=datos_email.get("subject", ""),
                sender=datos_email.get("from", ""),
                risk_score=resultado["risk_score"],
                is_phishing=is_phishing,
                notified=notified,
                error=notification_error,
            )
        )
        if notification_error is not None:
            continue

        seen_ids.add(correo.gmail_id)
        # Persistir tras cada correo evita repetir todo el lote si el proceso se
        # detiene antes de terminar el ciclo.
        guardar_estado(config.state_path, seen_ids)

    return resultados
