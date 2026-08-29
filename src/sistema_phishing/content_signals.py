"""Reglas basadas en texto visible y adjuntos.

Estas señales reflejan ingeniería social: urgencia, saludos genéricos,
peticiones de credenciales y referencias a documentos descargables.
"""

import re

from .configuracion import PALABRAS_URGENTES, SUBJECT_SOSPECHOSOS


def saludo_generico(texto: str) -> bool:
    """Detecta saludos o trato genéricos típicos de mensajes masivos o phishing."""
    # Los ataques masivos rara vez personalizan el saludo, por eso esta regla
    # busca fórmulas amplias como "estimado cliente".
    return bool(re.search(r"\b(estimado cliente|estimado usuario|estimado señor|estimada señora|a quien corresponda|cliente estimado|usuario estimado)\b", texto, flags=re.IGNORECASE))


def solicitud_datos_credenciales(texto: str) -> bool:
    """Detecta solicitudes directas de datos de acceso o credenciales en el mensaje."""
    return bool(re.search(r"\b(credenciales|contraseña|password|usuario|datos de acceso|iniciar sesión|inicie sesión|login|codigo de verificacion|código de verificación|verificación de seguridad)\b", texto, flags=re.IGNORECASE))


def cambio_datos_bancarios(texto: str) -> bool:
    """Detecta peticiones de sustituir datos bancarios o del beneficiario."""
    cambio = re.search(
        r"\b(cambi\w*|sustitu\w*|actualiz\w*|reemplaz\w*|nuev[oa]s?|"
        r"chang\w*|replac\w*|updat\w*|new)\b",
        texto,
        flags=re.IGNORECASE,
    )
    datos_bancarios = re.search(
        r"\b(iban|swift|cuenta bancaria|datos bancarios|beneficiari\w*|"
        r"bank account|bank details|banking details|beneficiar\w*|routing number)\b",
        texto,
        flags=re.IGNORECASE,
    )
    return bool(cambio and datos_bancarios)


def transferencia_urgente(texto: str) -> bool:
    """Detecta una orden urgente de transferencia o pago, en español o inglés."""
    operacion = re.search(
        r"\b(transferencia\w*|transfer\w*|pago\w*|payment\w*|wire)\b",
        texto,
        flags=re.IGNORECASE,
    )
    accion = re.search(
        r"\b(conf[ií]rm\w*|complet\w*|realiz\w*|proces\w*|ejecut\w*|"
        r"env[ií]\w*|autor[ií]z\w*|send\w*|make|pay|execut\w*|authori[sz]\w*)\b",
        texto,
        flags=re.IGNORECASE,
    )
    urgencia = re.search(
        r"\b(ahora|hoy|urgente\w*|inmediat\w*|antes de|"
        r"now|today|urgent\w*|immediate\w*|asap|before noon|end of day|eod)\b",
        texto,
        flags=re.IGNORECASE,
    )
    return bool(operacion and accion and urgencia)


def suplantacion_ejecutivo(texto: str) -> bool:
    """Detecta el pretexto de autoridad y aislamiento habitual en ataques BEC."""
    autoridad = re.search(
        r"\b(director(?:a)?|president(?:e|a)?|gerente|jefe|ceo|cfo|"
        r"finance director|chief executive|chief financial|boss)\b",
        texto,
        flags=re.IGNORECASE,
    )
    aislamiento = re.search(
        r"\b(reunid[oa]|no puedo atender|no (?:me )?llames|confidencial\w*|"
        r"en secreto|meeting|cannot (?:take|answer)|can't (?:take|answer)|"
        r"do not call|don't call|confidential\w*|secret\w*)\b",
        texto,
        flags=re.IGNORECASE,
    )
    return bool(autoridad and aislamiento)


def adjuntos_sospechosos(attachments: list[str]) -> bool:
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
