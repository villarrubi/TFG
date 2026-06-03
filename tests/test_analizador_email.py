import unittest

from sistema_phishing.analizador_email import parsear_eml_bytes


class TestAnalizadorEmail(unittest.TestCase):
    def test_parsear_eml_bytes_extrae_campos(self):
        raw = (
            "From: Prueba <prueba@example.com>\n"
            "To: destinatario@example.com\n"
            "Subject: Mensaje de prueba\n"
            "Content-Type: multipart/alternative; boundary=frontier\n\n"
            "--frontier\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "Este es un mensaje de prueba.\n"
            "--frontier\n"
            "Content-Type: text/html; charset=utf-8\n\n"
            "<html><body><p>Este es un mensaje de prueba.</p><a href=\"https://ejemplo.com\">Ejemplo</a></body></html>\n"
            "--frontier--\n"
        )
        datos = parsear_eml_bytes(raw.encode("utf-8"))
        self.assertEqual(datos["subject"], "Mensaje de prueba")
        self.assertEqual(datos["from"], "Prueba <prueba@example.com>")
        self.assertIn("Este es un mensaje de prueba", datos["body"])
        self.assertTrue(any(anchor["href"] == "https://ejemplo.com" for anchor in datos["anchors"]))
