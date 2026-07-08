"""Servicio comun de analisis heuristico, neuronal y combinado.

Este modulo contiene la logica compartida por la UI, el monitor y la extension
de Gmail Web. Los consumidores deciden de donde sale el correo, pero el modo de
analisis y la combinacion de resultados viven en un unico sitio.
"""

from __future__ import annotations

from typing import Protocol

from .analizador_email import construir_texto_para_analisis
from .heuristicas import analizar_correo
from .idioma import detectar_idioma_correo
from .modelo_neural import ModelStorage, NeuralPhishingClassifier, NeuralPhishingDetector


MODO_HEURISTICO = "heuristico"
MODO_NEURAL = "neural"
MODO_COMBINADO = "combinado"
VALID_MODES = {MODO_HEURISTICO, MODO_NEURAL, MODO_COMBINADO}


class AnalysisConfig(Protocol):
    """Atributos minimos que necesita el servicio de analisis."""

    threshold: float
    mode: str
    heur_weight: int
    neural_weight: int
    model_path_es: str
    model_path_en: str


def construir_resultado_combinado(resultado_heur: dict, resultado_neural: dict, config: AnalysisConfig) -> dict:
    """Combina heuristica y red neuronal usando la misma logica que la UI."""
    combined_score = (
        resultado_heur["risk_score"] * config.heur_weight
        + resultado_neural["risk_score"] * config.neural_weight
    ) / (config.heur_weight + config.neural_weight)
    return {
        "is_phishing": combined_score >= config.threshold,
        "risk_score": round(combined_score, 1),
        "description": "Resultado mixto ponderado entre heurística y red neuronal.",
        "urls": resultado_heur.get("urls", []),
        "anchors": resultado_heur.get("anchors", []),
        "headers": resultado_heur.get("headers", {}),
        "explanation": resultado_heur.get("explanation", []),
        "signals": resultado_heur.get("signals", {}),
    }


def cargar_detector_neural(config: AnalysisConfig, idioma: str = "es") -> NeuralPhishingDetector:
    """Carga un detector neuronal para el idioma indicado.

    Intenta primero el modelo del idioma detectado; si no existe en disco,
    reutiliza el del otro idioma antes de caer al modelo sintético. Esta es
    la misma lógica de alternativa que usa la detección manual en
    detect_app.py, para que el comportamiento sea consistente en toda la app.
    El parámetro `idioma` tiene un valor por defecto ('es') solo para no
    romper llamadas antiguas que no lo pasaban explícitamente.
    """
    path_principal = config.model_path_en if idioma == "en" else config.model_path_es
    path_alternativo = config.model_path_es if idioma == "en" else config.model_path_en
    classifier = ModelStorage(path_principal).load()
    if classifier is None:
        classifier = ModelStorage(path_alternativo).load()
    if classifier is None:
        classifier = NeuralPhishingClassifier()
        classifier.fit_default()
    return NeuralPhishingDetector(classifier)


class EmailAnalysisService:
    """Ejecuta el analisis configurado y reutiliza el detector cuando procede."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        # Se cachea un detector por idioma (no uno solo para toda la sesión):
        # el monitor puede encontrarse correos en español e inglés mezclados,
        # y antes se quedaba fijo con el primer idioma que tocara cargar.
        self._detectores: dict[str, NeuralPhishingDetector] = {}

    def analyze(self, datos_email: dict) -> dict:
        """Analiza un correo ya normalizado segun el modo configurado."""
        resultado_heur = analizar_correo(datos_email)

        if self.config.mode == MODO_HEURISTICO:
            return resultado_heur

        resultado_neural = self._analyze_neural(datos_email)
        if self.config.mode == MODO_NEURAL:
            return resultado_neural
        return construir_resultado_combinado(resultado_heur, resultado_neural, self.config)

    def _analyze_neural(self, datos_email: dict) -> dict:
        texto = construir_texto_para_analisis(datos_email)
        idioma = detectar_idioma_correo(texto)
        detector = self._detectores.get(idioma)
        if detector is None:
            detector = cargar_detector_neural(self.config, idioma)
            self._detectores[idioma] = detector
        return detector.analyze(
            texto,
            datos_email.get("from", ""),
            datos_email.get("subject", ""),
        )
