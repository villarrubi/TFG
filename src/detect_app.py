"""Interfaz Streamlit para analizar correos con heurísticas y modelo neuronal."""

import os

import streamlit as st

from sistema_phishing import (
    ModelStorage,
    NeuralPhishingClassifier,
    NeuralPhishingDetector,
)
from sistema_phishing.analizador_email import construir_texto_para_analisis, parsear_eml_bytes
from sistema_phishing.heuristicas import analizar_correo

try:
    from langdetect import detect as detectar_idioma
    LANGDETECT_DISPONIBLE = True
except ImportError:
    # La detección de idioma mejora la selección de modelo, pero la app puede
    # funcionar sin esta dependencia usando español como idioma por defecto.
    LANGDETECT_DISPONIBLE = False

# Los modelos se guardan junto al repositorio para que Streamlit pueda
# encontrarlos aunque la app se ejecute desde otro directorio.
MODEL_PATH_ES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modelo_neural_es.joblib"))
MODEL_PATH_EN = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modelo_neural_en.joblib"))


def _color_riesgo(score: float) -> str:
    """Convierte una puntuación 0-100 en un color verde-amarillo-rojo."""
    score = max(0.0, min(100.0, score))
    if score <= 30:
        ratio = score / 30.0
        r = int(76 + (255 - 76) * ratio)
        g = int(175 + (235 - 175) * ratio)
        b = int(80 - (80 * ratio))
    elif score <= 70:
        ratio = (score - 30.0) / 40.0
        r = int(255)
        g = int(235 - (128 * ratio))
        b = int(0 + (0 * ratio))
    else:
        ratio = (score - 70.0) / 30.0
        r = int(255)
        g = int(107 - (40 * ratio))
        b = int(0 + (0 * ratio))
    return f"#{r:02x}{g:02x}{b:02x}"


def mostrar_resultado_basico(resultado, titulo: str = "Resultado del análisis"):
    """Pinta los datos comunes a cualquier tipo de análisis."""
    st.subheader(titulo)
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
    st.write(f"**URLs detectadas:** {len(resultado.get('urls', []))}")
    st.write(f"**Enlaces HTML analizados:** {len(resultado.get('anchors', []))}")
    st.write(f"**Cabeceras incluidas:** {len(resultado.get('headers', {}))}")
    if resultado.get("description"):
        st.write(f"**Descripción:** {resultado['description']}")


def mostrar_resultado_heuristico(resultado):
    """Muestra la puntuación heurística y el detalle de reglas activadas."""
    mostrar_resultado_basico(resultado, "Análisis heurístico")
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
        with st.expander(f"Enlaces detectados ({len(resultado['urls'])})"):
            for enlace in resultado["urls"]:
                st.write(f"- {enlace}")

    if resultado.get("anchors"):
        with st.expander(f"Anclas detectadas en HTML ({len(resultado.get('anchors', []))})"):
            for anchor in resultado["anchors"]:
                st.write(f"- Texto: {anchor['text']} / URL: {anchor['href']}")

    if resultado.get("headers"):
        with st.expander("Cabeceras analizadas"):
            st.write({
                key: value
                for key, value in resultado["headers"].items()
                if key.lower() in ["from", "to", "subject", "reply-to", "return-path", "message-id"]
            })


def mostrar_resultado_neural(resultado):
    """Muestra la salida simplificada del clasificador neuronal."""
    mostrar_resultado_basico(resultado, "Análisis por red neuronal")
    st.markdown("### Detalle del modelo")
    st.write(f"**Probabilidad de phishing:** {resultado['risk_score']:.1f}%")
    st.write(f"**Clasificación:** {'Phishing probable' if resultado['is_phishing'] else 'No parece phishing'}")


def mostrar_combinado(resultado_heur, resultado_neural, heur_weight, neural_weight):
    """Combina los dos análisis con los pesos elegidos en la interfaz."""
    # Se mantiene el mismo umbral que la heurística para que la interpretación
    # del porcentaje sea homogénea en los tres modos de análisis.
    combined_score = (resultado_heur['risk_score'] * heur_weight + resultado_neural['risk_score'] * neural_weight) / (heur_weight + neural_weight)
    resultado = {
        'is_phishing': combined_score >= 45,
        'risk_score': round(combined_score, 1),
        'description': 'Resultado mixto ponderado entre heurística y red neuronal.',
        'urls': resultado_heur.get('urls', []),
        'anchors': resultado_heur.get('anchors', []),
        'headers': resultado_heur.get('headers', {}),
    }
    mostrar_resultado_basico(resultado, "Resultado combinado")
    st.markdown("### Ponderación aplicada")
    st.write(f"Peso heurístico: {heur_weight}%")
    st.write(f"Peso neuronal: {neural_weight}%")


def _detectar_idioma_texto(texto: str) -> str:
    """Devuelve 'es' o 'en' según el idioma detectado. Por defecto 'es'."""
    if not LANGDETECT_DISPONIBLE or not texto.strip():
        return "es"
    try:
        lang = detectar_idioma(texto)
        return "en" if lang == "en" else "es"
    except Exception:
        return "es"


def cargar_detector(idioma: str) -> NeuralPhishingDetector:
    """Carga el modelo del idioma detectado y usa alternativas si no existe."""
    path = MODEL_PATH_EN if idioma == "en" else MODEL_PATH_ES
    storage = ModelStorage(path)
    classifier = storage.load()
    if classifier is None:
        # Si falta el modelo del idioma detectado, reutiliza el otro modelo
        # entrenado antes de recurrir al dataset sintético.
        path_alt = MODEL_PATH_ES if idioma == "en" else MODEL_PATH_EN
        storage_alt = ModelStorage(path_alt)
        classifier = storage_alt.load()
    if classifier is None:
        # Último recurso para que la demo siga funcionando en un clon limpio.
        classifier = NeuralPhishingClassifier()
        classifier.fit_default()
    return NeuralPhishingDetector(classifier)


def main():
    st.title("Detección - Sistema de phishing")
    st.markdown(
        "Esta pantalla está dedicada exclusivamente a analizar correos. "
        "No hay ninguna funcionalidad de entrenamiento en esta interfaz."
    )

    es_disponible = ModelStorage(MODEL_PATH_ES).exists()
    en_disponible = ModelStorage(MODEL_PATH_EN).exists()

    if es_disponible and en_disponible:
        st.success("Modelos en español e inglés cargados. El idioma se detectará automáticamente.")
    elif es_disponible:
        st.info("Solo hay modelo en español. Se usará para todos los correos.")
    elif en_disponible:
        st.info("Solo hay modelo en inglés. Se usará para todos los correos.")
    else:
        st.warning("No hay modelos entrenados en disco. Se usa el modelo sintético por defecto.")

    modo = st.radio("Modo de entrada", ["Pegar texto del correo", "Subir archivo .eml"], index=0)
    texto_para_analisis = ""
    datos_email = None

    if modo == "Pegar texto del correo":
        texto_para_analisis = st.text_area("Pega aquí el contenido del correo (cabeceras + cuerpo):")
    else:
        archivo = st.file_uploader("Sube un archivo .eml", type=["eml"])
        if archivo is not None:
            # El parser devuelve una estructura rica: texto plano para el modelo
            # y HTML/anclas/adjuntos para las heurísticas.
            datos_email = parsear_eml_bytes(archivo.getvalue())
            texto_para_analisis = construir_texto_para_analisis(datos_email)
            st.markdown("#### Correo cargado")
            st.write({
                "From": datos_email["from"],
                "To": datos_email["to"],
                "Subject": datos_email["subject"],
            })

    tipo_analisis = st.radio("Tipo de análisis", ["Heurístico", "Red neuronal", "Combinado"], index=2)
    heur_weight = 60
    neural_weight = 40
    if tipo_analisis == "Combinado":
        heur_weight = st.slider("Peso heurístico (%)", 0, 100, 60)
        neural_weight = 100 - heur_weight

    if st.button("Analizar correo"):
        if not texto_para_analisis.strip():
            st.warning("Introduce texto o sube un archivo .eml antes de analizar.")
        else:
            if datos_email:
                # Para .eml se conserva el diccionario parseado, porque contiene
                # campos que no aparecen en un texto pegado manualmente.
                entrada = datos_email
                texto_modelo = construir_texto_para_analisis(datos_email)
                remitente = datos_email.get("from", "")
                subject = datos_email.get("subject", "")
            else:
                entrada = texto_para_analisis
                texto_modelo = texto_para_analisis
                remitente = ""
                subject = ""

            idioma = _detectar_idioma_texto(texto_modelo)
            st.caption(f"Idioma detectado: {'Español 🇪🇸' if idioma == 'es' else 'Inglés 🇬🇧'}")

            # Ambos análisis se calculan siempre para poder alternar entre
            # vistas sin duplicar la preparación de datos.
            detector = cargar_detector(idioma)
            resultado_heuristico = analizar_correo(entrada)
            resultado_neural = detector.analyze(texto_modelo, remitente, subject)

            if tipo_analisis == "Heurístico":
                mostrar_resultado_heuristico(resultado_heuristico)
            elif tipo_analisis == "Red neuronal":
                mostrar_resultado_neural(resultado_neural)
            else:
                mostrar_combinado(resultado_heuristico, resultado_neural, heur_weight, neural_weight)


if __name__ == "__main__":
    main()
