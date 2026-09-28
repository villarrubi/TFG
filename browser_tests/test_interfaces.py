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
sys.path.insert(0, str(ROOT / "src"))
from sistema_phishing.guidance import FINDINGS, build_guidance


def _capture_qa(page, name):
    """Capturas opcionales fuera del repositorio durante la revisión visual."""
    directory = os.environ.get("TFG_UI_QA_DIR")
    if directory:
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output / f"{name}.png"), animations="disabled")


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

    def _check_result_panel(self, browser):
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        response = {"risk_score": 76, "is_phishing": True, "signals": {
            "cambio_datos_bancarios": True, "transferencia_urgente": True,
            "suplantacion_ejecutivo": True, "lenguaje_urgente": True,
            "reply_to_diferente": False,
        }}

        def fulfill(route):
            response["guidance"] = build_guidance(response)
            route.fulfill(status=200, content_type="application/json",
                          headers={"Access-Control-Allow-Origin": "*"},
                          body=json.dumps(response))

        page.route("**/analyze", fulfill)
        page.set_content("""
          <div role="main"><h2 class="hP">Cambio de cuenta para el pago</h2>
          <div class="adn ads"><span class="gD" email="direccion@example.com">Dirección</span>
          <div class="a3s aiL">Necesito una transferencia urgente a la nueva cuenta bancaria.</div>
          </div></div>
        """)
        page.add_style_tag(path=str(EXTENSION / "styles.css"))
        page.add_script_tag(path=str(EXTENSION / "server_config.js"))
        page.add_script_tag(path=str(EXTENSION / "content.js"))
        card = page.locator("#tfg-phishing-card")
        page.locator("#tfg-phishing-card.danger").wait_for()
        self.assertIn("teléfono conocido", page.locator("#tfg-phishing-advice").inner_text())
        self.assertIn("Cambio de cuenta bancaria", page.locator("#tfg-phishing-signals").inner_text())
        self.assertNotIn("Reply-To", card.inner_text())
        _capture_qa(page, "extension-bec")

        # Todos los indicios, incluso el último y un texto largo, deben ser accesibles.
        response["signals"] = dict.fromkeys(FINDINGS, True)
        response["signals"]["mensaje_firmado_cifrado"] = True
        response["signals"]["regla_" + "x" * 300 + "<img src=x>"] = True
        page.evaluate("analyzeVisibleEmail({force: true})")
        toggle = page.locator("#tfg-phishing-toggle")
        toggle.focus()
        toggle.press("Enter")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
        self.assertEqual(page.locator(".tfg-phishing-finding").count(), 31)
        self.assertIn("Mención de un documento", page.locator("#tfg-phishing-details").inner_text())
        self.assertIn("no se ha verificado", page.locator("#tfg-phishing-details").inner_text())
        self.assertEqual(card.locator("img").count(), 0)
        for width, height in [(1280, 800), (360, 640), (320, 480), (1280, 400)]:
            with self.subTest(viewport=(width, height)):
                page.set_viewport_size({"width": width, "height": height})
                bounds = card.bounding_box()
                self.assertGreaterEqual(bounds["y"], 0)
                self.assertLessEqual(bounds["y"] + bounds["height"], height + 1)
                self.assertTrue(card.evaluate("el => el.scrollWidth <= el.clientWidth + 1"))
                last = page.locator("#tfg-phishing-details > p").last
                last.scroll_into_view_if_needed()
                self.assertLessEqual(last.bounding_box()["y"] + last.bounding_box()["height"], height)
                if width == 320:
                    _capture_qa(page, "extension-small-details")
        page.locator("#tfg-phishing-minimize").click()
        self.assertFalse(page.locator("#tfg-phishing-advice").is_visible())
        page.locator("#tfg-phishing-minimize").click()
        page.set_viewport_size({"width": 1280, "height": 800})

        response.update(risk_score=0, is_phishing=False, signals={"reply_to_diferente": False})
        page.locator(".a3s").evaluate("el => { el.textContent = 'Texto de relleno '.repeat(40); }")
        page.evaluate("analyzeVisibleEmail({force: true})")
        self.assertIn("no confirma", page.locator("#tfg-phishing-summary").inner_text())
        self.assertEqual(page.locator(".tfg-phishing-finding").count(), 0)
        self.assertNotIn("Cambio de cuenta bancaria", card.inner_text())
        _capture_qa(page, "extension-no-alert")
        response.update(risk_score=80, is_phishing=True, signals={})
        page.locator(".a3s").evaluate("el => { el.textContent += ' Petición añadida al final.'; }")
        page.evaluate("analyzeVisibleEmail()")
        self.assertIn("sin indicios heurísticos", page.locator("#tfg-phishing-summary").inner_text())
        self.assertEqual(page.locator(".tfg-phishing-finding").count(), 0)

        # Una respuesta tardía no puede presentar motivos del correo anterior.
        page.evaluate("""() => {
          window.fetchCalls = 0;
          window.fetch = () => new Promise(resolve => {
            window.fetchCalls += 1;
            window.resolveOld = resolve;
          });
          window.pendingAnalysis = analyzeVisibleEmail({force: true});
        }""")
        page.wait_for_function("typeof window.resolveOld === 'function'")
        page.evaluate("analyzeVisibleEmail()")
        self.assertEqual(page.evaluate("window.fetchCalls"), 1)
        self.assertTrue(toggle.is_disabled())
        page.evaluate("""async () => {
          document.querySelector('h2.hP').textContent = 'Otro correo';
          resolveOld(new Response(JSON.stringify({risk_score:99, is_phishing:true})));
          await pendingAnalysis;
        }""")
        self.assertNotIn("99.0%", card.inner_text())
        self.assertFalse(page.locator("#tfg-phishing-advice").is_visible())
        page.evaluate("() => { window.fetch = async () => { throw new Error('offline'); }; }")
        page.evaluate("analyzeVisibleEmail({force: true})")
        self.assertIn("Sin conexión", card.inner_text())
        self.assertFalse(page.locator("#tfg-phishing-advice").is_visible())
        page.locator("div[role='main']").evaluate("el => el.replaceChildren()")
        page.evaluate("analyzeVisibleEmail()")
        self.assertFalse(card.is_visible())
        page.close()

    def test_configuracion_y_resultados_legibles_de_la_extension(self):
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
            self._check_result_panel(browser)
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
                page.get_by_text("Qué hacer ahora", exact=True).first.wait_for()
                self.assertIn("no introduzcas claves", page.locator("body").inner_text())
                page.get_by_text("Qué hacer ahora", exact=True).first.evaluate(
                    "el => el.scrollIntoView({block: 'start'})"
                )
                _capture_qa(page, "web-result-guidance")

                page.get_by_role("button", name="Entrenamiento", exact=True).click()
                page.get_by_text("Administración de modelos", exact=True).wait_for()
                page.get_by_text("Modelo Español", exact=True).wait_for()
                page.get_by_text("Modelo Inglés", exact=True).wait_for()
                self.assertNotIn('<div class="ui-card">', page.locator("body").inner_text())
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
