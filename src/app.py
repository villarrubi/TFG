import streamlit as st

from sistema_phishing.analizador_email import construir_texto_para_analisis, parsear_eml_bytes
from sistema_phishing.heuristicas import analizar_correo


def mostrar_resultado(resultado):
    """Muestra en Streamlit los resultados del análisis de phishing."""
    st.subheader("Resultado del análisis")
    st.markdown(
        f"**Evaluación global:** {'✅ No parece phishing' if not resultado['is_phishing'] else '⚠️ Phishing probable'}"
    )
    st.markdown(f"**Puntuación de riesgo:** {resultado['risk_score']} %")
    st.progress(int(resultado['risk_score']))

    st.markdown("### Señales detectadas")
    for nombre, valor in resultado["signals"].items():
        estado = "⚠️" if valor else "✅"
        descripcion = nombre.replace("_", " ").capitalize()
        st.write(f"{estado} {descripcion}: {'Sí' if valor else 'No'}")

    st.markdown("### Explicación detallada")
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
            "- Validación de certificados y comparación de dominios con marcas legítimas."
        )


if __name__ == "__main__":
    main()
