"""Notificación de alertas mediante Telegram Bot API."""

from dataclasses import dataclass
from typing import Callable, Optional

import requests


class TelegramNotificationError(RuntimeError):
    """Error controlado al enviar una notificación por Telegram."""


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
    remitente = datos_email.get("from", "(sin remitente)")
    asunto = datos_email.get("subject", "(sin asunto)")
    urls = resultado.get("urls", [])
    explicaciones = resultado.get("explanation", [])[:5]
    lineas = [
        "<b>Posible phishing detectado</b>",
        "",
        f"<b>Riesgo:</b> {resultado['risk_score']:.1f}%",
        f"<b>Modo:</b> {modo}",
        f"<b>Remitente:</b> {remitente}",
        f"<b>Asunto:</b> {asunto}",
        f"<b>URLs detectadas:</b> {len(urls)}",
    ]
    if explicaciones:
        lineas.append("")
        lineas.append("<b>Motivos principales:</b>")
        lineas.extend(f"- {item}" for item in explicaciones)
    return "\n".join(lineas)
