"""Comprueba que la memoria y las evaluaciones identifican los modelos activos."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    evaluation = json.loads((ROOT / "evaluation/results.json").read_text(encoding="utf-8"))
    training = json.loads((ROOT / "evaluation/training_results.json").read_text(encoding="utf-8"))
    memory = (ROOT / "TFG.tex").read_text(encoding="utf-8")
    for language, key in (("es", "spanish"), ("en", "english")):
        path = ROOT / "runtime/server/models" / f"modelo_neural_{language}.joblib"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if (
            actual != evaluation["models"][language]["sha256"]
            or actual != training[key]["model"]["sha256"]
            or actual not in memory
        ):
            raise SystemExit(
                f"El modelo {language.upper()} no coincide con la memoria y las evaluaciones. "
                "Fija la versión de entrega y reproduce los resultados antes de publicarla."
            )
    print("Modelos ES/EN coherentes con la memoria y ambas evaluaciones.")


if __name__ == "__main__":
    main()
