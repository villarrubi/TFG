"""Carga sencilla de variables de entorno desde archivos locales."""

import os
from typing import Dict


def cargar_env_file(path: str) -> None:
    """Carga variables KEY=VALUE si el archivo existe."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def cargar_env_local(root_dir: str) -> None:
    """Carga .env.local y después .env si existen en la raíz del proyecto."""
    cargar_env_file(os.path.join(root_dir, ".env.local"))
    cargar_env_file(os.path.join(root_dir, ".env"))


def leer_env_file(path: str) -> Dict[str, str]:
    """Lee un archivo KEY=VALUE y devuelve sus variables."""
    valores: Dict[str, str] = {}
    if not os.path.exists(path):
        return valores
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            valores[key.strip()] = value.strip().strip('"').strip("'")
    return valores


def guardar_env_file(path: str, valores: Dict[str, str]) -> None:
    """Guarda variables KEY=VALUE y actualiza el entorno actual."""
    with open(path, "w", encoding="utf-8") as env_file:
        for key in sorted(valores):
            value = valores[key]
            env_file.write(f"{key}={value}\n")
            os.environ[key] = value


def actualizar_env_local(root_dir: str, nuevos_valores: Dict[str, str]) -> None:
    """Actualiza .env.local conservando valores previos no modificados."""
    path = os.path.join(root_dir, ".env.local")
    valores = leer_env_file(path)
    valores.update({key: value for key, value in nuevos_valores.items() if value is not None})
    guardar_env_file(path, valores)
