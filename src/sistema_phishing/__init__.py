"""Módulo del sistema de detección de phishing para correos electrónicos."""

__all__ = [
    "analizar_correo",
    "extraer_urls",
    "parsear_eml_bytes",
    "parsear_eml_archivo",
    "NeuralPhishingClassifier",
    "NeuralModelTrainer",
    "NeuralPhishingDetector",
    "ModelStorage",
    "generar_dataset_sintetico",
]

from .analizador_email import parsear_eml_archivo, parsear_eml_bytes
from .heuristicas import analizar_correo, extraer_urls
from .neural import (
    ModelStorage,
    NeuralModelTrainer,
    NeuralPhishingClassifier,
    NeuralPhishingDetector,
    generar_dataset_sintetico,
)
