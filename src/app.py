"""Punto de entrada principal con navegación entre las pantallas del TFG."""

import os

import streamlit as st

from sistema_phishing.backend_client import BackendClient
from sistema_phishing.env_loader import cargar_env_local, leer_env_file
from ui_components import (
    aplicar_estilos_base,
    encabezado_pagina,
    encabezado_seccion,
    estado_badge,
    render_html,
    render_marca,
)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_LOCAL_PATH = os.path.join(ROOT_DIR, ".env.local")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")
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
    render_marca()
    with st.container(key="top_navigation"):
        col_inicio, col_config, col_deteccion, col_monitor, col_entrenamiento = st.columns(5)
        if col_inicio.button("Inicio", use_container_width=True, disabled=vista == VISTA_INICIO):
            _cambiar_vista(VISTA_INICIO)
        if col_config.button(
            "Configuración",
            use_container_width=True,
            disabled=vista == VISTA_CONFIGURACION,
        ):
            _cambiar_vista(VISTA_CONFIGURACION)
        if col_deteccion.button(
            "Detección",
            use_container_width=True,
            disabled=vista == VISTA_DETECCION,
        ):
            _cambiar_vista(VISTA_DETECCION)
        if col_monitor.button(
            "Monitor",
            use_container_width=True,
            disabled=vista == VISTA_MONITOR,
        ):
            _cambiar_vista(VISTA_MONITOR)
        if col_entrenamiento.button(
            "Entrenamiento",
            use_container_width=True,
            disabled=vista == VISTA_ENTRENAMIENTO,
        ):
            _cambiar_vista(VISTA_ENTRENAMIENTO)


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
    try:
        backend_health = BackendClient().health()
        backend_ok = bool(backend_health.get("ok"))
        models_count = sum(
            bool(model.get("available"))
            for model in backend_health.get("models", {}).values()
        )
    except Exception:  # noqa: BLE001 - la portada debe poder explicar cómo arrancar
        backend_ok = False
        models_count = 0
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
                <div class="ui-label">Backend central</div>
                <div class="ui-value">{estado_badge(backend_ok, "Conectado", "Detenido")}</div>
                <div class="ui-note">{models_count}/2 artefactos encontrados; la vista de detección valida idioma e integridad.</div>
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
    encabezado_pagina(
        "Centro de operaciones · correo seguro",
        "Sistema de detección de phishing",
        "Analiza mensajes con reglas explicables y modelos neuronales centrales. "
        "La web envía cada correo al backend y presenta una respuesta clara y auditable.",
        "Arquitectura cliente-servidor",
        "Un único backend y los mismos modelos para web, Gmail y monitor.",
    )
    encabezado_seccion(
        "01",
        "Estado del sistema",
        "Disponibilidad de servicios e integraciones en este equipo.",
    )
    _mostrar_estado_inicio()

    encabezado_seccion(
        "02",
        "Áreas de trabajo",
        "Entra directamente en la tarea que necesites realizar.",
    )
    col_config, col_deteccion = st.columns(2)
    with col_config, st.container(border=True, key="home_config_card"):
        st.caption("INTEGRACIONES")
        st.subheader("Configuración")
        st.write("Conecta Gmail y Telegram y revisa los parámetros compartidos.")
        if st.button("Abrir configuración", use_container_width=True):
            _cambiar_vista(VISTA_CONFIGURACION)

    with col_deteccion, st.container(border=True, key="home_detect_card"):
        st.caption("ANÁLISIS PRINCIPAL")
        st.subheader("Detección")
        st.write("Analiza texto, archivos `.eml` o mensajes importados desde Gmail.")
        if st.button(
            "Analizar un correo",
            use_container_width=True,
            type="primary",
        ):
            _cambiar_vista(VISTA_DETECCION)

    col_monitor, col_entrenamiento = st.columns(2)
    with col_monitor, st.container(border=True, key="home_monitor_card"):
        st.caption("AUTOMATIZACIÓN")
        st.subheader("Monitor")
        st.write("Comprueba Gmail periódicamente y envía alertas por Telegram.")
        if st.button("Abrir monitor", use_container_width=True):
            _cambiar_vista(VISTA_MONITOR)

    with col_entrenamiento, st.container(border=True, key="home_train_card"):
        st.caption("MODELOS CENTRALES")
        st.subheader("Entrenamiento")
        st.write("Entrena y evalúa los modelos neuronales en español e inglés.")
        if st.button("Administrar modelos", use_container_width=True):
            _cambiar_vista(VISTA_ENTRENAMIENTO)

    encabezado_seccion(
        "03",
        "Comandos de operación",
        "Arranque manual del servidor y del proceso de monitorización.",
    )
    col_backend, col_mon = st.columns(2)
    with col_backend:
        st.code("python src/backend_server.py", language="powershell")
        st.caption("Backend obligatorio: análisis, entrenamiento y modelos compartidos.")
    with col_mon:
        st.code("python src/monitor_gmail.py", language="powershell")
        st.caption("Proceso 24/7 para revisar Gmail y enviar alertas.")


def main() -> None:
    """Renderiza la vista activa."""
    st.set_page_config(
        page_title="Sistema de detección de phishing",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    aplicar_estilos_globales()
    vista = _vista_actual()
    mostrar_navegacion(vista)

    if vista == VISTA_CONFIGURACION:
        import config_app

        config_app.main()
    elif vista == VISTA_DETECCION:
        import detect_app

        detect_app.main()
    elif vista == VISTA_MONITOR:
        import monitor_app

        monitor_app.main()
    elif vista == VISTA_ENTRENAMIENTO:
        import train_app

        train_app.main()
    else:
        mostrar_inicio()


if __name__ == "__main__":
    main()
