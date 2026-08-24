"""Superficie pública del sistema de detección de phishing.

Los símbolos se cargan cuando se solicitan. Así un consumidor heurístico no
importa scikit-learn ni los modelos neuronales durante el arranque.
"""

from importlib import import_module

__all__ = [
    "AnalysisBackendConfig",
    "AnalysisBackendService",
    "ClassificationMetrics",
    "ExplanationBuilder",
    "ModelStorage",
    "NeuralModelTrainer",
    "NeuralPhishingClassifier",
    "NeuralPhishingDetector",
    "SignalBuilder",
    "analizar_correo",
    "calcular_metricas_clasificacion",
    "extraer_urls",
    "generar_dataset_sintetico",
    "parsear_eml_archivo",
    "parsear_eml_bytes",
]

_EXPORTS = {
    "AnalysisBackendConfig": (".backend_service", "AnalysisBackendConfig"),
    "AnalysisBackendService": (".backend_service", "AnalysisBackendService"),
    "ClassificationMetrics": (".metrics", "ClassificationMetrics"),
    "ExplanationBuilder": (".explanations", "ExplanationBuilder"),
    "ModelStorage": (".neural", "ModelStorage"),
    "NeuralModelTrainer": (".neural", "NeuralModelTrainer"),
    "NeuralPhishingClassifier": (".neural", "NeuralPhishingClassifier"),
    "NeuralPhishingDetector": (".neural", "NeuralPhishingDetector"),
    "SignalBuilder": (".signal_builder", "SignalBuilder"),
    "analizar_correo": (".heuristicas", "analizar_correo"),
    "calcular_metricas_clasificacion": (".metrics", "calcular_metricas_clasificacion"),
    "extraer_urls": (".heuristicas", "extraer_urls"),
    "generar_dataset_sintetico": (".neural", "generar_dataset_sintetico"),
    "parsear_eml_archivo": (".analizador_email", "parsear_eml_archivo"),
    "parsear_eml_bytes": (".analizador_email", "parsear_eml_bytes"),
}


def __getattr__(name: str):
    """Resuelve y cachea una exportación pública en su primer acceso."""
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Incluye las exportaciones diferidas en herramientas de introspección."""
    return sorted(set(globals()) | set(__all__))
