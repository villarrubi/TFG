"""Comprueba la coherencia interna de citas y referencias de la memoria.

La verificación de contenido académico se realiza manualmente contra las fuentes
originales. Este script cubre los errores mecánicos que sí deben bloquear una
entrega: referencias sin citar, duplicados, URLs repetidas e identificadores de
arXiv asociados a otro título o autor.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_TEXT = ROOT / "TFG.txt"

ARXIV_EXPECTED = {
    "1802.03162": ("URLNet", "Le"),
    "2402.13871": ("Explainable Transformer-based Model", "Uddin"),
    "2402.18093": ("ChatSpamDetector", "Koide"),
    "2405.15936": ("Zero-shot spam email classification", "Rojas-Galeano"),
    "2506.13746": ("Evaluating large language models for phishing detection", "Kuikel"),
}


def _normalizar(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"\W+", "", ascii_value.casefold())


def _dividir_memoria(text: str) -> tuple[str, list[str]]:
    try:
        body, remainder = text.split("\nReferencias\n", maxsplit=1)
        references, _ = remainder.split("\nAnexos\n", maxsplit=1)
    except ValueError as exc:
        raise ValueError(
            "No se localizaron las secciones Referencias y Anexos."
        ) from exc
    entries = [
        paragraph.strip().replace("\n", " ")
        for paragraph in re.split(r"\n\s*\n", references)
        if paragraph.strip()
    ]
    return body, entries


def _clave_referencia(entry: str) -> tuple[str, str]:
    year_match = re.search(r"\(((?:19|20)\d{2}[a-z]?)\)", entry)
    if not year_match:
        raise ValueError(f"Referencia sin año reconocible: {entry}")
    prefix = entry[: year_match.start()].strip()
    author = prefix.split(",", maxsplit=1)[0].rstrip(". ")
    return author, year_match.group(1)


def audit(text: str) -> list[str]:
    body, entries = _dividir_memoria(text)
    errors: list[str] = []

    normalized = Counter(_normalizar(entry) for entry in entries)
    duplicates = [key for key, count in normalized.items() if count > 1]
    if duplicates:
        errors.append(f"Referencias duplicadas: {len(duplicates)}")

    urls = re.findall(r"https?://\S+", "\n".join(entries))
    duplicate_urls = sorted(url for url, count in Counter(urls).items() if count > 1)
    if duplicate_urls:
        errors.append("URLs duplicadas: " + ", ".join(duplicate_urls))

    body_normalized = (
        unicodedata.normalize("NFKD", body).encode("ascii", "ignore").decode()
    )
    for entry in entries:
        author, year = _clave_referencia(entry)
        author_ascii = (
            unicodedata.normalize("NFKD", author).encode("ascii", "ignore").decode()
        )
        cited = re.search(
            rf"\b{re.escape(author_ascii)}\b.{{0,100}}?\b{re.escape(year)}\b",
            body_normalized,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not cited:
            errors.append(f"Referencia no citada: {author} ({year})")

    references_text = "\n".join(entries)
    arxiv_ids = re.findall(
        r"arXiv:(\d{4}\.\d{4,5})", references_text, flags=re.IGNORECASE
    )
    if len(arxiv_ids) != len(set(arxiv_ids)):
        errors.append("Hay identificadores de arXiv duplicados.")
    for identifier in arxiv_ids:
        expected = ARXIV_EXPECTED.get(identifier)
        if expected is None:
            errors.append(f"Identificador de arXiv sin validar: {identifier}")
            continue
        entry = next(item for item in entries if f"arXiv:{identifier}" in item)
        if any(
            _normalizar(fragment) not in _normalizar(entry) for fragment in expected
        ):
            errors.append(
                f"arXiv:{identifier} no coincide con el título/autor esperado {expected}."
            )

    return errors


def main() -> None:
    errors = audit(MEMORY_TEXT.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    _, entries = _dividir_memoria(MEMORY_TEXT.read_text(encoding="utf-8"))
    print(
        f"Bibliografía coherente: {len(entries)} referencias citadas y sin duplicados."
    )


if __name__ == "__main__":
    main()
