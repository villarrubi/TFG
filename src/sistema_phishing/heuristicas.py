"""Fachada de heurísticas para el sistema de detección de phishing."""

from .analyzer import PhishingAnalyzer
from .signals import extraer_urls
from .correo import CorreoAnalizado


def analizar_correo(correo):
    """Analiza un correo y devuelve un informe de señales y riesgo.

    Esta función es la entrada pública del módulo heurístico: acepta tanto un
    texto plano como el diccionario generado por el parser de `.eml`.
    """
    # Primero se normaliza la entrada a una estructura común. Así el analizador
    # no necesita saber si el origen fue texto pegado o un fichero MIME.
    correo_analizado = CorreoAnalizado.from_input(correo)
    return PhishingAnalyzer(correo_analizado).analyze()
