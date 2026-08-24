"""Servidor HTTP local que expone el análisis centralizado del proyecto."""

from __future__ import annotations

import argparse
import os

from sistema_phishing.analysis_service import MODO_COMBINADO, VALID_MODES
from sistema_phishing.backend_service import (
    AnalysisBackendConfig,
    AnalysisBackendService,
)
from sistema_phishing.env_loader import cargar_env_local, env_float, env_int
from sistema_phishing.http_api import crear_servidor_http

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def parse_args() -> argparse.Namespace:
    """Lee la configuración del proceso sin ocultar errores de validación."""
    cargar_env_local(ROOT_DIR)
    parser = argparse.ArgumentParser(
        description="Servidor HTTP local para centralizar el análisis de phishing."
    )
    parser.add_argument("--host", default=os.getenv("BACKEND_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=env_int("BACKEND_PORT", 8766))
    parser.add_argument(
        "--mode", choices=sorted(VALID_MODES), default=os.getenv("BACKEND_MODE", MODO_COMBINADO)
    )
    parser.add_argument("--threshold", type=float, default=env_float("BACKEND_THRESHOLD", 45.0))
    parser.add_argument("--heur-weight", type=int, default=env_int("BACKEND_HEUR_WEIGHT", 60))
    parser.add_argument("--neural-weight", type=int, default=env_int("BACKEND_NEURAL_WEIGHT", 40))
    return parser.parse_args()


def main() -> None:
    """Arranca el servidor y deja el modelo reutilizable en memoria."""
    args = parse_args()
    config = AnalysisBackendConfig(
        threshold=args.threshold,
        mode=args.mode,
        heur_weight=args.heur_weight,
        neural_weight=args.neural_weight,
        model_path_es=os.getenv("BACKEND_MODEL_ES", os.path.join(ROOT_DIR, "modelo_neural_es.joblib")),
        model_path_en=os.getenv("BACKEND_MODEL_EN", os.path.join(ROOT_DIR, "modelo_neural_en.joblib")),
    )
    server = crear_servidor_http(args.host, args.port, AnalysisBackendService(config))
    print(f"Backend escuchando en http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBackend detenido por el usuario.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
