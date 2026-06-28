"""Pantalla informativa que redirige a las apps separadas del proyecto."""

import streamlit as st

# Punto de entrada mínimo: mantiene separadas las dos herramientas reales
# para evitar mezclar en una misma pantalla entrenamiento y detección. Esta
# página funciona como índice cuando se ejecuta `streamlit run src/app.py`.
st.title("TFG - Sistema de detección de phishing")
st.markdown(
    "Esta aplicación ya no incluye entrenamiento y detección juntos. "
    "Usa una de las dos aplicaciones separadas a continuación."
)
st.markdown("### Ejecutables disponibles:")
st.markdown("- `streamlit run src/detect_app.py` → interfaz de detección")
st.markdown("- `streamlit run src/train_app.py` → interfaz de entrenamiento")
st.markdown(
    "Si defines `TRAINING_PASSWORD` en el entorno, la app de entrenamiento mostrará un campo de contraseña."
)
