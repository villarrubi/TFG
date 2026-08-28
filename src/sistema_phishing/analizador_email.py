"""Módulo para parsear correos electrónicos en formato EML y extraer campos útiles."""

import re
from email import policy
from email.message import Message
from email.parser import BytesParser
from html.parser import HTMLParser

from .url_utils import extraer_urls

MAX_EMAIL_BYTES = 10 * 1024 * 1024


class EmailParseError(ValueError):
    """Indica que un mensaje no puede analizarse de forma segura."""


def _texto_unicode_seguro(valor: object) -> str:
    """Normaliza cabeceras SMTPUTF8 o defectuosas a texto JSON válido."""
    texto = str(valor)
    try:
        texto.encode("utf-8")
    except UnicodeEncodeError:
        # email.parser conserva bytes UTF-8 no conformes como surrogateescape.
        # Se recuperan cuando es posible y cualquier secuencia rota se sustituye.
        texto = texto.encode("utf-8", "surrogateescape").decode(
            "utf-8", "replace"
        )
    return texto


def _limpiar_html(html: str) -> str:
    """Extrae texto visible de HTML eliminando etiquetas y normalizando espacios."""
    class HTMLTextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []

        def handle_data(self, data):
            # Guarda el texto plano encontrado entre etiquetas HTML.
            self.text.append(data)

        def handle_entityref(self, name):
            # Convierte entidades HTML como &amp; en su representación de texto.
            self.text.append(self.unescape(f"&{name};"))

        def handle_charref(self, name):
            # Convierte referencias de caracteres numéricos en texto legible.
            self.text.append(self.unescape(f"&#{name};"))

    extractor = HTMLTextExtractor()
    extractor.feed(html)
    texto = "".join(extractor.text)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _extraer_anclas(html: str) -> list[dict[str, str]]:
    """Extrae los enlaces <a> de un HTML y devuelve su texto y href."""
    class AnchorExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.anchors = []
            self.current_href = None
            self.current_text = []

        def handle_starttag(self, tag, attrs):
            # Detecta el inicio de un enlace y almacena el valor href.
            if tag.lower() == "a":
                self.current_href = None
                self.current_text = []
                for name, value in attrs:
                    if name.lower() == "href":
                        self.current_href = value.strip()

        def handle_data(self, data):
            # Acumula el texto visible dentro del enlace mientras se está parseando.
            if self.current_href is not None:
                self.current_text.append(data)

        def handle_endtag(self, tag):
            # Cuando finaliza la etiqueta <a>, registra la ancla con texto y URL.
            if tag.lower() == "a" and self.current_href is not None:
                texto = "".join(self.current_text).strip()
                self.anchors.append({"text": texto, "href": self.current_href})
                self.current_href = None
                self.current_text = []

    extractor = AnchorExtractor()
    extractor.feed(html)
    return extractor.anchors


def parsear_eml_bytes(data: bytes) -> dict[str, object]:
    """Parsea un mensaje EML pasado como bytes y devuelve los campos extraídos."""
    if not isinstance(data, bytes):
        raise TypeError("El mensaje EML debe proporcionarse como bytes.")
    if not data:
        raise EmailParseError("El archivo EML está vacío.")
    if len(data) > MAX_EMAIL_BYTES:
        raise EmailParseError(
            f"El archivo EML supera el límite de {MAX_EMAIL_BYTES // (1024 * 1024)} MB."
        )
    # `policy.default` decodifica cabeceras y cuerpos de forma más cómoda que la
    # política legacy, especialmente con asuntos o remitentes internacionalizados.
    msg = BytesParser(policy=policy.default).parsebytes(data)
    return _extraer_campos(msg)


def parsear_eml_archivo(ruta: str) -> dict[str, object]:
    """Parsea un archivo .eml desde disco y devuelve los campos extraídos."""
    # Se lee como máximo un byte más que el límite para poder distinguir un
    # archivo válido de uno demasiado grande sin cargarlo completo en memoria.
    # Así la entrada desde disco aplica exactamente la misma política que la
    # entrada recibida por HTTP o Streamlit.
    try:
        with open(ruta, "rb") as f:
            data = f.read(MAX_EMAIL_BYTES + 1)
    except OSError as exc:
        raise EmailParseError("No se pudo leer el archivo EML.") from exc
    return parsear_eml_bytes(data)


def _contenido_seguro(part: Message) -> str:
    """Obtiene el contenido de una parte MIME tolerando partes no decodificables."""
    try:
        return str(part.get_content())
    except (AttributeError, LookupError, TypeError, UnicodeError):
        return ""


def _extraer_partes_mime(msg: Message) -> dict[str, object]:
    """Separa texto, HTML y adjuntos de un mensaje MIME."""
    cuerpo_texto = ""
    cuerpo_html = ""
    attachments = []

    if msg.is_multipart():
        # Los mensajes reales suelen ser multipart: texto, HTML y adjuntos
        # viajan como partes separadas dentro del mismo .eml.
        for part in msg.walk():
            tipo = part.get_content_type()
            disposicion = part.get_content_disposition()
            if disposicion == "attachment":
                attachments.append(part.get_filename() or "(adjunto sin nombre)")
                continue
            contenido = _contenido_seguro(part)
            if tipo == "text/plain" and not cuerpo_texto:
                cuerpo_texto = contenido.strip()
            elif tipo == "text/html" and not cuerpo_html:
                cuerpo_html = contenido.strip()
    else:
        # Los correos no multipart solo tienen una representación principal.
        tipo = msg.get_content_type()
        contenido = _contenido_seguro(msg)
        if tipo == "text/plain":
            cuerpo_texto = contenido.strip()
        elif tipo == "text/html":
            cuerpo_html = contenido.strip()

    return {
        "body": cuerpo_texto,
        "html_body": cuerpo_html,
        "attachments": attachments,
    }


def _agrupar_cabeceras(msg: Message) -> dict[str, str]:
    """Conserva cabeceras repetidas sin perder saltos Received o Authentication."""
    cabeceras: dict[str, list[str]] = {}
    for nombre, valor in msg.raw_items():
        limpio = " ".join(_texto_unicode_seguro(valor).splitlines()).strip()
        cabeceras.setdefault(nombre, []).append(limpio)
    return {nombre: "\n".join(valores) for nombre, valores in cabeceras.items()}


def _extraer_campos(msg: Message) -> dict[str, object]:
    """Extrae datos relevantes del objeto de correo parseado."""
    # Se separan cuerpo de texto, HTML, anclas y adjuntos porque cada familia de
    # reglas necesita mirar una representación distinta del mismo correo.
    partes_mime = _extraer_partes_mime(msg)
    cuerpo_texto = partes_mime["body"]
    cuerpo_html = partes_mime["html_body"]
    attachments = partes_mime["attachments"]
    anclas = []

    if cuerpo_html and not cuerpo_texto:
        # Si solo existe versión HTML, se genera texto visible para que el
        # clasificador y las reglas de lenguaje puedan analizarlo.
        cuerpo_texto = _limpiar_html(cuerpo_html)
    if cuerpo_html:
        anclas = _extraer_anclas(cuerpo_html)

    headers = _agrupar_cabeceras(msg)
    # Se conservan todas las cabeceras: SPF, DKIM, DMARC, Return-Path,
    # Message-ID y Received son parte esencial de las reglas técnicas.
    full_text = _construir_texto_para_analisis(msg.raw_items(), cuerpo_texto)
    # Se extraen URLs del texto plano final; las URLs de anclas HTML se añaden
    # después al normalizar el correo en CorreoAnalizado.
    urls = extraer_urls(full_text)

    return {
        # policy.default devuelve objetos de cabecera enriquecidos. Convertirlos
        # aquí garantiza que el resultado completo sea JSON-serializable cuando
        # el monitor lo envía al backend cliente-servidor.
        "subject": _texto_unicode_seguro(msg.get("subject", "") or ""),
        "from": _texto_unicode_seguro(msg.get("from", "") or ""),
        "to": _texto_unicode_seguro(msg.get("to", "") or ""),
        "body": cuerpo_texto,
        "html_body": cuerpo_html,
        "headers": headers,
        "anchors": anclas,
        "attachments": attachments,
        "urls": urls,
        "full_text": full_text,
    }


def _construir_texto_para_analisis(
    headers,
    cuerpo: str,
) -> str:
    """Construye una representación plana del correo a partir de cabeceras y cuerpo."""
    items = headers.items() if isinstance(headers, dict) else headers
    partes = [
        f"{nombre}: {' '.join(_texto_unicode_seguro(valor).splitlines()).strip()}"
        for nombre, valor in items
        if valor is not None
    ]
    if cuerpo:
        partes.append(cuerpo)
    return "\n".join(partes)


def construir_texto_para_analisis(datos: dict[str, object]) -> str:
    """Devuelve una representación completa aunque el origen no sea un EML."""
    full_text = str(datos.get("full_text", "") or "").strip()
    if full_text:
        return full_text
    headers = datos.get("headers", {})
    if not isinstance(headers, dict):
        headers = {}
    return _construir_texto_para_analisis(
        headers,
        str(datos.get("body", "") or ""),
    )
