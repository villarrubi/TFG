import base64
import unittest

from sistema_phishing.gmail_client import decodificar_raw_gmail


class TestGmailClient(unittest.TestCase):
    def test_decodificar_raw_gmail_admite_base64url_sin_padding(self):
        raw = b"From: prueba@example.com\nSubject: Test\n\nHola"
        encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

        self.assertEqual(decodificar_raw_gmail(encoded), raw)
