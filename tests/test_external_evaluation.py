import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from evaluate_external import load_rows, normalize_text
from prepare_defense_demo import build_payload


class TestExternalEvaluation(unittest.TestCase):
    def test_normalizacion_de_duplicados_es_determinista(self):
        self.assertEqual(normalize_text("  PÁGO\nurgente "), "págo urgente")

    def test_loader_valida_y_deduplica_jsonl(self):
        content = (
            json.dumps({"text": "Message one", "label": 0})
            + "\n"
            + json.dumps({"text": " Message   one ", "label": 0})
            + "\n"
            + json.dumps({"text": "Message two", "label": 1})
            + "\n"
        ).encode()
        digest = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.jsonl"
            path.write_bytes(content)
            with patch("evaluate_external.EXPECTED_SHA256", digest):
                rows, duplicates = load_rows(path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(duplicates, 1)

    def test_respaldo_de_defensa_contiene_dos_decisiones_opuestas(self):
        payload = build_payload()

        self.assertEqual(payload["health"]["architecture"], "client-server")
        self.assertNotIn("updated_at", payload["health"]["models"]["es"])
        self.assertEqual(
            {case["response_summary"]["label"] for case in payload["cases"]},
            {"phishing", "legitimate"},
        )
        for case in payload["cases"]:
            self.assertEqual(
                set(case["response_summary"]["mode_results"]),
                {"heuristico", "neural", "combinado"},
            )
            self.assertFalse(case["response_summary"]["model"]["fallback"])


if __name__ == "__main__":
    unittest.main()
