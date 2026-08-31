"""Prueba local reproducible de concurrencia del backend HTTP.

La medición no establece una capacidad de producción ni un SLA. Comprueba que
el servidor con hilos acepta varias solicitudes de análisis simultáneas en el
equipo donde se ejecuta y comunica latencia, rendimiento y fallos observados.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sistema_phishing.backend_service import (
    AnalysisBackendConfig,
    AnalysisBackendService,
)
from sistema_phishing.http_api import crear_servidor_http
from sistema_phishing.runtime_paths import server_model_path

PAYLOAD = {
    "raw_text": (
        "From: Banco Ejemplo <alerta@seguro.example>\n"
        "Reply-To: soporte@otro-dominio.example\n"
        "Subject: Verifica tu cuenta ahora\n\n"
        "Estimado cliente, valida urgentemente tus credenciales en "
        "https://secure-login.example/verify"
    ),
    "options": {"mode": "combinado", "include_all": False},
}


def _percentile(values: list[float], percentile: float) -> float:
    """Calcula un percentil interpolado para una muestra no vacía."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _post(url: str, data: bytes, timeout: float) -> float:
    """Envía una solicitud y devuelve su latencia en milisegundos."""
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        if response.status != 200 or "risk_score" not in payload:
            raise RuntimeError("El backend no devolvió un análisis válido.")
    return (time.perf_counter() - started) * 1000


def _measure_level(
    url: str,
    data: bytes,
    clients: int,
    requests_per_client: int,
    timeout: float,
) -> dict[str, float | int]:
    total_requests = clients * requests_per_client
    start_gate = threading.Event()

    def request_once() -> float:
        start_gate.wait()
        return _post(url, data, timeout)

    latencies: list[float] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=clients) as executor:
        futures = [executor.submit(request_once) for _ in range(total_requests)]
        started = time.perf_counter()
        start_gate.set()
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except (OSError, RuntimeError, json.JSONDecodeError):
                failures += 1
        elapsed = time.perf_counter() - started

    successful = len(latencies)
    return {
        "clients": clients,
        "requests": total_requests,
        "successful": successful,
        "failures": failures,
        "throughput_rps": round(successful / elapsed, 2) if elapsed else 0.0,
        "median_ms": round(statistics.median(latencies), 2) if latencies else 0.0,
        "p95_ms": round(_percentile(latencies, 0.95), 2) if latencies else 0.0,
    }


def run_benchmark(
    levels: list[int],
    requests_per_client: int,
    timeout: float,
) -> list[dict[str, float | int]]:
    """Levanta un backend efímero y ejecuta todos los niveles solicitados."""
    config = AnalysisBackendConfig(
        mode="combinado",
        model_path_es=str(server_model_path(ROOT, "es")),
        model_path_en=str(server_model_path(ROOT, "en")),
    )
    service = AnalysisBackendService(config, admin_token="")
    server = crear_servidor_http("127.0.0.1", 0, service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/analyze"
    data = json.dumps(PAYLOAD).encode("utf-8")
    try:
        _post(url, data, timeout)  # calentamiento de idioma y modelos
        return [
            _measure_level(url, data, level, requests_per_client, timeout)
            for level in levels
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _parse_levels(raw: str) -> list[int]:
    try:
        levels = [int(value.strip()) for value in raw.split(",") if value.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Los niveles deben ser enteros.") from exc
    if not levels or any(level < 1 or level > 256 for level in levels):
        raise argparse.ArgumentTypeError("Usa niveles entre 1 y 256 clientes.")
    return levels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clients",
        type=_parse_levels,
        default=_parse_levels("1,4,8,16,32"),
    )
    parser.add_argument("--requests-per-client", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.requests_per_client < 1 or args.timeout <= 0:
        parser.error("Las solicitudes y el timeout deben ser positivos.")

    results = run_benchmark(args.clients, args.requests_per_client, args.timeout)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print(f"{'clientes':>8} {'peticiones':>10} {'fallos':>7} {'req/s':>10} {'mediana ms':>12} {'p95 ms':>10}")
    for result in results:
        print(
            f"{result['clients']:>8} {result['requests']:>10} {result['failures']:>7} "
            f"{result['throughput_rps']:>10.2f} {result['median_ms']:>12.2f} "
            f"{result['p95_ms']:>10.2f}"
        )


if __name__ == "__main__":
    main()
