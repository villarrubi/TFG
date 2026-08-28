import os
import sys
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from evaluate_models import (
    build_payload,
    corpus_sha256,
    evaluate,
    load_eml_cases,
    load_rows,
    metrics_payload,
)

CALIBRATION_DATASET = os.path.join(
    ROOT, "evaluation", "calibration_controlled_v1.csv"
)
EML_MANIFEST = os.path.join(ROOT, "evaluation", "local_emails_v1", "manifest.json")


class TestEvaluationScript(unittest.TestCase):
    def test_holdout_es_bilingue_equilibrado_y_sin_ids_repetidos(self):
        rows = load_rows(Path(CALIBRATION_DATASET))
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

    def test_corpus_eml_es_bilingue_equilibrado_y_parseable(self):
        manifest = Path(EML_MANIFEST)
        cases, metadata = load_eml_cases(manifest)
        counts = {}
        for case in cases:
            key = (case["language"], case["label"])
            counts[key] = counts.get(key, 0) + 1
            self.assertTrue(case["payload"]["subject"])
            self.assertTrue(case["payload"]["from"])

        self.assertEqual(len(cases), 16)
        self.assertEqual(set(counts.values()), {4})
        self.assertTrue(metadata["representative_scenarios"])
        self.assertFalse(metadata["statistically_representative"])
        self.assertEqual(len(corpus_sha256(manifest, cases)), 64)

    def test_evaluacion_eml_es_reproducible(self):
        cases, _ = load_eml_cases(Path(EML_MANIFEST))

        first = evaluate(cases, 45, 20, 80)
        second = evaluate(cases, 45, 20, 80)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
