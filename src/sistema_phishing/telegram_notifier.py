"""Notificación de alertas mediante Telegram Bot API."""

from collections.abc import Callable
from dataclasses import dataclass
from html import escape

import requests


class TelegramNotificationError(RuntimeError):
    """Error controlado al enviar una notificación por Telegram."""


SUSPICIOUS_EXPLANATIONS = {
    "reply_to_diferente": "Reply-To diferente del From.",
    "nombre_display_engano": "Nombre visible del remitente incoherente con la dirección.",
    "remitente_marca_engano": "Uso de una marca conocida desde un dominio no correspondiente.",
    "cabecera_spoofing": "Return-Path o cabeceras de remitente incoherentes.",
    "incoherencia_remitente": "Incoherencias entre From, Return-Path y Received-SPF.",
    "enlaces_sospechosos": "Enlaces hacia dominios sospechosos, IPs directas o direcciones extrañas.",
    "dominio_blacklist": "URL incluida en la lista negra local.",
    "autenticacion_fallida": "Fallos de autenticación SPF/DKIM/DMARC.",
    "dmarc_fallido": "DMARC indica fallo de política.",
    "dkim_mal_formado": "Firma DKIM mal formada o incompleta.",
    "recibidos_sospechosos": "Cabeceras Received con intermediarios sospechosos.",
    "saludo_generico": "Saludo genérico típico de campañas masivas.",
    "solicitud_credenciales": "Solicitud explícita de credenciales o datos de acceso.",
    "cambio_datos_bancarios": "Solicitud de cambio de datos bancarios o beneficiario.",
    "transferencia_urgente": "Orden de transferencia o pago con presión temporal.",
    "suplantacion_ejecutivo": "Pretexto de autoridad, aislamiento o confidencialidad propio de BEC.",
    "mensaje_id_sospechoso": "Message-ID con dominio inconsistente.",
    "url_parametros_sospechosos": "Parámetros de URL compatibles con redirección sospechosa.",
    "meta_refresh_html": "HTML con meta refresh.",
    "javascript_redireccion": "HTML con JavaScript de redirección.",
    "html_sospechoso": "HTML con elementos sospechosos.",
    "adjunto_sospechoso": "Adjuntos con extensiones de riesgo.",
    "lenguaje_urgente": "Lenguaje urgente o de alta presión.",
    "asunto_sospechoso": "Asunto con fórmula típica de phishing.",
    "dominio_punycode_unicode": "Dominio con punycode o caracteres Unicode sospechosos.",
    "enlace_shortener": "Uso de acortador de enlaces.",
    "anchor_distinto": "Texto visible del enlace distinto a la URL real.",
    "formulario_html": "Formulario HTML potencialmente sospechoso.",
    "formulario_action_sospechoso": "Formulario con acción vacía, relativa o sospechosa.",
    "referencia_archivo": "Referencia a adjuntos o documentos potencialmente usada como gancho.",
}


def _recortar(texto: str, limite: int = 90) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else f"{texto[: limite - 3]}..."


def _clasificacion(score: float, is_phishing: bool = False) -> str:
    if is_phishing:
        return "Riesgo alto"
    if score >= 70:
        return "Riesgo alto"
    if score >= 45:
        return "Riesgo medio"
    return "Riesgo bajo"


@dataclass
class TelegramNotifier:
    """Cliente mínimo para enviar mensajes a un chat de Telegram."""

    bot_token: str
    chat_id: str
    timeout: int = 10
    post: Callable | None = None

    def enviar_mensaje(self, texto: str) -> None:
        """Envía un mensaje de texto al chat configurado."""
        if not self.bot_token or not self.chat_id:
            raise TelegramNotificationError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")

        post = self.post or requests.post
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            response = post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": texto,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            # Requests incluye la URL en algunos errores y esa URL contiene el
            # token del bot. Se devuelve un mensaje neutro para no filtrarlo en
            # Streamlit ni en los logs del monitor.
            raise TelegramNotificationError(
                "No se pudo contactar con la API de Telegram."
            ) from exc
        if response.status_code >= 400:
            raise TelegramNotificationError(
                f"Telegram devolvió HTTP {response.status_code}: "
                f"{_recortar(response.text, 200)}"
            )


def construir_mensaje_alerta(datos_email: dict, resultado: dict, modo: str) -> str:
    """Construye el texto enviado cuando se detecta un correo sospechoso."""
    remitente = escape(str(datos_email.get("from", "(sin remitente)")))
    asunto = escape(str(datos_email.get("subject", "(sin asunto)")))
    urls = resultado.get("urls", [])
    signals = resultado.get("signals", {})
    explicaciones = [
        escape(texto)
        for nombre, texto in SUSPICIOUS_EXPLANATIONS.items()
        if signals.get(nombre)
    ][:5]
    urls_resumen = [escape(_recortar(url)) for url in urls[:3]]
    modo_seguro = escape(str(modo))
    score = float(resultado["risk_score"])
    lineas = [
        "<b>ALERTA DE PHISHING</b>",
        f"<b>{_clasificacion(score, bool(resultado.get('is_phishing')))}</b> - {score:.1f}%",
        "",
        f"<b>Modo:</b> {modo_seguro}",
        f"<b>Remitente:</b> {remitente}",
        f"<b>Asunto:</b> {asunto}",
        f"<b>URLs:</b> {len(urls)} detectadas",
    ]
    if explicaciones:
        lineas.append("")
        lineas.append("<b>Señales activas:</b>")
        lineas.extend(f"- {item}" for item in explicaciones)
    else:
        lineas.append("")
        lineas.append("No hay señales heurísticas sospechosas destacadas en el mensaje.")
    if urls_resumen:
        lineas.append("")
        lineas.append("<b>Primeros enlaces:</b>")
        lineas.extend(f"- {url}" for url in urls_resumen)
    lineas.append("")
    lineas.append("Revisa el correo antes de abrir enlaces o responder.")
    return "\n".join(lineas)
