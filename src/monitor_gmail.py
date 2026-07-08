"""Proceso 24/7 para monitorizar Gmail y alertar por Telegram."""

import argparse
import os
import time
from datetime import datetime

from sistema_phishing.gmail_client import construir_servicio_gmail, obtener_ultimos_correos
from sistema_phishing.env_loader import cargar_env_local
from sistema_phishing.gmail_monitor import MonitorConfig, analizar_correos_nuevos
from sistema_phishing.telegram_notifier import TelegramNotifier


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cargar_env_local(ROOT_DIR)
DEFAULT_CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
DEFAULT_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")
DEFAULT_STATE_PATH = os.path.join(ROOT_DIR, "estado_monitor.json")
DEFAULT_MODEL_PATH_ES = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
DEFAULT_MODEL_PATH_EN = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")
ASCII_TITLE = r"""
 __  __  ___  _   _ ___ _____ ___  ____     ____ __  __    _    ___ _
|  \/  |/ _ \| \ | |_ _|_   _/ _ \|  _ \   / ___|  \/  |  / \  |_ _| |
| |\/| | | | |  \| || |  | || | | | |_) | | |  _| |\/| | / _ \  | || |
| |  | | |_| | |\  || |  | || |_| |  _ <  | |_| | |  | |/ ___ \ | || |___
|_|  |_|\___/|_| \_|___| |_| \___/|_| \_\  \____|_|  |_/_/   \_\___|_____|
"""


def _hora_actual() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _recortar(texto: str, limite: int = 72) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else f"{texto[: limite - 3]}..."


def _estado_archivo(path: str) -> str:
    return "encontrado" if os.path.exists(path) else "no encontrado"


def _ruta_legible(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT_DIR)
    except ValueError:
        return path


def _estado_configurado(valor: str) -> str:
    return "configurado" if valor else "no configurado"


def _linea_clave_valor(clave: str, valor: object) -> str:
    return f"  {clave:<24} {valor}"


def _env_int(name: str, default: int) -> int:
    """Lee un entero desde variables de entorno."""
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Lee un decimal desde variables de entorno."""
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def construir_config() -> MonitorConfig:
    """Construye la configuración del monitor desde variables de entorno."""
    return MonitorConfig(
        state_path=os.getenv("MONITOR_STATE_PATH", DEFAULT_STATE_PATH),
        threshold=_env_float("PHISHING_THRESHOLD", 45.0),
        mode=os.getenv("MONITOR_ANALYSIS_MODE", "combinado").lower(),
        heur_weight=_env_int("MONITOR_HEUR_WEIGHT", 60),
        neural_weight=_env_int("MONITOR_NEURAL_WEIGHT", 40),
        model_path_es=DEFAULT_MODEL_PATH_ES,
        model_path_en=DEFAULT_MODEL_PATH_EN,
        mark_existing_as_seen=os.getenv("MONITOR_MARK_EXISTING_AS_SEEN", "1") != "0",
    )


def construir_notifier() -> TelegramNotifier | None:
    """Crea el notificador si Telegram está configurado."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        return None
    return TelegramNotifier(bot_token=bot_token, chat_id=chat_id)


def mostrar_banner(args: argparse.Namespace, config: MonitorConfig, interval: int) -> None:
    """Muestra una pantalla inicial legible para el monitor."""
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH)
    token_path = os.getenv("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_PATH)
    query = os.getenv("GMAIL_MONITOR_QUERY", "in:inbox newer_than:1d")
    limit = _env_int("GMAIL_MONITOR_LIMIT", 20)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    print("")
    print("=" * 78)
    print(ASCII_TITLE.strip("\n"))
    print("TFG Phishing Monitor - Gmail API + Telegram")
    print("=" * 78)
    print("Vigilancia automatica de correos nuevos.")
    print("")
    print("Ejecucion")
    print(_linea_clave_valor("Modo:", "una comprobacion" if args.once else "continuo"))
    print(_linea_clave_valor("Intervalo:", f"{interval} segundos"))
    print(_linea_clave_valor("Primera ejecucion:", "marca existentes como vistos" if config.mark_existing_as_seen else "analiza existentes"))
    print("")
    print("Gmail")
    print(_linea_clave_valor("Credenciales:", f"{_ruta_legible(credentials_path)} ({_estado_archivo(credentials_path)})"))
    print(_linea_clave_valor("Token:", f"{_ruta_legible(token_path)} ({_estado_archivo(token_path)})"))
    print(_linea_clave_valor("Consulta:", query))
    print(_linea_clave_valor("Limite:", limit))
    print("")
    print("Analisis")
    print(_linea_clave_valor("Modo:", config.mode))
    print(_linea_clave_valor("Umbral phishing:", f"{config.threshold:.1f}%"))
    print(_linea_clave_valor("Peso heuristico:", f"{config.heur_weight}%"))
    print(_linea_clave_valor("Peso neuronal:", f"{config.neural_weight}%"))
    print(_linea_clave_valor("Modelo ES:", f"{_ruta_legible(config.model_path_es)} ({_estado_archivo(config.model_path_es)})"))
    print(_linea_clave_valor("Modelo EN:", f"{_ruta_legible(config.model_path_en)} ({_estado_archivo(config.model_path_en)})"))
    print("")
    print("Alertas")
    print(_linea_clave_valor("Telegram bot:", _estado_configurado(bot_token)))
    print(_linea_clave_valor("Telegram chat:", _estado_configurado(chat_id)))
    print("")
    print("Actividad")
    print("  Esperando el primer ciclo...")
    print("  Pulsa Ctrl+C para detener el monitor.")
    print("=" * 78)
    print("")


def ejecutar_ciclo(config: MonitorConfig, notifier: TelegramNotifier | None) -> None:
    """Ejecuta una comprobación completa de Gmail."""
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH)
    token_path = os.getenv("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_PATH)
    query = os.getenv("GMAIL_MONITOR_QUERY", "in:inbox newer_than:1d")
    limit = _env_int("GMAIL_MONITOR_LIMIT", 20)

    print(f"[{_hora_actual()}] Ciclo iniciado | query='{query}' | limite={limit}")
    servicio = construir_servicio_gmail(credentials_path, token_path)
    correos = obtener_ultimos_correos(servicio, limite=limit, query=query)
    resultados = analizar_correos_nuevos(correos, config, notifier)

    if not resultados:
        print(f"[{_hora_actual()}] Sin correos nuevos para analizar.")
        return

    for resultado in resultados:
        estado = "PHISHING" if resultado.is_phishing else "OK"
        aviso = "notificado" if resultado.notified else "sin notificar"
        subject = _recortar(resultado.subject or "(sin asunto)")
        print(f"[{_hora_actual()}] {estado:<8} {resultado.risk_score:5.1f}% | {subject} | {aviso}")


def main() -> None:
    """Ejecuta el monitor en bucle o una sola vez."""
    parser = argparse.ArgumentParser(
        description="Monitor de Gmail para deteccion automatica de phishing y alertas Telegram.",
        epilog="Ejemplo: python src/monitor_gmail.py --once",
    )
    parser.add_argument("--once", action="store_true", help="Ejecuta una sola comprobacion y termina.")
    args = parser.parse_args()

    interval = _env_int("MONITOR_INTERVAL_SECONDS", 120)
    config = construir_config()
    notifier = construir_notifier()
    mostrar_banner(args, config, interval)

    while True:
        try:
            ejecutar_ciclo(config, notifier)
        except KeyboardInterrupt:
            print(f"[{_hora_actual()}] Monitor detenido por el usuario.")
            break
        except Exception as exc:
            print(f"[{_hora_actual()}] ERROR en el ciclo de monitorizacion: {exc}")

        if args.once:
            break
        print(f"[{_hora_actual()}] Siguiente ciclo en {interval} segundos.")
        time.sleep(interval)


if __name__ == "__main__":
    main()
