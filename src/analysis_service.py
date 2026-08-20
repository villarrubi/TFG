"""Compatibilidad para scripts antiguos que importaban ``analysis_service``.

La implementación mantenida vive en ``sistema_phishing.analysis_service``;
este módulo evita duplicar reglas y conserva la importación histórica.
"""

from sistema_phishing.analysis_service import (
    MODO_COMBINADO,
    MODO_HEURISTICO,
    MODO_NEURAL,
    VALID_MODES,
    AnalysisConfigurationError,
    EmailAnalysisService,
    cargar_detector_neural,
    construir_resultado_combinado,
    validar_configuracion,
)

__all__ = [
    "MODO_COMBINADO",
    "MODO_HEURISTICO",
    "MODO_NEURAL",
    "VALID_MODES",
    "AnalysisConfigurationError",
    "EmailAnalysisService",
    "cargar_detector_neural",
    "construir_resultado_combinado",
    "validar_configuracion",
]
