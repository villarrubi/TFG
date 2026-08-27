import os
import sys
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from evaluate_models import build_payload, load_rows, metrics_payload

DATASET = os.path.join(ROOT, "evaluation", "controlled_holdout_v1.csv")


class TestEvaluationScript(unittest.TestCase):
    def test_holdout_es_bilingue_equilibrado_y_sin_ids_repetidos(self):
        rows = load_rows(Path(DATASET))
        counts = {}
        for row in rows:
            counts[(row["language"], row["label"])] = counts.get(
                (row["language"], row["label"]), 0
            ) + 1
        self.assertEqual(len(rows), 40)
        self.assertEqual(set(counts.values()), {10})

    def test_payload_separa_urls_y_metricas_exponen_errores(self):
        row = {
            "subject": "s",
            "sender": "a@example.com",
            "body": "b",
            "urls": "https://a.example|https://b.example",
        }
        self.assertEqual(len(build_payload(row)["urls"]), 2)
        metrics = metrics_payload([1, 0], [0, 1])
        self.assertEqual((metrics["fp"], metrics["fn"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
