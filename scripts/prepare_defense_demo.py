"""Genera un respaldo determinista para la demostración de la defensa."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from sistema_phishing.backend_service import AnalysisBackendService

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "defense_demo" / "expected_results.json"
CASES = (
    (
        "bec_sin_enlace_es",
        ROOT / "evaluation" / "local_emails_v1" / "es_phishing_bec.eml",
        "phishing",
    ),
    (
        "reunion_legitima_en",
        ROOT / "evaluation" / "local_emails_v1" / "en_legitimate_meeting.eml",
        "legitimate",
    ),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_model_metadata(metadata: dict[str, object] | None) -> dict[str, object] | None:
    """Elimina fechas de sistema de ficheros que cambian entre clones."""
    if metadata is None:
        return None
    stable_keys = (
        "language",
        "available",
        "version",
        "size_bytes",
        "active_source",
        "fallback",
        "artifact_version",
    )
    return {key: metadata[key] for key in stable_keys if key in metadata}


def compact_mode_result(result: dict[str, object]) -> dict[str, object]:
    """Resume una estrategia sin perder las señales explicables."""
    signals = result.get("signals", {})
    return {
        "risk_score": result["risk_score"],
        "is_phishing": result["is_phishing"],
        "active_signals": sorted(name for name, active in signals.items() if active),
    }


def compact_result(response: dict[str, object]) -> dict[str, object]:
    """Conserva los tres modos y el modelo realmente cargado para la demo."""
    result = response["result"]
    return {
        "label": response["label"],
        "selected_mode": response["selected_mode"],
        "language": response["language"],
        **compact_mode_result(result),
        "mode_results": {
            mode: compact_mode_result(mode_result)
            for mode, mode_result in response["results"].items()
        },
        "model": stable_model_metadata(response.get("model")),
    }


def build_payload() -> dict[str, object]:
    """Ejecuta el mismo caso de uso que atiende ``POST /analyze``."""
    service = AnalysisBackendService()
    cases = []
    for name, path, expected_label in CASES:
        response = service.analyze_payload(
            {
                "eml_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                "options": {"mode": "combinado", "include_all": True},
            }
        )
        compact = compact_result(response)
        if compact["label"] != expected_label:
            raise ValueError(f"El caso de demo {name} no produce {expected_label}.")
        cases.append(
            {
                "name": name,
                "source": path.relative_to(ROOT).as_posix(),
                "source_sha256": file_sha256(path),
                "expected_label": expected_label,
                "response_summary": compact,
            }
        )
    health = service.build_health_payload()
    health["models"] = {
        language: stable_model_metadata(metadata)
        for language, metadata in health["models"].items()
    }
    return {
        "schema_version": 1,
        "purpose": "offline_defense_fallback",
        "health": health,
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    serialized = json.dumps(build_payload(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("El respaldo de defensa no coincide con los modelos y reglas actuales.")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(f"Respaldo de defensa verificado: {args.output}")


if __name__ == "__main__":
    main()
