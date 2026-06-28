"""Reglas específicas para contenido HTML y anclas.

El HTML permite ocultar redirecciones, formularios y enlaces con texto visible
distinto del destino real; por eso se analiza separado del cuerpo plano.
"""

import re
from typing import Dict, List

from .configuracion import KNOWN_BRAND_TOKENS
from .url_utils import (
    es_dominio_confuso,
    es_dominio_listado_negro,
    es_ip_enlace,
    extraer_dominio,
    texto_contiene_dominio,
)


def contiene_meta_refresh(html: str) -> bool:
    """Detecta redirecciones automáticas mediante meta refresh en HTML."""
    # Los meta refresh pueden mandar al usuario a otra página sin interacción.
    return bool(re.search(r"(?i)<meta[^>]+http-equiv=['\"]refresh['\"]|<meta[^>]+content=['\"][^'\"]*url=", html))


def contiene_javascript_redireccion(html: str) -> bool:
    """Detecta redirecciones JavaScript ocultas o manipulación de location."""
    # Se buscan APIs habituales de redirección y ejecución dinámica.
    return bool(re.search(r"(?i)(window\.location|location\.href|document\.location|replace\(|eval\(|setTimeout\(|setInterval\(|location\.replace)", html))


def contiene_formulario_html(html: str) -> bool:
    """Detecta si el correo HTML contiene formularios con destinos sospechosos."""
    if not html:
        return False
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Si BeautifulSoup no está disponible, al menos se marca la presencia
        # de formularios para no perder por completo esa señal.
        return bool(re.search(r"<form\b.*?>", html, flags=re.IGNORECASE))

    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        action = form.get("action", "")
        # Formularios sin destino claro o con destino externo sospechoso son
        # relevantes porque pueden capturar credenciales directamente.
        if action:
            if "http" in action:
                if es_ip_enlace(action) or es_dominio_listado_negro(action) or es_dominio_confuso(action):
                    return True
            else:
                return True
        else:
            return True
    return False


def contiene_html_sospechoso(html: str) -> bool:
    """Detecta elementos HTML sospechosos que suelen usarse para ocultar phishing."""
    if not html:
        return False
    # iframe/base/javascript/data son técnicas frecuentes para ocultar contenido
    # externo, modificar URLs relativas o ejecutar código inesperado.
    if re.search(r"(?i)<iframe\b", html):
        return True
    if re.search(r"(?i)<base\b", html):
        return True
    if re.search(r"(?i)(href|src)=['\"]\s*(javascript:|data:)", html):
        return True
    return False


def texto_enlace_distinto(anchors: List[Dict[str, str]]) -> bool:
    """Detecta si el texto visible de un enlace difiere de la URL real del href."""
    for anchor in anchors:
        texto = anchor.get("text", "").strip().lower()
        href = anchor.get("href", "").strip().lower()
        if texto and href and href.startswith("http"):
            # Solo se compara dominio cuando el texto visible parece contener
            # una URL; si el texto es "pincha aquí" no hay dominio que contrastar.
            if texto_contiene_dominio(texto):
                if extraer_dominio(texto) != extraer_dominio(href):
                    return True
            if any(token in texto for token in KNOWN_BRAND_TOKENS) and texto_contiene_dominio(texto):
                if extraer_dominio(texto) != extraer_dominio(href):
                    return True
    return False


def formulario_action_sospechoso(html: str) -> bool:
    """Detecta formularios con acción vacía, relativa o dirigida a URLs sospechosas."""
    if not html:
        return False
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return bool(re.search(r"<form\b.*?>", html, flags=re.IGNORECASE))

    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        action = (form.get("action") or "").strip()
        # Una acción vacía, relativa o no HTTP resulta ambigua para un correo y
        # se marca como sospechosa.
        if not action:
            return True
        if action.startswith("/") or action.startswith("./") or action.startswith("../"):
            return True
        if not action.lower().startswith("http"):
            return True
        if es_ip_enlace(action) or es_dominio_listado_negro(action) or es_dominio_confuso(action):
            return True
    return False
