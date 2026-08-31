import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sistema_phishing.runtime_paths import (
    client_data_dir,
    gmail_credentials_path,
    gmail_token_path,
    monitor_state_path,
    server_data_dir,
    server_model_path,
)


class RuntimePathsTests(unittest.TestCase):
    def test_rutas_por_defecto_respetan_la_frontera(self):
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.dict(
            os.environ,
            {
                "PHISHING_CLIENT_DATA_DIR": "",
                "PHISHING_SERVER_DATA_DIR": "",
                "GMAIL_CREDENTIALS_PATH": "",
                "GMAIL_TOKEN_PATH": "",
                "MONITOR_STATE_PATH": "",
                "BACKEND_MODEL_ES": "",
            },
            clear=False,
        ):
            root = Path(tmpdir)
            self.assertEqual(client_data_dir(root), root / "runtime" / "client")
            self.assertEqual(server_data_dir(root), root / "runtime" / "server")
            self.assertEqual(
                gmail_credentials_path(root),
                root / "runtime" / "client" / "credentials.json",
            )
            self.assertEqual(
                gmail_token_path(root), root / "runtime" / "client" / "token.json"
            )
            self.assertEqual(
                monitor_state_path(root),
                root / "runtime" / "client" / "estado_monitor.json",
            )
            self.assertEqual(
                server_model_path(root, "es"),
                root
                / "runtime"
                / "server"
                / "models"
                / "modelo_neural_es.joblib",
            )

    def test_directorios_se_pueden_externalizar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            client = root / "cliente-privado"
            server = root / "servidor-persistente"
            with mock.patch.dict(
                os.environ,
                {
                    "PHISHING_CLIENT_DATA_DIR": str(client),
                    "PHISHING_SERVER_DATA_DIR": str(server),
                },
                clear=False,
            ):
                self.assertEqual(client_data_dir(root), client)
                self.assertEqual(server_data_dir(root), server)


if __name__ == "__main__":
    unittest.main()
