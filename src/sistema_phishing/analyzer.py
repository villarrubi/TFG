"""Analizador principal que combina señalización y puntuación de riesgo."""

from typing import Dict, List

from .correo import CorreoAnalizado
from .scorer import RiskScorer
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
    es_dominio_listado_negro,
    enlace_shortener,
    formulario_action_sospechoso,
    incoherencia_remitente,
    mensaje_firmado_o_cifrado,
    mensaje_id_sospechoso,
    nombre_display_engano,
    remitente_marca_engano,
    solicitud_datos_credenciales,
    saludo_generico,
    tiene_fallo_autenticacion,
    tiene_recibidos_sospechosos,
    tiene_reply_to_diferente,
    texto_enlace_distinto,
    tiene_parametros_sospechosos_url,
)


class PhishingAnalyzer:
    """Coordina las señales individuales y genera el informe final."""

    def __init__(self, correo: CorreoAnalizado):
        self.correo = correo

    def analyze(self) -> Dict[str, object]:
        """Ejecuta todas las reglas, calcula riesgo y prepara datos para la UI."""
        signals = self._build_signals()
        riesgo = RiskScorer.score(signals)
        return {
            "is_phishing": riesgo >= 45,
            "risk_score": round(riesgo, 1),
            "signals": signals,
            "urls": self.correo.urls,
            "anchors": self.correo.anchors,
            "headers": self.correo.headers,
            "html_body": self.correo.html_body,
            "from": self.correo.from_address,
            "subject": self.correo.subject,
            "explanation": self._build_explanations(signals),
        }

    def _build_signals(self) -> Dict[str, bool]:
        """Agrupa todas las heurísticas en un diccionario estable de booleanos."""
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

    def _build_explanations(self, signals: Dict[str, bool]) -> List[str]:
        """Traduce cada señal a una explicación legible para el usuario final."""
        return [
            "El mensaje contiene un Reply-To diferente del From, lo que es típico en intentos de suplantación." if signals["reply_to_diferente"] else "No se encontró un Reply-To claramente diferente al From.",
            "El nombre visible del remitente no coincide con la dirección de correo, lo que puede ser engañoso." if signals["nombre_display_engano"] else "El nombre de remitente parece coherente con la dirección.",
            "El remitente utiliza una marca conocida en el nombre, pero la dirección de correo no coincide con esa marca." if signals["remitente_marca_engano"] else "No se detectó un uso engañoso de marca en el remitente.",
            "La cabecera Return-Path no coincide con el remitente, lo que puede indicar suplantación técnica." if signals["cabecera_spoofing"] else "No se detectaron inconsistencias claras en las cabeceras de remitente.",
            "Se detectan incoherencias entre From, Return-Path y Received-SPF." if signals["incoherencia_remitente"] else "From, Return-Path y Received-SPF parecen ser consistentes.",
            "Se detectaron enlaces que apuntan a dominios sospechosos, IPs directas o direcciones extrañas." if signals["enlaces_sospechosos"] else "No se detectaron dominios de enlace claramente sospechosos.",
            "La URL forma parte de una lista negra de dominios sospechosos." if signals["dominio_blacklist"] else "No se encontró ninguna URL en la lista negra local.",
            "El correo muestra fallos de autenticación SPF/DKIM/DMARC en sus cabeceras." if signals["autenticacion_fallida"] else "No se detectaron fallos claros en SPF/DKIM/DMARC.",
            "El resultado DMARC del correo indica un fallo de política, una señal clara de riesgo." if signals["dmarc_fallido"] else "No se detectó fallo en DMARC.",
            "La firma DKIM parece mal formada o incompleta, lo que aumenta la sospecha del mensaje." if signals["dkim_mal_formado"] else "La firma DKIM no muestra indicios de estar malformada.",
            "La ruta de entrega contiene hops sospechosos, direcciones internas o nombres de host poco frecuentes." if signals["recibidos_sospechosos"] else "Las cabeceras Received no muestran indicadores obvios de intermediarios sospechosos.",
            "El saludo del mensaje es genérico y puede indicar un ataque masivo." if signals["saludo_generico"] else "El saludo del mensaje no es claramente genérico.",
            "El texto solicita datos de acceso o credenciales, un patrón típico en phishing." if signals["solicitud_credenciales"] else "No se detectaron solicitudes explícitas de credenciales.",
            "El Message-ID usa un dominio distinto al dominio esperado del remitente." if signals["mensaje_id_sospechoso"] else "El Message-ID parece coincidir con el dominio del remitente.",
            "El correo utiliza parámetros de redirección sospechosos en la URL." if signals["url_parametros_sospechosos"] else "No se detectaron parámetros de URL de redirección sospechosos.",
            "El HTML contiene un meta refresh, usado para redirecciones automáticas sospechosas." if signals["meta_refresh_html"] else "No se detectaron meta refresh automáticos en el HTML.",
            "El HTML incluye JavaScript de redirección o código dinámico peligroso." if signals["javascript_redireccion"] else "No se detectaron redirecciones JavaScript obvias.",
            "El HTML contiene elementos sospechosos como iframe, base href, o enlaces javascript/data." if signals["html_sospechoso"] else "No se detectaron elementos HTML sospechosos.",
            "El correo contiene adjuntos con extensiones potencialmente peligrosas." if signals["adjunto_sospechoso"] else "No se detectaron adjuntos con extensiones de riesgo conocidas.",
            "El cuerpo del mensaje contiene lenguaje urgente o de alta presión." if signals["lenguaje_urgente"] else "No se detectó lenguaje urgente en el texto.",
            "El asunto es sospechoso y emplea fórmulas típicas de phishing." if signals["asunto_sospechoso"] else "El asunto no parece pertenecer a los ejemplos típicos de phishing.",
            "La URL usa punycode o caracteres Unicode en el dominio, lo que suele ocultar un dominio falso." if signals["dominio_punycode_unicode"] else "No se detectaron dominios punycode o Unicode sospechosos.",
            "El mensaje contiene un enlace con texto visible distinto a la URL real." if signals["anchor_distinto"] else "Los textos de los enlaces y las URLs son consistentes.",
            "El correo HTML contiene un formulario que apunta a una URL potencialmente sospechosa." if signals["formulario_html"] else "No se detectaron formularios HTML sospechosos.",
            "El formulario HTML tiene una acción vacía, relativa o sospechosa." if signals["formulario_action_sospechoso"] else "No se detectaron formularios con acción sospechosa.",
            "Se menciona un adjunto o documento, algo habitual en mensajes de phishing." if signals["referencia_archivo"] else "No se detectaron referencias a adjuntos sospechosos.",
            "El correo parece estar firmado o cifrado por S/MIME/PGP, lo que puede ser una señal de autenticidad adicional." if signals["mensaje_firmado_cifrado"] else "No se detectó firma o cifrado de correo en el mensaje.",
        ]
