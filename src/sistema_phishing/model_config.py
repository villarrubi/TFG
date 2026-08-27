"""Contrato ligero de hiperparámetros compartido por clientes y backend.

Este módulo no importa scikit-learn ni joblib. Las interfaces pueden construir
y enviar una configuración de entrenamiento sin cargar la implementación del
modelo, que pertenece exclusivamente al backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ModelTrainingError(ValueError):
    """Indica que los datos o hiperparámetros no permiten entrenar el modelo."""


@dataclass
class HiperparametrosModelo:
    """Agrupa los hiperparámetros serializables del pipeline TF-IDF + MLP."""

    tfidf_ngram_range: tuple[int, int] = (1, 2)
    tfidf_max_features: int = 3000
    tfidf_min_df: int = 1
    mlp_hidden_layer_sizes: tuple[int, ...] = (64, 32)
    mlp_activation: str = "relu"
    mlp_alpha: float = 0.0001
    mlp_learning_rate_init: float = 0.001
    mlp_max_iter: int = 500
    mlp_early_stopping: bool = False
    mlp_random_state: int = 42

    def __post_init__(self) -> None:
        """Rechaza configuraciones que fallarían tarde dentro de scikit-learn."""
        minimo, maximo = self.tfidf_ngram_range
        if minimo < 1 or maximo < minimo:
            raise ModelTrainingError("El rango de n-gramas debe cumplir 1 <= mínimo <= máximo.")
        if self.tfidf_max_features < 1 or self.tfidf_min_df < 1:
            raise ModelTrainingError("max_features y min_df deben ser enteros positivos.")
        if not self.mlp_hidden_layer_sizes or any(
            capa < 1 for capa in self.mlp_hidden_layer_sizes
        ):
            raise ModelTrainingError("Las capas ocultas deben contener enteros positivos.")
        if self.mlp_activation not in {"identity", "logistic", "tanh", "relu"}:
            raise ModelTrainingError("La activación de la red neuronal no es válida.")
        if self.mlp_alpha < 0 or self.mlp_learning_rate_init <= 0 or self.mlp_max_iter < 1:
            raise ModelTrainingError("Los parámetros numéricos del MLP no son válidos.")


DEFAULT_HIPERPARAMETROS = HiperparametrosModelo()


def _entero_desde_env(clave: str, valor_por_defecto: int) -> int:
    try:
        return int(os.environ[clave])
    except (KeyError, ValueError):
        return valor_por_defecto


def _float_desde_env(clave: str, valor_por_defecto: float) -> float:
    try:
        return float(os.environ[clave])
    except (KeyError, ValueError):
        return valor_por_defecto


def _bool_desde_env(clave: str, valor_por_defecto: bool) -> bool:
    if clave not in os.environ:
        return valor_por_defecto
    return os.environ[clave].strip().lower() in {"1", "true", "si", "sí", "yes"}


def _tupla_enteros_desde_env(
    clave: str,
    valor_por_defecto: tuple[int, ...],
) -> tuple[int, ...]:
    """Lee algo como ``64,32`` desde el entorno y devuelve ``(64, 32)``."""
    valor = os.environ.get(clave, "")
    if not valor.strip():
        return valor_por_defecto
    try:
        return tuple(int(parte.strip()) for parte in valor.split(",") if parte.strip())
    except ValueError:
        return valor_por_defecto


def cargar_hiperparametros_desde_env() -> HiperparametrosModelo:
    """Construye la configuración de entrenamiento desde el entorno local."""
    base = DEFAULT_HIPERPARAMETROS
    return HiperparametrosModelo(
        tfidf_ngram_range=(
            _entero_desde_env("NEURAL_NGRAM_MIN", base.tfidf_ngram_range[0]),
            _entero_desde_env("NEURAL_NGRAM_MAX", base.tfidf_ngram_range[1]),
        ),
        tfidf_max_features=_entero_desde_env(
            "NEURAL_MAX_FEATURES", base.tfidf_max_features
        ),
        tfidf_min_df=_entero_desde_env("NEURAL_MIN_DF", base.tfidf_min_df),
        mlp_hidden_layer_sizes=_tupla_enteros_desde_env(
            "NEURAL_HIDDEN_LAYERS", base.mlp_hidden_layer_sizes
        ),
        mlp_activation=os.environ.get("NEURAL_ACTIVATION", base.mlp_activation),
        mlp_alpha=_float_desde_env("NEURAL_ALPHA", base.mlp_alpha),
        mlp_learning_rate_init=_float_desde_env(
            "NEURAL_LEARNING_RATE", base.mlp_learning_rate_init
        ),
        mlp_max_iter=_entero_desde_env("NEURAL_MAX_ITER", base.mlp_max_iter),
        mlp_early_stopping=_bool_desde_env(
            "NEURAL_EARLY_STOPPING", base.mlp_early_stopping
        ),
        mlp_random_state=base.mlp_random_state,
    )


__all__ = [
    "DEFAULT_HIPERPARAMETROS",
    "HiperparametrosModelo",
    "ModelTrainingError",
    "cargar_hiperparametros_desde_env",
]
