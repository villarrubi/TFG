"""Analizador principal que combina señalización y puntuación de riesgo."""

from typing import Dict

from .correo import CorreoAnalizado
from .explanations import ExplanationBuilder
from .scorer import RiskScorer
from .signal_builder import SignalBuilder


class PhishingAnalyzer:
    """Coordina las señales individuales y genera el informe final."""

    def __init__(
        self,
        correo: CorreoAnalizado,
        signal_builder: SignalBuilder | None = None,
        explanation_builder: ExplanationBuilder | None = None,
    ):
        # La inyección opcional de builders facilita probar o sustituir partes
        # del flujo sin modificar el coordinador principal.
        self.correo = correo
        self.signal_builder = signal_builder or SignalBuilder(correo)
        self.explanation_builder = explanation_builder or ExplanationBuilder()

    def analyze(self) -> Dict[str, object]:
        """Ejecuta todas las reglas, calcula riesgo y prepara datos para la UI."""
        signals = self.signal_builder.build()
        riesgo = RiskScorer.score(signals)
        # El resultado mantiene una estructura estable para que la UI pueda
        # pintar la misma tabla y los mismos campos aunque cambien las reglas.
        return {
            "is_phishing": riesgo >= 45,
            "risk_score": round(riesgo, 1),
            "signals": signals,
            "urls": self.correo.urls,
            "anchors": self.correo.anchors,
            "headers": self.correo.headers,
            "html_body": self.correo.html_body,
            "from": self.correo.from_address,
            "subject": self.correo.subject,
            "explanation": self.explanation_builder.build(signals),
        }
