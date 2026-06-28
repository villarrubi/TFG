"""Módulo de cálculo de puntuación de riesgo para las señales de phishing."""

from typing import Dict


class RiskScorer:
    """Convierte señales booleanas en una puntuación numérica de riesgo."""

    # Cada señal aporta una fracción del riesgo total. Los pesos negativos
    # representan indicadores que reducen ligeramente la sospecha.
    weights = {
        "reply_to_diferente": 0.14,
        "nombre_display_engano": 0.14,
        "remitente_marca_engano": 0.10,
        "cabecera_spoofing": 0.10,
        "enlaces_sospechosos": 0.10,
        "dominio_blacklist": 0.10,
        "autenticacion_fallida": 0.14,
        "dmarc_fallido": 0.08,
        "dkim_mal_formado": 0.05,
        "recibidos_sospechosos": 0.08,
        "saludo_generico": 0.06,
        "solicitud_credenciales": 0.06,
        "mensaje_id_sospechoso": 0.06,
        "meta_refresh_html": 0.06,
        "javascript_redireccion": 0.06,
        "html_sospechoso": 0.06,
        "adjunto_sospechoso": 0.06,
        "lenguaje_urgente": 0.06,
        "asunto_sospechoso": 0.05,
        "url_parametros_sospechosos": 0.05,
        "dominio_punycode_unicode": 0.05,
        "incoherencia_remitente": 0.08,
        "enlace_shortener": 0.05,
        "anchor_distinto": 0.05,
        "formulario_html": 0.04,
        "formulario_action_sospechoso": 0.05,
        "referencia_archivo": 0.04,
        "mensaje_firmado_cifrado": -0.03,
    }

    @classmethod
    def score(cls, signals: Dict[str, bool]) -> float:
        """Suma los pesos activos y limita el resultado al rango 0-100."""
        # Las señales desconocidas pesan 0 para poder añadir reglas nuevas sin
        # romper llamadas antiguas que todavía no tengan peso asignado.
        total = sum(cls.weights.get(name, 0.0) * (1.0 if value else 0.0) for name, value in signals.items())
        return min(max(total * 100, 0), 100)
