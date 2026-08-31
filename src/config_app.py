"""Pantalla de configuración centralizada del sistema."""

import html
import os

import streamlit as st

from sistema_phishing.backend_client import (
    DEFAULT_BACKEND_URL,
    BackendClient,
    BackendClientError,
    normalize_backend_url,
)
from sistema_phishing.defaults import (
    DEFAULT_HEUR_WEIGHT,
    DEFAULT_NEURAL_WEIGHT,
    DEFAULT_PHISHING_THRESHOLD,
)
from sistema_phishing.env_loader import (
    actualizar_env_cliente,
    cargar_env_cliente,
    leer_env_file,
)
from sistema_phishing.gmail_client import (
    GmailIntegrationError,
    construir_servicio_gmail,
    obtener_perfil_gmail,
)
from sistema_phishing.model_config import (
    DEFAULT_HIPERPARAMETROS,
    HiperparametrosModelo,
)
from sistema_phishing.runtime_paths import (
    client_env_path,
    gmail_credentials_path,
    gmail_token_path,
)
from sistema_phishing.telegram_notifier import (
    TelegramNotificationError,
    TelegramNotifier,
)
from ui_components import (
    aplicar_estilos_base,
    encabezado_pagina,
    estado_badge,
    render_html,
)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cargar_env_cliente(ROOT_DIR)
ENV_LOCAL_PATH = str(client_env_path(ROOT_DIR))
GMAIL_CREDENTIALS_PATH = str(gmail_credentials_path(ROOT_DIR))
GMAIL_TOKEN_PATH = str(gmail_token_path(ROOT_DIR))


def aplicar_estilos_configuracion() -> None:
    """Aplica estilos locales para la pantalla de configuración."""
    aplicar_estilos_base()


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


def _mostrar_estado_general(valores: dict) -> None:
    """Muestra el estado global de Gmail, Telegram y monitor."""
    gmail_ok = os.path.exists(GMAIL_TOKEN_PATH)
    telegram_ok = bool(
        valores.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
        and valores.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
    )
    interval = _valor_entero(valores, "MONITOR_INTERVAL_SECONDS", 120)
    monitor_mode = html.escape(valores.get("MONITOR_ANALYSIS_MODE", "combinado"))

    render_html(
        f"""
        <div class="ui-grid ui-grid-3">
            <div class="ui-card">
                <div class="ui-label">Gmail</div>
                <div class="ui-value">{estado_badge(gmail_ok, "Conectado", "Pendiente")}</div>
                <div class="ui-note">Token local: <code>{os.path.basename(GMAIL_TOKEN_PATH)}</code></div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Telegram</div>
                <div class="ui-value">{estado_badge(telegram_ok, "Configurado", "Pendiente")}</div>
                <div class="ui-note">Bot y chat para alertas del monitor.</div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Monitor</div>
                <div class="ui-value">Cada {interval}s</div>
                <div class="ui-note">Modo: {monitor_mode}</div>
            </div>
        </div>
        """
    )


def _mostrar_config_gmail() -> None:
    """Muestra y gestiona la cuenta Gmail usada por detección y monitor."""
    st.markdown("### Gmail")
    col_info, col_actions = st.columns([2, 1])

    with col_info:
        st.caption(f"Credenciales locales: `{os.path.basename(GMAIL_CREDENTIALS_PATH)}`")
        try:
            perfil = _perfil_gmail()
            if perfil:
                st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
            else:
                st.info("No hay ninguna cuenta de Gmail conectada.")
        except Exception as exc:  # noqa: BLE001 - límite de la integración UI
            st.error(f"No se pudo leer la cuenta conectada: {exc}")

    with col_actions:
        if st.button("Conectar Gmail", use_container_width=True, type="primary"):
            try:
                servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
                perfil = obtener_perfil_gmail(servicio)
                st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
            except GmailIntegrationError as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 - límite de la integración UI
                st.error(f"No se pudo conectar con Gmail: {exc}")

        if st.button("Cambiar cuenta", use_container_width=True):
            if os.path.exists(GMAIL_TOKEN_PATH):
                os.remove(GMAIL_TOKEN_PATH)
            st.session_state.pop("gmail_email", None)
            st.session_state.pop("gmail_resultados", None)
            st.session_state.pop("gmail_tipo_analisis", None)
            st.info("Sesión eliminada. Pulsa Conectar Gmail para elegir otra cuenta.")


def _mostrar_config_telegram(valores: dict) -> None:
    """Muestra y guarda la configuración de Telegram."""
    st.markdown("### Telegram")
    token_actual = valores.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_actual = valores.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
    col_bot, col_chat = st.columns(2)
    col_bot.metric("Bot", _mask_secret(token_actual))
    col_chat.metric("Chat destino", chat_actual or "No configurado")

    token_nuevo = st.text_input(
        "Nuevo token del bot",
        type="password",
        placeholder="Déjalo vacío para conservar el actual",
    )
    chat_id = st.text_input("Chat ID destino", value=chat_actual)

    col_guardar, col_probar = st.columns(2)
    if col_guardar.button("Guardar Telegram", use_container_width=True, type="primary"):
        nuevos_valores = {"TELEGRAM_CHAT_ID": chat_id.strip()}
        if token_nuevo.strip():
            nuevos_valores["TELEGRAM_BOT_TOKEN"] = token_nuevo.strip()
        actualizar_env_cliente(ROOT_DIR, nuevos_valores)
        st.success("Configuración de Telegram guardada.")

    if col_probar.button("Probar Telegram", use_container_width=True):
        cargar_env_cliente(ROOT_DIR)
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat = chat_id.strip() or os.getenv("TELEGRAM_CHAT_ID", "")
        try:
            TelegramNotifier(token, chat).enviar_mensaje(
                "Prueba de configuración: el sistema de phishing puede enviar alertas a este chat."
            )
            st.success("Mensaje de prueba enviado.")
        except TelegramNotificationError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - límite de la integración UI
            st.error(f"No se pudo enviar el mensaje: {exc}")


def _mostrar_config_monitor(valores: dict) -> None:
    """Muestra y guarda los parámetros del monitor."""
    st.markdown("### Monitor")
    interval = st.number_input(
        "Intervalo entre comprobaciones (segundos)",
        min_value=10,
        max_value=86400,
        value=_valor_entero(valores, "MONITOR_INTERVAL_SECONDS", 120),
    )
    threshold = st.slider(
        "Umbral de alerta",
        0,
        100,
        int(_valor_float(valores, "PHISHING_THRESHOLD", DEFAULT_PHISHING_THRESHOLD)),
    )
    mode_options = ["combinado", "heuristico", "neural"]
    mode = st.selectbox(
        "Modo de análisis",
        mode_options,
        index=mode_options.index(valores.get("MONITOR_ANALYSIS_MODE", "combinado"))
        if valores.get("MONITOR_ANALYSIS_MODE", "combinado") in mode_options
        else 0,
        key="monitor_mode",
    )
    heur_weight = st.slider(
        "Peso heurístico (%)",
        0,
        100,
        _valor_entero(valores, "MONITOR_HEUR_WEIGHT", DEFAULT_HEUR_WEIGHT),
        disabled=mode != "combinado",
        key="monitor_heur_weight",
    )
    if mode == "combinado":
        neural_weight = 100 - int(heur_weight)
        st.markdown(f"**Peso neuronal (%)**: {neural_weight} _(derivado automáticamente)_")
    else:
        neural_weight = _valor_entero(valores, "MONITOR_NEURAL_WEIGHT", DEFAULT_NEURAL_WEIGHT)
    query = st.text_input(
        "Consulta de Gmail del monitor",
        value=valores.get("GMAIL_MONITOR_QUERY", "in:inbox newer_than:1d"),
        key="monitor_query",
    )
    limit = st.number_input(
        "Máximo de correos por ciclo",
        min_value=1,
        max_value=100,
        value=_valor_entero(valores, "GMAIL_MONITOR_LIMIT", 20),
        key="monitor_limit",
    )
    mark_existing = st.checkbox(
        "Primera ejecución: marcar correos existentes como vistos",
        value=valores.get("MONITOR_MARK_EXISTING_AS_SEEN", "1") != "0",
        key="monitor_mark_existing",
    )

    if st.button("Guardar monitor", use_container_width=True, type="primary"):
        actualizar_env_cliente(
            ROOT_DIR,
            {
                "MONITOR_INTERVAL_SECONDS": str(int(interval)),
                "PHISHING_THRESHOLD": str(int(threshold)),
                "MONITOR_ANALYSIS_MODE": mode,
                "MONITOR_HEUR_WEIGHT": str(int(heur_weight)),
                "MONITOR_NEURAL_WEIGHT": str(int(neural_weight)),
                "GMAIL_MONITOR_QUERY": query.strip(),
                "GMAIL_MONITOR_LIMIT": str(int(limit)),
                "MONITOR_MARK_EXISTING_AS_SEEN": "1" if mark_existing else "0",
            },
        )
        st.success("Configuración del monitor guardada.")


def _mostrar_config_backend(valores: dict) -> None:
    """Configura el único backend que comparten todos los clientes."""
    st.markdown("### Backend central")
    st.caption(
        "Streamlit, el monitor y la extensión consumen esta misma API. Los modelos "
        "solo existen en el servidor y una actualización se aplica a todos."
    )
    current_url = valores.get(
        "PHISHING_BACKEND_URL",
        os.getenv("PHISHING_BACKEND_URL", DEFAULT_BACKEND_URL),
    )
    backend_url = st.text_input(
        "URL del backend",
        value=current_url,
        help="En local: http://127.0.0.1:8766. En despliegue puede ser HTTPS.",
    )
    token_actual = valores.get(
        "BACKEND_ADMIN_TOKEN",
        os.getenv("BACKEND_ADMIN_TOKEN", ""),
    )
    admin_token = st.text_input(
        "Nuevo token de administración",
        type="password",
        placeholder="Vacío conserva el actual",
        help="Protege entrenamiento y borrado; no se envía en /analyze.",
    )

    col_save, col_test = st.columns(2)
    if col_save.button("Guardar backend", use_container_width=True, type="primary"):
        try:
            normalized = normalize_backend_url(backend_url)
        except ValueError as exc:
            st.error(str(exc))
        else:
            updates = {"PHISHING_BACKEND_URL": normalized}
            if admin_token.strip():
                updates["BACKEND_ADMIN_TOKEN"] = admin_token.strip()
            actualizar_env_cliente(ROOT_DIR, updates)
            st.success(
                "Backend guardado. Configura la misma URL en Opciones de la extensión."
            )

    if col_test.button("Probar backend", use_container_width=True):
        try:
            client = BackendClient(
                backend_url,
                admin_token=admin_token.strip() or token_actual,
            )
            health = client.health()
            versions = ", ".join(
                f"{language.upper()}: {model.get('version') or 'fallback'}"
                for language, model in health.get("models", {}).items()
            )
            st.success(f"Backend conectado. {versions}")
        except (ValueError, BackendClientError) as exc:
            st.error(str(exc))


def _hiperparametros_desde_payload(payload: dict) -> HiperparametrosModelo:
    values = dict(payload)
    for key in ("tfidf_ngram_range", "mlp_hidden_layer_sizes"):
        if key in values:
            values[key] = tuple(int(item) for item in values[key])
    return HiperparametrosModelo(**values)


def _cliente_backend(valores: dict) -> BackendClient:
    return BackendClient(
        valores.get("PHISHING_BACKEND_URL", DEFAULT_BACKEND_URL),
        admin_token=valores.get("BACKEND_ADMIN_TOKEN", ""),
    )


def _mostrar_config_neural(valores: dict) -> None:
    """Administra por API los ajustes que pertenecen al servidor central."""
    st.markdown("### Ajustes centrales del servidor")
    st.caption(
        "Se guardan en el backend, no en este cliente. Sus cambios afectan a todos "
        "los clientes; los hiperparámetros se aplican al siguiente entrenamiento."
    )
    client = _cliente_backend(valores)
    try:
        settings = client.settings()
    except (ValueError, BackendClientError) as exc:
        st.error(f"No se pueden leer los ajustes centrales: {exc}")
        return

    analysis = settings["analysis_defaults"]
    mode_options = ["combinado", "heuristico", "neural"]
    mode = st.selectbox(
        "Modo predeterminado del servidor",
        mode_options,
        index=mode_options.index(analysis["mode"]),
        key="server_default_mode",
    )
    threshold = st.slider(
        "Umbral predeterminado",
        0,
        100,
        int(float(analysis["threshold"])),
        key="server_default_threshold",
    )
    heur_weight = st.slider(
        "Peso heurístico predeterminado (%)",
        0,
        100,
        int(analysis["heur_weight"]),
        disabled=mode != "combinado",
        key="server_default_heur_weight",
    )
    neural_weight = 100 - heur_weight if mode == "combinado" else int(
        analysis["neural_weight"]
    )
    high_confidence = st.slider(
        "Umbral de evidencia individual concluyente",
        0,
        100,
        int(float(analysis["high_confidence_threshold"])),
        key="server_high_confidence_threshold",
    )
    if st.button("Guardar ajustes de análisis en el servidor", use_container_width=True):
        try:
            client.update_settings(
                analysis_defaults={
                    "mode": mode,
                    "threshold": threshold,
                    "heur_weight": heur_weight,
                    "neural_weight": neural_weight,
                    "high_confidence_threshold": high_confidence,
                }
            )
        except BackendClientError as exc:
            st.error(str(exc))
        else:
            st.success("Ajustes centrales guardados en el servidor.")

    st.markdown("### Red neuronal (avanzado)")
    actuales = _hiperparametros_desde_payload(settings["training_defaults"])
    with st.expander("Vectorizador de texto (TF-IDF)", expanded=False):
        col1, col2, col3 = st.columns(3)
        ngram_min = col1.number_input(
            "N-grama mínimo", 1, 3, actuales.tfidf_ngram_range[0]
        )
        ngram_max = col2.number_input(
            "N-grama máximo", 1, 3, actuales.tfidf_ngram_range[1]
        )
        max_features = col3.number_input(
            "Vocabulario máximo", 100, 50000, actuales.tfidf_max_features, step=100
        )
        min_df = st.number_input(
            "Frecuencia mínima (min_df)", 1, 20, actuales.tfidf_min_df
        )

    with st.expander("Red neuronal (MLP)", expanded=False):
        capas_texto = st.text_input(
            "Neuronas por capa oculta",
            value=",".join(str(n) for n in actuales.mlp_hidden_layer_sizes),
        )
        col4, col5 = st.columns(2)
        activations = ["relu", "tanh", "logistic"]
        activation = col4.selectbox(
            "Función de activación",
            activations,
            index=activations.index(actuales.mlp_activation),
        )
        max_iter = col5.number_input(
            "Épocas máximas", 50, 5000, actuales.mlp_max_iter, step=50
        )
        col6, col7 = st.columns(2)
        alpha = col6.number_input(
            "Regularización (alpha)",
            0.0,
            1.0,
            float(actuales.mlp_alpha),
            step=0.0001,
            format="%.4f",
        )
        learning_rate = col7.number_input(
            "Velocidad de aprendizaje",
            0.00001,
            1.0,
            float(actuales.mlp_learning_rate_init),
            step=0.0001,
            format="%.5f",
        )
        early_stopping = st.checkbox(
            "Early stopping", value=actuales.mlp_early_stopping
        )

    if st.button(
        "Guardar hiperparámetros en el servidor",
        use_container_width=True,
        type="primary",
    ):
        try:
            capas = tuple(
                int(parte.strip())
                for parte in capas_texto.split(",")
                if parte.strip()
            )
            nuevos = HiperparametrosModelo(
                tfidf_ngram_range=(int(ngram_min), int(ngram_max)),
                tfidf_max_features=int(max_features),
                tfidf_min_df=int(min_df),
                mlp_hidden_layer_sizes=capas,
                mlp_activation=activation,
                mlp_alpha=float(alpha),
                mlp_learning_rate_init=float(learning_rate),
                mlp_max_iter=int(max_iter),
                mlp_early_stopping=bool(early_stopping),
            )
            client.update_settings(training_defaults=nuevos)
        except (TypeError, ValueError, BackendClientError) as exc:
            st.error(str(exc))
        else:
            st.success(
                "Hiperparámetros centrales guardados. Vuelve a entrenar para "
                "generar una nueva versión de los modelos."
            )

    if st.button("Restaurar hiperparámetros centrales", use_container_width=True):
        try:
            client.update_settings(training_defaults=DEFAULT_HIPERPARAMETROS)
        except BackendClientError as exc:
            st.error(str(exc))
        else:
            st.success("Valores centrales restaurados.")
            st.rerun()

def main() -> None:
    """Renderiza la pantalla de configuración."""
    aplicar_estilos_configuracion()
    cargar_env_cliente(ROOT_DIR)
    valores = leer_env_file(ENV_LOCAL_PATH)

    encabezado_pagina(
        "Preferencias del sistema",
        "Configuración",
        "Gestiona las preferencias del cliente y, por API, los ajustes del backend.",
        "Almacenamiento separado",
        "Los secretos del cliente permanecen en runtime/client y nunca se muestran completos.",
    )
    _mostrar_estado_general(valores)

    tab_conexiones, tab_monitor, tab_backend, tab_modelo = st.tabs(
        ["Conexiones", "Monitor", "Backend", "Red neuronal"]
    )
    with tab_conexiones:
        with st.container(border=True):
            _mostrar_config_gmail()
        with st.container(border=True):
            _mostrar_config_telegram(valores)
    with tab_monitor, st.container(border=True):
        _mostrar_config_monitor(valores)
    with tab_backend, st.container(border=True):
        _mostrar_config_backend(valores)
    with tab_modelo, st.container(border=True):
        _mostrar_config_neural(valores)
