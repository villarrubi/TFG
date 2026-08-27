from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extension_gmail"


class _QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class TestExtensionOptionsBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(_QuietStaticHandler, directory=str(EXTENSION))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/options.html"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_guarda_endpoint_local_y_comprueba_salud(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.add_init_script(
                """
                globalThis.__extensionStorage = {};
                globalThis.__requestedOrigins = [];
                globalThis.chrome = {storage: {local: {
                  get(defaults, callback) {
                    callback({...defaults, ...globalThis.__extensionStorage});
                  },
                  set(values, callback) {
                    Object.assign(globalThis.__extensionStorage, values);
                    if (callback) callback();
                  }
                }}, permissions: {
                  request(permission, callback) {
                    globalThis.__requestedOrigins = permission.origins || [];
                    callback(true);
                  }
                }};
                """
            )
            page.route(
                "http://127.0.0.1:9123/health",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"ok": True, "mode": "combinado"}),
                ),
            )
            page.goto(self.url)
            page.locator("#server-base-url").fill("http://127.0.0.1:9123/")
            page.locator("#retry-seconds").fill("15")
            page.locator("#save-button").click()
            self.assertEqual(page.locator("#save-status").inner_text(), "Guardado.")
            stored = page.evaluate("globalThis.__extensionStorage")
            self.assertEqual(stored["serverBaseUrl"], "http://127.0.0.1:9123")
            self.assertEqual(stored["retryIntervalMs"], 15000)

            page.locator("#check-button").click()
            page.locator("#server-status.online").wait_for()
            self.assertIn("Activo", page.locator("#server-status").inner_text())

            page.locator("#server-base-url").fill("http://192.168.1.20:8766")
            page.locator("#save-button").click()
            self.assertIn("HTTPS", page.locator("#save-status.error").inner_text())
            self.assertEqual(
                page.evaluate(
                    "PhishingServerConfig.normalizeServerBaseUrl('https://phishing.example')"
                ),
                "https://phishing.example",
            )
            page.locator("#server-base-url").fill("https://phishing.example")
            page.locator("#save-button").click()
            self.assertEqual(page.locator("#save-status").inner_text(), "Guardado.")
            stored = page.evaluate("globalThis.__extensionStorage")
            self.assertEqual(stored["serverBaseUrl"], "https://phishing.example")
            self.assertEqual(
                page.evaluate("globalThis.__requestedOrigins"),
                ["https://phishing.example/*"],
            )
            browser.close()


class TestStreamlitBrowser(unittest.TestCase):
    def test_cliente_web_envia_el_correo_al_backend_central(self):
        streamlit_port = _free_port()
        backend_port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["BACKEND_PORT"] = str(backend_port)
        env["PHISHING_BACKEND_URL"] = f"http://127.0.0.1:{backend_port}"
        backend_command = [sys.executable, "src/backend_server.py"]
        streamlit_command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/app.py",
            "--server.port",
            str(streamlit_port),
            "--server.headless",
            "true",
        ]
        backend = subprocess.Popen(
            backend_command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        streamlit = subprocess.Popen(
            streamlit_command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if backend.poll() is not None:
                    output = backend.stdout.read() if backend.stdout else ""
                    self.fail(f"El backend terminó antes de arrancar:\n{output}")
                try:
                    with urlopen(f"http://127.0.0.1:{backend_port}/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.25)
            else:
                self.fail("El backend no respondió en loopback dentro del plazo.")

            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if streamlit.poll() is not None:
                    output = streamlit.stdout.read() if streamlit.stdout else ""
                    self.fail(f"Streamlit terminó antes de arrancar:\n{output}")
                try:
                    with urlopen(
                        f"http://127.0.0.1:{streamlit_port}/_stcore/health",
                        timeout=1,
                    ) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.25)
            else:
                self.fail("Streamlit no respondió en loopback dentro del plazo.")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{streamlit_port}")
                page.get_by_text("Sistema de detección de phishing", exact=True).wait_for()
                self.assertIn("phishing", page.title().lower())

                page.get_by_role("button", name="Detección", exact=True).click()
                page.get_by_text("Detección de phishing", exact=True).wait_for()
                page.get_by_label(
                    "Pega aquí el contenido del correo (cabeceras + cuerpo):"
                ).fill(
                    "From: seguridad@banco-falso.example\n"
                    "Subject: Verifica tu cuenta\n\n"
                    "Accede urgentemente a http://192.168.1.1/login"
                )
                page.get_by_role("button", name="Analizar correo").click()
                page.get_by_text("Resultado combinado", exact=True).wait_for(timeout=20_000)
                page.get_by_text("Idioma detectado:").wait_for()
                browser.close()
        finally:
            for process in (streamlit, backend):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
