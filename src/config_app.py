"""Pantalla de configuración centralizada del sistema."""

import os

import streamlit as st

from sistema_phishing.env_loader import actualizar_env_local, cargar_env_local, leer_env_file
from sistema_phishing.gmail_client import (
    GmailIntegrationError,
    construir_servicio_gmail,
    obtener_perfil_gmail,
)
from sistema_phishing.telegram_notifier import TelegramNotifier, TelegramNotificationError


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_LOCAL_PATH = os.path.join(ROOT_DIR, ".env.local")
GMAIL_CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")


def _mask_secret(value: str) -> str:
    """Oculta casi todo un secreto para mostrarlo en pantalla."""
    if not value:
        return "No configurado"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _perfil_gmail():
    """Devuelve el perfil Gmail actual o None si no hay sesión."""
    if not os.path.exists(GMAIL_TOKEN_PATH):
        return None
    servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
    return obtener_perfil_gmail(servicio)


def _mostrar_config_gmail() -> None:
    """Muestra y gestiona la cuenta Gmail usada por detección y monitor."""
    st.subheader("Gmail")
    st.caption(f"Credenciales: `{GMAIL_CREDENTIALS_PATH}`")

    try:
        perfil = _perfil_gmail()
        if perfil:
            st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
        else:
            st.info("No hay ninguna cuenta de Gmail conectada.")
    except Exception as exc:
        st.error(f"No se pudo leer la cuenta conectada: {exc}")

    col_conectar, col_cambiar = st.columns(2)
    if col_conectar.button("Conectar Gmail", use_container_width=True):
        try:
            servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
            perfil = obtener_perfil_gmail(servicio)
            st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
        except GmailIntegrationError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"No se pudo conectar con Gmail: {exc}")

    if col_cambiar.button("Cambiar cuenta", use_container_width=True):
        if os.path.exists(GMAIL_TOKEN_PATH):
            os.remove(GMAIL_TOKEN_PATH)
        st.session_state.pop("gmail_email", None)
        st.session_state.pop("gmail_resultados", None)
        st.session_state.pop("gmail_tipo_analisis", None)
        st.info("Sesión eliminada. Pulsa Conectar Gmail para elegir otra cuenta.")


def _mostrar_config_telegram(valores: dict) -> None:
    """Muestra y guarda la configuración de Telegram."""
    st.subheader("Telegram")
    token_actual = valores.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_actual = valores.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
    st.write(f"Bot configurado: `{_mask_secret(token_actual)}`")
    st.write(f"Chat destino: `{chat_actual or 'No configurado'}`")

    token_nuevo = st.text_input(
        "Nuevo token del bot",
        type="password",
        placeholder="Déjalo vacío para conservar el actual",
    )
    chat_id = st.text_input("Chat ID destino", value=chat_actual)

    col_guardar, col_probar = st.columns(2)
    if col_guardar.button("Guardar Telegram", use_container_width=True):
        nuevos_valores = {"TELEGRAM_CHAT_ID": chat_id.strip()}
        if token_nuevo.strip():
            nuevos_valores["TELEGRAM_BOT_TOKEN"] = token_nuevo.strip()
        actualizar_env_local(ROOT_DIR, nuevos_valores)
        st.success("Configuración de Telegram guardada.")

    if col_probar.button("Probar Telegram", use_container_width=True):
        cargar_env_local(ROOT_DIR)
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat = chat_id.strip() or os.getenv("TELEGRAM_CHAT_ID", "")
        try:
            TelegramNotifier(token, chat).enviar_mensaje(
                "Prueba de configuración: el sistema de phishing puede enviar alertas a este chat."
            )
            st.success("Mensaje de prueba enviado.")
        except TelegramNotificationError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"No se pudo enviar el mensaje: {exc}")


def _mostrar_config_monitor(valores: dict) -> None:
    """Muestra y guarda los parámetros del monitor."""
    st.subheader("Monitor")
    interval = st.number_input(
        "Intervalo entre comprobaciones (segundos)",
        min_value=10,
        max_value=86400,
        value=int(valores.get("MONITOR_INTERVAL_SECONDS", "120")),
    )
    threshold = st.slider(
        "Umbral de alerta",
        0,
        100,
        int(float(valores.get("PHISHING_THRESHOLD", "45"))),
    )
    mode_options = ["combinado", "heuristico", "neural"]
    mode = st.selectbox(
        "Modo de análisis",
        mode_options,
        index=mode_options.index(valores.get("MONITOR_ANALYSIS_MODE", "combinado"))
        if valores.get("MONITOR_ANALYSIS_MODE", "combinado") in mode_options
        else 0,
    )
    heur_weight = st.slider(
        "Peso heurístico (%)",
        0,
        100,
        int(valores.get("MONITOR_HEUR_WEIGHT", "60")),
        disabled=mode != "combinado",
    )
    query = st.text_input(
        "Consulta de Gmail del monitor",
        value=valores.get("GMAIL_MONITOR_QUERY", "in:inbox newer_than:1d"),
    )
    limit = st.number_input(
        "Máximo de correos por ciclo",
        min_value=1,
        max_value=100,
        value=int(valores.get("GMAIL_MONITOR_LIMIT", "20")),
    )
    mark_existing = st.checkbox(
        "Primera ejecución: marcar correos existentes como vistos",
        value=valores.get("MONITOR_MARK_EXISTING_AS_SEEN", "1") != "0",
    )

    if st.button("Guardar monitor", use_container_width=True):
        actualizar_env_local(
            ROOT_DIR,
            {
                "MONITOR_INTERVAL_SECONDS": str(int(interval)),
                "PHISHING_THRESHOLD": str(int(threshold)),
                "MONITOR_ANALYSIS_MODE": mode,
                "MONITOR_HEUR_WEIGHT": str(int(heur_weight)),
                "GMAIL_MONITOR_QUERY": query.strip(),
                "GMAIL_MONITOR_LIMIT": str(int(limit)),
                "MONITOR_MARK_EXISTING_AS_SEEN": "1" if mark_existing else "0",
            },
        )
        st.success("Configuración del monitor guardada.")


def main() -> None:
    """Renderiza la pantalla de configuración."""
    cargar_env_local(ROOT_DIR)
    valores = leer_env_file(ENV_LOCAL_PATH)

    st.title("Configuración")
    st.markdown(
        "Centraliza la cuenta de Gmail, el destino de Telegram y los parámetros "
        "que usan tanto la detección como el monitor automático."
    )

    _mostrar_config_gmail()
    st.markdown("---")
    _mostrar_config_telegram(valores)
    st.markdown("---")
    _mostrar_config_monitor(valores)
