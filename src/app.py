import streamlit as st

from sistema_phishing.analizador_email import construir_texto_para_analisis, parsear_eml_bytes
from sistema_phishing.heuristicas import analizar_correo


def _color_riesgo(score: float) -> str:
    """Devuelve un color hex para un puntaje de riesgo de 0 a 100."""
    score = max(0.0, min(100.0, score))
    if score <= 30:
        # Verde a amarillo
        ratio = score / 30.0
        r = int(76 + (255 - 76) * ratio)
        g = int(175 + (235 - 175) * ratio)
        b = int(80 - (80 * ratio))
    elif score <= 70:
        # Amarillo a naranja
        ratio = (score - 30.0) / 40.0
        r = int(255)
        g = int(235 - (128 * ratio))
        b = int(0 + (0 * ratio))
    else:
        # Naranja a rojo
        ratio = (score - 70.0) / 30.0
        r = int(255)
        g = int(107 - (40 * ratio))
        b = int(0 + (0 * ratio))
    return f"#{r:02x}{g:02x}{b:02x}"


def mostrar_resultado(resultado):
    """Muestra en Streamlit los resultados del análisis de phishing."""
    st.subheader("Resultado del análisis")

    nivel = "No parece phishing" if not resultado["is_phishing"] else "Phishing probable"
    st.write("**Evaluación global:**", nivel)

    risk_score = int(round(resultado["risk_score"]))
    color = _color_riesgo(risk_score)

    col1, col2 = st.columns([1, 3])
    col1.metric("Puntuación de riesgo", f"{risk_score}%")
    col2.markdown(
        f"""
        <div style='width: 100%; background: #e0e0e0; border-radius: 16px; padding: 6px;'>
            <div style='width: {risk_score}%; min-width: 4px; height: 34px; border-radius: 12px; background: {color}; box-shadow: inset 0 0 8px rgba(0,0,0,0.12); transition: width 0.5s ease;'></div>
        </div>
        <div style='display:flex; justify-content: space-between; font-size: 0.85rem; color: #333; margin-top: 6px;'>
            <span>0</span>
            <span>50</span>
            <span>100</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Resumen del análisis")
    st.write(f"URLs detectadas: {len(resultado['urls'])}")
    st.write(f"Enlaces HTML analizados: {len(resultado.get('anchors', []))}")
    st.write(f"Cabeceras incluidas: {len(resultado.get('headers', {}))}")

    st.markdown("### Señales detectadas")
    detalle_senales = [
        {"Regla": nombre.replace("_", " ").capitalize(), "Activo": "Sí" if valor else "No"}
        for nombre, valor in resultado["signals"].items()
    ]
    st.table(detalle_senales)

    with st.expander("Explicación detallada de las señales"):
        for item in resultado["explanation"]:
            st.write(f"- {item}")

    if resultado["urls"]:
        st.markdown("### Enlaces detectados")
        for enlace in resultado["urls"]:
            st.write(f"- {enlace}")

    if resultado.get("anchors"):
        st.markdown("### Anclas detectadas en HTML")
        for anchor in resultado["anchors"]:
            st.write(f"- Texto: {anchor['text']} / URL: {anchor['href']}")

    if resultado.get("headers"):
        with st.expander("Cabeceras analizadas"):
            st.write({
                key: value
                for key, value in resultado["headers"].items()
                if key.lower() in ["from", "to", "subject", "reply-to", "return-path", "message-id"]
            })


def main():
    """Configuración principal de la aplicación Streamlit y control del flujo."""
    st.title("TFG - Sistema de detección de phishing en correos electrónicos")
    st.markdown(
        "Este prototipo analiza correos electrónicos mediante reglas heurísticas para identificar posibles ataques de phishing."
    )

    modo = st.radio("Modo de entrada", ["Pegar texto del correo", "Subir archivo .eml"])
    texto_para_analisis = ""
    datos_email = None

    if modo == "Pegar texto del correo":
        # Permite al usuario proporcionar el contenido completo del correo manualmente.
        texto_para_analisis = st.text_area("Pega aquí el contenido del correo (cabeceras + cuerpo):")
    else:
        archivo = st.file_uploader("Sube un archivo .eml", type=["eml"])
        if archivo is not None:
            # Parseamos el correo .eml e inferimos el texto para análisis.
            datos_email = parsear_eml_bytes(archivo.getvalue())
            texto_para_analisis = construir_texto_para_analisis(datos_email)
            st.markdown("#### Correo cargado")
            st.write({
                "From": datos_email["from"],
                "To": datos_email["to"],
                "Subject": datos_email["subject"],
                "Adjuntos": datos_email["attachments"],
            })

    if st.button("Analizar correo"):
        if not texto_para_analisis.strip():
            st.warning("Introduce texto de correo o sube un archivo .eml antes de analizar.")
        else:
            # Usamos el análisis estructurado si hay datos EML, o analizamos el texto plano.
            if datos_email:
                resultado = analizar_correo(datos_email)
            else:
                resultado = analizar_correo(texto_para_analisis)
            mostrar_resultado(resultado)

    with st.expander("Mejoras futuras y notas técnicas"):
        st.markdown(
            "- Conexión IMAP/POP3 para obtener correos directamente desde la cuenta del usuario.\n"
            "- Integración con listas negras y servicios de reputación externos.\n"
            "- Modelo de aprendizaje automático o deep learning para clasificar correos.\n"
            "- Validación de certificados y comparación de dominios con marcas legítimas.\n"
            "- Análisis de resultados SPF/DKIM/DMARC y heurísticas de rutas Received para detectar posibles intermediarios o ataques tipo MITM."
        )


if __name__ == "__main__":
    main()
