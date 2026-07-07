import os
import tempfile
import unittest

from sistema_phishing.env_loader import actualizar_env_local, cargar_env_file, leer_env_file


class TestEnvLoader(unittest.TestCase):
    def test_cargar_env_file_carga_variables_sencillas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, ".env.local")
            with open(path, "w", encoding="utf-8") as env_file:
                env_file.write("PRUEBA_ENV_LOADER=valor\n")

            old_value = os.environ.pop("PRUEBA_ENV_LOADER", None)
            try:
                cargar_env_file(path)
                self.assertEqual(os.environ["PRUEBA_ENV_LOADER"], "valor")
            finally:
                os.environ.pop("PRUEBA_ENV_LOADER", None)
                if old_value is not None:
                    os.environ["PRUEBA_ENV_LOADER"] = old_value

    def test_actualizar_env_local_conserva_valores_previos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, ".env.local")
            with open(path, "w", encoding="utf-8") as env_file:
                env_file.write("A=1\nB=2\n")

            old_value = os.environ.pop("B", None)
            try:
                actualizar_env_local(tmpdir, {"B": "nuevo", "C": "3"})
                valores = leer_env_file(path)

                self.assertEqual(valores["A"], "1")
                self.assertEqual(valores["B"], "nuevo")
                self.assertEqual(valores["C"], "3")
                self.assertEqual(os.environ["B"], "nuevo")
            finally:
                os.environ.pop("B", None)
                os.environ.pop("C", None)
                if old_value is not None:
                    os.environ["B"] = old_value
