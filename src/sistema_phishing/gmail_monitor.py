"""Monitor de Gmail para analizar correos nuevos y generar alertas."""

import json
import os
from dataclasses import dataclass
from typing import Iterable, List, Set

from .analysis_service import (
    MODO_COMBINADO,
    MODO_HEURISTICO,
    MODO_NEURAL,
    EmailAnalysisService,
    cargar_detector_neural as _cargar_detector_neural,
    construir_resultado_combinado as _construir_resultado_combinado,
)
from .analizador_email import parsear_eml_bytes
from .telegram_notifier import TelegramNotifier, construir_mensaje_alerta


@dataclass
class MonitorConfig:
    """Configuración del monitor de correos."""

    state_path: str
    threshold: float = 45.0
    mode: str = MODO_COMBINADO
    heur_weight: int = 60
    neural_weight: int = 40
    model_path_es: str = "modelo_neural_es.joblib"
    model_path_en: str = "modelo_neural_en.joblib"
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


def cargar_estado(path: str) -> Set[str]:
    """Carga los identificadores de Gmail ya revisados."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as state_file:
        data = json.load(state_file)
    return set(data.get("seen_ids", []))


def guardar_estado(path: str, seen_ids: Iterable[str]) -> None:
    """Guarda los identificadores de Gmail ya revisados."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as state_file:
        json.dump({"seen_ids": sorted(set(seen_ids))}, state_file, indent=2)


def construir_resultado_combinado(resultado_heur: dict, resultado_neural: dict, config: MonitorConfig) -> dict:
    """Combina heurística y red neuronal usando la misma lógica que la UI."""
    return _construir_resultado_combinado(resultado_heur, resultado_neural, config)


def cargar_detector_neural(config: MonitorConfig):
    """Carga un detector neuronal desde disco o usa el modelo sintético."""
    return _cargar_detector_neural(config)


def analizar_email_monitor(datos_email: dict, config: MonitorConfig) -> dict:
    """Analiza un correo con el modo seleccionado para el monitor."""
    return EmailAnalysisService(config).analyze(datos_email)


def analizar_correos_nuevos(correos_gmail, config: MonitorConfig, notifier: TelegramNotifier | None = None) -> List[MonitorResult]:
    """Analiza correos no vistos, envía alertas y actualiza el estado."""
    seen_ids = cargar_estado(config.state_path)
    if not seen_ids and config.mark_existing_as_seen:
        seen_ids.update(correo.gmail_id for correo in correos_gmail)
        guardar_estado(config.state_path, seen_ids)
        return []

    resultados: List[MonitorResult] = []
    for correo in correos_gmail:
        if correo.gmail_id in seen_ids:
            continue

        datos_email = parsear_eml_bytes(correo.raw_bytes)
        resultado = analizar_email_monitor(datos_email, config)
        is_phishing = resultado["risk_score"] >= config.threshold
        notified = False

        if is_phishing and notifier is not None:
            notifier.enviar_mensaje(construir_mensaje_alerta(datos_email, resultado, config.mode))
            notified = True

        resultados.append(
            MonitorResult(
                gmail_id=correo.gmail_id,
                subject=datos_email.get("subject", ""),
                sender=datos_email.get("from", ""),
                risk_score=resultado["risk_score"],
                is_phishing=is_phishing,
                notified=notified,
            )
        )
        seen_ids.add(correo.gmail_id)

    guardar_estado(config.state_path, seen_ids)
    return resultados
