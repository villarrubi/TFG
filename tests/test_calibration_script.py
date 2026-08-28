import os
import sys
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from calibrate_combined import build_result, predictions, stratified_folds

DATASET = Path(ROOT) / "evaluation" / "calibration_controlled_v1.csv"


class TestCalibrationScript(unittest.TestCase):
    def test_calibracion_es_determinista_y_mantiene_ambos_detectores(self):
        first = build_result(DATASET)
        second = build_result(DATASET)

        self.assertEqual(first, second)
        recommendation = first["recommendation"]
        self.assertGreaterEqual(recommendation["heur_weight"], 20)
        self.assertGreaterEqual(recommendation["neural_weight"], 20)
        self.assertEqual(
            recommendation["heur_weight"] + recommendation["neural_weight"],
            100,
        )
        self.assertIn(recommendation["high_confidence_threshold"], range(65, 86, 5))

    def test_particiones_y_formula_son_estables(self):
        scored = [
            {"id": f"x-{index}", "language": "es", "label": index % 2,
             "heuristic_score": 20.0, "neural_score": 80.0}
            for index in range(10)
        ]

        folds = stratified_folds(scored)
        self.assertEqual(sorted(index for fold in folds for index in fold), list(range(10)))
        self.assertEqual(predictions(scored, 20, 80, 45), [1] * 10)


if __name__ == "__main__":
    unittest.main()
