"""Cliente mínimo para leer correos de Gmail mediante la API oficial."""

import base64
import os
from dataclasses import dataclass
from typing import Dict, List, Optional


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailIntegrationError(RuntimeError):
    """Error controlado de la integración con Gmail."""


@dataclass
class GmailEmail:
    """Correo descargado desde Gmail en formato apto para el analizador."""

    gmail_id: str
    raw_bytes: bytes
    snippet: str = ""


def dependencias_disponibles() -> bool:
    """Indica si están instaladas las librerías de Google necesarias."""
    try:
        import google.auth.transport.requests  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        return False
    return True


def decodificar_raw_gmail(raw: str) -> bytes:
    """Convierte el campo raw base64url de Gmail en bytes EML."""
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def construir_servicio_gmail(credentials_path: str, token_path: str):
    """Crea un servicio autenticado de Gmail usando OAuth local."""
    if not dependencias_disponibles():
        raise GmailIntegrationError(
            "Faltan dependencias de Google. Instala las librerías indicadas en requirements.txt."
        )
    if not os.path.exists(credentials_path):
        raise GmailIntegrationError(f"No se ha encontrado el archivo de credenciales: {credentials_path}")

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def obtener_correo_raw(servicio, message_id: str) -> GmailEmail:
    """Descarga un mensaje concreto de Gmail en formato raw."""
    mensaje: Dict[str, str] = (
        servicio.users()
        .messages()
        .get(userId="me", id=message_id, format="raw")
        .execute()
    )
    raw = mensaje.get("raw")
    if not raw:
        raise GmailIntegrationError(f"Gmail no devolvió contenido raw para el mensaje {message_id}.")
    return GmailEmail(
        gmail_id=message_id,
        raw_bytes=decodificar_raw_gmail(raw),
        snippet=mensaje.get("snippet", ""),
    )


def obtener_ultimos_correos(
    servicio,
    limite: int = 10,
    query: str = "in:inbox",
) -> List[GmailEmail]:
    """Obtiene los últimos correos que coinciden con la consulta indicada."""
    respuesta: Dict[str, object] = (
        servicio.users()
        .messages()
        .list(userId="me", maxResults=limite, q=query)
        .execute()
    )
    mensajes = respuesta.get("messages", [])
    return [obtener_correo_raw(servicio, mensaje["id"]) for mensaje in mensajes]


def obtener_perfil_gmail(servicio) -> Dict[str, object]:
    """Devuelve datos básicos de la cuenta de Gmail autenticada."""
    return servicio.users().getProfile(userId="me").execute()
