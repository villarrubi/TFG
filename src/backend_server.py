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
from sistema_phishing.network import validar_host_local

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MIN_REMOTE_ADMIN_TOKEN_CHARS = 24


def validar_token_remoto(allow_remote: bool, admin_token: str) -> None:
    """Exige un secreto no trivial antes de escuchar fuera de loopback."""
    if not allow_remote:
        return
    if len(admin_token) < MIN_REMOTE_ADMIN_TOKEN_CHARS:
        raise SystemExit(
            "BACKEND_ADMIN_TOKEN debe tener al menos "
            f"{MIN_REMOTE_ADMIN_TOKEN_CHARS} caracteres con --allow-remote."
        )


def parse_args() -> argparse.Namespace:
    """Lee la configuración del proceso sin ocultar errores de validación."""
    cargar_env_local(ROOT_DIR)
    parser = argparse.ArgumentParser(
        description="Servidor HTTP local para centralizar el análisis de phishing."
    )
    parser.add_argument("--host", default=os.getenv("BACKEND_HOST", "127.0.0.1"))
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Permite escuchar fuera de loopback bajo responsabilidad del operador.",
    )
    parser.add_argument("--port", type=int, default=env_int("BACKEND_PORT", 8766))
    parser.add_argument(
        "--mode", choices=sorted(VALID_MODES), default=os.getenv("BACKEND_MODE", MODO_COMBINADO)
    )
    parser.add_argument("--threshold", type=float, default=env_float("BACKEND_THRESHOLD", 45.0))
    parser.add_argument("--heur-weight", type=int, default=env_int("BACKEND_HEUR_WEIGHT", 20))
    parser.add_argument("--neural-weight", type=int, default=env_int("BACKEND_NEURAL_WEIGHT", 80))
    parser.add_argument(
        "--high-confidence-threshold",
        type=float,
        default=env_float("BACKEND_HIGH_CONFIDENCE_THRESHOLD", 70.0),
    )
    return parser.parse_args()


def main() -> None:
    """Arranca el servidor y deja el modelo reutilizable en memoria."""
    args = parse_args()
    args.host = validar_host_local(args.host, allow_remote=args.allow_remote)
    admin_token = os.getenv("BACKEND_ADMIN_TOKEN", "")
    validar_token_remoto(args.allow_remote, admin_token)
    config = AnalysisBackendConfig(
        threshold=args.threshold,
        mode=args.mode,
        heur_weight=args.heur_weight,
        neural_weight=args.neural_weight,
        high_confidence_threshold=args.high_confidence_threshold,
        model_path_es=os.getenv("BACKEND_MODEL_ES", os.path.join(ROOT_DIR, "modelo_neural_es.joblib")),
        model_path_en=os.getenv("BACKEND_MODEL_EN", os.path.join(ROOT_DIR, "modelo_neural_en.joblib")),
    )
    service = AnalysisBackendService(config, admin_token=admin_token)
    server = crear_servidor_http(args.host, args.port, service)
    print(f"Backend central escuchando en http://{args.host}:{args.port}")
    print("Clientes: Streamlit, extensión Gmail y monitor.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBackend detenido por el usuario.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
