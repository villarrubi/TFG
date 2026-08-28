"""Detección del idioma de un correo, compartida por toda la app.

Se centraliza aquí porque hay tres consumidores distintos (la pestaña de
Detección manual, el monitor en segundo plano que avisa por Telegram, y el
servidor de la extensión de Gmail) y todos deben elegir el modelo neuronal
(español/inglés) con el mismo criterio. Antes cada uno tenía su propia copia
de esta lógica y se podían desincronizar con el tiempo.
"""

try:
    from langdetect import detect as _detect
    from langdetect.detector_factory import DetectorFactory

    # langdetect usa muestreo interno y, sin semilla, puede cambiar de idioma
    # para textos breves entre procesos. La selección del modelo debe ser
    # reproducible en evaluación, backend y monitor.
    DetectorFactory.seed = 0
    LANGDETECT_DISPONIBLE = True
except ImportError:
    # La detección de idioma mejora la selección de modelo, pero el sistema
    # puede seguir funcionando sin esta dependencia usando español por
    # defecto (ver requirements.txt: langdetect es una dependencia normal,
    # pero este try/except evita que un entorno sin ella rompa la app).
    LANGDETECT_DISPONIBLE = False


def detectar_idioma_correo(texto: str) -> str:
    """Devuelve 'es' o 'en' según el idioma detectado en el texto.

    Por defecto (sin librería disponible, texto vacío, o error de
    detección) se devuelve 'es'. Solo hay modelos entrenados para español e
    inglés, así que cualquier otro idioma detectado (francés, alemán...) se
    agrupa también como español.
    """
    if not LANGDETECT_DISPONIBLE or not texto.strip():
        return "es"
    try:
        lang = _detect(texto)
        return "en" if lang == "en" else "es"
    except Exception:  # noqa: BLE001 - langdetect falla con textos ambiguos
        return "es"
