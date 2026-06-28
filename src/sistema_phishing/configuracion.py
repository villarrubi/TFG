"""Constantes de configuración usadas por las reglas heurísticas y el modelo.

Centralizar estas listas evita duplicación entre reglas y permite ajustar el
comportamiento del prototipo sin entrar en la lógica de cada detector.
"""

# Vocabulario de presión o urgencia habitual en campañas de phishing.
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

# Frases de asunto que, combinadas con otras señales, elevan el riesgo.
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

# Expresión regular compartida para localizar URLs HTTP/HTTPS en texto plano.
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

# Lista local de stopwords en español para no depender de recursos externos de
# scikit-learn o NLTK durante el entrenamiento.
SPANISH_STOP_WORDS = {
    "a", "acuerdo", "adelante", "ademas", "ahi", "ahora", "al", "algo", "algunas",
    "algunos", "alla", "alli", "ambos", "ampleamos", "ante", "antes", "aun",
    "aunque", "bajo", "bien", "cada", "casi", "cierto", "como", "con", "conmigo",
    "contigo", "contra", "cual", "cuando", "cuanta", "cuantas", "cuanto", "cuantos",
    "de", "del", "demas", "demasiada", "demasiado", "dentro", "desde", "donde",
    "dos", "el", "ella", "ellas", "ellos", "empleais", "emplean", "emplear",
    "empleas", "en", "encima", "entre", "era", "erais", "eramos", "eran", "eras",
    "eres", "es", "esta", "estaba", "estado", "estais", "estamos", "estan", "este",
    "esto", "estos", "estoy", "esta", "etc", "fin", "fue", "fueron", "fui",
    "fuimos", "ha", "hace", "haceis", "hacemos", "hacen", "hacer", "haces", "hacia",
    "han", "hasta", "incluso", "intenta", "intentais", "intentamos", "intentan", "intentar",
    "intentas", "ir", "jamas", "junto", "la", "lado", "las", "le", "les", "lo", "los",
    "mas", "me", "menos", "mi", "mio", "muy", "ni", "no", "nos", "nosotras", "nosotros",
    "nuestra", "nuestro", "o", "os", "otra", "otras", "otro", "otros", "para", "pero",
    "poca", "pocas", "poco", "pocos", "por", "porque", "primero", "puede",
    "pueden", "puedo", "quien", "quienes", "que", "se", "sea", "seais", "seamos",
    "sean", "ser", "seria", "serias", "si", "sido", "sin", "sobre", "sois", "solamente",
    "solo", "somos", "soy", "su", "sus", "tal", "tales", "tambien", "tampoco", "te",
    "tiene", "tienen", "toda", "todas", "todo", "todos", "tras", "tu", "tus", "un",
    "una", "unas", "uno", "unos", "usted", "vosotras", "vosotros", "vuestra", "vuestro",
    "y", "ya", "yo"
}
