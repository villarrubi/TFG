"""Reglas basadas en texto visible y adjuntos.

Estas señales reflejan ingeniería social: urgencia, saludos genéricos,
peticiones de credenciales y referencias a documentos descargables.
"""

import re
from typing import List

from .configuracion import PALABRAS_URGENTES, SUBJECT_SOSPECHOSOS


def saludo_generico(texto: str) -> bool:
    """Detecta saludos o trato genéricos típicos de mensajes masivos o phishing."""
    # Los ataques masivos rara vez personalizan el saludo, por eso esta regla
    # busca fórmulas amplias como "estimado cliente".
    return bool(re.search(r"\b(estimado cliente|estimado usuario|estimado señor|estimada señora|a quien corresponda|cliente estimado|usuario estimado)\b", texto, flags=re.IGNORECASE))


def solicitud_datos_credenciales(texto: str) -> bool:
    """Detecta solicitudes directas de datos de acceso o credenciales en el mensaje."""
    return bool(re.search(r"\b(credenciales|contraseña|password|usuario|datos de acceso|iniciar sesión|inicie sesión|login|codigo de verificacion|código de verificación|verificación de seguridad)\b", texto, flags=re.IGNORECASE))


def adjuntos_sospechosos(attachments: List[str]) -> bool:
    """Detecta adjuntos con extensiones sospechosas en el correo."""
    # La lista mezcla ejecutables, scripts, comprimidos y documentos con macros:
    # formatos habituales para ocultar malware o payloads.
    extensiones_peligrosas = [
        ".exe",
        ".scr",
        ".zip",
        ".rar",
        ".js",
        ".vbs",
        ".cmd",
        ".bat",
        ".docm",
        ".xlsm",
        ".pif",
        ".jar",
        ".eml",
    ]
    for nombre in attachments:
        if nombre:
            nombre_bajo = nombre.lower()
            for ext in extensiones_peligrosas:
                if nombre_bajo.endswith(ext):
                    return True
    return False


def contiene_palabras_urgentes(texto: str) -> bool:
    """Busca frases urgentes o de presión que suelen aparecer en phishing."""
    # Se convierte a minúsculas una vez para comparar con la lista de términos
    # definida en configuración.
    texto = texto.lower()
    return any(palabra in texto for palabra in PALABRAS_URGENTES)


def asunto_sospechoso(texto: str) -> bool:
    """Evalúa si el asunto del correo coincide con patrones típicos de phishing."""
    texto = texto.lower()
    return any(frase in texto for frase in SUBJECT_SOSPECHOSOS)


def contiene_referencia_archivo(texto: str) -> bool:
    """Detecta referencias a adjuntos o documentos típicos en correos de phishing."""
    return bool(re.search(r"\b(adjunto|archivo|documento|pdf|zip|xls|doc|docx)\b", texto, flags=re.IGNORECASE))
