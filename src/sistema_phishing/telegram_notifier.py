"""Notificación de alertas mediante Telegram Bot API."""

from dataclasses import dataclass
from html import escape
from typing import Callable, Optional

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


@dataclass
class TelegramNotifier:
    """Cliente mínimo para enviar mensajes a un chat de Telegram."""

    bot_token: str
    chat_id: str
    timeout: int = 10
    post: Optional[Callable] = None

    def enviar_mensaje(self, texto: str) -> None:
        """Envía un mensaje de texto al chat configurado."""
        if not self.bot_token or not self.chat_id:
            raise TelegramNotificationError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")

        post = self.post or requests.post
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
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
        if response.status_code >= 400:
            raise TelegramNotificationError(
                f"Telegram devolvió HTTP {response.status_code}: {response.text}"
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
    modo_seguro = escape(str(modo))
    lineas = [
        "<b>Posible phishing detectado</b>",
        "",
        f"<b>Riesgo:</b> {resultado['risk_score']:.1f}%",
        f"<b>Modo:</b> {modo_seguro}",
        f"<b>Remitente:</b> {remitente}",
        f"<b>Asunto:</b> {asunto}",
        f"<b>URLs detectadas:</b> {len(urls)}",
    ]
    if explicaciones:
        lineas.append("")
        lineas.append("<b>Motivos principales:</b>")
        lineas.extend(f"- {item}" for item in explicaciones)
    else:
        lineas.append("")
        lineas.append("No hay señales heurísticas sospechosas destacadas en el mensaje.")
    return "\n".join(lineas)
