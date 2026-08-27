import os
import tempfile
import unittest

from sistema_phishing.gmail_client import GmailEmail
from sistema_phishing.gmail_monitor import (
    MonitorConfig,
    analizar_correos_nuevos,
    cargar_estado,
    guardar_estado,
)


class TestGmailMonitor(unittest.TestCase):
    def test_guardar_y_cargar_estado(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "estado.json")
            guardar_estado(path, {"b", "a"})

            self.assertEqual(cargar_estado(path), {"a", "b"})

    def test_primera_ejecucion_marca_existentes_sin_analizar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "estado.json")
            config = MonitorConfig(state_path=path, mark_existing_as_seen=True)
            correos = [
                GmailEmail(gmail_id="1", raw_bytes=b"Subject: Uno\n\nHola"),
                GmailEmail(gmail_id="2", raw_bytes=b"Subject: Dos\n\nHola"),
            ]

            resultados = analizar_correos_nuevos(correos, config)

            self.assertEqual(resultados, [])
            self.assertEqual(cargar_estado(path), {"1", "2"})

    def test_un_eml_invalido_no_interrumpe_el_resto_del_lote(self):
        class FakeAnalysisService:
            def analyze(self, datos_email):
                return {
                    "risk_score": 7.5,
                    "is_phishing": False,
                    "description": "Respuesta remota simulada.",
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "estado.json")
            config = MonitorConfig(
                state_path=path,
                mode="heuristico",
                mark_existing_as_seen=False,
            )
            correos = [
                GmailEmail(gmail_id="invalido", raw_bytes=b""),
                GmailEmail(
                    gmail_id="valido",
                    raw_bytes=b"From: equipo@empresa.com\nSubject: Reunion\n\nHola",
                ),
            ]

            resultados = analizar_correos_nuevos(
                correos,
                config,
                analysis_service=FakeAnalysisService(),
            )

            self.assertEqual(len(resultados), 2)
            self.assertIsNotNone(resultados[0].error)
            self.assertIsNone(resultados[1].error)
            self.assertEqual(cargar_estado(path), {"valido"})

    def test_estado_vacio_existente_no_oculta_el_primer_correo_nuevo(self):
        class FakeAnalysisService:
            def analyze(self, datos_email):
                return {"risk_score": 8.0, "is_phishing": False}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "estado.json")
            config = MonitorConfig(state_path=path, mark_existing_as_seen=True)

            self.assertEqual(analizar_correos_nuevos([], config), [])
            self.assertTrue(os.path.exists(path))
            resultados = analizar_correos_nuevos(
                [GmailEmail(gmail_id="nuevo", raw_bytes=b"Subject: Nuevo\n\nHola")],
                config,
                analysis_service=FakeAnalysisService(),
            )

            self.assertEqual(len(resultados), 1)
            self.assertEqual(resultados[0].gmail_id, "nuevo")
            self.assertEqual(cargar_estado(path), {"nuevo"})
