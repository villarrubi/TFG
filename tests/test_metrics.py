import unittest

import numpy as np

from sistema_phishing.metrics import calcular_metricas_clasificacion


class TestClassificationMetrics(unittest.TestCase):
    def test_calcula_matriz_y_metricas_derivadas(self):
        metricas = calcular_metricas_clasificacion(
            [1, 1, 1, 0, 0, 0],
            [1, 1, 0, 0, 0, 1],
        )

        self.assertEqual(metricas.verdaderos_positivos, 2)
        self.assertEqual(metricas.verdaderos_negativos, 2)
        self.assertEqual(metricas.falsos_positivos, 1)
        self.assertEqual(metricas.falsos_negativos, 1)
        self.assertAlmostEqual(metricas.accuracy, 4 / 6)
        self.assertAlmostEqual(metricas.precision, 2 / 3)
        self.assertAlmostEqual(metricas.recall, 2 / 3)
        self.assertAlmostEqual(metricas.f1, 2 / 3)

    def test_rechaza_longitudes_distintas(self):
        with self.assertRaises(ValueError):
            calcular_metricas_clasificacion([0, 1], [0])

    def test_divisiones_sin_positivos_no_fallan(self):
        metricas = calcular_metricas_clasificacion([0, 0], [0, 0])

        self.assertEqual(metricas.precision, 0.0)
        self.assertEqual(metricas.recall, 0.0)
        self.assertEqual(metricas.f1, 0.0)

    def test_admite_secuencias_numpy(self):
        metricas = calcular_metricas_clasificacion(
            np.array([1, 0]),
            np.array([1, 0]),
        )

        self.assertEqual(metricas.accuracy, 1.0)
