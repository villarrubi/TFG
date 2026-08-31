"""Evalúa el sistema sobre el split público de phishing de DIFrauD.

El corpus se descarga a una ruta ignorada, se verifica por SHA-256 y nunca se
ejecuta ni se siguen los enlaces que puedan aparecer en los mensajes. Solo se
versionan métricas, hashes de casos erróneos y procedencia.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

from sistema_phishing.analizador_email import parsear_eml_bytes
from sistema_phishing.analysis_service import EmailAnalysisService
from sistema_phishing.backend_service import AnalysisBackendConfig
from sistema_phishing.defaults import (
    DEFAULT_HEUR_WEIGHT,
    DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    DEFAULT_NEURAL_WEIGHT,
    DEFAULT_PHISHING_THRESHOLD,
)
from sistema_phishing.metrics import calcular_metricas_clasificacion
from sistema_phishing.modelo_neural import ModelStorage

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / ".external-evaluation"
DEFAULT_DATASET = DATASET_DIR / "difraud_phishing_test.jsonl"
DEFAULT_JSON = ROOT / "evaluation" / "external_results.json"
DEFAULT_REPORT = ROOT / "EXTERNAL_EVALUATION_REPORT.md"
REVISION = "c459612fbd74d57d18e924371cc85c0b1f310dda"
DATASET_URL = (
    "https://huggingface.co/datasets/difraud/difraud/resolve/"
    f"{REVISION}/phishing/test.jsonl"
)
EXPECTED_SHA256 = "a74a0eaef001d0d90dd7db6519a00213cd1bf99b18c06bf5ffc23f2044e5a068"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MODES = ("heuristico", "neural", "combinado")


def file_sha256(path: Path) -> str:
    """Calcula la huella del artefacto sin cargarlo entero en memoria."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    """Normaliza solo para comparar duplicados exactos de forma conservadora."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def download_dataset(target: Path) -> None:
    """Descarga exclusivamente la revisión fijada y limita su tamaño."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    request = Request(DATASET_URL, headers={"User-Agent": "TFG-external-evaluation/1.0"})
    size = 0
    try:
        with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            content_length = int(response.headers.get("Content-Length", "0") or 0)
            if content_length > MAX_DOWNLOAD_BYTES:
                raise ValueError("El corpus remoto supera el tamaño máximo permitido.")
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ValueError("El corpus remoto supera el tamaño máximo permitido.")
                output.write(block)
        if file_sha256(temporary) != EXPECTED_SHA256:
            raise ValueError("La huella del corpus descargado no coincide con la revisión fijada.")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def load_rows(path: Path) -> tuple[list[dict[str, object]], int]:
    """Valida el JSONL y elimina duplicados exactos sin alterar las etiquetas."""
    if file_sha256(path) != EXPECTED_SHA256:
        raise ValueError("SHA-256 inesperado: no se evaluará un corpus distinto del auditado.")
    unique: dict[str, dict[str, object]] = {}
    total = 0
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            total += 1
            item = json.loads(line)
            if set(item) != {"text", "label"}:
                raise ValueError(f"Esquema inesperado en la línea {line_number}.")
            text = item["text"]
            label = item["label"]
            if not isinstance(text, str) or not text.strip() or label not in {0, 1}:
                raise ValueError(f"Caso inválido en la línea {line_number}.")
            digest = text_hash(text)
            previous = unique.get(digest)
            if previous and previous["label"] != label:
                raise ValueError("El corpus contiene un texto duplicado con etiquetas opuestas.")
            unique.setdefault(
                digest,
                {"id": f"difraud-{digest[:16]}", "text": text, "label": int(label)},
            )
    return list(unique.values()), total - len(unique)


def local_reference_hashes() -> set[str]:
    """Reúne variantes exactas de los corpus locales de calibración y prueba."""
    hashes: set[str] = set()
    calibration = ROOT / "evaluation" / "calibration_controlled_v1.csv"
    with calibration.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            variants = (
                row.get("body", ""),
                "\n".join((row.get("subject", ""), row.get("sender", ""), row.get("body", ""))),
            )
            hashes.update(text_hash(value) for value in variants if value.strip())
    eml_dir = ROOT / "evaluation" / "local_emails_v1"
    for path in eml_dir.glob("*.eml"):
        parsed = parsear_eml_bytes(path.read_bytes())
        for key in ("body", "full_text"):
            value = str(parsed.get(key, "") or "")
            if value.strip():
                hashes.add(text_hash(value))
    return hashes


def training_metadata() -> dict[str, object]:
    """Registra fuentes declaradas y si existen textos para deduplicar."""
    models: dict[str, object] = {}
    for language in ("es", "en"):
        path = ROOT / "runtime" / "server" / "models" / f"modelo_neural_{language}.joblib"
        model = ModelStorage(str(path)).load()
        snapshots = list(getattr(model, "training_texts", []) or [])
        models[language] = {
            "model_sha256": file_sha256(path),
            "training_sources": list(getattr(model, "training_sources", []) or []),
            "training_protocol": getattr(model, "training_protocol", {}),
            "embedded_training_texts": len(snapshots),
        }
    return models


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


def evaluate(rows: list[dict[str, object]]) -> dict[str, object]:
    """Evalúa los tres modos y conserva solo identificadores de los errores."""
    config = AnalysisBackendConfig(
        mode="combinado",
        threshold=DEFAULT_PHISHING_THRESHOLD,
        heur_weight=DEFAULT_HEUR_WEIGHT,
        neural_weight=DEFAULT_NEURAL_WEIGHT,
        high_confidence_threshold=DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    )
    # El corpus se declara inglés; se fija el modelo EN para que mensajes muy
    # cortos no sean desviados por la inferencia probabilística de idioma.
    service = EmailAnalysisService(config, language_detector=lambda _text: "en")
    real = [int(row["label"]) for row in rows]
    predictions = {mode: [] for mode in MODES}
    errors = {mode: [] for mode in MODES}
    for row in rows:
        text = str(row["text"])
        results = service.analyze_all({"body": text, "full_text": text})
        for mode in MODES:
            result = results[mode]
            prediction = int(bool(result["is_phishing"]))
            predictions[mode].append(prediction)
            if prediction != int(row["label"]):
                errors[mode].append(
                    {
                        "id": row["id"],
                        "label": int(row["label"]),
                        "prediction": prediction,
                        "risk_score": round(float(result["risk_score"]), 4),
                    }
                )
    return {
        mode: {
            "metrics": metrics_payload(real, predictions[mode]),
            "misclassified": errors[mode],
        }
        for mode in MODES
    }


def build_result(dataset: Path) -> dict[str, object]:
    rows, duplicate_count = load_rows(dataset)
    local_hashes = local_reference_hashes()
    local_overlap = sum(text_hash(str(row["text"])) in local_hashes for row in rows)
    labels = {label: sum(int(row["label"]) == label for row in rows) for label in (0, 1)}
    metadata = training_metadata()
    return {
        "schema_version": 1,
        "purpose": "licensed_external_diagnostic",
        "dataset": {
            "name": "DIFrauD phishing test split",
            "repository": "https://huggingface.co/datasets/difraud/difraud",
            "revision": REVISION,
            "file": "phishing/test.jsonl",
            "sha256": EXPECTED_SHA256,
            "license": "MIT (según la ficha del repositorio)",
            "citation": "https://aclanthology.org/2024.lrec-main.468",
            "rows": len(rows),
            "labels": {"legitimate_0": labels[0], "phishing_1": labels[1]},
            "exact_duplicates_removed": duplicate_count,
            "exact_overlap_with_local_evaluation": local_overlap,
        },
        "configuration": {
            "threshold": DEFAULT_PHISHING_THRESHOLD,
            "heur_weight": DEFAULT_HEUR_WEIGHT,
            "neural_weight": DEFAULT_NEURAL_WEIGHT,
            "high_confidence_threshold": DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
            "forced_model_language": "en",
        },
        "training_audit": metadata,
        "independence": {
            "confirmed": False,
            "reason": (
                "El protocolo inglés ya fija y deduplica el CSV agregado usado para entrenar, "
                "pero DIFrauD remite a un benchmark histórico de 2020. No puede descartarse "
                "que alguna de sus fuentes originales aparezca también en aquel agregado."
            ),
        },
        "results": evaluate(rows),
    }


def pct(value: float) -> str:
    return f"{value * 100:.1f} %"


def render_report(payload: dict[str, object]) -> str:
    dataset = payload["dataset"]
    config = payload["configuration"]
    lines = [
        "# Diagnóstico sobre corpus externo licenciado",
        "",
        "## Resultado",
        "",
        "Esta prueba complementa los EML locales con el split de prueba de phishing de DIFrauD. Es una comprobación externa del flujo de texto, **no una estimación independiente de producción**: el corpus es histórico, no incluye la estructura MIME completa y no puede descartarse solapamiento de fuentes con el entrenamiento inglés.",
        "",
        "| Modo | N | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | FP | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in MODES:
        metrics = payload["results"][mode]["metrics"]
        lines.append(
            f"| {mode} | {metrics['n']} | {pct(metrics['accuracy'])} | "
            f"{pct(metrics['precision'])} | {pct(metrics['recall'])} | "
            f"{pct(metrics['f1'])} | {pct(metrics['balanced_accuracy'])} | "
            f"{metrics['fp']} | {metrics['fn']} |"
        )
    lines.extend(
        [
            "",
            "## Procedencia y controles",
            "",
            f"- Repositorio: [{dataset['name']}]({dataset['repository']}); licencia declarada: {dataset['license']}.",
            f"- Revisión fijada: `{dataset['revision']}`; SHA-256 del JSONL: `{dataset['sha256']}`.",
            f"- Composición: {dataset['rows']} textos ({dataset['labels']['phishing_1']} phishing y {dataset['labels']['legitimate_0']} legítimos).",
            f"- Duplicados exactos internos eliminados: {dataset['exact_duplicates_removed']}; coincidencias exactas con calibración/EML locales: {dataset['exact_overlap_with_local_evaluation']}.",
            "- Los enlaces contenidos en los textos no se visitan. El corpus bruto se guarda en `.external-evaluation/`, excluido de Git; solo se versionan métricas e identificadores hash de los errores.",
            f"- Configuración: umbral {config['threshold']:.0f}, fusión {config['heur_weight']}/{config['neural_weight']} y alta confianza {config['high_confidence_threshold']:.0f}.",
            "",
            "## Límite de independencia",
            "",
            payload["independence"]["reason"],
            "La ficha de DIFrauD describe ataques y correos benignos de usuarios reales, limpiados y etiquetados, pero remite a un benchmark de 2020. El entrenamiento inglés procede del agregado Phishing Email Dataset, cuyos componentes históricos incluyen CEAS, Enron, Ling, Nazario, Nigerian Fraud y SpamAssassin. Aunque la división interna del nuevo protocolo sí está deduplicada, no se ha demostrado la independencia entre las fuentes primarias de DIFrauD y ese agregado. Por ello estas cifras se etiquetan como diagnóstico con riesgo de fuga, no como validación externa concluyente.",
            "",
            "## Reproducción",
            "",
            "```powershell",
            "$env:PYTHONPATH = \"src\"",
            "python scripts/evaluate_external.py --download",
            "python scripts/evaluate_external.py --check",
            "```",
            "",
            "Referencia científica: [Boumber, Qachfar y Verma, LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.468).",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    if args.download:
        download_dataset(dataset)
    if not dataset.exists():
        raise SystemExit("Falta el corpus externo; ejecuta primero con --download.")
    result = build_result(dataset)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    report = render_report(result)
    if args.check:
        if not args.json_output.exists() or args.json_output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("El JSON externo guardado no coincide con la ejecución actual.")
        if not args.report_output.exists() or args.report_output.read_text(encoding="utf-8") != report:
            raise SystemExit("El informe externo guardado no coincide con la ejecución actual.")
    else:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(serialized, encoding="utf-8")
        args.report_output.write_text(report, encoding="utf-8")
    print(f"Evaluados {result['dataset']['rows']} textos externos. Informe: {args.report_output}")


if __name__ == "__main__":
    main()
