"""Fachada pública del subsistema neuronal.

El detalle de carga de datasets y entrenamiento vive en módulos separados para
mantener responsabilidades pequeñas sin romper la API importada por la app.
"""

# Se reexportan funciones privadas con su nombre anterior porque algunos tests
# o scripts de apoyo pueden depender de ellas mientras evoluciona el proyecto.
from .dataset import (
    cargar_dataset_csv,
    construir_texto_para_entrenamiento,
    generar_dataset_sintetico,
)
from .dataset import (
    encontrar_columna_etiqueta as _encontrar_columna_etiqueta,
)
from .dataset import (
    normalizar_etiqueta as _normalizar_etiqueta,
)
from .dataset import (
    obtener_campos_adicionales as _obtener_campos_adicionales,
)
from .dataset import (
    obtener_nombre_fuente as _obtener_nombre_fuente,
)
from .dataset import (
    obtener_texto_de_fila as _obtener_texto_de_fila,
)
from .modelo_neural import (
    HiperparametrosModelo,
    ModelStorage,
    NeuralModelTrainer,
    NeuralPhishingClassifier,
    NeuralPhishingDetector,
    TrainingStats,
)
from .modelo_neural import (
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
