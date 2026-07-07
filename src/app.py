"""Punto de entrada principal con navegación entre las pantallas del TFG."""

import streamlit as st

import detect_app
import train_app


VISTA_INICIO = "inicio"
VISTA_DETECCION = "deteccion"
VISTA_ENTRENAMIENTO = "entrenamiento"


def _vista_actual() -> str:
    """Lee la vista seleccionada desde la URL."""
    vista = st.query_params.get("vista", VISTA_INICIO)
    if vista not in {VISTA_INICIO, VISTA_DETECCION, VISTA_ENTRENAMIENTO}:
        return VISTA_INICIO
    return vista


def _cambiar_vista(vista: str) -> None:
    """Cambia de pantalla dentro de la misma aplicación Streamlit."""
    st.query_params["vista"] = vista
    st.rerun()


def mostrar_navegacion(vista: str) -> None:
    """Muestra la navegación común entre inicio, detección y entrenamiento."""
    col_inicio, col_deteccion, col_entrenamiento = st.columns(3)
    if col_inicio.button("Inicio", use_container_width=True, disabled=vista == VISTA_INICIO):
        _cambiar_vista(VISTA_INICIO)
    if col_deteccion.button("Detección", use_container_width=True, disabled=vista == VISTA_DETECCION):
        _cambiar_vista(VISTA_DETECCION)
    if col_entrenamiento.button(
        "Entrenamiento",
        use_container_width=True,
        disabled=vista == VISTA_ENTRENAMIENTO,
    ):
        _cambiar_vista(VISTA_ENTRENAMIENTO)
    st.markdown("---")


def aplicar_estilos_globales() -> None:
    """Ajustes visuales comunes para todas las vistas."""
    st.markdown(
        """
        <style>
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def mostrar_inicio() -> None:
    """Pantalla inicial que actúa como pivote del sistema."""
    st.title("TFG - Sistema de detección de phishing")
    st.markdown(
        "Herramienta para analizar correos electrónicos mediante heurísticas, "
        "modelo neuronal y conexión opcional con Gmail."
    )

    col_deteccion, col_entrenamiento = st.columns(2)
    with col_deteccion:
        st.subheader("Detección")
        st.write("Analiza correos pegados, archivos `.eml` o mensajes importados desde Gmail.")
        if st.button("Ir a detección", use_container_width=True):
            _cambiar_vista(VISTA_DETECCION)

    with col_entrenamiento:
        st.subheader("Entrenamiento")
        st.write("Entrena y evalúa los modelos neuronales en español e inglés.")
        if st.button("Ir a entrenamiento", use_container_width=True):
            _cambiar_vista(VISTA_ENTRENAMIENTO)

    st.markdown("---")
    st.info("Ejecuta esta pantalla con `streamlit run src/app.py` para usar la navegación completa.")


def main() -> None:
    """Renderiza la vista activa."""
    aplicar_estilos_globales()
    vista = _vista_actual()
    mostrar_navegacion(vista)

    if vista == VISTA_DETECCION:
        detect_app.main()
    elif vista == VISTA_ENTRENAMIENTO:
        train_app.main()
    else:
        mostrar_inicio()


if __name__ == "__main__":
    main()
