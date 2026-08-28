"""Calibra pesos y umbral del modo combinado sobre un conjunto separado.

El script no modifica modelos ni artefactos. Evalúa una rejilla determinista y
favorece configuraciones estables entre cinco particiones estratificadas. El
corpus usado aquí deja de considerarse holdout final: la comprobación final se
realiza sobre los EML locales reservados por ``evaluate_models.py``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from evaluate_models import build_payload, load_rows, metrics_payload, sha256

from sistema_phishing.analysis_service import EmailAnalysisService
from sistema_phishing.backend_service import AnalysisBackendConfig

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "evaluation" / "calibration_controlled_v1.csv"
DEFAULT_OUTPUT = ROOT / "evaluation" / "calibration_results.json"


@dataclass(frozen=True)
class Candidate:
    """Configuración y métricas usadas para ordenar la rejilla."""

    heur_weight: int
    neural_weight: int
    threshold: int
    high_confidence_threshold: int
    min_fold_balanced_accuracy: float
    mean_fold_balanced_accuracy: float
    overall_balanced_accuracy: float
    overall_f1: float
    overall_recall: float
    overall_precision: float

    def rank(self) -> tuple[float, ...]:
        """Prioriza estabilidad, equilibrio y sensibilidad ante phishing."""
        return (
            self.min_fold_balanced_accuracy,
            self.mean_fold_balanced_accuracy,
            self.overall_balanced_accuracy,
            self.overall_f1,
            self.overall_recall,
            self.overall_precision,
            -abs(self.threshold - 45),
            -abs(self.high_confidence_threshold - 70),
            self.neural_weight,
        )


def collect_scores(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Calcula una sola vez las puntuaciones base de cada mensaje."""
    service = EmailAnalysisService(AnalysisBackendConfig(mode="combinado"))
    scored = []
    for row in rows:
        results = service.analyze_all(build_payload(row))
        scored.append(
            {
                "id": row["id"],
                "language": row["language"],
                "label": int(row["label"]),
                "heuristic_score": float(results["heuristico"]["risk_score"]),
                "neural_score": float(results["neural"]["risk_score"]),
            }
        )
    return scored


def stratified_folds(scored: list[dict[str, object]], folds: int = 5) -> list[list[int]]:
    """Distribuye de forma estable cada idioma y clase entre particiones."""
    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, row in enumerate(scored):
        groups[(str(row["language"]), int(row["label"]))].append(index)
    output = [[] for _ in range(folds)]
    for indices in groups.values():
        for position, index in enumerate(indices):
            output[position % folds].append(index)
    return output


def predictions(
    scored: list[dict[str, object]],
    heur_weight: int,
    neural_weight: int,
    threshold: int,
    high_confidence_threshold: int = 70,
) -> list[int]:
    """Aplica la misma fusión ponderada usada por el backend."""
    total = heur_weight + neural_weight
    output = []
    for row in scored:
        heuristic_score = float(row["heuristic_score"])
        neural_score = float(row["neural_score"])
        weighted_score = (
            heuristic_score * heur_weight + neural_score * neural_weight
        ) / total
        maximum_score = max(heuristic_score, neural_score)
        combined_score = (
            max(weighted_score, maximum_score)
            if maximum_score >= high_confidence_threshold
            else weighted_score
        )
        output.append(int(combined_score >= threshold))
    return output


def search(scored: list[dict[str, object]]) -> list[Candidate]:
    """Recorre una rejilla acotada en la que ambos detectores contribuyen."""
    labels = [int(row["label"]) for row in scored]
    folds = stratified_folds(scored)
    candidates = []
    # Se reserva al menos un 20 % a cada detector para que "combinado" no sea
    # un alias práctico del modo neuronal o del heurístico.
    for heur_weight in range(20, 51, 5):
        neural_weight = 100 - heur_weight
        for threshold in range(20, 61):
            for high_confidence_threshold in range(65, 86, 5):
                predicted = predictions(
                    scored,
                    heur_weight,
                    neural_weight,
                    threshold,
                    high_confidence_threshold,
                )
                overall = metrics_payload(labels, predicted)
                fold_metrics = []
                for indices in folds:
                    fold_metrics.append(
                        metrics_payload(
                            [labels[index] for index in indices],
                            [predicted[index] for index in indices],
                        )
                    )
                balanced = [float(item["balanced_accuracy"]) for item in fold_metrics]
                candidates.append(
                    Candidate(
                        heur_weight=heur_weight,
                        neural_weight=neural_weight,
                        threshold=threshold,
                        high_confidence_threshold=high_confidence_threshold,
                        min_fold_balanced_accuracy=min(balanced),
                        mean_fold_balanced_accuracy=sum(balanced) / len(balanced),
                        overall_balanced_accuracy=float(overall["balanced_accuracy"]),
                        overall_f1=float(overall["f1"]),
                        overall_recall=float(overall["recall"]),
                        overall_precision=float(overall["precision"]),
                    )
                )
    return sorted(candidates, key=Candidate.rank, reverse=True)


def build_result(dataset: Path) -> dict[str, object]:
    """Genera el resultado reproducible de calibración."""
    rows = load_rows(dataset)
    scored = collect_scores(rows)
    ranked = search(scored)
    best = ranked[0]
    return {
        "schema_version": 1,
        "purpose": "combined_mode_calibration",
        "dataset": {
            "path": dataset.name,
            "sha256": sha256(dataset),
            "rows": len(rows),
            "training_use": False,
            "final_evaluation_use": False,
        },
        "method": {
            "folds": 5,
            "stratified_by": ["language", "label"],
            "heuristic_weights": "20..50 step 5",
            "neural_weight": "100 - heuristic_weight",
            "thresholds": "20..60 step 1",
            "high_confidence_thresholds": "65..85 step 5",
            "selection": "min fold balanced accuracy, mean fold balanced accuracy, overall metrics",
        },
        "recommendation": best.__dict__,
        "top_candidates": [candidate.__dict__ for candidate in ranked[:10]],
        "scores": scored,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    result = build_result(args.dataset.resolve())
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("La calibración guardada no coincide con la ejecución actual.")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    recommendation = result["recommendation"]
    print(
        "Recomendación: "
        f"heurístico={recommendation['heur_weight']} %, "
        f"neuronal={recommendation['neural_weight']} %, "
        f"umbral={recommendation['threshold']} %, "
        f"alta confianza={recommendation['high_confidence_threshold']} %."
    )


if __name__ == "__main__":
    main()
