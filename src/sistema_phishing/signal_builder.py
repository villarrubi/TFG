"""Construcción de señales heurísticas a partir de un correo normalizado.

La clase de este módulo agrupa las reglas existentes y decide qué parte del
correo debe recibir cada una. Así `PhishingAnalyzer` no conoce detalles de cada
heurística concreta.
"""

from typing import Dict

from .correo import CorreoAnalizado
from .signals import (
    adjuntos_sospechosos,
    asunto_sospechoso,
    cabecera_spoofing,
    contiene_formulario_html,
    contiene_html_sospechoso,
    contiene_javascript_redireccion,
    contiene_meta_refresh,
    contiene_palabras_urgentes,
    contiene_punycode_o_unicode,
    contiene_referencia_archivo,
    dkim_mal_formado,
    dmarc_fallido,
    dominios_sospechosos,
    enlace_shortener,
    es_dominio_listado_negro,
    formulario_action_sospechoso,
    incoherencia_remitente,
    mensaje_firmado_o_cifrado,
    mensaje_id_sospechoso,
    nombre_display_engano,
    remitente_marca_engano,
    saludo_generico,
    solicitud_datos_credenciales,
    texto_enlace_distinto,
    tiene_fallo_autenticacion,
    tiene_parametros_sospechosos_url,
    tiene_recibidos_sospechosos,
    tiene_reply_to_diferente,
)


class SignalBuilder:
    """Agrupa las reglas heurísticas en un diccionario estable de booleanos."""

    def __init__(self, correo: CorreoAnalizado):
        # El correo ya llega normalizado, por lo que aquí solo se coordina qué
        # señales se ejecutan y no cómo se parsea la entrada original.
        self.correo = correo

    def build(self) -> Dict[str, bool]:
        """Ejecuta las reglas disponibles sobre el correo normalizado."""
        # El orden se conserva para que la tabla de la interfaz y las
        # explicaciones aparezcan siempre de forma predecible.
        return {
            # Señales de identidad del remitente y coherencia de cabeceras.
            "reply_to_diferente": tiene_reply_to_diferente(self.correo.full_text),
            "nombre_display_engano": nombre_display_engano(self.correo.from_address),
            "remitente_marca_engano": remitente_marca_engano(self.correo.from_address),
            "cabecera_spoofing": cabecera_spoofing(self.correo.full_text),
            "incoherencia_remitente": incoherencia_remitente(self.correo.full_text),
            # Señales derivadas de URLs, dominios y reputación local.
            "enlaces_sospechosos": len(self.correo.urls) > 0 and dominios_sospechosos(self.correo.urls),
            "dominio_blacklist": len(self.correo.urls) > 0 and any(es_dominio_listado_negro(url) for url in self.correo.urls),
            "autenticacion_fallida": tiene_fallo_autenticacion(self.correo.full_text),
            "recibidos_sospechosos": tiene_recibidos_sospechosos(self.correo.full_text),
            "dmarc_fallido": dmarc_fallido(self.correo.full_text),
            "dkim_mal_formado": dkim_mal_formado(self.correo.full_text),
            # Señales de contenido social: presión, saludo genérico y petición de datos.
            "saludo_generico": saludo_generico(self.correo.body),
            "solicitud_credenciales": solicitud_datos_credenciales(self.correo.body),
            "mensaje_id_sospechoso": mensaje_id_sospechoso(self.correo.full_text, self.correo.from_address),
            # Señales propias del HTML y de adjuntos.
            "meta_refresh_html": contiene_meta_refresh(self.correo.html_body),
            "javascript_redireccion": contiene_javascript_redireccion(self.correo.html_body),
            "html_sospechoso": contiene_html_sospechoso(self.correo.html_body),
            "adjunto_sospechoso": adjuntos_sospechosos(self.correo.attachments),
            "lenguaje_urgente": contiene_palabras_urgentes(self.correo.full_text),
            "asunto_sospechoso": asunto_sospechoso(self.correo.subject),
            "url_parametros_sospechosos": len(self.correo.urls) > 0 and any(tiene_parametros_sospechosos_url(url) for url in self.correo.urls),
            "dominio_punycode_unicode": len(self.correo.urls) > 0 and any(contiene_punycode_o_unicode(url) for url in self.correo.urls),
            "enlace_shortener": len(self.correo.urls) > 0 and any(enlace_shortener(url) for url in self.correo.urls),
            "anchor_distinto": texto_enlace_distinto(self.correo.anchors),
            "formulario_html": contiene_formulario_html(self.correo.html_body),
            "formulario_action_sospechoso": formulario_action_sospechoso(self.correo.html_body),
            "referencia_archivo": contiene_referencia_archivo(self.correo.full_text),
            "mensaje_firmado_cifrado": mensaje_firmado_o_cifrado(self.correo.full_text),
        }
