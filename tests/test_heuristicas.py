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

    def test_analizar_correo_detecta_saludo_generico_y_adjunto_sospechoso(self):
        correo = {
            "from": "Seguridad <alertas@banco-falso.com>",
            "subject": "ACTUALICE SU CUENTA INMEDIATAMENTE",
            "full_text": (
                "From: Seguridad <alertas@banco-falso.com>\n"
                "Subject: ACTUALICE SU CUENTA INMEDIATAMENTE\n\n"
                "Estimado cliente, su cuenta ha sido bloqueada. Por favor ingrese sus credenciales "
                "y descargue el documento adjunto para recuperar el acceso."
            ),
            "urls": ["https://banco-falso.com/recuperar"],
            "anchors": [],
            "html_body": "<html><body><meta http-equiv='refresh' content='0;url=https://banco-falso.com/recuperar'></body></html>",
            "attachments": ["actualizacion.zip"],
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["saludo_generico"])
        self.assertTrue(resultado["signals"]["solicitud_credenciales"])
        self.assertTrue(resultado["signals"]["meta_refresh_html"])
        self.assertTrue(resultado["signals"]["adjunto_sospechoso"])

    def test_analizar_correo_detecta_dmarc_fallido_y_dkim_mal_formado(self):
        correo = {
            "from": "Soporte <soporte@servicio-legal.com>",
            "subject": "Problema con su cuenta",
            "full_text": (
                "From: Soporte <soporte@servicio-legal.com>\n"
                "Subject: Problema con su cuenta\n"
                "Authentication-Results: mx.google.com; dkim=pass header.i=@servicio-legal.com; dmarc=fail action=quarantine\n"
                "DKIM-Signature: v=1; a=rsa-sha256; d=servicio-legal.com; s=selector\n\n"
                "Estimado cliente, hemos detectado actividad inusual."
            ),
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["dmarc_fallido"])
        self.assertTrue(resultado["signals"]["dkim_mal_formado"])

    def test_analizar_correo_detecta_incoherencia_remitente_spf(self):
        correo = {
            "from": "Soporte <soporte@banco-real.com>",
            "subject": "Acción requerida",
            "full_text": (
                "From: Soporte <soporte@banco-real.com>\n"
                "Return-Path: <no-reply@fraude.com>\n"
                "Received-SPF: fail (google.com: domain of fraude.com does not designate 192.0.2.1 as permitted sender)\n"
                "Subject: Acción requerida\n\n"
                "Su cuenta está en riesgo. Ingrese ahora."
            ),
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["incoherencia_remitente"])

    def test_analizar_correo_detecta_html_sospechoso_y_punycode(self):
        correo = {
            "from": "Seguridad <alertas@servicio-normale.com>",
            "subject": "Actualice sus datos",
            "full_text": (
                "From: Seguridad <alertas@servicio-normale.com>\n"
                "Subject: Actualice sus datos\n\n"
                "Estimado cliente, revise su cuenta usando el enlace seguro."
            ),
            "urls": ["http://xn--pples-43d.com/login"],
            "anchors": [],
            "html_body": "<html><head><base href='http://xn--pples-43d.com/'></head><body><iframe src='http://malicioso.com'></iframe></body></html>",
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["html_sospechoso"])
        self.assertTrue(resultado["signals"]["dominio_punycode_unicode"])

    def test_analizar_correo_detecta_url_parametros_sospechosos_y_anchor_distinto(self):
        correo = {
            "from": "Banco Importante <info@banco-importante.com>",
            "subject": "Verifique su cuenta",
            "full_text": (
                "From: Banco Importante <info@banco-importante.com>\n"
                "Subject: Verifique su cuenta\n\n"
                "Para proteger su cuenta, visite el siguiente enlace:\n"
                "https://seguros-login.com/redirect?url=https://banco-importante.com/login"
            ),
            "urls": ["https://seguros-login.com/redirect?url=https://banco-importante.com/login"],
            "anchors": [
                {
                    "text": "https://banco-importante.com/login",
                    "href": "https://seguros-login.com/redirect?url=https://banco-importante.com/login",
                }
            ],
            "html_body": "<html><body></body></html>",
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["url_parametros_sospechosos"])
        self.assertTrue(resultado["signals"]["anchor_distinto"])

    def test_analizar_correo_detecta_formulario_action_sospechoso_y_remitente_marca_engano(self):
        correo = {
            "from": "Banco Santander <no-reply@external-falso.com>",
            "subject": "Actualización necesaria",
            "full_text": (
                "From: Banco Santander <no-reply@external-falso.com>\n"
                "Subject: Actualización necesaria\n\n"
                "Por favor, compruebe su información en el formulario adjunto."
            ),
            "urls": ["https://external-falso.com/actualizar"],
            "anchors": [],
            "html_body": "<html><body><form action='/actualizar'></form></body></html>",
        }
        resultado = analizar_correo(correo)
        self.assertTrue(resultado["signals"]["remitente_marca_engano"])
        self.assertTrue(resultado["signals"]["formulario_action_sospechoso"])

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
