"""Benchmark reproducible de los caminos críticos de la aplicación.

No pretende sustituir a un perfilador: ofrece una línea base rápida y estable
para detectar regresiones en arranque, carga de modelos e inferencia.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"


def _medir(funcion: Callable[[], object], iteraciones: int, repeticiones: int) -> dict[str, float]:
    """Devuelve tiempo mediano y mejor tiempo por operación, en milisegundos."""
    muestras: list[float] = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        for _ in range(iteraciones):
            funcion()
        muestras.append((time.perf_counter() - inicio) * 1000 / iteraciones)
    return {
        "median_ms": round(statistics.median(muestras), 4),
        "best_ms": round(min(muestras), 4),
    }


def _medir_importacion(modulo: str, repeticiones: int) -> dict[str, float]:
    """Mide una importación en procesos nuevos para evitar la caché de módulos."""
    codigo = (
        "import importlib,time;"
        "inicio=time.perf_counter();"
        f"importlib.import_module({modulo!r});"
        "print((time.perf_counter()-inicio)*1000)"
    )
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(SRC_DIR)
    muestras: list[float] = []
    for _ in range(repeticiones):
        proceso = subprocess.run(
            [sys.executable, "-B", "-c", codigo],
            cwd=ROOT_DIR,
            env=entorno,
            check=True,
            capture_output=True,
            text=True,
        )
        muestras.append(float(proceso.stdout.strip()))
    return {
        "median_ms": round(statistics.median(muestras), 4),
        "best_ms": round(min(muestras), 4),
    }


def ejecutar_benchmarks(iteraciones: int, repeticiones: int) -> dict[str, dict[str, float]]:
    """Ejecuta benchmarks de arranque, heurística e inferencia neuronal."""
    resultados = {
        "cold_import_heuristics": _medir_importacion(
            "sistema_phishing.heuristicas", repeticiones
        ),
        "cold_import_app": _medir_importacion("app", repeticiones),
    }

    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    heuristicas = importlib.import_module("sistema_phishing.heuristicas")
    idioma = importlib.import_module("sistema_phishing.idioma")
    modelo = importlib.import_module("sistema_phishing.modelo_neural")
    servicio_mod = importlib.import_module("sistema_phishing.analysis_service")
    defaults = importlib.import_module("sistema_phishing.defaults")

    texto = (
        "From: Banco Ejemplo <alerta@seguro.example>\n"
        "Subject: Acción urgente\n\n"
        "Estimado cliente, verifique sus credenciales inmediatamente en "
        "https://secure-login.example.com/login?next=https://evil.example"
    )
    email = {
        "full_text": texto,
        "body": texto,
        "subject": "Acción urgente",
        "from": "Banco Ejemplo <alerta@seguro.example>",
        "urls": ["https://secure-login.example.com/login?next=https://evil.example"],
    }
    config = SimpleNamespace(
        threshold=defaults.DEFAULT_PHISHING_THRESHOLD,
        mode="combinado",
        heur_weight=defaults.DEFAULT_HEUR_WEIGHT,
        neural_weight=defaults.DEFAULT_NEURAL_WEIGHT,
        model_path_es=str(ROOT_DIR / "runtime" / "server" / "models" / "modelo_neural_es.joblib"),
        model_path_en=str(ROOT_DIR / "runtime" / "server" / "models" / "modelo_neural_en.joblib"),
    )

    # Calentamiento: evita atribuir la inicialización interna de langdetect a
    # todas las operaciones posteriores.
    idioma.detectar_idioma_correo(texto)
    resultados["heuristic_analysis"] = _medir(
        lambda: heuristicas.analizar_correo(email), iteraciones, repeticiones
    )
    resultados["language_detection"] = _medir(
        lambda: idioma.detectar_idioma_correo(texto), iteraciones, repeticiones
    )

    storage = modelo.ModelStorage(config.model_path_es)
    iteraciones_carga = max(1, iteraciones // 20)
    resultados["model_load"] = _medir(storage.load, iteraciones_carga, repeticiones)

    classifier = storage.load()
    if classifier is None:
        raise RuntimeError(f"No se pudo cargar el modelo {config.model_path_es}")
    detector = modelo.NeuralPhishingDetector(classifier)
    resultados["neural_prediction"] = _medir(
        lambda: detector.analyze(texto), iteraciones, repeticiones
    )

    servicio = servicio_mod.EmailAnalysisService(config)
    servicio.analyze(email)
    resultados["combined_warm"] = _medir(
        lambda: servicio.analyze(email), iteraciones, repeticiones
    )
    iteraciones_frias = max(1, iteraciones // 100)
    resultados["combined_cold"] = _medir(
        lambda: servicio_mod.EmailAnalysisService(config).analyze(email),
        iteraciones_frias,
        repeticiones,
    )
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Emite JSON en lugar de tabla.")
    args = parser.parse_args()
    if args.iterations < 1 or args.repeats < 1:
        parser.error("iterations y repeats deben ser enteros positivos")

    resultados = ejecutar_benchmarks(args.iterations, args.repeats)
    if args.json:
        print(json.dumps(resultados, indent=2, sort_keys=True))
        return

    print(f"{'benchmark':<26} {'median_ms':>12} {'best_ms':>12}")
    for nombre, medicion in resultados.items():
        print(f"{nombre:<26} {medicion['median_ms']:>12.4f} {medicion['best_ms']:>12.4f}")


if __name__ == "__main__":
    main()
