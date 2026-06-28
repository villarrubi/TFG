"""Módulo para parsear correos electrónicos en formato EML y extraer campos útiles."""

import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Dict, List


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


def _extraer_anclas(html: str) -> List[Dict[str, str]]:
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


def parsear_eml_bytes(data: bytes) -> Dict[str, object]:
    """Parsea un mensaje EML pasado como bytes y devuelve los campos extraídos."""
    # `policy.default` decodifica cabeceras y cuerpos de forma más cómoda que la
    # política legacy, especialmente con asuntos o remitentes internacionalizados.
    msg = BytesParser(policy=policy.default).parsebytes(data)
    return _extraer_campos(msg)


def parsear_eml_archivo(ruta: str) -> Dict[str, object]:
    """Parsea un archivo .eml desde disco y devuelve los campos extraídos."""
    with open(ruta, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    return _extraer_campos(msg)


def _extraer_campos(msg) -> Dict[str, object]:
    """Extrae datos relevantes del objeto de correo parseado."""
    # Se separan cuerpo de texto, HTML, anclas y adjuntos porque cada familia de
    # reglas necesita mirar una representación distinta del mismo correo.
    cuerpo_texto = ""
    cuerpo_html = ""
    anclas = []
    attachments = []

    if msg.is_multipart():
        # Los mensajes reales suelen ser multipart: texto, HTML y adjuntos
        # viajan como partes separadas dentro del mismo .eml.
        for part in msg.walk():
            tipo = part.get_content_type()
            disposicion = part.get_content_disposition()
            if disposicion == "attachment":
                attachments.append(part.get_filename())
                continue
            try:
                contenido = part.get_content()
            except Exception:
                contenido = ""
            if tipo == "text/plain" and not cuerpo_texto:
                cuerpo_texto = str(contenido).strip()
            elif tipo == "text/html" and not cuerpo_html:
                cuerpo_html = str(contenido).strip()
    else:
        # Los correos no multipart solo tienen una representación principal.
        tipo = msg.get_content_type()
        contenido = msg.get_content()
        if tipo == "text/plain":
            cuerpo_texto = str(contenido).strip()
        elif tipo == "text/html":
            cuerpo_html = str(contenido).strip()

    if cuerpo_html and not cuerpo_texto:
        # Si solo existe versión HTML, se genera texto visible para que el
        # clasificador y las reglas de lenguaje puedan analizarlo.
        cuerpo_texto = _limpiar_html(cuerpo_html)
    if cuerpo_html:
        anclas = _extraer_anclas(cuerpo_html)

    headers = {k: v for k, v in msg.items()}
    # full_text conserva cabeceras relevantes junto al cuerpo para que las
    # heurísticas puedan trabajar con una representación plana del correo.
    full_text = _construir_texto_para_analisis(headers, cuerpo_texto)
    # Se extraen URLs del texto plano final; las URLs de anclas HTML se añaden
    # después al normalizar el correo en CorreoAnalizado.
    urls = re.findall(r"https?://[\w\-\.\:\/\?\#\&\=\%\+\;]+", full_text, flags=re.IGNORECASE)

    return {
        "subject": msg.get("subject", ""),
        "from": msg.get("from", ""),
        "to": msg.get("to", ""),
        "body": cuerpo_texto,
        "html_body": cuerpo_html,
        "headers": headers,
        "anchors": anclas,
        "attachments": attachments,
        "urls": urls,
        "full_text": full_text,
    }


def _construir_texto_para_analisis(headers: Dict[str, str], cuerpo: str) -> str:
    """Construye una representación plana del correo a partir de cabeceras y cuerpo."""
    partes: List[str] = []
    if headers.get("From"):
        partes.append(f"From: {headers['From']}")
    if headers.get("Reply-To"):
        partes.append(f"Reply-To: {headers['Reply-To']}")
    if headers.get("Subject"):
        partes.append(f"Subject: {headers['Subject']}")
    partes.append(cuerpo)
    return "\n".join(partes)


def construir_texto_para_analisis(datos: Dict[str, object]) -> str:
    """Devuelve el texto plano preparado para ser analizado por las heurísticas."""
    return datos.get("full_text", "")
