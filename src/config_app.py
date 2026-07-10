"""Pantalla de configuración centralizada del sistema."""

import os

import streamlit as st

from sistema_phishing.env_loader import actualizar_env_local, cargar_env_local, leer_env_file
from sistema_phishing.gmail_client import (
    GmailIntegrationError,
    construir_servicio_gmail,
    obtener_perfil_gmail,
)
from sistema_phishing.modelo_neural import DEFAULT_HIPERPARAMETROS, cargar_hiperparametros_desde_env
from sistema_phishing.telegram_notifier import TelegramNotifier, TelegramNotificationError
from ui_components import aplicar_estilos_base, estado_badge, render_html


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_LOCAL_PATH = os.path.join(ROOT_DIR, ".env.local")
GMAIL_CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")


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
                <div class="ui-note">Modo: {valores.get("MONITOR_ANALYSIS_MODE", "combinado")}</div>
            </div>
        </div>
        """
    )


def _mostrar_config_gmail() -> None:
    """Muestra y gestiona la cuenta Gmail usada por detección y monitor."""
    st.markdown("### Gmail")
    col_info, col_actions = st.columns([2, 1])

    with col_info:
        st.caption(f"Credenciales: `{GMAIL_CREDENTIALS_PATH}`")
        try:
            perfil = _perfil_gmail()
            if perfil:
                st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
            else:
                st.info("No hay ninguna cuenta de Gmail conectada.")
        except Exception as exc:
            st.error(f"No se pudo leer la cuenta conectada: {exc}")

    with col_actions:
        if st.button("Conectar Gmail", use_container_width=True):
            try:
                servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
                perfil = obtener_perfil_gmail(servicio)
                st.success(f"Cuenta conectada: {perfil.get('emailAddress', '')}")
            except GmailIntegrationError as exc:
                st.error(str(exc))
            except Exception as exc:
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
        int(_valor_float(valores, "PHISHING_THRESHOLD", 45)),
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
        _valor_entero(valores, "MONITOR_HEUR_WEIGHT", 60),
        disabled=mode != "combinado",
        key="monitor_heur_weight",
    )
    if mode == "combinado":
        neural_weight = 100 - int(heur_weight)
        st.markdown(f"**Peso neuronal (%)**: {neural_weight} _(derivado automáticamente)_")
    else:
        neural_weight = _valor_entero(valores, "MONITOR_NEURAL_WEIGHT", 40)
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

    if st.button("Guardar monitor", use_container_width=True):
        actualizar_env_local(
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
    """Muestra y guarda la configuración del backend centralizado."""
    st.markdown("### Backend centralizado")
    st.caption(
        "Estos valores permiten que la web, la extensión y el monitor consulten el mismo servicio HTTP "
        "en lugar de cargar modelos y reglas en cada cliente."
    )

    backend_url = st.text_input(
        "URL del backend para clientes",
        value=valores.get("BACKEND_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8766")),
        help="Ejemplo local: http://127.0.0.1:8766. En producción: https://detector.tu-dominio.com",
        key="backend_url",
    )
    backend_token_actual = valores.get("BACKEND_API_TOKEN", os.getenv("BACKEND_API_TOKEN", ""))
    st.caption(f"Token actual: {_mask_secret(backend_token_actual)}")
    backend_token = st.text_input(
        "Nuevo token del backend",
        type="password",
        placeholder="Déjalo vacío para conservar el actual",
        key="backend_token",
    )
    col_host, col_port = st.columns(2)
    host = col_host.text_input(
        "Host de escucha del backend",
        value=valores.get("BACKEND_HOST", "127.0.0.1"),
        key="backend_host",
    )
    port = col_port.number_input(
        "Puerto del backend",
        min_value=1,
        max_value=65535,
        value=_valor_entero(valores, "BACKEND_PORT", 8766),
        key="backend_port",
    )
    allowed_origins = st.text_input(
        "Orígenes CORS permitidos",
        value=valores.get("BACKEND_ALLOWED_ORIGINS", "*"),
        help="Usa * en local. En producción indica dominios separados por comas.",
        key="backend_allowed_origins",
    )
    mode_options = ["combinado", "heuristico", "neural"]
    mode = st.selectbox(
        "Modo de análisis del backend",
        mode_options,
        index=mode_options.index(valores.get("BACKEND_ANALYSIS_MODE", valores.get("MONITOR_ANALYSIS_MODE", "combinado")))
        if valores.get("BACKEND_ANALYSIS_MODE", valores.get("MONITOR_ANALYSIS_MODE", "combinado")) in mode_options
        else 0,
        key="backend_mode",
    )
    threshold = st.slider(
        "Umbral del backend (%)",
        0,
        100,
        int(_valor_float(valores, "BACKEND_PHISHING_THRESHOLD", _valor_float(valores, "PHISHING_THRESHOLD", 45))),
        key="backend_threshold",
    )
    heur_weight = st.slider(
        "Peso heurístico del backend (%)",
        0,
        100,
        _valor_entero(valores, "BACKEND_HEUR_WEIGHT", _valor_entero(valores, "MONITOR_HEUR_WEIGHT", 60)),
        disabled=mode != "combinado",
        key="backend_heur_weight",
    )
    neural_weight = 100 - int(heur_weight) if mode == "combinado" else _valor_entero(valores, "BACKEND_NEURAL_WEIGHT", 40)
    if mode == "combinado":
        st.markdown(f"**Peso neuronal del backend (%)**: {neural_weight} _(derivado automáticamente)_")

    if st.button("Guardar backend", use_container_width=True):
        nuevos_valores = {
            "BACKEND_URL": backend_url.strip().rstrip("/"),
            "BACKEND_HOST": host.strip(),
            "BACKEND_PORT": str(int(port)),
            "BACKEND_ALLOWED_ORIGINS": allowed_origins.strip(),
            "BACKEND_ANALYSIS_MODE": mode,
            "BACKEND_PHISHING_THRESHOLD": str(int(threshold)),
            "BACKEND_HEUR_WEIGHT": str(int(heur_weight)),
            "BACKEND_NEURAL_WEIGHT": str(int(neural_weight)),
        }
        if backend_token.strip():
            nuevos_valores["BACKEND_API_TOKEN"] = backend_token.strip()
        actualizar_env_local(ROOT_DIR, nuevos_valores)
        st.success("Configuración del backend guardada.")


def _mostrar_config_gmail_extension(valores: dict) -> None:
    """Muestra y guarda la configuración de la extensión Gmail Web."""
    st.markdown("### Extensión Gmail Web")
    st.caption(
        "Estos valores configuran el servidor local usado por la extensión de Gmail Web. "
        "Los cambios afectan al servidor si se reinicia después de guardar."
    )

    host = st.text_input(
        "Host del servidor de extensión",
        value=valores.get("GMAIL_EXTENSION_HOST", "127.0.0.1"),
        help="Host local donde escucha el servidor para la extensión de Gmail.",
        key="gmail_ext_host",
    )
    port = st.number_input(
        "Puerto del servidor de extensión",
        min_value=1,
        max_value=65535,
        value=_valor_entero(valores, "GMAIL_EXTENSION_PORT", 8765),
        help="Puerto local usado por la extensión de Gmail Web.",
        key="gmail_ext_port",
    )
    mode_options = ["combinado", "heuristico", "neural"]
    mode = st.selectbox(
        "Modo de análisis",
        mode_options,
        index=mode_options.index(valores.get("GMAIL_EXTENSION_MODE", "combinado"))
        if valores.get("GMAIL_EXTENSION_MODE", "combinado") in mode_options
        else 0,
        key="gmail_ext_mode",
    )
    threshold = st.slider(
        "Umbral de phishing (%)",
        0,
        100,
        int(_valor_float(valores, "GMAIL_EXTENSION_THRESHOLD", 45.0)),
        key="gmail_ext_threshold",
    )
    heur_weight = st.slider(
        "Peso heurístico (%)",
        0,
        100,
        _valor_entero(valores, "GMAIL_EXTENSION_HEUR_WEIGHT", 60),
        disabled=mode != "combinado",
        key="gmail_ext_heur_weight",
    )
    if mode == "combinado":
        neural_weight = 100 - int(heur_weight)
        st.markdown(f"**Peso neuronal (%)**: {neural_weight} _(derivado automáticamente)_")
    else:
        neural_weight = _valor_entero(valores, "GMAIL_EXTENSION_NEURAL_WEIGHT", 40)
    model_es = st.text_input(
        "Ruta del modelo español",
        value=valores.get("GMAIL_EXTENSION_MODEL_ES", os.path.join(ROOT_DIR, "modelo_neural_es.joblib")),
        key="gmail_ext_model_es",
    )
    model_en = st.text_input(
        "Ruta del modelo inglés",
        value=valores.get("GMAIL_EXTENSION_MODEL_EN", os.path.join(ROOT_DIR, "modelo_neural_en.joblib")),
        key="gmail_ext_model_en",
    )

    if st.button("Guardar configuración de Gmail Web", use_container_width=True):
        actualizar_env_local(
            ROOT_DIR,
            {
                "GMAIL_EXTENSION_HOST": host.strip(),
                "GMAIL_EXTENSION_PORT": str(int(port)),
                "GMAIL_EXTENSION_MODE": mode,
                "GMAIL_EXTENSION_THRESHOLD": str(int(threshold)),
                "GMAIL_EXTENSION_HEUR_WEIGHT": str(int(heur_weight)),
                "GMAIL_EXTENSION_NEURAL_WEIGHT": str(int(neural_weight)),
                "GMAIL_EXTENSION_MODEL_ES": model_es.strip(),
                "GMAIL_EXTENSION_MODEL_EN": model_en.strip(),
            },
        )
        st.success("Configuración de Gmail Web guardada.")


def _mostrar_config_neural(valores: dict) -> None:
    """Muestra y guarda los hiperparámetros de las redes neuronales (ES/EN).

    Estos valores se guardan en .env.local y se leen automáticamente la
    próxima vez que se entrene un modelo desde la pestaña "Entrenar" (o desde
    cualquier otro sitio que entrene sin indicar hiperparámetros propios).
    No afectan a modelos ya entrenados: hay que volver a entrenar para que
    el cambio se note, incluido el modelo que usa el monitor de Gmail.
    """
    st.markdown("### Red neuronal (avanzado)")
    st.caption(
        "Estos valores se aplican la PRÓXIMA vez que entrenes un modelo en la pestaña "
        "'Entrenar' de la app de entrenamiento. Los modelos ya entrenados no cambian solos."
    )

    actuales = cargar_hiperparametros_desde_env()

    with st.expander("Vectorizador de texto (TF-IDF)", expanded=False):
        col1, col2, col3 = st.columns(3)
        ngram_min = col1.number_input(
            "N-grama mínimo", min_value=1, max_value=3, value=actuales.tfidf_ngram_range[0],
            help="1 = palabras sueltas.",
        )
        ngram_max = col2.number_input(
            "N-grama máximo", min_value=1, max_value=3, value=actuales.tfidf_ngram_range[1],
            help="2 = incluye también parejas de palabras seguidas (bigramas). Súbelo a 3 para trigramas.",
        )
        max_features = col3.number_input(
            "Vocabulario máximo (max_features)", min_value=100, max_value=50000, step=100,
            value=actuales.tfidf_max_features,
            help="Nº máximo de términos distintos que aprende el modelo. Más alto = más detalle, más lento.",
        )
        min_df = st.number_input(
            "min_df (frecuencia mínima)", min_value=1, max_value=20, value=actuales.tfidf_min_df,
            help="Ignora palabras que aparecen en menos de N correos del dataset. Súbelo para reducir ruido.",
        )

    with st.expander("Red neuronal (MLP)", expanded=False):
        capas_texto = st.text_input(
            "Neuronas por capa oculta",
            value=",".join(str(n) for n in actuales.mlp_hidden_layer_sizes),
            help="Separadas por comas. Ej: '64,32' = dos capas ocultas de 64 y 32 neuronas. '100' = una sola capa.",
        )
        col4, col5 = st.columns(2)
        activation = col4.selectbox(
            "Función de activación", ["relu", "tanh", "logistic"],
            index=["relu", "tanh", "logistic"].index(actuales.mlp_activation)
            if actuales.mlp_activation in ["relu", "tanh", "logistic"] else 0,
        )
        max_iter = col5.number_input(
            "Épocas máximas (max_iter)", min_value=50, max_value=5000, step=50, value=actuales.mlp_max_iter,
        )
        col6, col7 = st.columns(2)
        alpha = col6.number_input(
            "Regularización (alpha)", min_value=0.0, max_value=1.0, value=float(actuales.mlp_alpha),
            step=0.0001, format="%.4f",
            help="Súbelo si el modelo memoriza el entrenamiento pero falla con correos nuevos (overfitting).",
        )
        learning_rate = col7.number_input(
            "Velocidad de aprendizaje (learning_rate_init)", min_value=0.00001, max_value=1.0,
            value=float(actuales.mlp_learning_rate_init), step=0.0001, format="%.5f",
        )
        early_stopping = st.checkbox(
            "Early stopping (parar antes si deja de mejorar)", value=actuales.mlp_early_stopping,
        )

    if st.button("Guardar hiperparámetros de la red neuronal", use_container_width=True):
        if ngram_min > ngram_max:
            st.error("El n-grama mínimo no puede ser mayor que el máximo.")
        else:
            try:
                capas = tuple(int(parte.strip()) for parte in capas_texto.split(",") if parte.strip())
                if not capas:
                    raise ValueError("Debes indicar al menos una capa.")
            except ValueError:
                st.error("Las neuronas por capa deben ser números enteros separados por comas, p.ej. '64,32'.")
            else:
                actualizar_env_local(
                    ROOT_DIR,
                    {
                        "NEURAL_NGRAM_MIN": str(int(ngram_min)),
                        "NEURAL_NGRAM_MAX": str(int(ngram_max)),
                        "NEURAL_MAX_FEATURES": str(int(max_features)),
                        "NEURAL_MIN_DF": str(int(min_df)),
                        "NEURAL_HIDDEN_LAYERS": ",".join(str(n) for n in capas),
                        "NEURAL_ACTIVATION": activation,
                        "NEURAL_MAX_ITER": str(int(max_iter)),
                        "NEURAL_ALPHA": str(alpha),
                        "NEURAL_LEARNING_RATE": str(learning_rate),
                        "NEURAL_EARLY_STOPPING": "1" if early_stopping else "0",
                    },
                )
                st.success(
                    "Hiperparámetros guardados. Ve a la app de entrenamiento y pulsa "
                    "'Entrenar modelo desde CSV' para crear un modelo nuevo con estos valores."
                )

    if st.button("Restaurar valores por defecto", use_container_width=True):
        d = DEFAULT_HIPERPARAMETROS
        actualizar_env_local(
            ROOT_DIR,
            {
                "NEURAL_NGRAM_MIN": str(d.tfidf_ngram_range[0]),
                "NEURAL_NGRAM_MAX": str(d.tfidf_ngram_range[1]),
                "NEURAL_MAX_FEATURES": str(d.tfidf_max_features),
                "NEURAL_MIN_DF": str(d.tfidf_min_df),
                "NEURAL_HIDDEN_LAYERS": ",".join(str(n) for n in d.mlp_hidden_layer_sizes),
                "NEURAL_ACTIVATION": d.mlp_activation,
                "NEURAL_MAX_ITER": str(d.mlp_max_iter),
                "NEURAL_ALPHA": str(d.mlp_alpha),
                "NEURAL_LEARNING_RATE": str(d.mlp_learning_rate_init),
                "NEURAL_EARLY_STOPPING": "1" if d.mlp_early_stopping else "0",
            },
        )
        st.success("Restaurados los valores por defecto. Recuerda volver a entrenar para aplicarlos.")
        st.rerun()

def main() -> None:
    """Renderiza la pantalla de configuración."""
    aplicar_estilos_configuracion()
    cargar_env_local(ROOT_DIR)
    valores = leer_env_file(ENV_LOCAL_PATH)

    st.title("Configuración")
    st.caption("Gestiona Gmail, Telegram y los parámetros compartidos por la detección y el monitor.")
    _mostrar_estado_general(valores)

    _mostrar_config_gmail()
    st.markdown("---")
    _mostrar_config_telegram(valores)
    st.markdown("---")
    _mostrar_config_backend(valores)
    st.markdown("---")
    _mostrar_config_monitor(valores)
    st.markdown("---")
    _mostrar_config_gmail_extension(valores)
    st.markdown("---")
    _mostrar_config_neural(valores)
