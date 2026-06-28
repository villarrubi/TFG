import os
import tempfile
import unittest
from io import StringIO

from sistema_phishing import ExplanationBuilder, SignalBuilder
from sistema_phishing.correo import CorreoAnalizado
from sistema_phishing.dataset import cargar_dataset_csv
from sistema_phishing.modelo_neural import ModelStorage, NeuralPhishingClassifier, NeuralPhishingDetector
from sistema_phishing.neural import generar_dataset_sintetico as generar_dataset_desde_fachada
from sistema_phishing.signals import contiene_formulario_html, extraer_urls, tiene_parametros_sospechosos_url


class TestRefactorizacion(unittest.TestCase):
    def test_signals_mantiene_fachada_compatible(self):
        texto = "Revise https://ejemplo.com/login?next=https://banco.com"
        urls = extraer_urls(texto)

        self.assertEqual(len(urls), 1)
        self.assertTrue(tiene_parametros_sospechosos_url(urls[0]))
        self.assertTrue(contiene_formulario_html("<form action='/login'></form>"))

    def test_signal_builder_y_explanation_builder_generan_resultados_estables(self):
        correo = CorreoAnalizado(
            full_text=(
                "From: Banco Santander <alerta@externo.com>\n"
                "Reply-To: soporte@otro-dominio.com\n"
                "Subject: Verifica tu cuenta\n\n"
                "Estimado cliente, actualice sus credenciales."
            ),
            urls=["https://secure-login.example.com"],
            from_address="Banco Santander <alerta@externo.com>",
            subject="Verifica tu cuenta",
            body="Estimado cliente, actualice sus credenciales.",
        )

        signals = SignalBuilder(correo).build()
        explanations = ExplanationBuilder().build(signals)

        self.assertTrue(signals["reply_to_diferente"])
        self.assertTrue(signals["remitente_marca_engano"])
        self.assertTrue(signals["saludo_generico"])
        self.assertEqual(len(explanations), len(signals))

    def test_dataset_csv_admite_columnas_alternativas(self):
        csv_data = StringIO(
            "message,target,sender,links\n"
            "\"Actualice sus credenciales\",phishing,alerta@banco-falso.com,https://falso.com\n"
            "\"Gracias por su compra\",ham,ventas@tienda.com,https://tienda.com\n"
        )

        textos, etiquetas = cargar_dataset_csv(csv_data, label_column="target", text_column="message")

        self.assertEqual(etiquetas, [1, 0])
        self.assertIn("From: alerta@banco-falso.com", textos[0])
        self.assertIn("Links: https://tienda.com", textos[1])

    def test_neural_fachada_y_storage_funcionan_con_modulos_refactorizados(self):
        textos, etiquetas = generar_dataset_desde_fachada()
        clasificador = NeuralPhishingClassifier()
        clasificador.fit(textos, etiquetas)

        detector = NeuralPhishingDetector(clasificador)
        resultado = detector.analyze("Verifica tu cuenta y actualiza tus credenciales")

        self.assertIn("risk_score", resultado)
        self.assertGreaterEqual(resultado["risk_score"], 0)
        self.assertLessEqual(resultado["risk_score"], 100)

        with tempfile.TemporaryDirectory() as tmpdir:
            ruta = os.path.join(tmpdir, "modelo.joblib")
            storage = ModelStorage(ruta)
            storage.save(clasificador)
            cargado = storage.load()

        self.assertIsNotNone(cargado)
        self.assertEqual(len(cargado.predict(["Gracias por su compra"])), 1)

