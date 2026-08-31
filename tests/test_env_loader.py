import os
import tempfile
import unittest
from unittest import mock

from sistema_phishing.env_loader import (
    actualizar_env_cliente,
    actualizar_env_servidor,
    cargar_env_file,
    env_float,
    env_int,
    guardar_env_file,
    leer_env_file,
)
from sistema_phishing.runtime_paths import client_env_path, server_env_path


class TestEnvLoader(unittest.TestCase):
    def test_cargar_env_file_carga_variables_sencillas(self):
        with mock.patch.dict(
            os.environ,
            {"TEST_INT": "12", "TEST_FLOAT": "2.5", "TEST_INVALID": "no"},
            clear=False,
        ):
            self.assertEqual(env_int("TEST_INT", 3), 12)
            self.assertEqual(env_float("TEST_FLOAT", 1.0), 2.5)
            self.assertEqual(env_int("TEST_INVALID", 3), 3)
            self.assertEqual(env_float("TEST_INVALID", 1.0), 1.0)

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
            path = client_env_path(tmpdir)
            path.parent.mkdir(parents=True)
            with open(path, "w", encoding="utf-8") as env_file:
                env_file.write("A=1\nB=2\n")

            old_value = os.environ.pop("B", None)
            try:
                actualizar_env_cliente(tmpdir, {"B": "nuevo", "C": "3"})
                valores = leer_env_file(str(path))

                self.assertEqual(valores["A"], "1")
                self.assertEqual(valores["B"], "nuevo")
                self.assertEqual(valores["C"], "3")
                self.assertEqual(os.environ["B"], "nuevo")
            finally:
                os.environ.pop("B", None)
                os.environ.pop("C", None)
                if old_value is not None:
                    os.environ["B"] = old_value

    def test_cliente_y_servidor_se_guardan_en_ficheros_distintos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ,
                {
                    "PHISHING_CLIENT_DATA_DIR": "",
                    "PHISHING_SERVER_DATA_DIR": "",
                },
                clear=False,
            ):
                actualizar_env_cliente(tmpdir, {"TELEGRAM_CHAT_ID": "cliente"})
                actualizar_env_servidor(tmpdir, {"BACKEND_MODE": "neural"})

                client_values = leer_env_file(str(client_env_path(tmpdir)))
                server_values = leer_env_file(str(server_env_path(tmpdir)))

            self.assertEqual(client_values, {"TELEGRAM_CHAT_ID": "cliente"})
            self.assertEqual(server_values, {"BACKEND_MODE": "neural"})

    def test_guardar_env_rechaza_saltos_de_linea(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, ".env.local")
            with self.assertRaisesRegex(ValueError, "saltos de línea"):
                guardar_env_file(path, {"TOKEN": "valor\nOTRA=inyectada"})
            self.assertFalse(os.path.exists(path))
