"""Reentrena y evalúa los modelos entregados con un protocolo reproducible.

Los CSV permanecen fuera del repositorio. El manifiesto versionado fija sus
fuentes y SHA-256; este script rechaza cualquier archivo que no coincida. La
salida contiene métricas y huellas de las particiones, nunca textos de correo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from sistema_phishing.dataset import cargar_dataset_csv
from sistema_phishing.defaults import (
    DEFAULT_HEUR_WEIGHT,
    DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    DEFAULT_NEURAL_WEIGHT,
    DEFAULT_PHISHING_THRESHOLD,
)
from sistema_phishing.heuristicas import analizar_correo
from sistema_phishing.metrics import calcular_metricas_clasificacion
from sistema_phishing.model_config import DEFAULT_HIPERPARAMETROS
from sistema_phishing.modelo_neural import (
    ModelStorage,
    NeuralPhishingClassifier,
    TrainingSourceInfo,
)
from sistema_phishing.training_protocol import (
    TrainingExample,
    clean_training_examples,
    split_fingerprint,
    stratified_split,
    training_text_hash,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT.parents[1] / "datos_entrenamiento"
MANIFEST_PATH = ROOT / "evaluation" / "training_sources.json"
RESULTS_PATH = ROOT / "evaluation" / "training_results.json"
REPORT_PATH = ROOT / "TRAINING_EVALUATION_REPORT.md"
RANDOM_STATE = 42
TEST_FRACTION = 0.2
MODES = ("heuristico", "neural", "combinado")
MODE_LABELS = {
    "heuristico": "Heurístico",
    "neural": "Neuronal",
    "combinado": "Combinado",
}


def file_sha256(path: Path) -> str:
    """Calcula la huella de un archivo sin cargarlo entero en memoria."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def language_directory(data_root: Path, prefix: str) -> Path:
    """Resuelve las carpetas español/inglés sin depender de sus tildes."""

    matches = [
        path
        for path in data_root.iterdir()
        if path.is_dir() and path.name.casefold().startswith(prefix)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Se esperaba una carpeta cuyo nombre empezara por {prefix!r} en {data_root}."
        )
    return matches[0]


def resolve_sources(data_root: Path, manifest: dict) -> dict[str, Path]:
    """Localiza los CSV y comprueba que coincidan con el manifiesto."""

    paths: dict[str, Path] = {}
    for source_id, metadata in manifest["sources"].items():
        folder = language_directory(
            data_root, metadata["language_directory_prefix"]
        )
        path = folder / metadata["file"]
        if not path.is_file():
            raise FileNotFoundError(f"Falta el archivo requerido: {path}")
        actual_hash = file_sha256(path)
        if actual_hash != metadata["sha256"]:
            raise ValueError(f"SHA-256 inesperado para {source_id}: {actual_hash}")
        paths[source_id] = path
    return paths


def load_examples(
    path: Path,
    source: str,
    *,
    text_column: str,
    label_column: str,
) -> list[TrainingExample]:
    """Convierte un CSV verificado al contrato común del protocolo."""

    texts, labels = cargar_dataset_csv(
        str(path),
        label_column=label_column,
        text_column=text_column,
        subject_column="",
        body_column="",
    )
    return [
        TrainingExample(text, label, source)
        for text, label in zip(texts, labels)
    ]


def class_summary(examples: list[TrainingExample]) -> dict[str, int]:
    counts = Counter(example.label for example in examples)
    return {
        "rows": len(examples),
        "phishing": counts[1],
        "legitimate": counts[0],
    }


def prepare_datasets(paths: dict[str, Path]) -> dict[str, object]:
    """Aplica el protocolo español, inglés y la validación secundaria."""

    es_test_raw = load_examples(
        paths["es_hf_test"],
        "es_hf_test",
        text_column="mensaje",
        label_column="tipo",
    )
    es_test, es_test_cleaning = clean_training_examples(es_test_raw)
    es_training_raw = load_examples(
        paths["es_hf_train"],
        "es_hf_train",
        text_column="mensaje",
        label_column="tipo",
    )
    es_training_raw += load_examples(
        paths["es_kaggle_train"],
        "es_kaggle_train",
        text_column="mensaje",
        label_column="tipo",
    )
    es_training, es_cleaning = clean_training_examples(
        es_training_raw,
        excluded_hashes={training_text_hash(example.text) for example in es_test},
    )

    en_raw = load_examples(
        paths["en_kaggle_merged"],
        "en_kaggle_merged",
        text_column="text_combined",
        label_column="label",
    )
    en_clean, en_cleaning = clean_training_examples(en_raw)
    en_training, en_test = stratified_split(
        en_clean,
        test_fraction=TEST_FRACTION,
        random_state=RANDOM_STATE,
    )

    en_external_raw = load_examples(
        paths["en_zenodo_validation"],
        "en_zenodo_validation",
        text_column="Email Text",
        label_column="Email Type",
    )
    en_external_unique, en_external_cleaning = clean_training_examples(
        en_external_raw
    )
    return {
        "es_training": es_training,
        "es_test": es_test,
        "es_cleaning": es_cleaning,
        "es_test_cleaning": es_test_cleaning,
        "en_training": en_training,
        "en_test": en_test,
        "en_cleaning": en_cleaning,
        "en_external_raw": en_external_raw,
        "en_external_unique": en_external_unique,
        "en_external_cleaning": en_external_cleaning,
    }


def protocol_metadata(
    language: str,
    prepared: dict[str, object],
    manifest: dict,
) -> dict[str, object]:
    """Construye los metadatos que también se guardarán en el modelo."""

    if language == "es":
        training = prepared["es_training"]
        test = prepared["es_test"]
        cleaning = prepared["es_cleaning"]
        sources = ["es_hf_train", "es_kaggle_train"]
        split_method = (
            "Prueba oficial de Hugging Face; sus coincidencias se retiran "
            "del entrenamiento."
        )
    else:
        training = prepared["en_training"]
        test = prepared["en_test"]
        cleaning = prepared["en_cleaning"]
        sources = ["en_kaggle_merged"]
        split_method = "División estratificada 80/20 después de deduplicar."
    return {
        "protocol_id": "tfg-reproducible-v1",
        "random_state": RANDOM_STATE,
        "normalization": (
            "Unicode NFKC, espacios colapsados y casefold solo para detectar "
            "igualdad exacta."
        ),
        "conflicts": (
            "Se retira el grupo entero cuando un mismo texto tiene etiquetas opuestas."
        ),
        "split_method": split_method,
        "training": class_summary(training),
        "test": class_summary(test),
        "training_fingerprint": split_fingerprint(training),
        "test_fingerprint": split_fingerprint(test),
        "cleaning": cleaning.to_dict(),
        "sources": {
            source_id: {
                "sha256": manifest["sources"][source_id]["sha256"],
                "repository": manifest["sources"][source_id]["repository"],
            }
            for source_id in sources
        },
    }


def source_info(
    examples: list[TrainingExample], manifest: dict
) -> list[TrainingSourceInfo]:
    """Resume la contribución limpia de cada fuente al modelo."""

    output = []
    for source_id in dict.fromkeys(example.source for example in examples):
        subset = [example for example in examples if example.source == source_id]
        counts = class_summary(subset)
        output.append(
            TrainingSourceInfo(
                source=manifest["sources"][source_id]["citation"],
                n_samples=counts["rows"],
                phishing_count=counts["phishing"],
                legit_count=counts["legitimate"],
            )
        )
    return output


def train_model(
    language: str,
    examples: list[TrainingExample],
    protocol: dict,
    manifest: dict,
) -> NeuralPhishingClassifier:
    """Entrena con los hiperparámetros entregados, no con variables locales."""

    model = NeuralPhishingClassifier(
        language="spanish" if language == "es" else "english",
        hiperparametros=DEFAULT_HIPERPARAMETROS,
    )
    sources = source_info(examples, manifest)
    model.training_sources = [item.source for item in sources]
    model.training_sources_info = sources
    model.training_columns = {
        "label": "tipo" if language == "es" else "label",
        "text": "mensaje" if language == "es" else "text_combined",
        "subject": "",
        "body": "",
    }
    model.training_protocol = protocol
    model.trained_with_default = False
    model.fit(
        [example.text for example in examples],
        [example.label for example in examples],
    )
    return model


def save_models(models: dict[str, NeuralPhishingClassifier]) -> None:
    """Verifica temporales y reemplaza cada artefacto de forma atómica."""

    temporary: dict[str, Path] = {}
    try:
        for language, model in models.items():
            target = ROOT / f"modelo_neural_{language}.joblib"
            temp = target.with_suffix(target.suffix + ".tmp")
            model.save(str(temp))
            loaded = ModelStorage(str(temp)).load()
            protocol = getattr(loaded, "training_protocol", {}) if loaded else {}
            if protocol.get("protocol_id") != "tfg-reproducible-v1":
                raise RuntimeError(
                    f"No se pudo verificar el modelo temporal {language}."
                )
            temporary[language] = temp
        for language, temp in temporary.items():
            os.replace(temp, ROOT / f"modelo_neural_{language}.joblib")
    finally:
        for temp in temporary.values():
            temp.unlink(missing_ok=True)


def metrics_payload(labels: list[int], predictions: list[int]) -> dict[str, object]:
    metrics = calcular_metricas_clasificacion(labels, predictions)
    return {
        "n": metrics.total,
        "tp": metrics.verdaderos_positivos,
        "tn": metrics.verdaderos_negativos,
        "fp": metrics.falsos_positivos,
        "fn": metrics.falsos_negativos,
        "confusion_matrix": [
            [metrics.verdaderos_negativos, metrics.falsos_positivos],
            [metrics.falsos_negativos, metrics.verdaderos_positivos],
        ],
        "accuracy": round(metrics.accuracy, 6),
        "precision": round(metrics.precision, 6),
        "recall": round(metrics.recall, 6),
        "f1": round(metrics.f1, 6),
        "balanced_accuracy": round(metrics.balanced_accuracy, 6),
    }


def evaluate_text_dataset(
    model: NeuralPhishingClassifier,
    examples: list[TrainingExample],
) -> dict[str, object]:
    """Compara los tres modos con el mismo umbral operativo."""

    texts = [example.text for example in examples]
    labels = [example.label for example in examples]
    neural_scores = [probability * 100 for probability in model.predict_proba(texts)]
    heuristic_scores = [
        float(analizar_correo({"body": text, "full_text": text})["risk_score"])
        for text in texts
    ]
    predictions = {mode: [] for mode in MODES}
    total_weight = DEFAULT_HEUR_WEIGHT + DEFAULT_NEURAL_WEIGHT
    for heuristic, neural in zip(heuristic_scores, neural_scores):
        weighted = (
            heuristic * DEFAULT_HEUR_WEIGHT + neural * DEFAULT_NEURAL_WEIGHT
        ) / total_weight
        maximum = max(heuristic, neural)
        combined = (
            maximum
            if maximum >= DEFAULT_HIGH_CONFIDENCE_THRESHOLD
            else weighted
        )
        predictions["heuristico"].append(
            int(heuristic >= DEFAULT_PHISHING_THRESHOLD)
        )
        predictions["neural"].append(int(neural >= DEFAULT_PHISHING_THRESHOLD))
        predictions["combinado"].append(
            int(combined >= DEFAULT_PHISHING_THRESHOLD)
        )
    return {
        mode: metrics_payload(labels, predictions[mode]) for mode in MODES
    }


def model_payload(
    language: str, model: NeuralPhishingClassifier
) -> dict[str, object]:
    path = ROOT / f"modelo_neural_{language}.joblib"
    return {
        "sha256": file_sha256(path),
        "format_version": model.model_format_version,
        "trained_at_utc": model.last_training_datetime,
        "hyperparameters": asdict(model.hiperparametros),
        "training_accuracy_descriptive": round(
            model.last_training_stats.accuracy, 6
        ),
        "raw_training_texts_stored": len(model.training_texts),
    }


def build_result(
    prepared: dict[str, object],
    manifest: dict,
    models: dict[str, NeuralPhishingClassifier],
) -> dict[str, object]:
    """Calcula la evidencia experimental que se versionará."""

    es_protocol = protocol_metadata("es", prepared, manifest)
    en_protocol = protocol_metadata("en", prepared, manifest)
    return {
        "schema_version": 1,
        "configuration": {
            "threshold": DEFAULT_PHISHING_THRESHOLD,
            "heuristic_weight": DEFAULT_HEUR_WEIGHT,
            "neural_weight": DEFAULT_NEURAL_WEIGHT,
            "high_confidence_threshold": DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
            "random_state": RANDOM_STATE,
        },
        "spanish": {
            "protocol": es_protocol,
            "model": model_payload("es", models["es"]),
            "heldout_results": evaluate_text_dataset(
                models["es"], prepared["es_test"]
            ),
            "limitation": (
                "Los dos corpus son SMS spam/ham en español; se usan como "
                "aproximación textual a smishing/phishing y no como correo MIME completo."
            ),
        },
        "english": {
            "protocol": en_protocol,
            "model": model_payload("en", models["en"]),
            "heldout_results": evaluate_text_dataset(
                models["en"], prepared["en_test"]
            ),
            "secondary_external_validation": {
                "raw": class_summary(prepared["en_external_raw"]),
                "unique": class_summary(prepared["en_external_unique"]),
                "cleaning": prepared["en_external_cleaning"].to_dict(),
                "unique_results": evaluate_text_dataset(
                    models["en"], prepared["en_external_unique"]
                ),
                "row_weighted_results": evaluate_text_dataset(
                    models["en"], prepared["en_external_raw"]
                ),
                "source": manifest["sources"]["en_zenodo_validation"],
            },
            "limitation": (
                "La clase positiva agrega phishing y spam de varios corpus "
                "históricos; la partición mide generalización interna, no producción."
            ),
        },
        "interpretation": (
            "Los holdouts de texto no contienen cabeceras ni estructura MIME "
            "completa. Por ello infravaloran el modo heurístico; la comparación "
            "funcional con EML completos se publica por separado."
        ),
    }


def pct(value: float) -> str:
    return f"{value * 100:.1f} %".replace(".", ",")


def integer_es(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def result_table(results: dict[str, object]) -> list[str]:
    rows = [
        "| Modo | N | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | FP | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in MODES:
        item = results[mode]
        rows.append(
            f"| {MODE_LABELS[mode]} | {integer_es(item['n'])} | "
            f"{pct(item['accuracy'])} | "
            f"{pct(item['precision'])} | {pct(item['recall'])} | "
            f"{pct(item['f1'])} | {pct(item['balanced_accuracy'])} | "
            f"{item['fp']} | {item['fn']} |"
        )
    return rows


def render_report(payload: dict[str, object]) -> str:
    es = payload["spanish"]
    en = payload["english"]
    external = en["secondary_external_validation"]
    lines = [
        "# Entrenamiento y evaluación reproducibles",
        "",
        "## Protocolo corregido",
        "",
        (
            f"El modelo español usa {integer_es(es['protocol']['training']['rows'])} textos "
            f"limpios y una prueba oficial separada de "
            f"{integer_es(es['protocol']['test']['rows'])}. El inglés usa exclusivamente el "
            f"CSV agregado, deduplicado a {integer_es(en['protocol']['cleaning']['clean_rows'])} "
            f"textos, y una división estratificada 80/20 con semilla 42 "
            f"({integer_es(en['protocol']['training']['rows'])} entrenamiento y "
            f"{integer_es(en['protocol']['test']['rows'])} prueba). Los seis corpus componentes "
            "no se añaden de nuevo."
        ),
        "",
        (
            "Se eliminan copias exactas normalizadas, grupos con etiquetas "
            "contradictorias y cualquier coincidencia exacta entre entrenamiento "
            "y prueba. Los SHA-256, URLs, licencias y huellas de las particiones "
            "están en `evaluation/training_sources.json` y "
            "`evaluation/training_results.json`. Los CSV brutos no se versionan."
        ),
        "",
        "## Holdout español",
        "",
        *result_table(es["heldout_results"]),
        "",
        "## Holdout inglés interno",
        "",
        *result_table(en["heldout_results"]),
        "",
        "## Validación inglesa secundaria (Zenodo, textos únicos)",
        "",
        (
            f"El fichero contiene {integer_es(external['raw']['rows'])} filas pero solo "
            f"{integer_es(external['unique']['rows'])} textos únicos; la tabla principal "
            "pondera cada texto una sola vez."
        ),
        "",
        *result_table(external["unique_results"]),
        "",
        "## Interpretación y límites",
        "",
        f"- {payload['interpretation']}",
        f"- Español: {es['limitation']}",
        f"- Inglés: {en['limitation']}",
        (
            "- La accuracy del propio entrenamiento se conserva solo como dato "
            "descriptivo; las conclusiones se basan en pruebas no usadas para ajustar."
        ),
        "- Las matrices de confusión completas se encuentran en el JSON reproducible.",
        "",
        "## Reproducción",
        "",
        "```powershell",
        '$env:PYTHONPATH = "src"',
        (
            'python scripts/retrain_reproducible.py --data-root '
            '"C:\\ruta\\a\\datos_entrenamiento"'
        ),
        (
            'python scripts/retrain_reproducible.py --data-root '
            '"C:\\ruta\\a\\datos_entrenamiento" --evaluate-only --check'
        ),
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="No reentrena; vuelve a evaluar los modelos activos.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Comprueba que JSON e informe coincidan sin escribirlos.",
    )
    args = parser.parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    paths = resolve_sources(args.data_root.resolve(), manifest)
    prepared = prepare_datasets(paths)
    protocols = {
        language: protocol_metadata(language, prepared, manifest)
        for language in ("es", "en")
    }
    if args.evaluate_only or args.check:
        models = {
            language: ModelStorage(
                str(ROOT / f"modelo_neural_{language}.joblib")
            ).load()
            for language in ("es", "en")
        }
        if any(model is None for model in models.values()):
            raise RuntimeError("No se pudieron cargar los dos modelos activos.")
        for language, model in models.items():
            if getattr(model, "training_protocol", {}) != protocols[language]:
                raise RuntimeError(
                    f"El modelo {language} no corresponde al protocolo actual."
                )
    else:
        models = {
            "es": train_model(
                "es", prepared["es_training"], protocols["es"], manifest
            ),
            "en": train_model(
                "en", prepared["en_training"], protocols["en"], manifest
            ),
        }
        save_models(models)
    result = build_result(prepared, manifest, models)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    report = render_report(result)
    if args.check:
        if (
            not RESULTS_PATH.exists()
            or RESULTS_PATH.read_text(encoding="utf-8") != serialized
        ):
            raise SystemExit(
                "El JSON de entrenamiento no coincide con la ejecución actual."
            )
        if (
            not REPORT_PATH.exists()
            or REPORT_PATH.read_text(encoding="utf-8") != report
        ):
            raise SystemExit(
                "El informe de entrenamiento no coincide con la ejecución actual."
            )
    else:
        RESULTS_PATH.write_text(serialized, encoding="utf-8")
        REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Protocolo reproducido. Informe: {REPORT_PATH}")


if __name__ == "__main__":
    main()
