"""Pantalla Streamlit para configurar y probar el monitor de Gmail."""

import html
import os

import streamlit as st

from sistema_phishing.gmail_client import (
    GmailIntegrationError,
    construir_servicio_gmail,
    dependencias_disponibles,
    obtener_perfil_gmail,
    obtener_ultimos_correos,
)
from sistema_phishing.env_loader import cargar_env_local, leer_env_file
from sistema_phishing.gmail_monitor import MonitorConfig, analizar_correos_nuevos
from sistema_phishing.telegram_notifier import TelegramNotifier, TelegramNotificationError
from ui_components import aplicar_estilos_base, estado_badge, render_html


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cargar_env_local(ROOT_DIR)
GMAIL_CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")
MONITOR_STATE_PATH = os.path.join(ROOT_DIR, "estado_monitor.json")
MODEL_PATH_ES = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
MODEL_PATH_EN = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")
ENV_LOCAL_PATH = os.path.join(ROOT_DIR, ".env.local")


def aplicar_estilos_monitor() -> None:
    """Aplica estilos locales para la pantalla de monitorización."""
    aplicar_estilos_base(
        """
        .result-card {
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            background: #ffffff;
            padding: 14px 16px;
            margin-bottom: 10px;
        }
        .result-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 4px;
        }
        .result-meta {
            color: #64748b;
            font-size: 0.85rem;
        }
        """
    )


def _valor_entero(valores: dict, key: str, default: int) -> int:
    try:
        return int(valores.get(key, str(default)))
    except ValueError:
        return default


def _valor_float(valores: dict, key: str, default: float) -> float:
    try:
        return float(valores.get(key, str(default)))
    except ValueError:
        return default


def _telegram_configurado() -> bool:
    """Indica si existen credenciales de Telegram en el entorno."""
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def _crear_notifier() -> TelegramNotifier | None:
    """Crea un notificador Telegram si está configurado."""
    if not _telegram_configurado():
        return None
    return TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
    )


def _config_desde_ui(modo: str, threshold: float, heur_weight: int) -> MonitorConfig:
    """Construye la configuración del monitor desde la pantalla."""
    return MonitorConfig(
        state_path=MONITOR_STATE_PATH,
        threshold=threshold,
        mode=modo,
        heur_weight=heur_weight,
        neural_weight=100 - heur_weight,
        model_path_es=MODEL_PATH_ES,
        model_path_en=MODEL_PATH_EN,
        mark_existing_as_seen=False,
    )


def _mostrar_estado_general(valores: dict) -> None:
    """Pinta una fila de estado con Gmail, Telegram y proceso 24/7."""
    gmail_ok = os.path.exists(GMAIL_TOKEN_PATH)
    telegram_ok = _telegram_configurado()
    interval = _valor_entero(valores, "MONITOR_INTERVAL_SECONDS", 120)

    render_html(
        f"""
        <div class="ui-grid ui-grid-3">
            <div class="ui-card">
                <div class="ui-label">Gmail</div>
                <div class="ui-value">{estado_badge(gmail_ok, "Conectado", "Sin token")}</div>
                <div class="ui-note">Cuenta usada por el monitor automático.</div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Telegram</div>
                <div class="ui-value">{estado_badge(telegram_ok, "Configurado", "Pendiente")}</div>
                <div class="ui-note">Destino de alertas cuando hay phishing.</div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Proceso 24/7</div>
                <div class="ui-value">Cada {interval}s</div>
                <div class="ui-note">Se ejecuta aparte con <code>python src/monitor_gmail.py</code>.</div>
            </div>
        </div>
        """
    )


def _mostrar_configuracion_activa(valores: dict) -> None:
    """Muestra los parámetros que gobernarán la comprobación."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Umbral", f"{_valor_float(valores, 'PHISHING_THRESHOLD', 45):.0f}%")
    col2.metric("Modo", valores.get("MONITOR_ANALYSIS_MODE", "combinado"))
    col3.metric("Query", valores.get("GMAIL_MONITOR_QUERY", "in:inbox newer_than:1d"))
    col4.metric("Límite", _valor_entero(valores, "GMAIL_MONITOR_LIMIT", 20))


def _color_resultado(score: float, is_phishing: bool) -> str:
    if is_phishing:
        return "#dc2626"
    if score >= 45:
        return "#d97706"
    return "#11845b"


def _mostrar_resultado_monitor(resultado) -> None:
    """Pinta una tarjeta de resultado de monitorización."""
    color = _color_resultado(resultado.risk_score, resultado.is_phishing)
    clasificacion = "Phishing probable" if resultado.is_phishing else "No parece phishing"
    aviso = "Alerta enviada por Telegram" if resultado.notified else "Sin notificación"
    subject = html.escape(resultado.subject or "(sin asunto)")
    sender = html.escape(resultado.sender or "(sin remitente)")
    render_html(
        f"""
        <div class="result-card">
            <div class="result-title">{subject}</div>
            <div class="result-meta">Remitente: {sender}</div>
            <div style="margin-top:10px; display:flex; align-items:center; gap:12px;">
                <div style="font-size:1.8rem; font-weight:800; color:{color};">{resultado.risk_score:.1f}%</div>
                <div>
                    <div style="font-weight:800; color:#0f172a;">{clasificacion}</div>
                    <div class="result-meta">{aviso}</div>
                </div>
            </div>
        </div>
        """
    )


def main():
    """Renderiza la pantalla de monitorización."""
    aplicar_estilos_monitor()
    cargar_env_local(ROOT_DIR)
    valores = leer_env_file(ENV_LOCAL_PATH)
    st.title("Monitor de Gmail")
    st.caption("Comprueba correos nuevos, calcula riesgo y envía alertas por Telegram.")
    _mostrar_estado_general(valores)

    if not dependencias_disponibles():
        st.warning("Faltan dependencias de Google. Ejecuta `pip install -r requirements.txt`.")

    st.markdown("### Configuración activa")
    _mostrar_configuracion_activa(valores)

    col_gmail, col_telegram = st.columns(2)
    with col_gmail:
        st.subheader("Gmail")
        if os.path.exists(GMAIL_TOKEN_PATH):
            try:
                servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
                perfil = obtener_perfil_gmail(servicio)
                st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
            except Exception as exc:
                st.error(f"No se pudo leer la cuenta conectada: {exc}")
        else:
            st.info("Aún no hay token de Gmail. Conecta Gmail desde la pantalla de detección.")

    with col_telegram:
        st.subheader("Telegram")
        if _telegram_configurado():
            st.success("Telegram configurado correctamente.")
        else:
            st.warning("Configura el bot y el chat destino desde la vista Configuración.")
        if st.button("Probar Telegram", disabled=not _telegram_configurado()):
            try:
                _crear_notifier().enviar_mensaje("Prueba del monitor de phishing: Telegram configurado correctamente.")
                st.success("Mensaje de prueba enviado.")
            except TelegramNotificationError as exc:
                st.error(str(exc))

    st.markdown("### Comprobación manual")
    query = st.text_input("Consulta de Gmail", value=valores.get("GMAIL_MONITOR_QUERY", "in:inbox newer_than:1d"))
    limit = st.number_input(
        "Máximo de correos a revisar",
        min_value=1,
        max_value=50,
        value=int(valores.get("GMAIL_MONITOR_LIMIT", "10")),
    )
    modo_options = ["combinado", "heuristico", "neural"]
    modo = st.selectbox(
        "Modo de análisis",
        modo_options,
        index=modo_options.index(valores.get("MONITOR_ANALYSIS_MODE", "combinado"))
        if valores.get("MONITOR_ANALYSIS_MODE", "combinado") in modo_options
        else 0,
    )
    threshold = st.slider("Umbral de alerta", 0, 100, int(float(valores.get("PHISHING_THRESHOLD", "45"))))
    heur_weight = 60
    if modo == "combinado":
        heur_weight = st.slider("Peso heurístico (%)", 0, 100, int(valores.get("MONITOR_HEUR_WEIGHT", "60")))
    enviar_alertas = st.checkbox("Enviar alertas Telegram durante esta comprobación", value=False)

    if st.button("Comprobar correos ahora"):
        try:
            servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
            correos = obtener_ultimos_correos(servicio, limite=int(limit), query=query)
            notifier = _crear_notifier() if enviar_alertas else None
            resultados = analizar_correos_nuevos(
                correos,
                _config_desde_ui(modo, float(threshold), int(heur_weight)),
                notifier,
            )
            if not resultados:
                st.info("No hay correos nuevos para analizar con el estado actual del monitor.")
            for resultado in resultados:
                _mostrar_resultado_monitor(resultado)
        except GmailIntegrationError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"No se pudo ejecutar la comprobación: {exc}")

    st.markdown("### Ejecución 24/7")
    st.code("python src/monitor_gmail.py", language="powershell")
    st.write("Para una prueba puntual sin bucle continuo:")
    st.code("python src/monitor_gmail.py --once", language="powershell")
