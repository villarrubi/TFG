import base64
import unittest

from sistema_phishing.gmail_client import (
    decodificar_raw_gmail,
    obtener_correo_raw,
    obtener_perfil_gmail,
    obtener_ultimos_correos,
)


class _Executable:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Messages:
    def __init__(self, encoded):
        self.encoded = encoded
        self.list_args = None

    def list(self, **kwargs):
        self.list_args = kwargs
        return _Executable({"messages": [{"id": "gmail-1"}]})

    def get(self, **kwargs):
        return _Executable({"raw": self.encoded, "snippet": "resumen"})


class _Users:
    def __init__(self, encoded):
        self._messages = _Messages(encoded)

    def messages(self):
        return self._messages

    def getProfile(self, **kwargs):
        return _Executable({"emailAddress": "cuenta-pruebas@example.test"})


class _GmailService:
    def __init__(self, encoded):
        self._users = _Users(encoded)

    def users(self):
        return self._users


class TestGmailClient(unittest.TestCase):
    def test_decodificar_raw_gmail_admite_base64url_sin_padding(self):
        raw = b"From: prueba@example.com\nSubject: Test\n\nHola"
        encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

        self.assertEqual(decodificar_raw_gmail(encoded), raw)

    def test_cliente_gmail_lista_descarga_y_lee_perfil(self):
        raw = b"From: prueba@example.test\nSubject: Test\n\nHola"
        encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        service = _GmailService(encoded)

        emails = obtener_ultimos_correos(service, limite=3, query="in:inbox")
        direct = obtener_correo_raw(service, "gmail-1")
        profile = obtener_perfil_gmail(service)

        self.assertEqual(emails[0].raw_bytes, raw)
        self.assertEqual(direct.snippet, "resumen")
        self.assertEqual(profile["emailAddress"], "cuenta-pruebas@example.test")
        self.assertEqual(service._users._messages.list_args["maxResults"], 3)
