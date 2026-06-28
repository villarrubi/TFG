"""Interfaz Streamlit para entrenar y evaluar modelos neuronales del TFG."""

import os
from io import StringIO

import streamlit as st

from sistema_phishing import ModelStorage, NeuralModelTrainer
from sistema_phishing.neural import cargar_dataset_csv

MODEL_PATH_ES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modelo_neural_es.joblib"))
MODEL_PATH_EN = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modelo_neural_en.joblib"))
MODEL_PATHS = {"Español": MODEL_PATH_ES, "Inglés": MODEL_PATH_EN}
# La contraseña puede venir del entorno; el valor por defecto facilita las
# pruebas locales, pero en despliegue conviene definir TRAINING_PASSWORD.
TRAINING_PASSWORD = os.getenv("TRAINING_PASSWORD", "123456")


def cargar_modelo_existente(path: str) -> None:
    """Carga un modelo si existe; se usa para consultar modelos guardados."""
    storage = ModelStorage(path)
    return storage.load()


def main():
    """Construye la pantalla de entrenamiento y evaluación de modelos."""
    st.title("Entrenamiento - Sistema de detección de phishing")
    st.markdown(
        "Esta pantalla está dedicada exclusivamente al entrenamiento del modelo neuronal. "
        "No hay ninguna funcionalidad de detección en esta interfaz."
    )

    if TRAINING_PASSWORD:
        # Streamlit detiene la ejecución del script si la clave no es correcta.
        clave = st.text_input("Contraseña de administrador", type="password")
        if clave != TRAINING_PASSWORD:
            st.warning("Introduce la contraseña correcta para acceder al entrenamiento.")
            st.stop()

    st.markdown("---")
    st.subheader("Datos de entrenamiento")
    uploaded_files = st.file_uploader("Sube uno o varios CSV de entrenamiento", type=["csv"], accept_multiple_files=True)
    text_format = st.radio("Formato del dataset", ["Texto completo", "Asunto + cuerpo"], index=0)
    label_column = st.text_input("Columna de etiqueta", value="label")
    lenguaje = st.selectbox("Lenguaje del modelo", ["Español", "Inglés"], index=0)

    if text_format == "Texto completo":
        # Formato habitual en datasets ya preprocesados: una sola columna con
        # asunto, cabeceras y cuerpo unidos.
        text_column = st.text_input("Columna de texto completo", value="text")
        subject_column = ""
        body_column = ""
    else:
        # Formato más estructurado: se combinan asunto y cuerpo antes de entrenar.
        text_column = ""
        subject_column = st.text_input("Columna de asunto", value="subject")
        body_column = st.text_input("Columna de cuerpo", value="body")

    if uploaded_files:
        st.markdown("**Archivos cargados:**")
        for archivo in uploaded_files:
            st.write(f"- {archivo.name}")

    if st.button("Entrenar modelo desde CSV"):
        if not uploaded_files:
            st.error("Sube al menos un archivo CSV antes de entrenar.")
        else:
            try:
                fuentes = []
                for archivo in uploaded_files:
                    # Streamlit entrega bytes; StringIO permite reutilizar el
                    # cargador CSV, que también acepta rutas de fichero.
                    texto_csv = archivo.getvalue().decode("utf-8", errors="replace")
                    sio = StringIO(texto_csv)
                    sio.name = archivo.name
                    fuentes.append(sio)

                language_map = {
                    "Español": "spanish",
                    "Inglés": "english",
                }
                # Cada idioma se guarda en un fichero distinto para que la app
                # de detección pueda elegir el modelo automáticamente.
                model_path = MODEL_PATHS[lenguaje]
                storage = ModelStorage(model_path)
                trainer = NeuralModelTrainer(storage)
                clasificador_entrenado = trainer.train_from_csvs(
                    fuentes,
                    language=language_map[lenguaje],
                    label_column=label_column,
                    text_column=text_column,
                    subject_column=subject_column,
                    body_column=body_column,
                )
                trainer.save(clasificador_entrenado)
                st.success(f"Modelo en {lenguaje} entrenado y guardado correctamente.")
                st.write(f"Guardado en: `{model_path}`")
                if clasificador_entrenado.last_training_stats:
                    stats = clasificador_entrenado.last_training_stats
                    st.markdown("**Resumen de entrenamiento:**")
                    st.write(f"- Ejemplos totales: {stats.n_samples}")
                    st.write(f"- Phishing: {stats.phishing_count}")
                    st.write(f"- Legítimos: {stats.legit_count}")
                    st.write(f"- Accuracy: {stats.accuracy * 100:.1f}%")
            except Exception as e:
                st.error(f"Error durante el entrenamiento: {e}")

    st.markdown("---")
    st.subheader("Pruebas del modelo")
    st.markdown(
        "Sube un CSV con correos etiquetados para evaluar la fiabilidad del modelo actual. "
        "Este CSV **no se usa para entrenar**, solo para medir cuántos correos clasifica correctamente."
    )

    test_file = st.file_uploader("Sube un CSV de prueba", type=["csv"], key="test_uploader")
    test_text_format = st.radio("Formato del CSV de prueba", ["Texto completo", "Asunto + cuerpo"], index=0, key="test_format")
    test_label_column = st.text_input("Columna de etiqueta (prueba)", value="label", key="test_label")

    if test_text_format == "Texto completo":
        # Los campos de prueba pueden llamarse distinto a los de entrenamiento,
        # por eso se piden de nuevo en esta sección.
        test_text_column = st.text_input("Columna de texto completo (prueba)", value="text", key="test_text")
        test_subject_column = ""
        test_body_column = ""
    else:
        test_text_column = ""
        test_subject_column = st.text_input("Columna de asunto (prueba)", value="subject", key="test_subject")
        test_body_column = st.text_input("Columna de cuerpo (prueba)", value="body", key="test_body")

    if st.button("Evaluar modelo"):
        storage_eval = ModelStorage(MODEL_PATHS[lenguaje])
        if not storage_eval.exists():
            st.error(f"No hay modelo entrenado en {lenguaje}. Entrénalo primero.")
        elif not test_file:
            st.error("Sube un archivo CSV de prueba antes de evaluar.")
        else:
            try:
                # Este flujo evalúa el modelo cargado sin modificarlo ni
                # reentrenarlo, por eso usa el CSV solo como conjunto de prueba.
                texto_csv = test_file.getvalue().decode("utf-8", errors="replace")
                textos, etiquetas_reales = cargar_dataset_csv(
                    StringIO(texto_csv),
                    label_column=test_label_column,
                    text_column=test_text_column,
                    subject_column=test_subject_column,
                    body_column=test_body_column,
                )
                clasificador = storage_eval.load()
                predicciones = clasificador.predict(textos)

                total = len(etiquetas_reales)
                phishing_real = sum(etiquetas_reales)
                legitimos_real = total - phishing_real

                correctas = sum(1 for pred, real in zip(predicciones, etiquetas_reales) if pred == real)
                accuracy = correctas / total if total else 0.0

                verdaderos_positivos = sum(1 for pred, real in zip(predicciones, etiquetas_reales) if pred == 1 and real == 1)
                falsos_positivos = sum(1 for pred, real in zip(predicciones, etiquetas_reales) if pred == 1 and real == 0)
                verdaderos_negativos = sum(1 for pred, real in zip(predicciones, etiquetas_reales) if pred == 0 and real == 0)
                falsos_negativos = sum(1 for pred, real in zip(predicciones, etiquetas_reales) if pred == 0 and real == 1)

                # La matriz de confusión se muestra desglosada porque en
                # phishing el coste de un falso negativo suele ser más alto.
                st.success("Evaluación completada.")
                st.markdown("**Resultados del CSV de prueba:**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de correos", total)
                col2.metric("Phishing reales", phishing_real)
                col3.metric("Legítimos reales", legitimos_real)

                st.markdown("**Predicciones del modelo:**")
                col4, col5, col6, col7 = st.columns(4)
                col4.metric("Correctas", correctas)
                col5.metric("Accuracy", f"{accuracy * 100:.1f}%")
                col6.metric("Falsos positivos", falsos_positivos, help="Legítimos clasificados como phishing")
                col7.metric("Falsos negativos", falsos_negativos, help="Phishing clasificados como legítimos")

                st.markdown("**Detalle:**")
                st.write(f"- Verdaderos positivos (phishing bien detectado): {verdaderos_positivos}")
                st.write(f"- Verdaderos negativos (legítimos bien clasificados): {verdaderos_negativos}")
                st.write(f"- Falsos positivos (legítimos marcados como phishing): {falsos_positivos}")
                st.write(f"- Falsos negativos (phishing no detectado): {falsos_negativos}")

            except Exception as e:
                st.error(f"Error durante la evaluación: {e}")

    st.markdown("---")
    st.subheader("Modelos guardados")
    for nombre_idioma, path in MODEL_PATHS.items():
        storage = ModelStorage(path)
        with st.expander(f"Modelo en {nombre_idioma} — {'✅ Entrenado' if storage.exists() else '❌ No entrenado'}"):
            if storage.exists():
                # La carga permite mostrar metadatos guardados junto al modelo,
                # pero si el fichero está corrupto no se bloquea la interfaz.
                st.write(f"Ruta: `{path}`")
                classifier = storage.load()
                if classifier is not None:
                    st.write(f"- Lenguaje: {classifier.language}")
                    st.write(f"- Entrenado con datos sintéticos: {'Sí' if getattr(classifier, 'trained_with_default', False) else 'No'}")
                    st.write(f"- Último entrenamiento: {getattr(classifier, 'last_training_datetime', 'Desconocido')}")
                    st.write("- Archivos de entrenamiento:")
                    for fuente in getattr(classifier, 'training_sources', []) or []:
                        st.write(f"  - {fuente}")
                if st.button(f"Eliminar modelo en {nombre_idioma}", key=f"delete_{nombre_idioma}"):
                    os.remove(path)
                    st.warning(f"Modelo en {nombre_idioma} eliminado. Reinicia la app para actualizar el estado.")
            else:
                st.write("Este modelo aún no ha sido entrenado.")


if __name__ == "__main__":
    main()
