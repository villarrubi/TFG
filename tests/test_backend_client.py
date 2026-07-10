import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema_phishing.backend_client import BackendAnalysisClient, analyze_via_backend


class BackendClientTests(unittest.TestCase):
    def test_analyze_uses_backend_payload(self):
        response = unittest.mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"risk_score": 12.0, "is_phishing": False}

        with patch("sistema_phishing.backend_client.requests.post", return_value=response) as post_mock:
            client = BackendAnalysisClient("http://127.0.0.1:8766")
            result = client.analyze({"subject": "Hola"})

        self.assertEqual(result["risk_score"], 12.0)
        post_mock.assert_called_once()

    def test_analyze_sends_token_when_configured(self):
        response = unittest.mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"risk_score": 12.0, "is_phishing": False}

        with patch("sistema_phishing.backend_client.requests.post", return_value=response) as post_mock:
            client = BackendAnalysisClient("http://127.0.0.1:8766", api_token="secreto")
            client.analyze({"subject": "Hola"})

        headers = post_mock.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer secreto")
        self.assertEqual(headers["X-API-Key"], "secreto")

    def test_analyze_falls_back_to_callable_when_backend_unavailable(self):
        with patch("sistema_phishing.backend_client.requests.post", side_effect=Exception("offline")):
            result = analyze_via_backend(
                {"subject": "Hola"},
                fallback=lambda payload: {"risk_score": 5.0, "is_phishing": False, "source": "fallback"},
            )

        self.assertEqual(result["source"], "fallback")


if __name__ == "__main__":
    unittest.main()
