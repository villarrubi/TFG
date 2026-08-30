"""Utilidades reproducibles para preparar corpus de entrenamiento y prueba.

La aplicación permite entrenar CSV arbitrarios desde el backend. Este módulo
se reserva para el protocolo experimental entregado con el TFG: normaliza
únicamente para detectar copias exactas, retira contradicciones y crea una
partición estratificada estable sin conservar los textos dentro del modelo.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

from sklearn.model_selection import train_test_split


@dataclass(frozen=True)
class TrainingExample:
    """Texto etiquetado junto con el identificador público de su fuente."""

    text: str
    label: int
    source: str


@dataclass(frozen=True)
class CleaningSummary:
    """Cuenta qué ha cambiado durante la limpieza conservadora."""

    raw_rows: int
    clean_rows: int
    removed_duplicate_rows: int
    removed_conflicting_rows: int
    conflicting_groups: int
    removed_overlap_rows: int
    phishing_rows: int
    legitimate_rows: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def normalize_training_text(text: str) -> str:
    """Normaliza Unicode, mayúsculas y espacios para comparar igualdad exacta."""

    normalized = unicodedata.normalize("NFKC", str(text))
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def training_text_hash(text: str) -> str:
    """Devuelve un identificador irreversible del texto normalizado."""

    return hashlib.sha256(normalize_training_text(text).encode("utf-8")).hexdigest()


def clean_training_examples(
    examples: list[TrainingExample],
    *,
    excluded_hashes: set[str] | None = None,
) -> tuple[list[TrainingExample], CleaningSummary]:
    """Elimina copias, contradicciones y coincidencias con un holdout.

    Cuando el mismo texto tiene etiquetas distintas se retira el grupo entero:
    escoger una etiqueta de forma arbitraria introduciría ruido y ocultaría el
    conflicto. Para duplicados coherentes se conserva la primera aparición.
    """

    excluded_hashes = excluded_hashes or set()
    groups: dict[str, list[TrainingExample]] = defaultdict(list)
    for example in examples:
        if example.label not in {0, 1}:
            raise ValueError("Las etiquetas del protocolo deben ser 0 o 1.")
        if not example.text.strip():
            raise ValueError("El protocolo no admite textos vacíos.")
        groups[training_text_hash(example.text)].append(example)

    clean: list[TrainingExample] = []
    duplicate_rows = 0
    conflicting_rows = 0
    conflicting_groups = 0
    overlap_rows = 0
    for digest, group in groups.items():
        if len({example.label for example in group}) > 1:
            conflicting_groups += 1
            conflicting_rows += len(group)
            continue
        if digest in excluded_hashes:
            overlap_rows += len(group)
            continue
        clean.append(group[0])
        duplicate_rows += len(group) - 1

    counts = Counter(example.label for example in clean)
    summary = CleaningSummary(
        raw_rows=len(examples),
        clean_rows=len(clean),
        removed_duplicate_rows=duplicate_rows,
        removed_conflicting_rows=conflicting_rows,
        conflicting_groups=conflicting_groups,
        removed_overlap_rows=overlap_rows,
        phishing_rows=counts[1],
        legitimate_rows=counts[0],
    )
    return clean, summary


def stratified_split(
    examples: list[TrainingExample],
    *,
    test_fraction: float = 0.2,
    random_state: int = 42,
) -> tuple[list[TrainingExample], list[TrainingExample]]:
    """Crea una división aleatoria estratificada y determinista."""

    if not 0 < test_fraction < 1:
        raise ValueError("La fracción de prueba debe estar entre 0 y 1.")
    labels = [example.label for example in examples]
    if set(labels) != {0, 1}:
        raise ValueError("La división necesita ejemplos de ambas clases.")
    indices = list(range(len(examples)))
    train_indices, test_indices = train_test_split(
        indices,
        test_size=test_fraction,
        random_state=random_state,
        stratify=labels,
    )
    return (
        [examples[index] for index in train_indices],
        [examples[index] for index in test_indices],
    )


def split_fingerprint(examples: list[TrainingExample]) -> str:
    """Identifica una partición sin publicar ni serializar sus mensajes."""

    rows = sorted(
        f"{training_text_hash(example.text)}:{example.label}" for example in examples
    )
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


__all__ = [
    "CleaningSummary",
    "TrainingExample",
    "clean_training_examples",
    "normalize_training_text",
    "split_fingerprint",
    "stratified_split",
    "training_text_hash",
]
