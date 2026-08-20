"""Métricas independientes para evaluar clasificadores binarios de phishing."""

from collections.abc import Sequence
from dataclasses import dataclass


def _division_segura(numerador: int, denominador: int) -> float:
    return numerador / denominador if denominador else 0.0


@dataclass(frozen=True)
class ClassificationMetrics:
    """Resume la matriz de confusión y las métricas derivadas.

    La clase positiva es phishing (1) y la negativa es correo legítimo (0).
    """

    verdaderos_positivos: int
    verdaderos_negativos: int
    falsos_positivos: int
    falsos_negativos: int

    @property
    def total(self) -> int:
        return (
            self.verdaderos_positivos
            + self.verdaderos_negativos
            + self.falsos_positivos
            + self.falsos_negativos
        )

    @property
    def phishing_reales(self) -> int:
        return self.verdaderos_positivos + self.falsos_negativos

    @property
    def legitimos_reales(self) -> int:
        return self.verdaderos_negativos + self.falsos_positivos

    @property
    def accuracy(self) -> float:
        aciertos = self.verdaderos_positivos + self.verdaderos_negativos
        return _division_segura(aciertos, self.total)

    @property
    def precision(self) -> float:
        positivos_predichos = self.verdaderos_positivos + self.falsos_positivos
        return _division_segura(self.verdaderos_positivos, positivos_predichos)

    @property
    def recall(self) -> float:
        return _division_segura(self.verdaderos_positivos, self.phishing_reales)

    @property
    def f1(self) -> float:
        return _division_segura(
            2 * self.verdaderos_positivos,
            2 * self.verdaderos_positivos + self.falsos_positivos + self.falsos_negativos,
        )

    @property
    def especificidad(self) -> float:
        return _division_segura(self.verdaderos_negativos, self.legitimos_reales)

    @property
    def balanced_accuracy(self) -> float:
        return (self.recall + self.especificidad) / 2


def calcular_metricas_clasificacion(
    etiquetas_reales: Sequence[int],
    predicciones: Sequence[int],
) -> ClassificationMetrics:
    """Calcula métricas binarias y valida que ambas series sean comparables."""
    reales = list(etiquetas_reales)
    predichas = list(predicciones)
    if len(reales) != len(predichas):
        raise ValueError("Las etiquetas reales y las predicciones deben tener igual longitud.")
    if len(reales) == 0:
        raise ValueError("No hay ejemplos con los que calcular métricas.")
    if any(valor not in {0, 1} for valor in reales + predichas):
        raise ValueError("Las métricas binarias solo admiten las etiquetas 0 y 1.")

    pares = zip(predichas, reales)
    verdaderos_positivos = sum(pred == 1 and real == 1 for pred, real in pares)
    pares = zip(predichas, reales)
    verdaderos_negativos = sum(pred == 0 and real == 0 for pred, real in pares)
    pares = zip(predichas, reales)
    falsos_positivos = sum(pred == 1 and real == 0 for pred, real in pares)
    pares = zip(predichas, reales)
    falsos_negativos = sum(pred == 0 and real == 1 for pred, real in pares)

    return ClassificationMetrics(
        verdaderos_positivos=verdaderos_positivos,
        verdaderos_negativos=verdaderos_negativos,
        falsos_positivos=falsos_positivos,
        falsos_negativos=falsos_negativos,
    )
