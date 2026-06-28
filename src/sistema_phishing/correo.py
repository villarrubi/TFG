"""Definición del correo analizado y reglas de construcción de datos de correo."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Union

from .signals import extraer_urls


@dataclass
class CorreoAnalizado:
    """Representación interna común para texto pegado y archivos .eml."""

    full_text: str
    urls: List[str] = field(default_factory=list)
    anchors: List[Dict[str, str]] = field(default_factory=list)
    html_body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    from_address: str = ""
    subject: str = ""
    body: str = ""
    attachments: List[str] = field(default_factory=list)

    @classmethod
    def from_input(cls, correo: Union[str, Dict[str, object]]) -> "CorreoAnalizado":
        """Normaliza la entrada antes de aplicar las reglas heurísticas."""
        if isinstance(correo, dict):
            # Los .eml parseados ya traen URLs y anclas. Se añaden los href de
            # las anclas para que las reglas revisen también los enlaces HTML.
            urls = correo.get("urls", []) + [anchor.get("href", "") for anchor in correo.get("anchors", []) if anchor.get("href")]
            return cls(
                full_text=correo.get("full_text", ""),
                urls=urls,
                anchors=correo.get("anchors", []),
                html_body=correo.get("html_body", ""),
                headers=correo.get("headers", {}),
                from_address=correo.get("from", ""),
                subject=correo.get("subject", ""),
                body=correo.get("body", correo.get("full_text", "")),
                attachments=correo.get("attachments", []),
            )

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
