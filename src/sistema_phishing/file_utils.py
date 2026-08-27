"""Escrituras atómicas para configuración, credenciales y estado local."""

from __future__ import annotations

import os
import uuid


def atomic_write_text(
    path: str,
    content: str,
    *,
    mode: int | None = None,
) -> None:
    """Escribe texto en un hermano temporal y sustituye el destino al final."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    filename = os.path.basename(path) or "file"
    temporary_path = os.path.join(
        directory,
        f".{filename}.{uuid.uuid4().hex}.tmp",
    )
    descriptor = None
    try:
        descriptor = os.open(
            temporary_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            mode if mode is not None else 0o666,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        if mode is not None:
            os.chmod(path, mode)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
