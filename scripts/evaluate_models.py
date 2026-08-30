"""Evalúa los tres modos sobre un conjunto separado y genera evidencia reproducible."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from sistema_phishing.analizador_email import parsear_eml_bytes
from sistema_phishing.analysis_service import EmailAnalysisService
from sistema_phishing.backend_service import AnalysisBackendConfig
from sistema_phishing.defaults import (
    DEFAULT_HEUR_WEIGHT,
    DEFAULT_NEURAL_WEIGHT,
    DEFAULT_PHISHING_THRESHOLD,
)
from sistema_phishing.metrics import calcular_metricas_clasificacion
from sistema_phishing.modelo_neural import ModelStorage

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "evaluation" / "local_emails_v1" / "manifest.json"
DEFAULT_CALIBRATION = ROOT / "evaluation" / "calibration_results.json"
DEFAULT_JSON = ROOT / "evaluation" / "results.json"
DEFAULT_REPORT = ROOT / "EVALUATION_REPORT.md"
MODES = ("heuristico", "neural", "combinado")
LANGUAGES = ("es", "en")
REQUIRED_COLUMNS = {"id", "language", "label", "subject", "sender", "body", "urls"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Faltan columnas obligatorias: {', '.join(sorted(missing))}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError("El conjunto de evaluación está vacío.")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Los identificadores del conjunto deben ser únicos.")
    for row in rows:
        if row["language"] not in LANGUAGES or row["label"] not in {"0", "1"}:
            raise ValueError(f"Fila no válida: {row['id']}")
    return rows


def load_eml_cases(path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Carga un manifiesto seguro y parsea sus archivos EML locales."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("cases"), list):
        raise TypeError("El manifiesto EML debe contener una lista 'cases'.")
    raw_cases = manifest["cases"]
    if not raw_cases:
        raise ValueError("El corpus EML está vacío.")

    identifiers: set[str] = set()
    cases = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise TypeError("Cada caso EML debe ser un objeto JSON.")
        identifier = str(raw.get("id", "")).strip()
        language = str(raw.get("language", "")).strip()
        try:
            label = int(raw.get("label"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Etiqueta no válida en {identifier or '(sin id)'}."
            ) from exc
        filename = str(raw.get("file", "")).strip()
        if (
            not identifier
            or identifier in identifiers
            or language not in LANGUAGES
            or label not in {0, 1}
            or Path(filename).name != filename
            or not filename.lower().endswith(".eml")
        ):
            raise ValueError(f"Caso EML no válido: {identifier or '(sin id)'}.")
        identifiers.add(identifier)
        eml_path = path.parent / filename
        if not eml_path.is_file():
            raise ValueError(f"No existe el EML declarado: {filename}.")
        cases.append(
            {
                "id": identifier,
                "language": language,
                "label": label,
                "scenario": str(raw.get("scenario", "")),
                "file": filename,
                "payload": parsear_eml_bytes(eml_path.read_bytes()),
            }
        )
    metadata = {key: value for key, value in manifest.items() if key != "cases"}
    return cases, metadata


def load_cases(path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Admite el corpus EML reservado y CSV compatibles para experimentación."""
    if path.suffix.lower() == ".json":
        return load_eml_cases(path)
    rows = load_rows(path)
    return (
        [
            {
                "id": row["id"],
                "language": row["language"],
                "label": int(row["label"]),
                "scenario": row.get("provenance", ""),
                "payload": build_payload(row),
            }
            for row in rows
        ],
        {
            "name": path.stem,
            "representative_scenarios": False,
            "statistically_representative": False,
            "training_use": False,
            "calibration_use": False,
        },
    )


def corpus_sha256(path: Path, cases: list[dict[str, object]]) -> str:
    """Identifica el manifiesto y todos sus EML, no solo el índice JSON."""
    if path.suffix.lower() != ".json":
        return sha256(path)
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    for case in sorted(cases, key=lambda item: str(item["file"])):
        filename = str(case["file"])
        digest.update(filename.encode("utf-8"))
        digest.update((path.parent / filename).read_bytes())
    return digest.hexdigest()


def build_payload(row: dict[str, str]) -> dict[str, object]:
    urls = [value.strip() for value in row["urls"].split("|") if value.strip()]
    return {
        "subject": row["subject"],
        "from": row["sender"],
        "body": row["body"],
        "urls": urls,
        "headers": {"Subject": row["subject"], "From": row["sender"]},
        "full_text": "\n".join((row["subject"], row["sender"], row["body"])),
    }


def metrics_payload(real: list[int], predicted: list[int]) -> dict[str, object]:
    metrics = calcular_metricas_clasificacion(real, predicted)
    return {
        "n": metrics.total,
        "tp": metrics.verdaderos_positivos,
        "tn": metrics.verdaderos_negativos,
        "fp": metrics.falsos_positivos,
        "fn": metrics.falsos_negativos,
        "accuracy": round(metrics.accuracy, 4),
        "precision": round(metrics.precision, 4),
        "recall": round(metrics.recall, 4),
        "f1": round(metrics.f1, 4),
        "balanced_accuracy": round(metrics.balanced_accuracy, 4),
    }


def evaluate(
    rows: list[dict[str, object]],
    threshold: float,
    heur_weight: int,
    neural_weight: int,
    high_confidence_threshold: float = 70.0,
) -> dict[str, object]:
    by_mode: dict[str, object] = {}
    for mode in MODES:
        config = AnalysisBackendConfig(
            mode=mode,
            threshold=threshold,
            heur_weight=heur_weight,
            neural_weight=neural_weight,
            high_confidence_threshold=high_confidence_threshold,
        )
        service = EmailAnalysisService(config)
        predictions = []
        cases = []
        for row in rows:
            result = service.analyze(dict(row["payload"]))
            prediction = int(bool(result["is_phishing"]))
            predictions.append(prediction)
            cases.append(
                {
                    "id": row["id"],
                    "language": row["language"],
                    "label": int(row["label"]),
                    "prediction": prediction,
                    "risk_score": float(result["risk_score"]),
                    "scenario": str(row.get("scenario", "")),
                }
            )
        real = [int(row["label"]) for row in rows]
        per_language = {}
        for language in LANGUAGES:
            indices = [
                index for index, row in enumerate(rows) if row["language"] == language
            ]
            per_language[language] = metrics_payload(
                [real[index] for index in indices],
                [predictions[index] for index in indices],
            )
        by_mode[mode] = {
            "overall": metrics_payload(real, predictions),
            "by_language": per_language,
            "cases": cases,
        }
    return by_mode


def pct(value: float) -> str:
    return f"{value * 100:.1f} %"


def model_payload(path: Path) -> dict[str, object]:
    """Identifica el artefacto y expone solo sus metadatos no sensibles."""
    model = ModelStorage(str(path)).load()
    if model is None:
        raise ValueError(f"No se puede cargar el modelo declarado: {path.name}.")
    stats = asdict(model.last_training_stats) if model.last_training_stats else None
    return {
        "path": path.name,
        "sha256": sha256(path),
        "training_stats": stats,
        "training_sources": list(model.training_sources),
        "training_datetime": model.last_training_datetime,
        "raw_training_texts_stored": len(model.training_texts),
    }


def render_report(payload: dict[str, object]) -> str:
    lines = [
        "# Informe de evaluación separada",
        "",
        "## Alcance y límites",
        "",
        "Esta ejecución usa un corpus local de archivos EML reservado después de calibrar los parámetros. Incluye cabeceras, autenticación, texto, HTML y adjuntos en escenarios bilingües. **No estima el rendimiento en producción**, porque los mensajes están anonimizados y son sintéticos: representan situaciones operativas, no la distribución estadística del correo real.",
        "",
        f"- Dataset: `{payload['dataset']['path']}` ({payload['dataset']['rows']} EML; SHA-256 de manifiesto + mensajes `{payload['dataset']['sha256']}`).",
        f"- Composición: {payload['dataset']['composition']}.",
        f"- Calibración separada: `{payload['calibration']['path']}` ({payload['calibration']['rows']} casos; SHA-256 `{payload['calibration']['dataset_sha256']}`).",
        f"- Umbral común: {payload['threshold']:.1f} %; combinado {payload['weights']['heuristic']} % heurístico + {payload['weights']['neural']} % neuronal.",
        f"- Evidencia de alta confianza: si cualquier detector alcanza {payload['high_confidence_threshold']:.1f} %, su puntuación no se diluye en la media.",
        f"- Modelo ES SHA-256: `{payload['models']['es']['sha256']}`.",
        f"- Modelo EN SHA-256: `{payload['models']['en']['sha256']}`.",
        "",
        "## Artefactos de entrenamiento",
        "",
        "Los modelos conservan el tamaño, la distribución y las fuentes declaradas, pero no los textos originales. Por ello se describe el entrenamiento histórico sin atribuirle una partición 70/30 inexistente ni prometer su reconstrucción exacta.",
        "",
        "| Modelo | Muestras | Phishing | Legítimas | Fuentes declaradas | Textos brutos guardados |",
        "| --- | ---: | ---: | ---: | --- | ---: |",
        f"| ES | {payload['models']['es']['training_stats']['n_samples']} | {payload['models']['es']['training_stats']['phishing_count']} | {payload['models']['es']['training_stats']['legit_count']} | {', '.join(payload['models']['es']['training_sources'])} | {payload['models']['es']['raw_training_texts_stored']} |",
        f"| EN | {payload['models']['en']['training_stats']['n_samples']} | {payload['models']['en']['training_stats']['phishing_count']} | {payload['models']['en']['training_stats']['legit_count']} | {', '.join(payload['models']['en']['training_sources'])} | {payload['models']['en']['raw_training_texts_stored']} |",
        "",
        "## Resultados globales",
        "",
        "| Modo | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | VP | VN | FP | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in MODES:
        result = payload["results"][mode]["overall"]
        lines.append(
            f"| {mode} | {pct(result['accuracy'])} | {pct(result['precision'])} | "
            f"{pct(result['recall'])} | {pct(result['f1'])} | "
            f"{pct(result['balanced_accuracy'])} | {result['tp']} | {result['tn']} | "
            f"{result['fp']} | {result['fn']} |"
        )
    lines.extend(
        [
            "",
            "## Desglose por idioma",
            "",
            "| Modo | Idioma | N | Accuracy | Recall | F1 | FP | FN |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for mode in MODES:
        for language in LANGUAGES:
            result = payload["results"][mode]["by_language"][language]
            lines.append(
                f"| {mode} | {language.upper()} | {result['n']} | {pct(result['accuracy'])} | "
                f"{pct(result['recall'])} | {pct(result['f1'])} | {result['fp']} | {result['fn']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretación responsable",
            "",
            "La comparación revela cómo responden los artefactos actuales ante EML completos no usados para entrenar ni calibrar. El corpus permite probar de forma local escenarios de robo de credenciales, BEC sin enlace, enlaces discordantes, adjuntos, avisos legítimos y textos de concienciación. La muestra sigue siendo pequeña y sintética; una estimación estadística externa requeriría correo real licenciado, anonimizado y deduplicado frente al entrenamiento.",
            "",
            "## Reproducción",
            "",
            "```powershell",
            '$env:PYTHONPATH = "src"',
            "python scripts/calibrate_combined.py --check",
            "python scripts/evaluate_models.py",
            "```",
            "",
            "El JSON detallado conserva la predicción, puntuación y escenario de cada EML para analizar errores sin alterar el corpus ni los modelos.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--threshold", type=float, default=DEFAULT_PHISHING_THRESHOLD)
    parser.add_argument("--heur-weight", type=int, default=DEFAULT_HEUR_WEIGHT)
    parser.add_argument("--neural-weight", type=int, default=DEFAULT_NEURAL_WEIGHT)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    rows, dataset_metadata = load_cases(dataset)
    composition = Counter((row["language"], str(row["label"])) for row in rows)
    if args.heur_weight < 0 or args.neural_weight < 0:
        raise ValueError("Los pesos no pueden ser negativos.")
    if args.heur_weight + args.neural_weight == 0:
        raise ValueError("El modo combinado necesita al menos un peso positivo.")
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    models = {
        language: model_payload(path)
        for language, path in {
            "es": ROOT / "modelo_neural_es.joblib",
            "en": ROOT / "modelo_neural_en.joblib",
        }.items()
    }
    high_confidence_threshold = float(
        calibration["recommendation"]["high_confidence_threshold"]
    )
    payload = {
        "schema_version": 3,
        "dataset": {
            "path": dataset.relative_to(ROOT).as_posix(),
            "sha256": corpus_sha256(dataset, rows),
            "rows": len(rows),
            "composition": ", ".join(
                f"{language.upper()} clase {label}: {composition[(language, label)]}"
                for language in LANGUAGES
                for label in ("0", "1")
            ),
            "representative_scenarios": bool(
                dataset_metadata.get("representative_scenarios", False)
            ),
            "statistically_representative": bool(
                dataset_metadata.get("statistically_representative", False)
            ),
            "training_use": False,
            "calibration_use": False,
        },
        "calibration": {
            "path": args.calibration.relative_to(ROOT).as_posix(),
            "dataset_sha256": calibration["dataset"]["sha256"],
            "rows": calibration["dataset"]["rows"],
            "recommendation": calibration["recommendation"],
        },
        "models": models,
        "threshold": args.threshold,
        "weights": {
            "heuristic": args.heur_weight,
            "neural": args.neural_weight,
        },
        "high_confidence_threshold": high_confidence_threshold,
        "results": evaluate(
            rows,
            args.threshold,
            args.heur_weight,
            args.neural_weight,
            high_confidence_threshold,
        ),
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.report_output.write_text(render_report(payload), encoding="utf-8")
    print(f"Evaluados {len(rows)} casos. Informe: {args.report_output}")


if __name__ == "__main__":
    main()
