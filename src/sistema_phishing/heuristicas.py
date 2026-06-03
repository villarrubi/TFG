"""Módulo de heurísticas para la detección de phishing en correos electrónicos."""

import re
from typing import Dict, List, Union

PALABRAS_URGENTES = [
    "urgente",
    "inmediato",
    "actualiza",
    "actualizar",
    "verificar",
    "verifica",
    "credenciales",
    "bloqueado",
    "alerta",
    "seguridad",
    "sanción",
    "problema",
    "acción requerida",
    "pago",
    "factura",
    "comisión",
    "suspendido",
    "reenviar",
]

SUBJECT_SOSPECHOSOS = [
    "verifica tu cuenta",
    "actualiza tu cuenta",
    "bloqueado",
    "compte suspendu",
    "confirmar sesión",
    "problema con su cuenta",
    "revisa tu cuenta",
    "actualización necesaria",
]

URL_PATTERN = r"https?://[\w\-\.\:\/\?\#\&\=\%\+\;]+"
DOMINIO_SOSPECHOSO = [
    "login",
    "secure",
    "account",
    "update",
    "verify",
    "webscr",
    "confirm",
    "bank",
    "securepay",
    "signin",
    "cliente",
    "factura",
    "servicio",
]
SHORTENER_DOMINIOS = [
    "bit.ly",
    "tinyurl.com",
    "goo.gl",
    "t.co",
    "ow.ly",
    "is.gd",
    "buff.ly",
]


def extraer_urls(texto: str) -> List[str]:
    """Extrae todas las URLs HTTP/HTTPS encontradas en el texto proporcionado."""
    return re.findall(URL_PATTERN, texto, flags=re.IGNORECASE)


def extraer_dominio(url: str) -> str:
    """Devuelve el dominio principal de una URL, sin protocolo ni parámetros."""
    dominio = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    dominio = dominio.split("/")[0]
    dominio = dominio.split("?")[0]
    return dominio.lower().strip(".")


def es_ip_enlace(url: str) -> bool:
    """Comprueba si la URL utiliza una dirección IP en lugar de un dominio."""
    dominio = extraer_dominio(url)
    return bool(re.match(r"^(\d{1,3}\.){3}\d{1,3}$", dominio))


def enlace_shortener(url: str) -> bool:
    """Detecta si una URL pertenece a un servicio de acortamiento conocido."""
    dominio = extraer_dominio(url)
    return any(shortener in dominio for shortener in SHORTENER_DOMINIOS)


def nombre_display_engano(from_header: str) -> bool:
    """Determina si el nombre visible del remitente es diferente de la dirección real."""
    if "<" in from_header and ">" in from_header:
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


def tiene_reply_to_diferente(texto: str) -> bool:
    """Detecta si la cabecera Reply-To difiere de From, una señal frecuente de suplantación."""
    enviar = re.search(r"(?im)^from:\s*(.+)$", texto)
    reply = re.search(r"(?im)^reply-to:\s*(.+)$", texto)
    if enviar and reply:
        email_from = obtener_email_desde_cabecera(enviar.group(1))
        email_reply = obtener_email_desde_cabecera(reply.group(1))
        return email_from and email_reply and email_from != email_reply
    return False


def contiene_palabras_urgentes(texto: str) -> bool:
    """Busca frases urgentes o de presión que suelen aparecer en phishing."""
    texto = texto.lower()
    return any(palabra in texto for palabra in PALABRAS_URGENTES)


def asunto_sospechoso(texto: str) -> bool:
    """Evalúa si el asunto del correo coincide con patrones típicos de phishing."""
    texto = texto.lower()
    return any(frase in texto for frase in SUBJECT_SOSPECHOSOS)


def dominios_sospechosos(urls: List[str]) -> bool:
    """Comprueba si alguna URL apunta a dominios o patrones sospechosos."""
    for url in urls:
        dominio = extraer_dominio(url)
        if any(palabra in dominio for palabra in DOMINIO_SOSPECHOSO):
            return True
        if es_ip_enlace(url):
            return True
        if "@" in url:
            return True
    return False


def texto_enlace_distinto(anchors: List[Dict[str, str]]) -> bool:
    """Detecta si el texto visible de un enlace difiere de la URL real del href."""
    for anchor in anchors:
        texto = anchor.get("text", "").lower()
        href = anchor.get("href", "").lower()
        if texto and href and "http" in href:
            if "http" not in texto and "." in texto:
                if obtener_email_desde_cabecera(texto) or ".com" in texto or ".es" in texto:
                    if extraer_dominio(texto) != extraer_dominio(href):
                        return True
    return False


def contiene_referencia_archivo(texto: str) -> bool:
    """Detecta referencias a adjuntos o documentos típicos en correos de phishing."""
    return bool(re.search(r"\b(adjunto|archivo|documento|pdf|zip|xls|doc|docx)\b", texto, flags=re.IGNORECASE))


def puntuacion_senal(signals: Dict[str, bool]) -> float:
    """Convierte un conjunto de señales booleanas en una puntuación de riesgo porcentual."""
    pesos = {
        "reply_to_diferente": 0.18,
        "nombre_display_engano": 0.18,
        "enlaces_sospechosos": 0.20,
        "lenguaje_urgente": 0.14,
        "asunto_sospechoso": 0.10,
        "enlace_shortener": 0.10,
        "anchor_distinto": 0.10,
        "referencia_archivo": 0.10,
    }
    score = sum(pesos.get(k, 0.0) * (1.0 if v else 0.0) for k, v in signals.items())
    return min(score * 100, 100)


def analizar_correo(correo: Union[str, Dict[str, object]]) -> Dict[str, object]:
    """Analiza un correo y devuelve un informe de señales de phishing y riesgo."""
    if isinstance(correo, dict):
        texto = correo.get("full_text", "")
        urls = correo.get("urls", []) + [anchor.get("href", "") for anchor in correo.get("anchors", []) if anchor.get("href")]
        anchors = correo.get("anchors", [])
    else:
        texto = correo
        urls = extraer_urls(texto)
        anchors = []

    remitente = ""
    asunto = ""
    if isinstance(correo, dict):
        remitente = correo.get("from", "")
        asunto = correo.get("subject", "")
    else:
        remitente_match = re.search(r"(?im)^from:\s*(.+)$", texto)
        asunto_match = re.search(r"(?im)^subject:\s*(.+)$", texto)
        remitente = remitente_match.group(1).strip() if remitente_match else ""
        asunto = asunto_match.group(1).strip() if asunto_match else ""

    signals = {
        "reply_to_diferente": tiene_reply_to_diferente(texto),
        "nombre_display_engano": nombre_display_engano(remitente),
        "enlaces_sospechosos": len(urls) > 0 and dominios_sospechosos(urls),
        "lenguaje_urgente": contiene_palabras_urgentes(texto),
        "asunto_sospechoso": asunto_sospechoso(asunto),
        "enlace_shortener": len(urls) > 0 and any(enlace_shortener(url) for url in urls),
        "anchor_distinto": texto_enlace_distinto(anchors),
        "referencia_archivo": contiene_referencia_archivo(texto),
    }

    riesgo = puntuacion_senal(signals)
    explicaciones = [
        "El mensaje contiene un Reply-To diferente del From, lo que es típico en intentos de suplantación." if signals["reply_to_diferente"] else "No se encontró un Reply-To claramente diferente al From.",
        "El nombre visible del remitente no coincide con la dirección de correo, lo que puede ser engañoso." if signals["nombre_display_engano"] else "El nombre de remitente parece coherente con la dirección.",
        "Se detectaron enlaces que apuntan a dominios sospechosos, IPs directas o direcciones extrañas." if signals["enlaces_sospechosos"] else "No se detectaron dominios de enlace claramente sospechosos.",
        "El cuerpo del mensaje contiene lenguaje urgente o de alta presión." if signals["lenguaje_urgente"] else "No se detectó lenguaje urgente en el texto.",
        "El asunto es sospechoso y emplea fórmulas típicas de phishing." if signals["asunto_sospechoso"] else "El asunto no parece pertenecer a los ejemplos típicos de phishing.",
        "Se ha detectado un enlace acortado, que suele ocultar la URL real." if signals["enlace_shortener"] else "No se encontraron enlaces de servicios acortadores conocidos.",
        "El texto del enlace no coincide con la URL real, un indicador de engaño." if signals["anchor_distinto"] else "Los textos de los enlaces y las URLs son consistentes.",
        "Se menciona un adjunto o documento, algo habitual en mensajes de phishing." if signals["referencia_archivo"] else "No se detectaron referencias a adjuntos sospechosos.",
    ]

    return {
        "is_phishing": riesgo >= 45,
        "risk_score": round(riesgo, 1),
        "signals": signals,
        "urls": urls,
        "anchors": anchors,
        "from": remitente,
        "subject": asunto,
        "explanation": explicaciones,
    }
