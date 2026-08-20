"""Reglas relacionadas con remitente, cabeceras y autenticación.

Estas funciones miran la parte técnica del correo: identidad declarada,
Return-Path, resultados SPF/DKIM/DMARC y ruta de entrega.
"""

import re
from email.utils import parseaddr

from .configuracion import KNOWN_BRAND_DOMAINS
from .url_utils import dominio_es_o_subdominio, extraer_dominio


def nombre_display_engano(from_header: str) -> bool:
    """Detecta cuando el nombre visible oculta otro correo o dominio.

    Un nombre personal normal no tiene por qué aparecer dentro de la dirección.
    La versión anterior marcaba por ello casi cualquier formato Nombre <correo>.
    """
    nombre, direccion = parseaddr(from_header or "")
    if not nombre or not direccion:
        return False

    email_visible = obtener_email_desde_cabecera(nombre)
    if email_visible:
        return email_visible != direccion.lower()

    dominio_visible = re.search(
        r"\b(?:https?://)?([\w.-]+\.[a-z]{2,})\b",
        nombre,
        flags=re.IGNORECASE,
    )
    if not dominio_visible:
        return False
    dominio_real = obtener_dominio_desde_email(direccion)
    return extraer_dominio(dominio_visible.group(1)) != dominio_real


def obtener_email_desde_cabecera(texto: str) -> str:
    """Extrae la primera dirección de correo válida encontrada en un texto."""
    _, direccion = parseaddr(texto or "")
    if direccion and "@" in direccion:
        return direccion.lower()
    match = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", texto or "")
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
    return bool(auth and re.search(r"(?i)\bdmarc=\s*(fail|permerror|temperror)\b", auth))


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
    return bool(received_spf and re.search(r"(?i)\b(fail|softfail|permerror|temperror)\b", received_spf))


def tiene_recibidos_sospechosos(texto: str) -> bool:
    """Busca patrones inusuales en las cabeceras Received que pueden indicar intermediarios sospechosos."""
    recibidos = re.findall(r"(?im)^received:\s*(.+)$", texto)
    for recibido in recibidos:
        # Las IP privadas son habituales en saltos internos legítimos. Se exige
        # un indicador explícito de origen no identificado para reducir ruido.
        if re.search(
            r"\b(?:unknown|anonymous|undisclosed)\b",
            recibido,
            flags=re.IGNORECASE,
        ):
            return True
    return False


def mensaje_firmado_o_cifrado(texto: str) -> bool:
    """Detecta si el mensaje contiene firmas o cifrado de correo (S/MIME o PGP)."""
    if re.search(r"(?im)^content-type:\s*(multipart/signed|application/(pkcs7-signature|pkcs7-mime|x-pkcs7-signature|pgp-signature|pgp-encrypted))", texto):
        return True
    return bool(re.search(r"-----BEGIN PGP (SIGNED MESSAGE|PGP MESSAGE)-----", texto))


def mensaje_id_sospechoso(texto: str, remitente: str) -> bool:
    """Detecta mensajes con Message-ID cuyo dominio no coincide con el dominio esperado del remitente."""
    message_id = obtener_cabecera(texto, "message-id")
    if not message_id or "@" not in message_id or "@" not in remitente:
        return False
    # El dominio del Message-ID suele pertenecer a la infraestructura del
    # remitente. Una divergencia no es concluyente, pero sí útil como señal.
    dominio_message_id = extraer_dominio(
        "http://" + message_id.split("@", 1)[1].strip(" <>")
    )
    dominio_remitente = obtener_dominio_desde_email(remitente)
    return bool(
        dominio_message_id
        and dominio_remitente
        and not dominio_es_o_subdominio(dominio_message_id, dominio_remitente)
        and not dominio_es_o_subdominio(dominio_remitente, dominio_message_id)
    )


def tiene_reply_to_diferente(texto: str) -> bool:
    """Detecta si Reply-To conduce a un dominio distinto del remitente."""
    enviar = obtener_cabecera(texto, "from")
    reply = obtener_cabecera(texto, "reply-to")
    if enviar and reply:
        dominio_from = obtener_dominio_desde_email(enviar)
        dominio_reply = obtener_dominio_desde_email(reply)
        return bool(
            dominio_from
            and dominio_reply
            and not dominio_es_o_subdominio(dominio_from, dominio_reply)
            and not dominio_es_o_subdominio(dominio_reply, dominio_from)
        )
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
    return bool(received_spf and enviar and re.search(
        r"(?i)domain of\s+[\w\.\-]+\s+does not designate", received_spf
    ))


def remitente_marca_engano(from_header: str) -> bool:
    """Detecta si el nombre del remitente usa una marca conocida pero la dirección de correo no."""
    nombre, direccion = parseaddr(from_header or "")
    dominio = obtener_dominio_desde_email(direccion)
    if not nombre or not dominio:
        return False
    nombre = nombre.lower()
    for marca, oficiales in KNOWN_BRAND_DOMAINS.items():
        if marca in nombre and not any(
            dominio_es_o_subdominio(dominio, oficial) for oficial in oficiales
        ):
            return True
    return False
