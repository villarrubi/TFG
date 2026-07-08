"""Punto de entrada principal con navegación entre las pantallas del TFG."""

import os

import streamlit as st

import config_app
import detect_app
import monitor_app
import train_app
from sistema_phishing.env_loader import cargar_env_local, leer_env_file
from ui_components import aplicar_estilos_base, estado_badge, render_html


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_LOCAL_PATH = os.path.join(ROOT_DIR, ".env.local")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")
MODEL_PATH_ES = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
MODEL_PATH_EN = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")
VISTA_INICIO = "inicio"
VISTA_CONFIGURACION = "configuracion"
VISTA_DETECCION = "deteccion"
VISTA_MONITOR = "monitor"
VISTA_ENTRENAMIENTO = "entrenamiento"


def _vista_actual() -> str:
    """Lee la vista seleccionada desde la URL."""
    vista = st.query_params.get("vista", VISTA_INICIO)
    if vista not in {VISTA_INICIO, VISTA_CONFIGURACION, VISTA_DETECCION, VISTA_MONITOR, VISTA_ENTRENAMIENTO}:
        return VISTA_INICIO
    return vista


def _cambiar_vista(vista: str) -> None:
    """Cambia de pantalla dentro de la misma aplicación Streamlit."""
    st.query_params["vista"] = vista
    st.rerun()


def mostrar_navegacion(vista: str) -> None:
    """Muestra la navegación común entre inicio, detección y entrenamiento."""
    col_inicio, col_config, col_deteccion, col_monitor, col_entrenamiento = st.columns(5)
    if col_inicio.button("Inicio", use_container_width=True, disabled=vista == VISTA_INICIO):
        _cambiar_vista(VISTA_INICIO)
    if col_config.button("Configuración", use_container_width=True, disabled=vista == VISTA_CONFIGURACION):
        _cambiar_vista(VISTA_CONFIGURACION)
    if col_deteccion.button("Detección", use_container_width=True, disabled=vista == VISTA_DETECCION):
        _cambiar_vista(VISTA_DETECCION)
    if col_monitor.button("Monitor", use_container_width=True, disabled=vista == VISTA_MONITOR):
        _cambiar_vista(VISTA_MONITOR)
    if col_entrenamiento.button(
        "Entrenamiento",
        use_container_width=True,
        disabled=vista == VISTA_ENTRENAMIENTO,
    ):
        _cambiar_vista(VISTA_ENTRENAMIENTO)
    st.markdown("---")


def aplicar_estilos_globales() -> None:
    """Ajustes visuales comunes para todas las vistas."""
    aplicar_estilos_base()


def _mostrar_estado_inicio() -> None:
    """Muestra el estado general del sistema en la pantalla de inicio."""
    cargar_env_local(ROOT_DIR)
    valores = leer_env_file(ENV_LOCAL_PATH)
    gmail_ok = os.path.exists(GMAIL_TOKEN_PATH)
    telegram_ok = bool(
        valores.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
        and valores.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
    )
    models_count = sum(1 for path in (MODEL_PATH_ES, MODEL_PATH_EN) if os.path.exists(path))
    extension_ready = os.path.exists(os.path.join(ROOT_DIR, "extension_gmail", "manifest.json"))

    render_html(
        f"""
        <div class="ui-grid ui-grid-4">
            <div class="ui-card">
                <div class="ui-label">Gmail</div>
                <div class="ui-value">{estado_badge(gmail_ok, "Conectado", "Sin token")}</div>
                <div class="ui-note">Permite analizar correos reales desde la API.</div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Telegram</div>
                <div class="ui-value">{estado_badge(telegram_ok, "Configurado", "Pendiente")}</div>
                <div class="ui-note">Envía alertas cuando el monitor detecta riesgo.</div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Modelos</div>
                <div class="ui-value">{models_count}/2 disponibles</div>
                <div class="ui-note">Español e inglés pueden entrenarse por separado.</div>
            </div>
            <div class="ui-card">
                <div class="ui-label">Extensión Gmail</div>
                <div class="ui-value">{estado_badge(extension_ready, "Disponible", "No encontrada")}</div>
                <div class="ui-note">Integra el análisis dentro de Gmail Web.</div>
            </div>
        </div>
        """
    )


def mostrar_inicio() -> None:
    """Pantalla inicial que actúa como pivote del sistema."""
    st.title("Sistema de detección de phishing")
    st.caption("Análisis heurístico, modelo neuronal, Gmail Web, monitor automático y alertas por Telegram.")
    _mostrar_estado_inicio()

    col_config, col_deteccion = st.columns(2)
    with col_config:
        st.subheader("Configuración")
        st.write("Gestiona Gmail, Telegram y los parámetros del monitor.")
        if st.button("Ir a configuración", use_container_width=True):
            _cambiar_vista(VISTA_CONFIGURACION)

    with col_deteccion:
        st.subheader("Detección")
        st.write("Analiza correos pegados, archivos `.eml` o mensajes importados desde Gmail.")
        if st.button("Ir a detección", use_container_width=True):
            _cambiar_vista(VISTA_DETECCION)

    col_monitor, col_entrenamiento = st.columns(2)
    with col_monitor:
        st.subheader("Monitor")
        st.write("Comprueba Gmail periódicamente y envía alertas por Telegram.")
        if st.button("Ir a monitor", use_container_width=True):
            _cambiar_vista(VISTA_MONITOR)

    with col_entrenamiento:
        st.subheader("Entrenamiento")
        st.write("Entrena y evalúa los modelos neuronales en español e inglés.")
        if st.button("Ir a entrenamiento", use_container_width=True):
            _cambiar_vista(VISTA_ENTRENAMIENTO)

    st.markdown("### Comandos rápidos")
    col_ext, col_mon = st.columns(2)
    with col_ext:
        st.code("python src/gmail_extension_server.py", language="powershell")
        st.caption("Servidor local usado por la extensión de Gmail Web.")
    with col_mon:
        st.code("python src/monitor_gmail.py", language="powershell")
        st.caption("Proceso 24/7 para revisar Gmail y enviar alertas.")


def main() -> None:
    """Renderiza la vista activa."""
    aplicar_estilos_globales()
    vista = _vista_actual()
    mostrar_navegacion(vista)

    if vista == VISTA_CONFIGURACION:
        config_app.main()
    elif vista == VISTA_DETECCION:
        detect_app.main()
    elif vista == VISTA_MONITOR:
        monitor_app.main()
    elif vista == VISTA_ENTRENAMIENTO:
        train_app.main()
    else:
        mostrar_inicio()


if __name__ == "__main__":
    main()
