"""Cliente Streamlit para administrar los modelos del backend central."""

from __future__ import annotations

import os

import streamlit as st

from sistema_phishing.backend_client import BackendClient, BackendClientError
from sistema_phishing.env_loader import cargar_env_local
from sistema_phishing.model_config import (
    HiperparametrosModelo,
    cargar_hiperparametros_desde_env,
)
from ui_components import (
    aplicar_estilos_base,
    encabezado_pagina,
    estado_badge,
    render_html,
)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def aplicar_estilos_entrenamiento() -> None:
    aplicar_estilos_base()


def _columns(prefix: str, dataset_format: str) -> dict[str, str]:
    label = st.text_input("Columna de etiqueta", value="label", key=f"{prefix}_label")
    if dataset_format == "Texto completo":
        text = st.text_input(
            "Columna de texto completo",
            value="text",
            key=f"{prefix}_text",
        )
        subject = ""
        body = ""
    else:
        text = ""
        subject = st.text_input(
            "Columna de asunto",
            value="subject",
            key=f"{prefix}_subject",
        )
        body = st.text_input(
            "Columna de cuerpo",
            value="body",
            key=f"{prefix}_body",
        )
    return {"label": label, "text": text, "subject": subject, "body": body}


def _hyperparameters_form(
    prefix: str,
    *,
    enabled_label: str = "Usar hiperparámetros personalizados",
) -> HiperparametrosModelo | None:
    defaults = cargar_hiperparametros_desde_env()
    enabled = st.checkbox(enabled_label, value=False, key=f"{prefix}_enabled")
    if not enabled:
        # Se envían explícitamente para que el resultado no dependa del entorno
        # del proceso servidor, que puede estar en otro equipo.
        return defaults

    col1, col2, col3 = st.columns(3)
    ngram_min = col1.number_input(
        "N-grama mínimo",
        1,
        3,
        defaults.tfidf_ngram_range[0],
        key=f"{prefix}_ngram_min",
    )
    ngram_max = col2.number_input(
        "N-grama máximo",
        1,
        3,
        defaults.tfidf_ngram_range[1],
        key=f"{prefix}_ngram_max",
    )
    max_features = col3.number_input(
        "Vocabulario máximo",
        100,
        50000,
        defaults.tfidf_max_features,
        step=100,
        key=f"{prefix}_max_features",
    )
    min_df = st.number_input(
        "min_df",
        1,
        20,
        defaults.tfidf_min_df,
        key=f"{prefix}_min_df",
    )
    layers_text = st.text_input(
        "Neuronas por capa",
        value=",".join(str(item) for item in defaults.mlp_hidden_layer_sizes),
        key=f"{prefix}_layers",
    )
    col4, col5 = st.columns(2)
    activation_options = ["relu", "tanh", "logistic"]
    activation = col4.selectbox(
        "Activación",
        activation_options,
        index=activation_options.index(defaults.mlp_activation)
        if defaults.mlp_activation in activation_options
        else 0,
        key=f"{prefix}_activation",
    )
    max_iter = col5.number_input(
        "Épocas máximas",
        20,
        5000,
        defaults.mlp_max_iter,
        step=20,
        key=f"{prefix}_max_iter",
    )
    col6, col7 = st.columns(2)
    alpha = col6.number_input(
        "Alpha",
        0.0,
        1.0,
        float(defaults.mlp_alpha),
        step=0.0001,
        format="%.4f",
        key=f"{prefix}_alpha",
    )
    learning_rate = col7.number_input(
        "Learning rate",
        0.00001,
        1.0,
        float(defaults.mlp_learning_rate_init),
        step=0.0001,
        format="%.5f",
        key=f"{prefix}_learning_rate",
    )
    early_stopping = st.checkbox(
        "Early stopping",
        value=defaults.mlp_early_stopping,
        key=f"{prefix}_early_stopping",
    )
    try:
        layers = tuple(int(value.strip()) for value in layers_text.split(",") if value.strip())
        return HiperparametrosModelo(
            tfidf_ngram_range=(int(ngram_min), int(ngram_max)),
            tfidf_max_features=int(max_features),
            tfidf_min_df=int(min_df),
            mlp_hidden_layer_sizes=layers,
            mlp_activation=activation,
            mlp_alpha=float(alpha),
            mlp_learning_rate_init=float(learning_rate),
            mlp_max_iter=int(max_iter),
            mlp_early_stopping=bool(early_stopping),
        )
    except (TypeError, ValueError) as exc:
        st.error(f"Hiperparámetros no válidos: {exc}")
        return None


def _show_metrics(metrics: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", metrics["total"])
    col2.metric("Accuracy", f"{metrics['accuracy'] * 100:.1f}%")
    col3.metric("Precisión", f"{metrics['precision'] * 100:.1f}%")
    col4.metric("Recall", f"{metrics['recall'] * 100:.1f}%")
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("F1", f"{metrics['f1'] * 100:.1f}%")
    col6.metric("VP", metrics["true_positives"])
    col7.metric("FP", metrics["false_positives"])
    col8.metric("FN", metrics["false_negatives"])


def _show_model_cards(models: dict) -> None:
    cards = []
    for language, label in (("es", "Español"), ("en", "Inglés")):
        model = models.get(language, {})
        available = bool(model.get("available"))
        valid = bool(model.get("valid"))
        version = model.get("version") or "fallback sintético"
        if valid:
            status = estado_badge(True, "Activo", "")
        elif available:
            status = estado_badge(False, "", "Artefacto no válido")
        else:
            status = estado_badge(False, "", "Sin artefacto")
        cards.append(
            f"""
            <div class="ui-card">
                <div class="ui-label">Modelo {label}</div>
                <div class="ui-value">{status}</div>
                <div class="ui-note">Versión: <code>{version}</code></div>
            </div>
            """
        )
    render_html(f'<div class="ui-grid ui-grid-2">{"".join(cards)}</div>')


def _training_tab(client: BackendClient) -> None:
    st.markdown("### Entrenar y activar un modelo central")
    st.info(
        "Los CSV se envían al backend. El servidor entrena, guarda de forma atómica "
        "y hace que todos los clientes usen la nueva versión."
    )
    files = st.file_uploader(
        "CSV de entrenamiento",
        type=["csv"],
        accept_multiple_files=True,
        key="train_files",
    )
    dataset_format = st.radio(
        "Formato",
        ["Texto completo", "Asunto + cuerpo"],
        key="train_format",
    )
    columns = _columns("train", dataset_format)
    language = st.selectbox("Idioma", ["es", "en"], format_func=lambda x: x.upper())
    with st.expander("Hiperparámetros", expanded=False):
        hyperparameters = _hyperparameters_form("train_hp")

    col_summary, col_train = st.columns(2)
    if col_summary.button("Resumir en el servidor", use_container_width=True):
        if not files:
            st.error("Sube al menos un CSV.")
        else:
            try:
                summaries = client.summarize(files, columns=columns)["datasets"]
                st.dataframe(summaries, use_container_width=True)
            except BackendClientError as exc:
                st.error(str(exc))

    if col_train.button("Entrenar y activar", use_container_width=True, type="primary"):
        if not files:
            st.error("Sube al menos un CSV.")
            return
        if hyperparameters is None:
            st.error("Corrige los hiperparámetros antes de entrenar.")
            return
        with st.spinner("El backend está entrenando el modelo..."):
            try:
                response = client.train(
                    files,
                    language=language,
                    columns=columns,
                    hyperparameters=hyperparameters,
                )
            except BackendClientError as exc:
                st.error(str(exc))
                return
        st.success(
            f"Modelo {language.upper()} activado para todos los clientes. "
            f"Versión {response['model']['version']}."
        )
        if response.get("training"):
            stats = response["training"]
            st.write(
                {
                    "Ejemplos": stats["n_samples"],
                    "Phishing": stats["phishing_count"],
                    "Legítimos": stats["legit_count"],
                    "Accuracy de entrenamiento": f"{stats['accuracy'] * 100:.1f}%",
                }
            )


def _evaluation_tab(client: BackendClient) -> None:
    st.markdown("### Evaluar el modelo activo")
    file = st.file_uploader("CSV de prueba", type=["csv"], key="evaluation_file")
    dataset_format = st.radio(
        "Formato de prueba",
        ["Texto completo", "Asunto + cuerpo"],
        key="evaluation_format",
    )
    columns = _columns("evaluation", dataset_format)
    language = st.selectbox(
        "Modelo",
        ["es", "en"],
        format_func=lambda x: x.upper(),
        key="evaluation_language",
    )
    if st.button("Evaluar en el servidor", use_container_width=True, type="primary"):
        if file is None:
            st.error("Sube un CSV de prueba.")
            return
        try:
            response = client.evaluate([file], language=language, columns=columns)
        except BackendClientError as exc:
            st.error(str(exc))
            return
        st.success(f"Evaluación completada con la versión {response['model']['version']}.")
        _show_metrics(response["metrics"])


def _comparison_tab(client: BackendClient) -> None:
    st.markdown("### Comparar configuraciones sin cambiar el modelo activo")
    training_files = st.file_uploader(
        "CSV de entrenamiento",
        type=["csv"],
        accept_multiple_files=True,
        key="compare_training",
    )
    test_file = st.file_uploader("CSV de prueba", type=["csv"], key="compare_test")
    dataset_format = st.radio(
        "Formato de los CSV",
        ["Texto completo", "Asunto + cuerpo"],
        key="compare_format",
    )
    columns = _columns("compare", dataset_format)
    language = st.selectbox(
        "Idioma",
        ["es", "en"],
        format_func=lambda x: x.upper(),
        key="compare_language",
    )
    model_count = st.number_input("Configuraciones", 1, 3, 1)
    models = []
    for index in range(int(model_count)):
        with st.expander(f"Modelo {index + 1}", expanded=index == 0):
            name = st.text_input(
                "Nombre",
                value=f"Modelo {chr(65 + index)}",
                key=f"compare_name_{index}",
            )
            hyperparameters = _hyperparameters_form(
                f"compare_hp_{index}",
                enabled_label="Personalizar esta configuración",
            )
            models.append({"name": name, "hyperparameters": hyperparameters})
    if st.button("Comparar en el servidor", use_container_width=True, type="primary"):
        if not training_files or test_file is None:
            st.error("Sube entrenamiento y prueba.")
            return
        if any(model["hyperparameters"] is None for model in models):
            st.error("Corrige los hiperparámetros antes de comparar.")
            return
        try:
            response = client.compare(
                training_files,
                [test_file],
                language=language,
                columns=columns,
                models=models,
            )
        except BackendClientError as exc:
            st.error(str(exc))
            return
        rows = []
        for item in response["results"]:
            metrics = item["metrics"]
            rows.append(
                {
                    "Modelo": item["name"],
                    "Accuracy": f"{metrics['accuracy'] * 100:.1f}%",
                    "Precisión": f"{metrics['precision'] * 100:.1f}%",
                    "Recall": f"{metrics['recall'] * 100:.1f}%",
                    "F1": f"{metrics['f1'] * 100:.1f}%",
                }
            )
        st.dataframe(rows, use_container_width=True)


def _models_tab(client: BackendClient, models: dict) -> None:
    st.markdown("### Modelos activos en el servidor")
    for language, label in (("es", "Español"), ("en", "Inglés")):
        model = models.get(language, {})
        with st.expander(f"{label} · {model.get('version') or 'sin artefacto'}"):
            st.json(model)
            confirmation = st.checkbox(
                f"Confirmo que quiero eliminar el modelo {label}",
                key=f"delete_confirmation_{language}",
            )
            if st.button(
                f"Eliminar modelo {label}",
                disabled=not confirmation or not model.get("available"),
                key=f"delete_model_{language}",
            ):
                try:
                    client.delete_model(language)
                except BackendClientError as exc:
                    st.error(str(exc))
                else:
                    st.success("Modelo eliminado en el backend.")
                    st.rerun()


def main() -> None:
    cargar_env_local(ROOT_DIR)
    aplicar_estilos_entrenamiento()
    encabezado_pagina(
        "Ciclo de vida del modelo",
        "Administración de modelos",
        "Entrena, evalúa y activa versiones centrales en español e inglés sin "
        "distribuir artefactos entre los clientes.",
        "Operaciones del servidor",
        "Los CSV se procesan en el backend y la activación se realiza de forma atómica.",
    )

    training_password = os.getenv("TRAINING_PASSWORD", "")
    if training_password:
        password = st.text_input("Contraseña de acceso", type="password")
        if password != training_password:
            st.warning("Introduce la contraseña para acceder a la administración.")
            st.stop()

    client = BackendClient()
    try:
        health = client.health()
        models = client.models()["models"]
    except BackendClientError as exc:
        st.error(str(exc))
        st.code("python src/backend_server.py", language="powershell")
        st.stop()

    st.success(f"Backend central conectado: `{client.base_url}`")
    st.caption(f"Contrato API {health.get('api_version', 'desconocido')}")
    _show_model_cards(models)
    tab_train, tab_eval, tab_compare, tab_models = st.tabs(
        ["Entrenar", "Evaluar", "Comparar", "Modelos activos"]
    )
    with tab_train:
        _training_tab(client)
    with tab_eval:
        _evaluation_tab(client)
    with tab_compare:
        _comparison_tab(client)
    with tab_models:
        _models_tab(client, models)


if __name__ == "__main__":
    main()
