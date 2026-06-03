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

    def test_analizar_correo_detecta_formulario_y_lista_negra(self):
        correo = {
            "from": "Banco Real <seguridad@banco-real.net>",
            "subject": "URGENTE: Verifica tu cuenta ahora",
            "full_text": (
                "From: Banco Real <seguridad@banco-real.net>\n"
                "Subject: URGENTE: Verifica tu cuenta ahora\n\n"
                "Debe verificar su cuenta inmediatamente en "
                "https://banco-real-seguro.login-verificacion.com/actualizar"
            ),
            "urls": ["https://banco-real-seguro.login-verificacion.com/actualizar"],
            "anchors": [{"text": "Banco Real", "href": "https://banco-real-seguro.login-verificacion.com/actualizar"}],
            "html_body": "<html><body><form action='https://banco-real-seguro.login-verificacion.com/actualizar'></form></body></html>",
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["dominio_blacklist"])
        self.assertTrue(resultado["signals"]["formulario_html"])
        self.assertTrue(resultado["signals"]["asunto_sospechoso"])

    def test_analizar_correo_detecta_autenticacion_fallida_y_recibidos(self):
        correo = (
            "From: Soporte <soporte@servicio-legal.com>\n"
            "Received: from [192.168.1.10] (unknown [192.168.1.10])\n"
            "Received-SPF: fail (google.com: domain of servicio-legal.com does not designate 192.168.1.10 as permitted sender)\n"
            "Subject: Verifica tu acceso\n\n"
            "Su acceso ha sido detectado desde un dispositivo no habitual. Ingrese en "
            "https://servicio-legal.com/actualizar"
        )
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["autenticacion_fallida"])
        self.assertTrue(resultado["signals"]["recibidos_sospechosos"])

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
