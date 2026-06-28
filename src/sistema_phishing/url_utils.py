"""Utilidades para extraer y evaluar URLs y dominios.

Este módulo concentra la lógica de enlaces para que las reglas HTML, cabeceras
y señalización general puedan reutilizar la misma interpretación de dominios.
"""

import re
from typing import List

from .configuracion import (
    BLACKLIST_DOMINIOS,
    DOMINIO_SOSPECHOSO,
    KNOWN_BRAND_TOKENS,
    SHORTENER_DOMINIOS,
    URL_PATTERN,
)


def extraer_urls(texto: str) -> List[str]:
    """Extrae todas las URLs HTTP/HTTPS encontradas en el texto proporcionado."""
    return re.findall(URL_PATTERN, texto, flags=re.IGNORECASE)


def extraer_dominio(url: str) -> str:
    """Devuelve el dominio principal de una URL, sin protocolo ni parámetros."""
    # No se usa un parser de URL completo porque en correos sospechosos aparecen
    # URLs incompletas o malformadas; esta extracción tolerante basta para las
    # heurísticas del prototipo.
    dominio = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    dominio = dominio.split("/")[0]
    dominio = dominio.split("?")[0]
    return dominio.lower().strip(".")


def es_dominio_listado_negro(url: str) -> bool:
    """Detecta si una URL pertenece a un dominio conocido de lista negra."""
    dominio = extraer_dominio(url)
    return any(negro in dominio for negro in BLACKLIST_DOMINIOS)


def es_dominio_confuso(url: str) -> bool:
    """Detecta si un dominio contiene tokens de marca pero no es una URL oficial clara."""
    dominio = extraer_dominio(url)
    # Regla simple de prototipo: marca en subdominio/dominio combinado suele ser
    # sospechosa cuando no coincide con dominios oficiales básicos.
    for token in KNOWN_BRAND_TOKENS:
        if token in dominio and token + ".com" not in dominio and token + ".es" not in dominio:
            return True
    return False


def es_ip_enlace(url: str) -> bool:
    """Comprueba si la URL utiliza una dirección IP en lugar de un dominio."""
    dominio = extraer_dominio(url)
    return bool(re.match(r"^(\d{1,3}\.){3}\d{1,3}$", dominio))


def enlace_shortener(url: str) -> bool:
    """Detecta si una URL pertenece a un servicio de acortamiento conocido."""
    dominio = extraer_dominio(url)
    return any(shortener in dominio for shortener in SHORTENER_DOMINIOS)


def contiene_punycode_o_unicode(url: str) -> bool:
    """Detecta si el dominio de una URL está en punycode o contiene caracteres Unicode no ASCII."""
    dominio = extraer_dominio(url)
    # Punycode y caracteres no ASCII pueden usarse para homógrafos visuales,
    # por ejemplo dominios que se parecen a marcas conocidas.
    if dominio.startswith("xn--"):
        return True
    try:
        dominio.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def tiene_parametros_sospechosos_url(url: str) -> bool:
    """Detecta parámetros que suelen ocultar redirecciones o URLs engañosas."""
    texto = url.lower()
    # El patrón usuario@dominio puede esconder el destino real de la URL.
    if re.search(r"https?://[^/]*@[^/]+", texto):
        return True
    # Parámetros como redirect o next son habituales en enlaces de salto; si
    # contienen otra URL completa se consideran una señal de riesgo.
    if re.search(r"\b(?:redirect|redirect_to|url|next|continue|return|verify|token|session)=https?://", texto):
        return True
    return False


def dominios_sospechosos(urls: List[str]) -> bool:
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
