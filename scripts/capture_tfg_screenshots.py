"""Genera capturas reproducibles de la aplicación cliente-servidor."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "images"
PHISHING_EML = ROOT / "evaluation" / "local_emails_v1" / "es_phishing_bec.eml"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for(url: str, process: subprocess.Popen[str], label: str) -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"{label} terminó antes de arrancar:\n{output}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"{label} no respondió dentro del plazo.")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    backend_port = _free_port()
    streamlit_port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["BACKEND_PORT"] = str(backend_port)
    env["PHISHING_BACKEND_URL"] = f"http://127.0.0.1:{backend_port}"
    backend = subprocess.Popen(
        [sys.executable, "src/backend_server.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    streamlit = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/app.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(streamlit_port),
            "--server.headless",
            "true",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for(f"http://127.0.0.1:{backend_port}/health", backend, "Backend")
        _wait_for(
            f"http://127.0.0.1:{streamlit_port}/_stcore/health",
            streamlit,
            "Streamlit",
        )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{streamlit_port}")
            page.get_by_text("Sistema de detección de phishing", exact=True).wait_for()
            page.screenshot(
                path=OUTPUT / "figura_6_1_inicio_cliente_servidor.png",
                animations="disabled",
            )

            page.get_by_role("button", name="Detección", exact=True).click()
            page.get_by_text("Detección de phishing", exact=True).wait_for()
            page.get_by_label(
                "Pega aquí el contenido del correo (cabeceras + cuerpo):"
            ).fill(PHISHING_EML.read_text(encoding="utf-8"))
            page.get_by_role("button", name="Analizar correo").click()
            result = page.get_by_text("Resultado combinado", exact=True)
            result.wait_for(timeout=30_000)
            result.scroll_into_view_if_needed()
            page.locator(".risk-card").screenshot(
                path=OUTPUT / "figura_6_2_resultado_bec_combinado.png",
                animations="disabled",
            )
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
    print(f"Capturas generadas en {OUTPUT}")


if __name__ == "__main__":
    main()
