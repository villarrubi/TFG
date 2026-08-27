"""Coordina en el backend los modos heurístico, neuronal y combinado.

El servidor concentra la selección de estrategia, el umbral y la carga de
modelos. Streamlit, el monitor y la extensión se limitan a consumir por HTTP el
resultado que produce este módulo dentro del backend central.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING, Protocol

from .analizador_email import construir_texto_para_analisis
from .heuristicas import analizar_correo
from .idioma import detectar_idioma_correo

if TYPE_CHECKING:
    from .modelo_neural import NeuralPhishingDetector

MODO_HEURISTICO = "heuristico"
MODO_NEURAL = "neural"
MODO_COMBINADO = "combinado"
VALID_MODES = {MODO_HEURISTICO, MODO_NEURAL, MODO_COMBINADO}


class AnalysisConfig(Protocol):
    """Atributos mínimos requeridos por el caso de uso de análisis."""

    threshold: float
    mode: str
    heur_weight: int
    neural_weight: int
    model_path_es: str
    model_path_en: str


class AnalysisConfigurationError(ValueError):
    """Indica que los parámetros del análisis son incompatibles."""


def validar_configuracion(config: AnalysisConfig) -> None:
    """Rechaza configuraciones ambiguas antes de procesar mensajes."""
    if config.mode not in VALID_MODES:
        permitidos = ", ".join(sorted(VALID_MODES))
        raise AnalysisConfigurationError(
            f"Modo de análisis no válido: {config.mode!r}. Valores permitidos: {permitidos}."
        )
    if not 0 <= config.threshold <= 100:
        raise AnalysisConfigurationError("El umbral debe estar entre 0 y 100.")
    if config.heur_weight < 0 or config.neural_weight < 0:
        raise AnalysisConfigurationError("Los pesos no pueden ser negativos.")
    if config.mode == MODO_COMBINADO and config.heur_weight + config.neural_weight == 0:
        raise AnalysisConfigurationError(
            "El modo combinado necesita al menos un peso mayor que cero."
        )


def _aplicar_umbral(resultado: dict, threshold: float) -> dict:
    """Copia un resultado y aplica el umbral común del consumidor."""
    salida = dict(resultado)
    salida["is_phishing"] = float(salida.get("risk_score", 0.0)) >= threshold
    return salida


def construir_resultado_combinado(
    resultado_heur: dict,
    resultado_neural: dict,
    config: AnalysisConfig,
) -> dict:
    """Combina las dos puntuaciones mediante los pesos configurados."""
    validar_configuracion(config)
    peso_total = config.heur_weight + config.neural_weight
    combined_score = (
        resultado_heur["risk_score"] * config.heur_weight
        + resultado_neural["risk_score"] * config.neural_weight
    ) / peso_total
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


def cargar_detector_neural(
    config: AnalysisConfig,
    idioma: str = "es",
) -> NeuralPhishingDetector:
    """Carga el modelo del idioma indicado y aplica alternativas controladas."""
    # Se importa aquí para que el modo puramente heurístico no pague el coste
    # de importar scikit-learn ni joblib durante el arranque.
    from .modelo_neural import (
        ModelStorage,
        NeuralPhishingClassifier,
        NeuralPhishingDetector,
    )

    ruta_principal = config.model_path_en if idioma == "en" else config.model_path_es
    classifier = ModelStorage(ruta_principal).load()
    idioma_esperado = "english" if idioma == "en" else "spanish"
    source = "artifact"
    # Nunca se reutiliza silenciosamente un modelo del idioma opuesto: puede
    # cargar, pero produce una decisión lingüísticamente incoherente.
    if classifier is not None and getattr(classifier, "language", None) != idioma_esperado:
        classifier = None
    if classifier is None:
        source = "synthetic_fallback"
        classifier = NeuralPhishingClassifier(
            language=idioma_esperado
        )
        classifier.fit_default()
    return NeuralPhishingDetector(classifier, source=source)


class EmailAnalysisService:
    """Ejecuta una estrategia de análisis y reutiliza modelos por idioma."""

    def __init__(
        self,
        config: AnalysisConfig,
        heuristic_analyzer: Callable[[dict], dict] | None = None,
        detector_loader: Callable[[AnalysisConfig, str], NeuralPhishingDetector]
        | None = None,
        language_detector: Callable[[str], str] | None = None,
    ):
        validar_configuracion(config)
        self.config = config
        # Las dependencias son reemplazables en pruebas o futuras versiones;
        # el coordinador no queda acoplado a una implementación concreta.
        self._heuristic_analyzer = heuristic_analyzer or analizar_correo
        self._detector_loader = detector_loader or cargar_detector_neural
        self._language_detector = language_detector or detectar_idioma_correo
        self._detectores: dict[str, NeuralPhishingDetector] = {}
        self._detector_lock = Lock()

    def analyze(self, datos_email: dict) -> dict:
        """Analiza un correo normalizado según el modo configurado."""
        if self.config.mode == MODO_HEURISTICO:
            resultado = self._heuristic_analyzer(datos_email)
            return _aplicar_umbral(resultado, self.config.threshold)

        resultado_neural = self._analyze_neural(datos_email)
        if self.config.mode == MODO_NEURAL:
            return _aplicar_umbral(resultado_neural, self.config.threshold)

        resultado_heur = self._heuristic_analyzer(datos_email)
        return construir_resultado_combinado(
            resultado_heur,
            resultado_neural,
            self.config,
        )

    def analyze_all(self, datos_email: dict) -> dict[str, dict]:
        """Devuelve las tres estrategias usando una misma normalización y modelo.

        La vista de detección necesita mostrar comparativamente sus resultados.
        Centralizar esta operación evita que esa vista vuelva a implementar la
        carga de modelos, el umbral o la fórmula de ponderación.
        """
        resultado_heur = _aplicar_umbral(
            self._heuristic_analyzer(datos_email), self.config.threshold
        )
        resultado_neural = _aplicar_umbral(
            self._analyze_neural(datos_email), self.config.threshold
        )
        resultado_combinado = construir_resultado_combinado(
            resultado_heur,
            resultado_neural,
            self.config,
        )
        return {
            "heuristico": resultado_heur,
            "neural": resultado_neural,
            "combinado": resultado_combinado,
        }

    def analyze_heuristic(self, datos_email: dict) -> dict:
        """Ejecuta únicamente las reglas, sin cargar el modelo neuronal."""
        return self._heuristic_analyzer(datos_email)

    def analyze_neural(self, datos_email: dict) -> dict:
        """Ejecuta únicamente el detector neuronal cacheado por idioma."""
        return self._analyze_neural(datos_email)

    def invalidate_detector(self, idioma: str | None = None) -> None:
        """Descarta modelos cacheados después de una actualización central.

        El backend reemplaza los artefactos de forma atómica y llama a este
        método para que la siguiente petición cargue la nueva versión. Los
        clientes nunca necesitan reiniciarse ni conocer rutas de ``.joblib``.
        """
        with self._detector_lock:
            if idioma is None:
                self._detectores.clear()
            else:
                self._detectores.pop(idioma, None)

    def detector_source(self, idioma: str) -> str | None:
        """Indica si el detector cacheado procede de artefacto o fallback."""
        with self._detector_lock:
            detector = self._detectores.get(idioma)
            return None if detector is None else getattr(detector, "source", None)

    def _analyze_neural(self, datos_email: dict) -> dict:
        """Selecciona y reutiliza el detector apropiado para cada idioma."""
        texto = construir_texto_para_analisis(datos_email)
        idioma = self._language_detector(texto)
        detector = self._detectores.get(idioma)
        if detector is None:
            # El servidor HTTP atiende en varios hilos; solo una petición debe
            # cargar el modelo de un idioma cuando llega la primera solicitud.
            with self._detector_lock:
                detector = self._detectores.get(idioma)
                if detector is None:
                    detector = self._detector_loader(self.config, idioma)
                    self._detectores[idioma] = detector
        return detector.analyze(
            texto,
            datos_email.get("from", ""),
            datos_email.get("subject", ""),
        )
