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

URL_PATTERN = r"https?://[\w\-\.\:/\?\#\&\=\%\+\;]+"
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
BLACKLIST_DOMINIOS = [
    "banco-real",
    "login-verificacion",
    "secure-login",
    "verificacion-online",
    "atencion-cliente",
    "soporte-seguro",
    "alerta-seguridad",
    "cliente-online",
    "confirmar-sesion",
    "banco-seguro",
]
KNOWN_BRAND_TOKENS = [
    "banco",
    "paypal",
    "amazon",
    "apple",
    "google",
    "microsoft",
    "facebook",
    "telefónica",
    "movistar",
    "iberdrola",
    "bbva",
    "santander",
    "caixa",
    "ibank",
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


def es_dominio_listado_negro(url: str) -> bool:
    """Detecta si una URL pertenece a un dominio conocido de lista negra."""
    dominio = extraer_dominio(url)
    return any(negro in dominio for negro in BLACKLIST_DOMINIOS)


def es_dominio_confuso(url: str) -> bool:
    """Detecta si un dominio contiene tokens de marca pero no es una URL oficial clara."""
    dominio = extraer_dominio(url)
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


def obtener_cabecera(texto: str, nombre: str) -> str:
    """Extrae el valor de una cabecera específica del texto del correo."""
    match = re.search(rf"(?im)^{re.escape(nombre)}:\s*(.+)$", texto)
    return match.group(1).strip() if match else ""


def tiene_fallo_autenticacion(texto: str) -> bool:
    """Detecta fallos en SPF, DKIM o DMARC a partir de las cabeceras de autenticación."""
    auth = obtener_cabecera(texto, "authentication-results")
    arc = obtener_cabecera(texto, "arc-authentication-results")
    received_spf = obtener_cabecera(texto, "received-spf")

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
    """Detecta si cabeceras como Return-Path no coinciden con From, otra señal de suplantación."""
    enviar = obtener_cabecera(texto, "from")
    return_path = obtener_cabecera(texto, "return-path")
    if enviar and return_path:
        email_from = obtener_email_desde_cabecera(enviar)
        email_return = obtener_email_desde_cabecera(return_path)
        return email_from and email_return and email_from != email_return
    return False


def contiene_palabras_urgentes(texto: str) -> bool:
    """Busca frases urgentes o de presión que suelen aparecer en phishing."""
    texto = texto.lower()
    return any(palabra in texto for palabra in PALABRAS_URGENTES)


def contiene_formulario_html(html: str) -> bool:
    """Detecta si el correo HTML contiene formularios con destinos sospechosos."""
    if not html:
        return False
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return bool(re.search(r"<form\b.*?>", html, flags=re.IGNORECASE))

    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        action = form.get("action", "")
        if action:
            if "http" in action:
                if es_ip_enlace(action) or es_dominio_listado_negro(action) or es_dominio_confuso(action):
                    return True
            else:
                return True
        else:
            return True
    return False


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
        if es_dominio_listado_negro(url):
            return True
        if es_dominio_confuso(url):
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
        "reply_to_diferente": 0.16,
        "nombre_display_engano": 0.16,
        "cabecera_spoofing": 0.12,
        "enlaces_sospechosos": 0.12,
        "dominio_blacklist": 0.12,
        "autenticacion_fallida": 0.15,
        "recibidos_sospechosos": 0.10,
        "lenguaje_urgente": 0.08,
        "asunto_sospechoso": 0.06,
        "enlace_shortener": 0.06,
        "anchor_distinto": 0.06,
        "formulario_html": 0.05,
        "referencia_archivo": 0.05,
        "mensaje_firmado_cifrado": -0.04,
    }
    score = sum(pesos.get(k, 0.0) * (1.0 if v else 0.0) for k, v in signals.items())
    return min(max(score * 100, 0), 100)


def analizar_correo(correo: Union[str, Dict[str, object]]) -> Dict[str, object]:
    """Analiza un correo y devuelve un informe de señales de phishing y riesgo."""
    if isinstance(correo, dict):
        texto = correo.get("full_text", "")
        urls = correo.get("urls", []) + [anchor.get("href", "") for anchor in correo.get("anchors", []) if anchor.get("href")]
        anchors = correo.get("anchors", [])
        html_body = correo.get("html_body", "")
        headers = correo.get("headers", {})
    else:
        texto = correo
        urls = extraer_urls(texto)
        anchors = []
        html_body = ""
        headers = {}

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
        "cabecera_spoofing": cabecera_spoofing(texto),
        "enlaces_sospechosos": len(urls) > 0 and dominios_sospechosos(urls),
        "dominio_blacklist": len(urls) > 0 and any(es_dominio_listado_negro(url) for url in urls),
        "autenticacion_fallida": tiene_fallo_autenticacion(texto),
        "recibidos_sospechosos": tiene_recibidos_sospechosos(texto),
        "lenguaje_urgente": contiene_palabras_urgentes(texto),
        "asunto_sospechoso": asunto_sospechoso(asunto),
        "enlace_shortener": len(urls) > 0 and any(enlace_shortener(url) for url in urls),
        "anchor_distinto": texto_enlace_distinto(anchors),
        "formulario_html": contiene_formulario_html(html_body),
        "referencia_archivo": contiene_referencia_archivo(texto),
        "mensaje_firmado_cifrado": mensaje_firmado_o_cifrado(texto),
    }

    riesgo = puntuacion_senal(signals)
    explicaciones = [
        "El mensaje contiene un Reply-To diferente del From, lo que es típico en intentos de suplantación." if signals["reply_to_diferente"] else "No se encontró un Reply-To claramente diferente al From.",
        "El nombre visible del remitente no coincide con la dirección de correo, lo que puede ser engañoso." if signals["nombre_display_engano"] else "El nombre de remitente parece coherente con la dirección.",
        "La cabecera Return-Path no coincide con el remitente, lo que puede indicar suplantación técnica." if signals["cabecera_spoofing"] else "No se detectaron inconsistencias claras en las cabeceras de remitente.",
        "Se detectaron enlaces que apuntan a dominios sospechosos, IPs directas o direcciones extrañas." if signals["enlaces_sospechosos"] else "No se detectaron dominios de enlace claramente sospechosos.",
        "La URL forma parte de una lista negra de dominios sospechosos." if signals["dominio_blacklist"] else "No se encontró ninguna URL en la lista negra local.",
        "El correo muestra fallos de autenticación SPF/DKIM/DMARC en sus cabeceras." if signals["autenticacion_fallida"] else "No se detectaron fallos claros en SPF/DKIM/DMARC.",
        "La ruta de entrega contiene hops sospechosos, direcciones internas o nombres de host poco frecuentes." if signals["recibidos_sospechosos"] else "Las cabeceras Received no muestran indicadores obvios de intermediarios sospechosos.",
        "El cuerpo del mensaje contiene lenguaje urgente o de alta presión." if signals["lenguaje_urgente"] else "No se detectó lenguaje urgente en el texto.",
        "El asunto es sospechoso y emplea fórmulas típicas de phishing." if signals["asunto_sospechoso"] else "El asunto no parece pertenecer a los ejemplos típicos de phishing.",
        "Se ha detectado un enlace acortado, que suele ocultar la URL real." if signals["enlace_shortener"] else "No se encontraron enlaces de servicios acortadores conocidos.",
        "El texto del enlace no coincide con la URL real, un indicador de engaño." if signals["anchor_distinto"] else "Los textos de los enlaces y las URLs son consistentes.",
        "El correo HTML contiene un formulario que apunta a una URL potencialmente sospechosa." if signals["formulario_html"] else "No se detectaron formularios HTML sospechosos.",
        "Se menciona un adjunto o documento, algo habitual en mensajes de phishing." if signals["referencia_archivo"] else "No se detectaron referencias a adjuntos sospechosos.",
        "El correo parece estar firmado o cifrado por S/MIME/PGP, lo que puede ser una señal de autenticidad adicional." if signals["mensaje_firmado_cifrado"] else "No se detectó firma o cifrado de correo en el mensaje.",
    ]

    return {
        "is_phishing": riesgo >= 45,
        "risk_score": round(riesgo, 1),
        "signals": signals,
        "urls": urls,
        "anchors": anchors,
        "headers": headers,
        "html_body": html_body,
        "from": remitente,
        "subject": asunto,
        "explanation": explicaciones,
    }

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
