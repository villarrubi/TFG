"""Migra el almacenamiento histórico de la raíz a cliente y servidor."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sistema_phishing.env_loader import guardar_env_file, leer_env_file
from sistema_phishing.runtime_paths import (
    client_data_dir,
    client_env_path,
    server_env_path,
)

PRIVATE_CLIENT_FILES = ("credentials.json", "token.json", "estado_monitor.json")


def _split_env(values: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Separa claves sin mostrar ni transformar sus valores."""
    client: dict[str, str] = {}
    server: dict[str, str] = {}
    for key, value in values.items():
        if key == "BACKEND_ADMIN_TOKEN":
            # Es el secreto del servidor y, a la vez, la credencial presentada
            # por este cliente administrador.
            client[key] = value
            server[key] = value
        elif key.startswith(("BACKEND_", "NEURAL_")):
            server[key] = value
        else:
            client[key] = value
    return client, server


def _merged(
    destination: Path,
    template: Path,
    migrated: dict[str, str],
) -> dict[str, str]:
    """Respeta cualquier valor que ya exista en el nuevo destino."""
    values = leer_env_file(str(template))
    values.update(migrated)
    values.update(leer_env_file(str(destination)))
    return values


def migrate(*, apply: bool) -> list[str]:
    actions: list[str] = []
    legacy_env = ROOT / ".env.local"
    client_dir = client_data_dir(ROOT)
    client_env = client_env_path(ROOT)
    server_env = server_env_path(ROOT)
    client_template = ROOT / "config" / "client.env.example"
    server_template = ROOT / "config" / "server.env.example"

    legacy_values = leer_env_file(str(legacy_env))
    client_values, server_values = _split_env(legacy_values)
    actions.append(
        f"Configuración: {len(client_values)} claves cliente y "
        f"{len(server_values)} claves servidor."
    )

    if apply:
        client_dir.mkdir(parents=True, exist_ok=True)
        server_env.parent.mkdir(parents=True, exist_ok=True)
        guardar_env_file(
            str(client_env),
            _merged(client_env, client_template, client_values),
        )
        guardar_env_file(
            str(server_env),
            _merged(server_env, server_template, server_values),
        )

    for filename in PRIVATE_CLIENT_FILES:
        source = ROOT / filename
        destination = client_dir / filename
        if not source.exists():
            continue
        if destination.exists():
            actions.append(f"Conservado {source.name}: el destino ya existe.")
            continue
        actions.append(f"Mover {source.name} a runtime/client/.")
        if apply:
            os.replace(source, destination)

    if legacy_env.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = ROOT / f".env.local.legacy-{timestamp}"
        actions.append(f"Archivar .env.local como {archive.name}.")
        if apply:
            shutil.move(str(legacy_env), str(archive))

    return actions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Separa datos privados del cliente y ajustes del servidor."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica la migración; sin esta opción solo muestra el plan.",
    )
    args = parser.parse_args()
    for action in migrate(apply=args.apply):
        print(action)
    if not args.apply:
        print("Vista previa: vuelve a ejecutar con --apply para escribir los cambios.")


if __name__ == "__main__":
    main()
