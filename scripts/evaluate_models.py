"""Evalúa los tres modos sobre un conjunto separado y genera evidencia reproducible."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from sistema_phishing.analysis_service import EmailAnalysisService
from sistema_phishing.backend_service import AnalysisBackendConfig
from sistema_phishing.metrics import calcular_metricas_clasificacion

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "evaluation" / "controlled_holdout_v1.csv"
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
            raise ValueError(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}")
        rows = list(reader)
    if not rows:
        raise ValueError("El conjunto de evaluación está vacío.")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Los identificadores del conjunto deben ser únicos.")
    for row in rows:
        if row["language"] not in LANGUAGES or row["label"] not in {"0", "1"}:
            raise ValueError(f"Fila no válida: {row['id']}")
    return rows


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


def evaluate(rows: list[dict[str, str]], threshold: float) -> dict[str, object]:
    by_mode: dict[str, object] = {}
    for mode in MODES:
        config = AnalysisBackendConfig(mode=mode, threshold=threshold)
        service = EmailAnalysisService(config)
        predictions = []
        cases = []
        for row in rows:
            result = service.analyze(build_payload(row))
            prediction = int(bool(result["is_phishing"]))
            predictions.append(prediction)
            cases.append(
                {
                    "id": row["id"],
                    "language": row["language"],
                    "label": int(row["label"]),
                    "prediction": prediction,
                    "risk_score": float(result["risk_score"]),
                }
            )
        real = [int(row["label"]) for row in rows]
        per_language = {}
        for language in LANGUAGES:
            indices = [index for index, row in enumerate(rows) if row["language"] == language]
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


def render_report(payload: dict[str, object]) -> str:
    lines = [
        "# Informe de evaluación separada",
        "",
        "## Alcance y límites",
        "",
        "Esta ejecución usa un conjunto de desafío controlado creado después de congelar los modelos y excluido del entrenamiento. Los resultados sirven como regresión funcional comparable entre modos. **No estiman el rendimiento en producción**, porque los mensajes son sintéticos y la muestra no representa la distribución real del correo.",
        "",
        f"- Dataset: `evaluation/controlled_holdout_v1.csv` ({payload['dataset']['rows']} casos; SHA-256 `{payload['dataset']['sha256']}`).",
        f"- Composición: {payload['dataset']['composition']}.",
        f"- Umbral común: {payload['threshold']:.1f} %; combinado 60 % heurístico + 40 % neuronal.",
        f"- Modelo ES SHA-256: `{payload['models']['es']['sha256']}`.",
        f"- Modelo EN SHA-256: `{payload['models']['en']['sha256']}`.",
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
            "La comparación revela cómo responden los artefactos actuales ante un reto bilingüe no usado para ajustarlos. Cualquier cifra de entrenamiento almacenada en los modelos se mantiene separada de esta tabla. Para defender capacidad de generalización sigue siendo necesario evaluar un corpus externo real, licenciado y deduplicado frente a todas las fuentes de entrenamiento.",
            "",
            "## Reproducción",
            "",
            "```powershell",
            "$env:PYTHONPATH = \"src\"",
            "python scripts/evaluate_models.py",
            "```",
            "",
            "El JSON detallado conserva la predicción y puntuación de cada caso para analizar errores sin alterar el conjunto.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--threshold", type=float, default=45.0)
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    rows = load_rows(dataset)
    composition = Counter((row["language"], row["label"]) for row in rows)
    models = {
        language: {
            "path": path.name,
            "sha256": sha256(path),
        }
        for language, path in {
            "es": ROOT / "modelo_neural_es.joblib",
            "en": ROOT / "modelo_neural_en.joblib",
        }.items()
    }
    payload = {
        "schema_version": 1,
        "dataset": {
            "path": dataset.name,
            "sha256": sha256(dataset),
            "rows": len(rows),
            "composition": ", ".join(
                f"{language.upper()} clase {label}: {composition[(language, label)]}"
                for language in LANGUAGES
                for label in ("0", "1")
            ),
            "representative": False,
            "training_use": False,
        },
        "models": models,
        "threshold": args.threshold,
        "results": evaluate(rows, args.threshold),
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
