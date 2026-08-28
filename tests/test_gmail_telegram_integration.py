import threading
import unittest
from pathlib import Path

from sistema_phishing.backend_client import BackendClient
from sistema_phishing.backend_service import (
    AnalysisBackendConfig,
    AnalysisBackendService,
)
from sistema_phishing.gmail_client import GmailEmail
from sistema_phishing.gmail_monitor import (
    MonitorConfig,
    analizar_correos_nuevos,
    cargar_estado,
)
from sistema_phishing.http_api import crear_servidor_http
from sistema_phishing.telegram_notifier import TelegramNotifier

ROOT = Path(__file__).resolve().parents[1]
EMAILS = ROOT / "evaluation" / "local_emails_v1"


class _TelegramResponse:
    status_code = 200
    text = '{"ok":true}'


class TestGmailTelegramIntegration(unittest.TestCase):
    def setUp(self):
        service = AnalysisBackendService(
            AnalysisBackendConfig(
                model_path_es=str(ROOT / "modelo_neural_es.joblib"),
                model_path_en=str(ROOT / "modelo_neural_en.joblib"),
            )
        )
        self.server = crear_servidor_http("127.0.0.1", 0, service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_gmail_eml_backend_y_telegram_completan_el_recorrido_local(self):
        telegram_calls = []

        def fake_post(url, json, timeout):
            telegram_calls.append((url, json, timeout))
            return _TelegramResponse()

        notifier = TelegramNotifier(
            bot_token="TOKEN_LOCAL",
            chat_id="CHAT_LOCAL",
            post=fake_post,
        )
        emails = [
            GmailEmail(
                gmail_id="gmail-phishing-1",
                raw_bytes=(EMAILS / "es_phishing_auth_fail.eml").read_bytes(),
            ),
            GmailEmail(
                gmail_id="gmail-legitimate-1",
                raw_bytes=(EMAILS / "es_legitimate_meeting.eml").read_bytes(),
            ),
        ]

        state = ROOT / "tests" / ".gmail-telegram-integration-state.json"
        state.unlink(missing_ok=True)
        try:
            state_path = str(state)
            config = MonitorConfig(
                state_path=state_path,
                backend_url=self.base_url,
                mode="combinado",
                threshold=45,
                heur_weight=20,
                neural_weight=80,
                mark_existing_as_seen=False,
            )
            results = analizar_correos_nuevos(
                emails,
                config,
                notifier=notifier,
                analysis_service=BackendClient(self.base_url),
            )

            self.assertEqual(len(results), 2)
            self.assertTrue(results[0].is_phishing)
            self.assertTrue(results[0].notified)
            self.assertFalse(results[1].is_phishing)
            self.assertFalse(results[1].notified)
            self.assertEqual(
                cargar_estado(state_path),
                {"gmail-phishing-1", "gmail-legitimate-1"},
            )
        finally:
            state.unlink(missing_ok=True)

        self.assertEqual(len(telegram_calls), 1)
        self.assertIn("ALERTA DE PHISHING", telegram_calls[0][1]["text"])
        self.assertEqual(telegram_calls[0][1]["chat_id"], "CHAT_LOCAL")


if __name__ == "__main__":
    unittest.main()
