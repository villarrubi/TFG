import unittest

from sistema_phishing.heuristicas import analizar_correo


class TestHeuristicas(unittest.TestCase):
    def test_analizar_correo_identifica_fraude_basico(self):
        correo = (
            "From: Bank Support <no-reply@banco-seguro.com>\n"
            "Reply-To: soporte@atencion-cliente.com\n"
            "Subject: Verifica tu cuenta ahora\n\n"
            "Estimado cliente, su cuenta ha sido bloqueada. Por favor actualizar "
            "sus credenciales en https://secure-login.banco-seguro-login.com/login"
        )
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["is_phishing"])
        self.assertGreaterEqual(resultado["risk_score"], 45)
        self.assertTrue(resultado["signals"]["reply_to_diferente"])
        self.assertTrue(resultado["signals"]["lenguaje_urgente"])

    def test_analizar_correo_no_phishing(self):
        correo = (
            "From: Servicio de atención al cliente <soporte@empresa-ejemplo.com>\n"
            "Subject: Confirmación de pedido\n\n"
            "Buenos días, su pedido ha sido procesado correctamente. Gracias por "
            "confiar en nosotros."
        )
        resultado = analizar_correo(correo)
        self.assertFalse(resultado["is_phishing"])
        self.assertLess(resultado["risk_score"], 45)
