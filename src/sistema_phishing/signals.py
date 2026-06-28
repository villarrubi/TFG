"""Funciones de señalización y utilidades para detectar phishing en correos."""

import re
from typing import Dict, List

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

URL_PATTERN = r"https?://[\w\-\.:/\?#\&=\%\+;]+"
# Listas locales usadas por reglas sencillas. No sustituyen una reputación en
# tiempo real, pero aportan señales explicables para el prototipo.
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


def saludo_generico(texto: str) -> bool:
    """Detecta saludos o trato genéricos típicos de mensajes masivos o phishing."""
    return bool(re.search(r"\b(estimado cliente|estimado usuario|estimado señor|estimada señora|a quien corresponda|cliente estimado|usuario estimado)\b", texto, flags=re.IGNORECASE))


def solicitud_datos_credenciales(texto: str) -> bool:
    """Detecta solicitudes directas de datos de acceso o credenciales en el mensaje."""
    return bool(re.search(r"\b(credenciales|contraseña|password|usuario|datos de acceso|iniciar sesión|inicie sesión|login|codigo de verificacion|código de verificación|verificación de seguridad)\b", texto, flags=re.IGNORECASE))


def contiene_meta_refresh(html: str) -> bool:
    """Detecta redirecciones automáticas mediante meta refresh en HTML."""
    return bool(re.search(r"(?i)<meta[^>]+http-equiv=['\"]refresh['\"]|<meta[^>]+content=['\"][^'\"]*url=", html))


def contiene_javascript_redireccion(html: str) -> bool:
    """Detecta redirecciones JavaScript ocultas o manipulación de location."""
    return bool(re.search(r"(?i)(window\.location|location\.href|document\.location|replace\(|eval\(|setTimeout\(|setInterval\(|location\.replace)", html))


def adjuntos_sospechosos(attachments: List[str]) -> bool:
    """Detecta adjuntos con extensiones sospechosas en el correo."""
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


def mensaje_id_sospechoso(texto: str, remitente: str) -> bool:
    """Detecta mensajes con Message-ID cuyo dominio no coincide con el dominio esperado del remitente."""
    message_id = obtener_cabecera(texto, "message-id")
    if not message_id or "@" not in message_id or "@" not in remitente:
        return False
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
        # Si BeautifulSoup no está disponible, al menos se marca la presencia
        # de formularios para no perder por completo esa señal.
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


def contiene_punycode_o_unicode(url: str) -> bool:
    """Detecta si el dominio de una URL está en punycode o contiene caracteres Unicode no ASCII."""
    dominio = extraer_dominio(url)
    if dominio.startswith("xn--"):
        return True
    try:
        dominio.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


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
    return bool(re.search(r"\b[\w.-]+\.(com|net|org|es|info|biz|online|xyz|club)\b", texto, flags=re.IGNORECASE))


def contiene_html_sospechoso(html: str) -> bool:
    """Detecta elementos HTML sospechosos que suelen usarse para ocultar phishing."""
    if not html:
        return False
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


def tiene_parametros_sospechosos_url(url: str) -> bool:
    """Detecta parámetros que suelen ocultar redirecciones o URLs engañosas."""
    texto = url.lower()
    if re.search(r"https?://[^/]*@[^/]+", texto):
        return True
    if re.search(r"\b(?:redirect|redirect_to|url|next|continue|return|verify|token|session)=https?://", texto):
        return True
    return False


def remitente_marca_engano(from_header: str) -> bool:
    """Detecta si el nombre del remitente usa una marca conocida pero la dirección de correo no."""
    if "<" in from_header and ">" in from_header:
        nombre = from_header.split("<", 1)[0].strip().lower()
        direccion = from_header.split("<", 1)[1].split(">", 1)[0].strip().lower()
        for token in KNOWN_BRAND_TOKENS:
            if token in nombre and token not in direccion:
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
        if not action:
            return True
        if action.startswith("/") or action.startswith("./") or action.startswith("../"):
            return True
        if not action.lower().startswith("http"):
            return True
        if es_ip_enlace(action) or es_dominio_listado_negro(action) or es_dominio_confuso(action):
            return True
    return False


def contiene_referencia_archivo(texto: str) -> bool:
    """Detecta referencias a adjuntos o documentos típicos en correos de phishing."""
    return bool(re.search(r"\b(adjunto|archivo|documento|pdf|zip|xls|doc|docx)\b", texto, flags=re.IGNORECASE))
