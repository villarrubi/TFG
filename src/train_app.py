"""Interfaz Streamlit para entrenar y evaluar modelos neuronales del TFG."""

import os
from io import StringIO
from textwrap import dedent

import streamlit as st

from sistema_phishing import ModelStorage, NeuralModelTrainer
from sistema_phishing.env_loader import cargar_env_local
from sistema_phishing.modelo_neural import (
    HiperparametrosModelo,
    NeuralPhishingClassifier,
    cargar_hiperparametros_desde_env,
)
from sistema_phishing.neural import cargar_dataset_csv
from ui_components import aplicar_estilos_base, estado_badge, render_html

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MODEL_PATH_ES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modelo_neural_es.joblib"))
MODEL_PATH_EN = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modelo_neural_en.joblib"))
MODEL_PATHS = {"Español": MODEL_PATH_ES, "Inglés": MODEL_PATH_EN}
# La contraseña puede venir del entorno; el valor por defecto facilita las
# pruebas locales, pero en despliegue conviene definir TRAINING_PASSWORD.
TRAINING_PASSWORD = os.getenv("TRAINING_PASSWORD", "")


def aplicar_estilos_entrenamiento() -> None:
    """Aplica estilos locales para la pantalla de entrenamiento."""
    aplicar_estilos_base()


def _mostrar_estado_modelos() -> None:
    """Muestra el estado de los modelos guardados."""
    cards = []
    for idioma, path in MODEL_PATHS.items():
        exists = ModelStorage(path).exists()
        # dedent + strip en CADA tarjeta (no solo al final) es clave: si queda
        # una línea de solo-espacios entre tarjetas al hacer join, Markdown la
        # interpreta como línea en blanco, cierra el bloque HTML y el resto se
        # renderiza como bloque de código indentado (texto crudo en pantalla).
        cards.append(
            dedent(
                f"""
                <div class="ui-card">
                    <div class="ui-label">Modelo {idioma}</div>
                    <div class="ui-value">{estado_badge(exists, "Entrenado", "Pendiente")}</div>
                    <div class="ui-note"><code>{os.path.basename(path)}</code></div>
                </div>
                """
            ).strip()
        )
    render_html(f'<div class="ui-grid ui-grid-2">{"".join(cards)}</div>')


def resumir_dataset_subido(archivo, label_column: str, text_column: str, subject_column: str, body_column: str) -> dict:
    """Calcula métricas rápidas de un CSV subido antes de entrenar."""
    texto_csv = archivo.getvalue().decode("utf-8", errors="replace")
    sio = StringIO(texto_csv)
    sio.name = archivo.name
    try:
        _, etiquetas = cargar_dataset_csv(
            sio,
            label_column=label_column,
            text_column=text_column,
            subject_column=subject_column,
            body_column=body_column,
        )
        phishing = sum(etiquetas)
        legitimos = len(etiquetas) - phishing
        return {
            "Archivo": archivo.name,
            "Filas válidas": len(etiquetas),
            "Phishing": phishing,
            "Legítimos": legitimos,
            "Estado": "OK",
        }
    except Exception as exc:
        return {
            "Archivo": archivo.name,
            "Filas válidas": 0,
            "Phishing": 0,
            "Legítimos": 0,
            "Estado": str(exc),
        }


def main():
    """Construye la pantalla de entrenamiento y evaluación de modelos."""
    cargar_env_local(ROOT_DIR)
    aplicar_estilos_entrenamiento()
    st.title("Entrenamiento de modelos")
    st.caption("Entrena, evalúa y revisa los modelos neuronales usados por la detección.")

    if TRAINING_PASSWORD:
        # Streamlit detiene la ejecución del script si la clave no es correcta.
        clave = st.text_input("Contraseña de administrador", type="password")
        if clave != TRAINING_PASSWORD:
            st.warning("Introduce la contraseña correcta para acceder al entrenamiento.")
            st.stop()

    _mostrar_estado_modelos()
    tab_train, tab_eval, tab_compare, tab_models = st.tabs([
        "Entrenar",
        "Evaluar",
        "Comparar modelos",
        "Modelos guardados",
    ])

    with tab_train:
        st.markdown("### Datos de entrenamiento")
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

        custom_hp = None
        if uploaded_files:
            st.markdown("**Archivos cargados:**")
            for archivo in uploaded_files:
                st.write(f"- {archivo.name}")
            resumenes = [
                resumir_dataset_subido(
                    archivo,
                    label_column=label_column,
                    text_column=text_column,
                    subject_column=subject_column,
                    body_column=body_column,
                )
                for archivo in uploaded_files
            ]
            total_validas = sum(item["Filas válidas"] for item in resumenes)
            total_phishing = sum(item["Phishing"] for item in resumenes)
            total_legitimos = sum(item["Legítimos"] for item in resumenes)
            st.markdown("**Resumen previo de datos:**")
            col_total, col_phishing, col_legitimos = st.columns(3)
            col_total.metric("Filas válidas", total_validas)
            col_phishing.metric("Phishing", total_phishing)
            col_legitimos.metric("Legítimos", total_legitimos)
            st.dataframe(resumenes, use_container_width=True)

            hp_activos = cargar_hiperparametros_desde_env()
            with st.expander("Hiperparámetros que se usarán al entrenar (editar en Configuración)", expanded=False):
                st.write(
                    f"- Capas ocultas: `{hp_activos.mlp_hidden_layer_sizes}` · "
                    f"Activación: `{hp_activos.mlp_activation}` · "
                    f"Alpha: `{hp_activos.mlp_alpha}` · "
                    f"Learning rate: `{hp_activos.mlp_learning_rate_init}` · "
                    f"Épocas máx.: `{hp_activos.mlp_max_iter}` · "
                    f"Early stopping: `{hp_activos.mlp_early_stopping}`"
                )
                st.write(
                    f"- N-gramas: `{hp_activos.tfidf_ngram_range}` · "
                    f"Vocabulario máx.: `{hp_activos.tfidf_max_features}` · "
                    f"min_df: `{hp_activos.tfidf_min_df}`"
                )
                st.caption("Para cambiarlos, ve a la pestaña Configuración → 'Red neuronal (avanzado)'.")

                with st.expander("Usar parámetros personalizados solo en este entrenamiento", expanded=False):
                    st.caption("Estos valores no se guardan en Configuración; solo se usan durante este entrenamiento.")
                    custom_hp_enabled = st.checkbox("Activar parámetros personalizados", value=False)
                    custom_hp_error = None
                    if custom_hp_enabled:
                        col1, col2, col3 = st.columns(3)
                        ngram_min = col1.number_input(
                            "N-grama mínimo", min_value=1, max_value=3, value=hp_activos.tfidf_ngram_range[0],
                            help="1 = palabras sueltas.",
                        )
                        ngram_max = col2.number_input(
                            "N-grama máximo", min_value=1, max_value=3, value=hp_activos.tfidf_ngram_range[1],
                            help="2 = incluye bigramas.",
                        )
                        max_features = col3.number_input(
                            "Vocabulario máximo", min_value=100, max_value=50000, step=100,
                            value=hp_activos.tfidf_max_features,
                        )
                        min_df = st.number_input(
                            "min_df", min_value=1, max_value=20, value=hp_activos.tfidf_min_df,
                        )
                        capas_texto = st.text_input(
                            "Neuronas por capa oculta",
                            value=",".join(str(n) for n in hp_activos.mlp_hidden_layer_sizes),
                            help="Ej: '64,32' = dos capas de 64 y 32 neuronas.",
                        )
                        col4, col5 = st.columns(2)
                        activation = col4.selectbox(
                            "Función de activación", ["relu", "tanh", "logistic"],
                            index=["relu", "tanh", "logistic"].index(hp_activos.mlp_activation)
                            if hp_activos.mlp_activation in ["relu", "tanh", "logistic"] else 0,
                        )
                        max_iter = col5.number_input(
                            "Épocas máximas", min_value=50, max_value=5000, step=50,
                            value=hp_activos.mlp_max_iter,
                        )
                        col6, col7 = st.columns(2)
                        alpha = col6.number_input(
                            "Regularización (alpha)", min_value=0.0, max_value=1.0,
                            value=float(hp_activos.mlp_alpha), step=0.0001, format="%.4f",
                            help="Sube alpha si el modelo memoriza demasiado.",
                        )
                        learning_rate = col7.number_input(
                            "Learning rate", min_value=0.00001, max_value=1.0,
                            value=float(hp_activos.mlp_learning_rate_init), step=0.0001, format="%.5f",
                        )
                        early_stopping = st.checkbox(
                            "Early stopping", value=hp_activos.mlp_early_stopping,
                        )
                        if ngram_min > ngram_max:
                            custom_hp_error = "El n-grama mínimo no puede ser mayor que el máximo."
                        else:
                            try:
                                capas = tuple(int(parte.strip()) for parte in capas_texto.split(",") if parte.strip())
                                if not capas:
                                    raise ValueError("Debes indicar al menos una capa.")
                            except ValueError:
                                custom_hp_error = "Las neuronas por capa deben ser números enteros separados por comas."
                            else:
                                custom_hp = HiperparametrosModelo(
                                    tfidf_ngram_range=(ngram_min, ngram_max),
                                    tfidf_max_features=max_features,
                                    tfidf_min_df=min_df,
                                    mlp_hidden_layer_sizes=capas,
                                    mlp_activation=activation,
                                    mlp_alpha=alpha,
                                    mlp_learning_rate_init=learning_rate,
                                    mlp_max_iter=max_iter,
                                    mlp_early_stopping=early_stopping,
                                )
                        if custom_hp_error:
                            st.error(custom_hp_error)
        else:
            custom_hp = None

        if st.button("Entrenar modelo desde CSV", use_container_width=True):
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
                        hiperparametros=custom_hp,
                    )
                    trainer.save(clasificador_entrenado)
                    st.success(f"Modelo en {lenguaje} entrenado y guardado correctamente.")
                    st.write(f"Guardado en: `{model_path}`")
                    if clasificador_entrenado.last_training_stats:
                        stats = clasificador_entrenado.last_training_stats
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Ejemplos", stats.n_samples)
                        col2.metric("Phishing", stats.phishing_count)
                        col3.metric("Legítimos", stats.legit_count)
                        col4.metric("Accuracy", f"{stats.accuracy * 100:.1f}%")
                except Exception as e:
                    st.error(f"Error durante el entrenamiento: {e}")

    with tab_eval:
        st.markdown("### Pruebas del modelo")
        st.info(
            "El CSV de prueba no se usa para entrenar. Solo mide cuántos correos clasifica correctamente."
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

        lenguaje_eval = st.selectbox("Modelo a evaluar", ["Español", "Inglés"], index=0, key="eval_lang")
        if st.button("Evaluar modelo", use_container_width=True):
            storage_eval = ModelStorage(MODEL_PATHS[lenguaje_eval])
            if not storage_eval.exists():
                st.error(f"No hay modelo entrenado en {lenguaje_eval}. Entrénalo primero.")
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
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total", total)
                    col2.metric("Accuracy", f"{accuracy * 100:.1f}%")
                    col3.metric("Phishing reales", phishing_real)
                    col4.metric("Legítimos reales", legitimos_real)

                    st.markdown("**Matriz de confusión:**")
                    col5, col6, col7, col8 = st.columns(4)
                    col5.metric("VP", verdaderos_positivos, help="Phishing bien detectado")
                    col6.metric("VN", verdaderos_negativos, help="Legítimos bien clasificados")
                    col7.metric("FP", falsos_positivos, help="Legítimos clasificados como phishing")
                    col8.metric("FN", falsos_negativos, help="Phishing clasificados como legítimos")

                except Exception as e:
                    st.error(f"Error durante la evaluación: {e}")

    with tab_compare:
        st.markdown("### Comparar modelos neuronales")
        st.info(
            "Entrena hasta 3 redes con diferentes parámetros y compara sus resultados "
            "en un CSV de prueba."
        )

        compare_train_files = st.file_uploader(
            "Sube uno o varios CSV de entrenamiento", type=["csv"], accept_multiple_files=True, key="compare_train"
        )
        compare_test_file = st.file_uploader(
            "Sube el CSV de prueba", type=["csv"], key="compare_test"
        )
        compare_format = st.radio(
            "Formato de los CSV", ["Texto completo", "Asunto + cuerpo"], index=0, key="compare_format"
        )
        compare_label_column = st.text_input(
            "Columna de etiqueta", value="label", key="compare_label"
        )
        lenguaje_compare = st.selectbox(
            "Lenguaje del modelo", ["Español", "Inglés"], index=0, key="compare_language"
        )

        if compare_format == "Texto completo":
            compare_text_column = st.text_input(
                "Columna de texto completo", value="text", key="compare_text"
            )
            compare_subject_column = ""
            compare_body_column = ""
        else:
            compare_text_column = ""
            compare_subject_column = st.text_input(
                "Columna de asunto", value="subject", key="compare_subject"
            )
            compare_body_column = st.text_input(
                "Columna de cuerpo", value="body", key="compare_body"
            )

        if compare_train_files:
            st.markdown("**Resumen combinado de entrenamiento**")
            resumenes_compare = [
                resumir_dataset_subido(
                    archivo,
                    label_column=compare_label_column,
                    text_column=compare_text_column,
                    subject_column=compare_subject_column,
                    body_column=compare_body_column,
                )
                for archivo in compare_train_files
            ]
            total_validas_compare = sum(item["Filas válidas"] for item in resumenes_compare)
            total_phishing_compare = sum(item["Phishing"] for item in resumenes_compare)
            total_legitimos_compare = sum(item["Legítimos"] for item in resumenes_compare)
            col_total, col_phishing, col_legitimos = st.columns(3)
            col_total.metric("Filas válidas", total_validas_compare)
            col_phishing.metric("Phishing", total_phishing_compare)
            col_legitimos.metric("Legítimos", total_legitimos_compare)
            st.dataframe(resumenes_compare, use_container_width=True)

        default_hp = cargar_hiperparametros_desde_env()
        models_to_compare = []
        for index in range(3):
            with st.expander(f"Modelo {index + 1}", expanded=(index == 0)):
                enabled = st.checkbox(
                    "Usar este modelo",
                    value=True if index == 0 else False,
                    key=f"compare_enabled_{index}",
                )
                if not enabled:
                    st.write("Este modelo no se incluirá en la comparación.")
                    continue

                model_name = st.text_input(
                    "Nombre del modelo",
                    value=f"Modelo {chr(65 + index)}",
                    key=f"compare_name_{index}",
                )
                col1, col2, col3 = st.columns(3)
                ngram_min = col1.number_input(
                    "N-grama mínimo",
                    min_value=1,
                    max_value=3,
                    value=default_hp.tfidf_ngram_range[0],
                    key=f"compare_ngram_min_{index}",
                )
                ngram_max = col2.number_input(
                    "N-grama máximo",
                    min_value=1,
                    max_value=3,
                    value=default_hp.tfidf_ngram_range[1],
                    key=f"compare_ngram_max_{index}",
                )
                max_features = col3.number_input(
                    "Vocabulario máximo",
                    min_value=100,
                    max_value=50000,
                    step=100,
                    value=default_hp.tfidf_max_features,
                    key=f"compare_max_features_{index}",
                )
                min_df = st.number_input(
                    "min_df",
                    min_value=1,
                    max_value=20,
                    value=default_hp.tfidf_min_df,
                    key=f"compare_min_df_{index}",
                )
                capas_texto = st.text_input(
                    "Neuronas por capa oculta",
                    value=",".join(str(n) for n in default_hp.mlp_hidden_layer_sizes),
                    key=f"compare_hidden_layers_{index}",
                )
                col4, col5 = st.columns(2)
                activation = col4.selectbox(
                    "Activación",
                    ["relu", "tanh", "logistic"],
                    index=["relu", "tanh", "logistic"].index(default_hp.mlp_activation)
                    if default_hp.mlp_activation in ["relu", "tanh", "logistic"]
                    else 0,
                    key=f"compare_activation_{index}",
                )
                max_iter = col5.number_input(
                    "Épocas máximas",
                    min_value=50,
                    max_value=5000,
                    step=50,
                    value=default_hp.mlp_max_iter,
                    key=f"compare_max_iter_{index}",
                )
                col6, col7 = st.columns(2)
                alpha = col6.number_input(
                    "Alpha",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(default_hp.mlp_alpha),
                    step=0.0001,
                    format="%.4f",
                    key=f"compare_alpha_{index}",
                )
                learning_rate = col7.number_input(
                    "Learning rate",
                    min_value=0.00001,
                    max_value=1.0,
                    value=float(default_hp.mlp_learning_rate_init),
                    step=0.0001,
                    format="%.5f",
                    key=f"compare_learning_rate_{index}",
                )
                early_stopping = st.checkbox(
                    "Early stopping",
                    value=default_hp.mlp_early_stopping,
                    key=f"compare_early_stopping_{index}",
                )

                try:
                    capas = tuple(int(parte.strip()) for parte in capas_texto.split(",") if parte.strip())
                    if not capas:
                        raise ValueError()
                except ValueError:
                    st.error("Neuronas por capa inválidas. Usa enteros separados por comas, por ejemplo 64,32.")
                    continue

                models_to_compare.append(
                    {
                        "name": model_name,
                        "hiperparametros": HiperparametrosModelo(
                            tfidf_ngram_range=(ngram_min, ngram_max),
                            tfidf_max_features=max_features,
                            tfidf_min_df=min_df,
                            mlp_hidden_layer_sizes=capas,
                            mlp_activation=activation,
                            mlp_alpha=alpha,
                            mlp_learning_rate_init=learning_rate,
                            mlp_max_iter=max_iter,
                            mlp_early_stopping=early_stopping,
                        ),
                    }
                )

        if st.button("Entrenar y comparar modelos", use_container_width=True):
            if not compare_train_files:
                st.error("Sube primero uno o varios CSV de entrenamiento.")
            elif not compare_test_file:
                st.error("Sube primero el CSV de prueba.")
            elif not models_to_compare:
                st.error("Activa al menos un modelo para la comparación.")
            else:
                try:
                    fuentes = []
                    for archivo in compare_train_files:
                        texto_csv = archivo.getvalue().decode("utf-8", errors="replace")
                        sio = StringIO(texto_csv)
                        sio.name = archivo.name
                        fuentes.append(sio)

                    train_texts, train_labels = cargar_dataset_csv(
                        fuentes[0],
                        label_column=compare_label_column,
                        text_column=compare_text_column,
                        subject_column=compare_subject_column,
                        body_column=compare_body_column,
                    )
                    for extra in fuentes[1:]:
                        textos_extra, etiquetas_extra = cargar_dataset_csv(
                            extra,
                            label_column=compare_label_column,
                            text_column=compare_text_column,
                            subject_column=compare_subject_column,
                            body_column=compare_body_column,
                        )
                        train_texts.extend(textos_extra)
                        train_labels.extend(etiquetas_extra)
                    test_csv = compare_test_file.getvalue().decode("utf-8", errors="replace")
                    test_texts, test_labels = cargar_dataset_csv(
                        StringIO(test_csv),
                        label_column=compare_label_column,
                        text_column=compare_text_column,
                        subject_column=compare_subject_column,
                        body_column=compare_body_column,
                    )

                    language_map = {"Español": "spanish", "Inglés": "english"}
                    language_code = language_map[lenguaje_compare]
                    results = []
                    for model in models_to_compare:
                        classifier = NeuralPhishingClassifier(
                            language=language_code,
                            hiperparametros=model["hiperparametros"],
                        )
                        classifier.fit(train_texts, train_labels)
                        predictions = classifier.predict(test_texts)
                        total = len(test_labels)
                        correctas = sum(1 for pred, real in zip(predictions, test_labels) if pred == real)
                        phishing_real = sum(test_labels)
                        legitimos_real = total - phishing_real
                        vp = sum(1 for pred, real in zip(predictions, test_labels) if pred == 1 and real == 1)
                        vn = sum(1 for pred, real in zip(predictions, test_labels) if pred == 0 and real == 0)
                        fp = sum(1 for pred, real in zip(predictions, test_labels) if pred == 1 and real == 0)
                        fn = sum(1 for pred, real in zip(predictions, test_labels) if pred == 0 and real == 1)
                        accuracy = correctas / total if total else 0.0
                        results.append(
                            {
                                "Modelo": model["name"],
                                "Accuracy": f"{accuracy * 100:.2f}%",
                                "Total prueba": total,
                                "VP": vp,
                                "VN": vn,
                                "FP": fp,
                                "FN": fn,
                                "Phishing reales": phishing_real,
                                "Legítimos reales": legitimos_real,
                            }
                        )

                    st.markdown("**Resultados comparativos en el CSV de prueba:**")
                    st.dataframe(results, use_container_width=True)

                    for item in results:
                        with st.expander(f"Detalle: {item['Modelo']}"):
                            st.write(f"Accuracy: {item['Accuracy']}")
                            st.write(f"VP: {item['VP']}  VN: {item['VN']}  FP: {item['FP']}  FN: {item['FN']}")
                            st.write(f"Phishing reales: {item['Phishing reales']}  Legítimos reales: {item['Legítimos reales']}")

                except Exception as exc:
                    st.error(f"Error al comparar modelos: {exc}")

    with tab_models:
        st.markdown("### Modelos guardados")
        for nombre_idioma, path in MODEL_PATHS.items():
            storage = ModelStorage(path)
            with st.expander(f"Modelo en {nombre_idioma} - {'Entrenado' if storage.exists() else 'No entrenado'}"):
                if storage.exists():
                    # La carga permite mostrar metadatos guardados junto al modelo,
                    # pero si el fichero está corrupto no se bloquea la interfaz.
                    st.write(f"Ruta: `{path}`")
                    classifier = storage.load()
                    if classifier is None:
                        st.error(
                            "El archivo del modelo existe pero no se ha podido cargar "
                            "(puede estar corrupto o incompleto)."
                        )
                    else:
                        st.write(f"- Lenguaje: {classifier.language}")
                        st.write(f"- Entrenado con datos sintéticos: {'Sí' if getattr(classifier, 'trained_with_default', False) else 'No'}")
                        st.write(f"- Último entrenamiento: {getattr(classifier, 'last_training_datetime', 'Desconocido')}")

                        # Estadísticas del último entrenamiento: antes solo se veían
                        # justo al terminar de entrenar (y se perdían al recargar la
                        # página); ahora se guardan en el propio .joblib y se pueden
                        # consultar aquí en cualquier momento.
                        stats = getattr(classifier, "last_training_stats", None)
                        if stats is not None:
                            st.markdown("**Estadísticas del entrenamiento:**")
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Ejemplos", stats.n_samples)
                            col2.metric("Phishing", stats.phishing_count)
                            col3.metric("Legítimos", stats.legit_count)
                            col4.metric("Accuracy", f"{stats.accuracy * 100:.1f}%")
                        else:
                            st.caption("No hay estadísticas guardadas para este modelo (formato antiguo).")

                        columnas = getattr(classifier, "training_columns", None)
                        if columnas:
                            st.markdown("**Columnas usadas al entrenar:**")
                            st.write(
                                f"- Etiqueta: `{columnas.get('label', 'n/a')}` · "
                                f"Texto: `{columnas.get('text', 'n/a')}` · "
                                f"Asunto: `{columnas.get('subject', 'n/a')}` · "
                                f"Cuerpo: `{columnas.get('body', 'n/a')}`"
                            )

                        fuentes = getattr(classifier, "training_sources", []) or []
                        fuentes_info = getattr(classifier, "training_sources_info", []) or []
                        st.markdown("**Archivos de entrenamiento:**")
                        if fuentes_info:
                            for fuente_info in fuentes_info:
                                st.write(
                                    f"- {fuente_info.source}: "
                                    f"{fuente_info.n_samples} ejemplos "
                                    f"({fuente_info.phishing_count} phishing, "
                                    f"{fuente_info.legit_count} legítimos)"
                                )
                        elif fuentes:
                            for fuente in fuentes:
                                st.write(f"- {fuente}")
                        else:
                            st.caption("Sin registro de archivos de origen.")

                    st.divider()
                    # Confirmación explícita antes de borrar: evita eliminar un
                    # modelo por un clic accidental. El st.rerun() al final es lo
                    # que faltaba para que el estado se refresque al instante en
                    # vez de necesitar reiniciar la app manualmente.
                    confirmar_borrado = st.checkbox(
                        "Confirmo que quiero eliminar este modelo",
                        key=f"confirm_delete_{nombre_idioma}",
                    )
                    if st.button(
                        f"Eliminar modelo en {nombre_idioma}",
                        key=f"delete_{nombre_idioma}",
                        disabled=not confirmar_borrado,
                        use_container_width=True,
                    ):
                        os.remove(path)
                        st.success(f"Modelo en {nombre_idioma} eliminado. Ya puedes volver a entrenarlo desde cero.")
                        st.rerun()
                else:
                    st.write("Este modelo aún no ha sido entrenado.")


if __name__ == "__main__":
    main()