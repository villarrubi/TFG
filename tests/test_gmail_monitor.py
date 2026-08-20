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

            resultados = analizar_correos_nuevos(correos, config)

            self.assertEqual(len(resultados), 2)
            self.assertIsNotNone(resultados[0].error)
            self.assertIsNone(resultados[1].error)
            self.assertEqual(cargar_estado(path), {"valido"})
