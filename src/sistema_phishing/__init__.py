"""Módulo del sistema de detección de phishing para correos electrónicos."""

# Este archivo define la superficie pública del paquete. Los módulos internos
# pueden cambiar por refactorizaciones, pero estos imports se mantienen estables
# para las aplicaciones Streamlit y para posibles usos externos.
__all__ = [
    "analizar_correo",
    "extraer_urls",
    "parsear_eml_bytes",
    "parsear_eml_archivo",
    "NeuralPhishingClassifier",
    "NeuralModelTrainer",
    "NeuralPhishingDetector",
    "ModelStorage",
    "SignalBuilder",
    "ExplanationBuilder",
    "AnalysisBackendConfig",
    "AnalysisBackendService",
    "generar_dataset_sintetico",
]

from .analizador_email import parsear_eml_archivo, parsear_eml_bytes
from .backend_service import AnalysisBackendConfig, AnalysisBackendService
from .explanations import ExplanationBuilder
from .heuristicas import analizar_correo, extraer_urls
from .neural import (
    ModelStorage,
    NeuralModelTrainer,
    NeuralPhishingClassifier,
    NeuralPhishingDetector,
    generar_dataset_sintetico,
)
from .signal_builder import SignalBuilder
