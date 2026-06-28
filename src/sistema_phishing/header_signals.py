"""Reglas relacionadas con remitente, cabeceras y autenticación.

Estas funciones miran la parte técnica del correo: identidad declarada,
Return-Path, resultados SPF/DKIM/DMARC y ruta de entrega.
"""

import re

from .configuracion import KNOWN_BRAND_TOKENS
from .url_utils import extraer_dominio


def nombre_display_engano(from_header: str) -> bool:
    """Determina si el nombre visible del remitente es diferente de la dirección real."""
    if "<" in from_header and ">" in from_header:
        # Ejemplo sospechoso: "Banco Real <alerta@dominio-externo.com>".
        nombre = from_header.split("<", 1)[0].strip().lower()
        direccion = from_header.split("<", 1)[1].split(">", 1)[0].strip().lower()
        if nombre and direccion and nombre not in direccion:
            if "@" in direccion:
                return True
    return False


def obtener_email_desde_cabecera(texto: str) -> str:
    """Extrae la primera dirección de correo válida encontrada en un texto."""
    match = re.search(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", texto)
    return match.group(0).lower() if match else ""


def obtener_cabecera(texto: str, nombre: str) -> str:
    """Extrae el valor de una cabecera específica del texto del correo."""
    # La búsqueda es case-insensitive y multilinea para tolerar correos pegados
    # manualmente con cabeceras en distinto formato.
    match = re.search(rf"(?im)^{re.escape(nombre)}:\s*(.+)$", texto)
    return match.group(1).strip() if match else ""


def obtener_dominio_desde_email(texto: str) -> str:
    """Devuelve solo el dominio de la primera dirección encontrada."""
    email = obtener_email_desde_cabecera(texto)
    if not email or "@" not in email:
        return ""
    return extraer_dominio("http://" + email.split("@", 1)[1])


def extraer_dominio_spf(received_spf: str) -> str:
    """Extrae el dominio declarado en una cabecera Received-SPF fallida."""
    match = re.search(r"domain of\s+([\w\.-]+)\s+does", received_spf, flags=re.IGNORECASE)
    return match.group(1).lower() if match else ""


def dkim_mal_formado(texto: str) -> bool:
    """Comprueba si DKIM-Signature existe pero carece de campos obligatorios."""
    signature = obtener_cabecera(texto, "dkim-signature")
    if not signature:
        return False
    # Una firma DKIM incompleta no prueba phishing por sí sola, pero sí aporta
    # sospecha cuando se combina con otras incoherencias.
    required = ["v=", "a=", "d=", "s=", "b=", "h="]
    signature_lower = signature.lower()
    return not all(tag in signature_lower for tag in required)


def dmarc_fallido(texto: str) -> bool:
    """Detecta resultados DMARC de fallo en Authentication-Results."""
    auth = obtener_cabecera(texto, "authentication-results")
    if auth and re.search(r"(?i)\bdmarc=\s*(fail|permerror|temperror)\b", auth):
        return True
    return False


def incoherencia_remitente(texto: str) -> bool:
    """Compara dominios de From, Return-Path y Received-SPF."""
    remitente = obtener_cabecera(texto, "from")
    return_path = obtener_cabecera(texto, "return-path")
    if remitente and return_path:
        # From es lo que ve el usuario; Return-Path identifica el canal técnico
        # de rebotes. Si no coinciden los dominios, aumenta la sospecha.
        dominio_from = obtener_dominio_desde_email(remitente)
        dominio_return = obtener_dominio_desde_email(return_path)
        if dominio_from and dominio_return and dominio_from != dominio_return:
            return True

    received_spf = obtener_cabecera(texto, "received-spf")
    if received_spf and remitente:
        dominio_spf = extraer_dominio_spf(received_spf)
        dominio_from = obtener_dominio_desde_email(remitente)
        if dominio_spf and dominio_from and dominio_spf != dominio_from:
            return True
    return False


def tiene_fallo_autenticacion(texto: str) -> bool:
    """Detecta fallos en SPF, DKIM o DMARC a partir de las cabeceras de autenticación."""
    auth = obtener_cabecera(texto, "authentication-results")
    arc = obtener_cabecera(texto, "arc-authentication-results")
    received_spf = obtener_cabecera(texto, "received-spf")

    # Se agrupan SPF, DKIM y DMARC en una sola expresión porque todos comparten
    # estados de fallo parecidos en las cabeceras.
    fallo_regex = re.compile(r"(?i)\b(spf|dkim|dmarc)=\s*(fail|softfail|permerror|temperror)\b")
    if auth and fallo_regex.search(auth):
        return True
    if arc and fallo_regex.search(arc):
        return True
    if received_spf and re.search(r"(?i)\b(fail|softfail|permerror|temperror)\b", received_spf):
        return True
    return False


def tiene_recibidos_sospechosos(texto: str) -> bool:
    """Busca patrones inusuales en las cabeceras Received que pueden indicar intermediarios sospechosos."""
    recibidos = re.findall(r"(?im)^received:\s*(.+)$", texto)
    for recibido in recibidos:
        # Direcciones privadas o localhost en Received pueden indicar reenvíos,
        # pruebas internas o rutas poco confiables para un correo externo.
        if re.search(r"\b(127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+)\b", recibido):
            return True
        if re.search(r"\b(localhost|unknown|anonymous|undisclosed|relay)\b", recibido, flags=re.IGNORECASE):
            return True
    return False


def mensaje_firmado_o_cifrado(texto: str) -> bool:
    """Detecta si el mensaje contiene firmas o cifrado de correo (S/MIME o PGP)."""
    if re.search(r"(?im)^content-type:\s*(multipart/signed|application/(pkcs7-signature|pkcs7-mime|x-pkcs7-signature|pgp-signature|pgp-encrypted))", texto):
        return True
    if re.search(r"-----BEGIN PGP (SIGNED MESSAGE|PGP MESSAGE)-----", texto):
        return True
    return False


def mensaje_id_sospechoso(texto: str, remitente: str) -> bool:
    """Detecta mensajes con Message-ID cuyo dominio no coincide con el dominio esperado del remitente."""
    message_id = obtener_cabecera(texto, "message-id")
    if not message_id or "@" not in message_id or "@" not in remitente:
        return False
    # El dominio del Message-ID suele pertenecer a la infraestructura del
    # remitente. Una divergencia no es concluyente, pero sí útil como señal.
    dominio_message_id = extraer_dominio("http://" + message_id.split("@", 1)[1].strip(" <>") )
    dominio_remitente = extraer_dominio("http://" + obtener_email_desde_cabecera(remitente).split("@", 1)[1]) if obtener_email_desde_cabecera(remitente) else ""
    return dominio_message_id and dominio_remitente and dominio_message_id != dominio_remitente


def tiene_reply_to_diferente(texto: str) -> bool:
    """Detecta si la cabecera Reply-To difiere de From, una señal frecuente de suplantación."""
    enviar = obtener_cabecera(texto, "from")
    reply = obtener_cabecera(texto, "reply-to")
    if enviar and reply:
        email_from = obtener_email_desde_cabecera(enviar)
        email_reply = obtener_email_desde_cabecera(reply)
        return email_from and email_reply and email_from != email_reply
    return False


def cabecera_spoofing(texto: str) -> bool:
    """Detecta si cabeceras como Return-Path no coinciden con From o Received-SPF indica incoherencias."""
    enviar = obtener_cabecera(texto, "from")
    return_path = obtener_cabecera(texto, "return-path")
    if enviar and return_path:
        email_from = obtener_email_desde_cabecera(enviar)
        email_return = obtener_email_desde_cabecera(return_path)
        if email_from and email_return and email_from != email_return:
            return True

    received_spf = obtener_cabecera(texto, "received-spf")
    if received_spf and enviar:
        if re.search(r"(?i)domain of\s+[\w\.\-]+\s+does not designate", received_spf):
            return True
    return False


def remitente_marca_engano(from_header: str) -> bool:
    """Detecta si el nombre del remitente usa una marca conocida pero la dirección de correo no."""
    if "<" in from_header and ">" in from_header:
        # Se comprueba el nombre visible frente a la dirección real para detectar
        # suplantaciones sencillas de marcas conocidas.
        nombre = from_header.split("<", 1)[0].strip().lower()
        direccion = from_header.split("<", 1)[1].split(">", 1)[0].strip().lower()
        for token in KNOWN_BRAND_TOKENS:
            if token in nombre and token not in direccion:
                return True
    return False
