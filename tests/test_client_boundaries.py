import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestClientBoundaries(unittest.TestCase):
    def test_vistas_no_importan_runtime_de_machine_learning(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        code = (
            "import sys; import config_app, train_app; "
            "assert 'joblib' not in sys.modules; "
            "assert not any(n == 'sklearn' or n.startswith('sklearn.') for n in sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clientes_no_importan_implementacion_del_modelo(self):
        for relative_path in ("src/config_app.py", "src/train_app.py"):
            source = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("sistema_phishing.modelo_neural", source)
            self.assertIn("sistema_phishing.model_config", source)

    def test_dependencias_documentales_son_solo_de_desarrollo(self):
        runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        development = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("python-docx", runtime)
        self.assertNotIn("pillow", runtime)
        self.assertIn("python-docx", development)
        self.assertIn("pillow", development)


if __name__ == "__main__":
    unittest.main()
