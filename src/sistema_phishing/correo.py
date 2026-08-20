"""Definición del correo analizado y reglas de construcción de datos de correo."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from .signals import extraer_urls


@dataclass
class CorreoAnalizado:
    """Representación interna común para texto pegado y archivos .eml."""

    # `full_text` conserva la representación plana que consumen muchas reglas
    # basadas en cabeceras y expresiones regulares.
    full_text: str
    # Las URLs incluyen enlaces encontrados en texto y, si procede, hrefs HTML.
    urls: list[str] = field(default_factory=list)
    anchors: list[dict[str, str]] = field(default_factory=list)
    html_body: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    from_address: str = ""
    subject: str = ""
    body: str = ""
    attachments: list[str] = field(default_factory=list)

    @staticmethod
    def _lista(valor: object, nombre: str) -> list[object]:
        """Valida colecciones de entrada y evita iterar accidentalmente strings."""
        if valor in (None, ""):
            return []
        if not isinstance(valor, (list, tuple)):
            raise TypeError(f"El campo {nombre} debe ser una lista.")
        return list(valor)

    @classmethod
    def from_input(cls, correo: str | Mapping[str, object]) -> "CorreoAnalizado":
        """Normaliza la entrada antes de aplicar las reglas heurísticas."""
        if isinstance(correo, Mapping):
            # Los .eml parseados ya traen URLs y anclas. Se añaden los href de
            # las anclas para que las reglas revisen también los enlaces HTML.
            anchors = [
                {"text": str(anchor.get("text", "")), "href": str(anchor.get("href", ""))}
                for anchor in cls._lista(correo.get("anchors", []), "anchors")
                if isinstance(anchor, Mapping) and anchor.get("href")
            ]
            urls_origen = [
                str(url)
                for url in cls._lista(correo.get("urls", []), "urls")
                if str(url).strip()
            ]
            urls = list(
                dict.fromkeys(urls_origen + [anchor["href"] for anchor in anchors])
            )
            headers = correo.get("headers", {})
            return cls(
                full_text=str(correo.get("full_text", "") or ""),
                urls=urls,
                anchors=anchors,
                html_body=str(correo.get("html_body", "") or ""),
                headers={
                    str(nombre): str(valor)
                    for nombre, valor in headers.items()
                }
                if isinstance(headers, Mapping)
                else {},
                from_address=str(correo.get("from", "") or ""),
                subject=str(correo.get("subject", "") or ""),
                body=str(
                    correo.get("body", correo.get("full_text", "")) or ""
                ),
                attachments=[
                    str(nombre)
                    for nombre in cls._lista(correo.get("attachments", []), "attachments")
                    if nombre
                ],
            )

        if not isinstance(correo, str):
            raise TypeError("El correo debe ser texto o un diccionario normalizado.")
        texto = correo
        # En texto pegado no hay parser MIME, así que se extraen los campos más
        # importantes con expresiones regulares simples y el cuerpo queda como
        # el texto completo recibido.
        remitente_match = re.search(r"(?im)^from:\s*(.+)$", texto)
        asunto_match = re.search(r"(?im)^subject:\s*(.+)$", texto)
        return cls(
            full_text=texto,
            urls=extraer_urls(texto),
            anchors=[],
            html_body="",
            headers={},
            from_address=remitente_match.group(1).strip() if remitente_match else "",
            subject=asunto_match.group(1).strip() if asunto_match else "",
            body=texto,
            attachments=[],
        )
