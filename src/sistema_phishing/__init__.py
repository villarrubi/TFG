"""Módulo del sistema de detección de phishing para correos electrónicos."""

__all__ = [
    "analizar_correo",
    "extraer_urls",
    "parsear_eml_bytes",
    "parsear_eml_archivo",
]

from .analizador_email import parsear_eml_archivo, parsear_eml_bytes
from .heuristicas import analizar_correo, extraer_urls
