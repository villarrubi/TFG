"""Utilidades para extraer y evaluar URLs y dominios.

Este módulo concentra la lógica de enlaces para que las reglas HTML, cabeceras
y señalización general puedan reutilizar la misma interpretación de dominios.
"""

import ipaddress
import re
from urllib.parse import parse_qsl, unquote, urlsplit

from .configuracion import (
    BLACKLIST_DOMINIOS,
    DOMINIO_SOSPECHOSO,
    KNOWN_BRAND_DOMAINS,
    KNOWN_BRAND_TOKENS,
    SHORTENER_DOMINIOS,
    URL_PATTERN,
)


def extraer_urls(texto: str) -> list[str]:
    """Extrae todas las URLs HTTP/HTTPS encontradas en el texto proporcionado."""
    urls = re.findall(URL_PATTERN, texto or "", flags=re.IGNORECASE)
    # Los signos siguientes suelen cerrar una frase y no forman parte del URL.
    return list(dict.fromkeys(url.rstrip(".,;:!?)]}'\"") for url in urls))


def extraer_dominio(url: str) -> str:
    """Devuelve el hostname normalizado, sin credenciales ni puerto."""
    valor = (url or "").strip()
    if not valor:
        return ""
    candidato = valor if "://" in valor else f"http://{valor}"
    try:
        dominio = urlsplit(candidato).hostname or ""
    except ValueError:
        return ""
    return dominio.rstrip(".").lower()


def dominio_es_o_subdominio(dominio: str, esperado: str) -> bool:
    """Comprueba límites de etiqueta para evitar coincidencias por subcadena."""
    dominio = dominio.lower().rstrip(".")
    esperado = esperado.lower().rstrip(".")
    return dominio == esperado or dominio.endswith(f".{esperado}")


def es_dominio_listado_negro(url: str) -> bool:
    """Detecta si una URL pertenece a un dominio conocido de lista negra."""
    dominio = extraer_dominio(url)
    return any(
        dominio_es_o_subdominio(dominio, negro) or negro in dominio.split(".")[0]
        for negro in BLACKLIST_DOMINIOS
    )


def es_dominio_confuso(url: str) -> bool:
    """Detecta si un dominio contiene tokens de marca pero no es una URL oficial clara."""
    dominio = extraer_dominio(url)
    if not dominio:
        return False
    for marca, oficiales in KNOWN_BRAND_DOMAINS.items():
        if marca in dominio and not any(
            dominio_es_o_subdominio(dominio, oficial) for oficial in oficiales
        ):
            return True
    # Los tokens genéricos solo se buscan en la primera etiqueta para reducir
    # coincidencias accidentales en dominios legítimos.
    tokens_especificos = set(KNOWN_BRAND_DOMAINS)
    for token in set(KNOWN_BRAND_TOKENS) - tokens_especificos:
        if token in dominio.split(".")[0]:
            return True
    return False


def es_ip_enlace(url: str) -> bool:
    """Comprueba si la URL utiliza una dirección IP en lugar de un dominio."""
    dominio = extraer_dominio(url)
    try:
        ipaddress.ip_address(dominio)
    except ValueError:
        return False
    return True


def enlace_shortener(url: str) -> bool:
    """Detecta si una URL pertenece a un servicio de acortamiento conocido."""
    dominio = extraer_dominio(url)
    return any(dominio_es_o_subdominio(dominio, shortener) for shortener in SHORTENER_DOMINIOS)


def contiene_punycode_o_unicode(url: str) -> bool:
    """Detecta si el dominio de una URL está en punycode o contiene caracteres Unicode no ASCII."""
    dominio = extraer_dominio(url)
    # Punycode y caracteres no ASCII pueden usarse para homógrafos visuales,
    # por ejemplo dominios que se parecen a marcas conocidas.
    if any(etiqueta.startswith("xn--") for etiqueta in dominio.split(".")):
        return True
    try:
        dominio.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def tiene_parametros_sospechosos_url(url: str) -> bool:
    """Detecta parámetros que suelen ocultar redirecciones o URLs engañosas."""
    texto = (url or "").lower()
    # El patrón usuario@dominio puede esconder el destino real de la URL.
    if re.search(r"https?://[^/]*@[^/]+", texto):
        return True
    # Parámetros como redirect o next son habituales en enlaces de salto; si
    # contienen otra URL completa se consideran una señal de riesgo.
    try:
        query = urlsplit(texto).query
    except ValueError:
        query = ""
    claves_redireccion = {
        "continue",
        "dest",
        "destination",
        "next",
        "redirect",
        "redirect_to",
        "return",
        "url",
    }
    for clave, valor in parse_qsl(query, keep_blank_values=True):
        if clave.lower() in claves_redireccion:
            destino = unquote(valor).strip().lower()
            if destino.startswith(("http://", "https://", "//")):
                return True
    return False


def dominios_sospechosos(urls: list[str]) -> bool:
    """Comprueba si alguna URL apunta a dominios o patrones sospechosos."""
    for url in urls:
        dominio = extraer_dominio(url)
        # Las comprobaciones se ordenan de lo más barato a lo más específico.
        if any(palabra in dominio for palabra in DOMINIO_SOSPECHOSO):
            return True
        if es_ip_enlace(url):
            return True
        if "@" in url and re.search(r"https?://[^/]*@[^/]+", url.lower()):
            return True
        if es_dominio_listado_negro(url):
            return True
        if es_dominio_confuso(url):
            return True
        if contiene_punycode_o_unicode(url):
            return True
        if tiene_parametros_sospechosos_url(url):
            return True
    return False


def texto_contiene_dominio(texto: str) -> bool:
    """Detecta si un texto contiene un patrón parecido a un dominio web."""
    # Se usa para comparar el texto visible de un enlace con su href real.
    return bool(re.search(r"\b[\w.-]+\.(com|net|org|es|info|biz|online|xyz|club)\b", texto, flags=re.IGNORECASE))
