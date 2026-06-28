import unittest

from sistema_phishing.neural import NeuralPhishingClassifier, generar_dataset_sintetico


class TestNeuralPhishingClassifier(unittest.TestCase):
    def test_generar_dataset_sintetico_devuelve_datos(self):
        textos, etiquetas = generar_dataset_sintetico()
        self.assertEqual(len(textos), len(etiquetas))
        self.assertGreaterEqual(len(textos), 10)
        self.assertIn(1, etiquetas)
        self.assertIn(0, etiquetas)

    def test_neural_classifier_entrena_y_predice(self):
        textos, etiquetas = generar_dataset_sintetico()
        clasificador = NeuralPhishingClassifier()
        clasificador.fit(textos, etiquetas)

        muestras = [
            "From: Banco Falso <soporte@banco-falso.com>\nSubject: Verifica tu cuenta\n\nConfirme sus datos en https://falso-banco.com/seguridad.",
            "From: Newsletter <info@empresa.com>\nSubject: Actualización mensual\n\nLe compartimos los mejores consejos y novedades.",
        ]
        predicciones = clasificador.predict(muestras)
        self.assertEqual(len(predicciones), 2)
        self.assertIn(1, predicciones)
        self.assertIn(0, predicciones)

    def test_neural_classifier_predict_proba_retornos_entre_0_y_1(self):
        clasificador = NeuralPhishingClassifier()
        clasificador.fit_default()

        probas = clasificador.predict_proba([
            "From: Valid Service <info@empresa.com>\nSubject: Confirmación\n\nSu pedido ha sido enviado.",
            "From: Alerta de Seguridad <alerta@seguridad-falsa.com>\nSubject: Acción inmediata requerida\n\nActualice su contraseña ahora.",
        ])
        self.assertEqual(len(probas), 2)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in probas))
