"""Fachada pública del subsistema neuronal.

El detalle de carga de datasets y entrenamiento vive en módulos separados para
mantener responsabilidades pequeñas sin romper la API importada por la app.
"""

# Se reexportan funciones privadas con su nombre anterior porque algunos tests
# o scripts de apoyo pueden depender de ellas mientras evoluciona el proyecto.
from .dataset import (
    cargar_dataset_csv,
    construir_texto_para_entrenamiento,
    encontrar_columna_etiqueta as _encontrar_columna_etiqueta,
    generar_dataset_sintetico,
    normalizar_etiqueta as _normalizar_etiqueta,
    obtener_campos_adicionales as _obtener_campos_adicionales,
    obtener_nombre_fuente as _obtener_nombre_fuente,
    obtener_texto_de_fila as _obtener_texto_de_fila,
)
from .modelo_neural import (
    HiperparametrosModelo,
    ModelStorage,
    NeuralModelTrainer,
    NeuralPhishingClassifier,
    NeuralPhishingDetector,
    TrainingStats,
    get_stop_words as _get_stop_words,
)

__all__ = [
    "HiperparametrosModelo",
    "ModelStorage",
    "NeuralModelTrainer",
    "NeuralPhishingClassifier",
    "NeuralPhishingDetector",
    "TrainingStats",
    "_encontrar_columna_etiqueta",
    "_get_stop_words",
    "_normalizar_etiqueta",
    "_obtener_campos_adicionales",
    "_obtener_nombre_fuente",
    "_obtener_texto_de_fila",
    "cargar_dataset_csv",
    "construir_texto_para_entrenamiento",
    "generar_dataset_sintetico",
]
