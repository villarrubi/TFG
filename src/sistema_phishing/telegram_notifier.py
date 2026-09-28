"""Notificación de alertas mediante Telegram Bot API."""

from collections.abc import Callable
from dataclasses import dataclass
from html import escape

import requests

from .guidance import FINDINGS, build_guidance


class TelegramNotificationError(RuntimeError):
    """Error controlado al enviar una notificación por Telegram."""


SUSPICIOUS_EXPLANATIONS = {name: values[1] for name, values in FINDINGS.items()}


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
    remitente = escape(_recortar(datos_email.get("from", "(sin remitente)"), 90))
    asunto = escape(_recortar(datos_email.get("subject", "(sin asunto)"), 120))
    urls = resultado.get("urls", [])
    guidance = build_guidance(resultado)
    findings = guidance["findings"]
    explicaciones = [escape(item["title"]) for item in findings[:3]]
    urls_resumen = [escape(_recortar(url, 70)) for url in urls[:2]]
    modo_seguro = escape(_recortar(modo, 30))
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
        if len(findings) > 3:
            remaining = len(findings) - 3
            noun = "indicio" if remaining == 1 else "indicios"
            lineas.append(f"Y {remaining} {noun} más en el detalle del análisis.")
    else:
        lineas.append("")
        lineas.append(escape(guidance["summary"]))
    if urls_resumen:
        lineas.append("")
        lineas.append("<b>Primeros enlaces:</b>")
        lineas.extend(f"- {url}" for url in urls_resumen)
    lineas.append("")
    lineas.append("<b>Qué hacer ahora:</b>")
    lineas.extend(f"- {escape(action)}" for action in guidance["actions"][:3])
    return "\n".join(lineas)
