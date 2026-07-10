"""Interfaz Streamlit para analizar correos con heurísticas y modelo neuronal."""

import os
from types import SimpleNamespace

import streamlit as st

from sistema_phishing import (
    ModelStorage,
    NeuralPhishingClassifier,
    NeuralPhishingDetector,
)
from sistema_phishing.analysis_service import construir_resultado_combinado as combinar_resultados
from sistema_phishing.analizador_email import construir_texto_para_analisis, parsear_eml_bytes
from sistema_phishing.backend_client import analyze_via_backend
from sistema_phishing.gmail_client import (
    GmailIntegrationError,
    construir_servicio_gmail,
    dependencias_disponibles,
    obtener_perfil_gmail,
    obtener_ultimos_correos,
)
from sistema_phishing.heuristicas import analizar_correo
from sistema_phishing.idioma import detectar_idioma_correo
from ui_components import aplicar_estilos_base, render_html

# Los modelos se guardan junto al repositorio para que Streamlit pueda
# encontrarlos aunque la app se ejecute desde otro directorio.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH_ES = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
MODEL_PATH_EN = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")
GMAIL_CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")

# Chuleta de operadores de búsqueda de Gmail para el botón de ayuda (❓) junto
# al campo de consulta. Se mantiene como constante para no ensuciar main().
GMAIL_QUERY_HELP_MD = """
**Parámetros comunes de búsqueda en Gmail**

| Operador | Qué hace |
|---|---|
| `in:inbox` | Solo bandeja de entrada |
| `in:spam` | Solo correos marcados como spam |
| `in:trash` | Solo correos en la papelera |
| `is:unread` | Correos no leídos |
| `is:starred` | Correos destacados |
| `from:persona@dominio.com` | De un remitente concreto |
| `to:persona@dominio.com` | Dirigidos a una dirección concreta |
| `subject:factura` | El asunto contiene esa palabra |
| `has:attachment` | Con archivos adjuntos |
| `filename:pdf` | Adjunto con esa extensión |
| `after:2024/01/01` | Recibidos después de esa fecha |
| `before:2024/12/31` | Recibidos antes de esa fecha |
| `newer_than:7d` | Última semana (`d`=días, `m`=meses, `y`=años) |
| `older_than:1m` | Más antiguos de 1 mes |
| `label:importante` | Con una etiqueta concreta |

Puedes combinar varios operadores en la misma consulta, por ejemplo:

`in:inbox is:unread newer_than:7d has:attachment`
"""


def aplicar_estilos_deteccion() -> None:
    """Aplica estilos locales para que la pantalla de detección sea más legible."""
    aplicar_estilos_base(
        """
        .risk-card {
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            background: #ffffff;
            padding: 18px 20px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
            margin: 12px 0 18px;
        }
        .risk-card h3 {
            margin: 0 0 4px;
            font-size: 1.15rem;
        }
        .risk-kicker {
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .risk-score {
            font-size: 2.6rem;
            font-weight: 800;
            line-height: 1;
            margin: 8px 0;
        }
        .risk-summary {
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.4;
            margin: 0;
        }
        .risk-bar-track {
            height: 14px;
            overflow: hidden;
            border-radius: 999px;
            background: #e2e8f0;
            margin-top: 14px;
        }
        .risk-bar-fill {
            height: 100%;
            border-radius: 999px;
        }
        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .status-low {
            background: #f0fdf4;
            color: #166534;
            border: 1px solid #bbf7d0;
        }
        .status-medium {
            background: #fefce8;
            color: #854d0e;
            border: 1px solid #fde68a;
        }
        .status-high {
            background: #fff7ed;
            color: #9a3412;
            border: 1px solid #fed7aa;
        }
        .status-critical {
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        .metric-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0 18px;
        }
        .metric-tile {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background: #f8fafc;
            padding: 12px;
        }
        .metric-label {
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .metric-value {
            color: #0f172a;
            font-size: 1.35rem;
            font-weight: 800;
            margin-top: 4px;
        }
        @media (max-width: 720px) {
            .metric-strip {
                grid-template-columns: 1fr;
            }
            .risk-score {
                font-size: 2.1rem;
            }
        }
        """
    )


def _color_riesgo(score: float) -> str:
    """Convierte una puntuación 0-100 en un color verde-amarillo-rojo."""
    # Se limita la entrada para que un valor accidentalmente fuera de rango no
    # genere colores inválidos ni barras con porcentajes incoherentes.
    score = max(0.0, min(100.0, score))
    if score <= 30:
        # Tramo bajo: transición de verde a amarillo.
        ratio = score / 30.0
        r = int(76 + (255 - 76) * ratio)
        g = int(175 + (235 - 175) * ratio)
        b = int(80 - (80 * ratio))
    elif score <= 70:
        # Tramo medio: transición de amarillo a naranja.
        ratio = (score - 30.0) / 40.0
        r = int(255)
        g = int(235 - (128 * ratio))
        b = int(0 + (0 * ratio))
    else:
        # Tramo alto: transición de naranja a rojo intenso.
        ratio = (score - 70.0) / 30.0
        r = int(255)
        g = int(107 - (40 * ratio))
        b = int(0 + (0 * ratio))
    return f"#{r:02x}{g:02x}{b:02x}"


def _nivel_riesgo(score: float, is_phishing: bool) -> tuple[str, str, str]:
    """Devuelve etiqueta, clase CSS y resumen para una puntuación."""
    if is_phishing or score >= 70:
        return (
            "Riesgo alto",
            "status-critical",
            "El correo supera el umbral de seguridad. Conviene tratarlo como sospechoso.",
        )
    if score >= 45:
        return (
            "Riesgo medio",
            "status-high",
            "Hay señales relevantes. Revisa remitente, enlaces y contenido antes de actuar.",
        )
    if score >= 25:
        return (
            "Riesgo bajo",
            "status-medium",
            "Se han encontrado algunas señales leves, pero no superan el umbral.",
        )
    return (
        "Riesgo muy bajo",
        "status-low",
        "No se han detectado señales fuertes de phishing en los datos analizados.",
    )


def _render_metric_strip(resultado) -> None:
    """Muestra contadores comunes del análisis."""
    render_html(
        f"""
        <div class="metric-strip">
            <div class="metric-tile">
                <div class="metric-label">URLs</div>
                <div class="metric-value">{len(resultado.get('urls', []))}</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">Anclas HTML</div>
                <div class="metric-value">{len(resultado.get('anchors', []))}</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">Cabeceras</div>
                <div class="metric-value">{len(resultado.get('headers', {}))}</div>
            </div>
        </div>
        """
    )


def mostrar_resultado_basico(resultado, titulo: str = "Resultado del análisis"):
    """Pinta los datos comunes a cualquier tipo de análisis."""
    risk_score = max(0, min(100, int(round(resultado["risk_score"]))))
    color = _color_riesgo(risk_score)
    nivel, clase, resumen = _nivel_riesgo(risk_score, resultado["is_phishing"])
    veredicto = "Phishing probable" if resultado["is_phishing"] else "No parece phishing"

    render_html(
        f"""
        <div class="risk-card">
            <div class="risk-kicker">{titulo}</div>
            <span class="status-pill {clase}">{nivel}</span>
            <div class="risk-score" style="color:{color};">{risk_score}%</div>
            <h3>{veredicto}</h3>
            <p class="risk-summary">{resumen}</p>
            <div class="risk-bar-track">
                <div class="risk-bar-fill" style="width:{risk_score}%; background:{color};"></div>
            </div>
        </div>
        """
    )
    _render_metric_strip(resultado)
    if resultado.get("description"):
        st.info(resultado["description"])


SIGNAL_GROUPS = {
    "Identidad y cabeceras": [
        "reply_to_diferente",
        "nombre_display_engano",
        "remitente_marca_engano",
        "cabecera_spoofing",
        "incoherencia_remitente",
        "autenticacion_fallida",
        "recibidos_sospechosos",
        "dmarc_fallido",
        "dkim_mal_formado",
        "mensaje_id_sospechoso",
        "mensaje_firmado_cifrado",
    ],
    "Enlaces y dominios": [
        "enlaces_sospechosos",
        "dominio_blacklist",
        "url_parametros_sospechosos",
        "dominio_punycode_unicode",
        "enlace_shortener",
        "anchor_distinto",
    ],
    "Contenido y adjuntos": [
        "saludo_generico",
        "solicitud_credenciales",
        "lenguaje_urgente",
        "asunto_sospechoso",
        "adjunto_sospechoso",
        "referencia_archivo",
    ],
    "HTML": [
        "meta_refresh_html",
        "javascript_redireccion",
        "html_sospechoso",
        "formulario_html",
        "formulario_action_sospechoso",
    ],
}


def _nombre_senal(nombre: str) -> str:
    return nombre.replace("_", " ").capitalize()


def _mostrar_senales_agrupadas(signals: dict) -> None:
    """Muestra las señales por familia para facilitar la revisión."""
    for grupo, nombres in SIGNAL_GROUPS.items():
        filas = [
            {"Señal": _nombre_senal(nombre), "Estado": "Activa" if signals.get(nombre) else "Correcta"}
            for nombre in nombres
            if nombre in signals
        ]
        activas = sum(1 for fila in filas if fila["Estado"] == "Activa")
        with st.expander(f"{grupo} ({activas}/{len(filas)} activas)", expanded=activas > 0):
            st.table(filas)


def mostrar_resultado_heuristico(resultado):
    """Muestra la puntuación heurística y el detalle de reglas activadas."""
    mostrar_resultado_basico(resultado, "Análisis heurístico")
    st.markdown("### Señales por categoría")
    _mostrar_senales_agrupadas(resultado["signals"])

    with st.expander("Explicación detallada de las señales"):
        for item in resultado["explanation"]:
            st.write(f"- {item}")

    if resultado["urls"]:
        with st.expander(f"Enlaces detectados ({len(resultado['urls'])})"):
            for enlace in resultado["urls"]:
                st.write(f"- {enlace}")

    if resultado.get("anchors"):
        with st.expander(f"Anclas detectadas en HTML ({len(resultado.get('anchors', []))})"):
            for anchor in resultado["anchors"]:
                st.write(f"- Texto: {anchor['text']} / URL: {anchor['href']}")

    if resultado.get("headers"):
        with st.expander("Cabeceras analizadas"):
            st.write({
                key: value
                for key, value in resultado["headers"].items()
                if key.lower() in ["from", "to", "subject", "reply-to", "return-path", "message-id"]
            })


def mostrar_resultado_neural(resultado):
    """Muestra la salida simplificada del clasificador neuronal."""
    mostrar_resultado_basico(resultado, "Análisis por red neuronal")
    st.markdown("### Detalle del modelo")
    st.write(f"**Probabilidad de phishing:** {resultado['risk_score']:.1f}%")
    st.write(f"**Clasificación:** {'Phishing probable' if resultado['is_phishing'] else 'No parece phishing'}")


def mostrar_combinado(resultado_heur, resultado_neural, heur_weight, neural_weight):
    """Combina los dos análisis con los pesos elegidos en la interfaz."""
    resultado = construir_resultado_combinado(resultado_heur, resultado_neural, heur_weight, neural_weight)
    mostrar_resultado_basico(resultado, "Resultado combinado")
    st.markdown("### Ponderación aplicada")
    st.write(f"Peso heurístico: {heur_weight}%")
    st.write(f"Peso neuronal: {neural_weight}%")


def construir_resultado_combinado(resultado_heur, resultado_neural, heur_weight, neural_weight):
    """Devuelve el resultado mixto sin pintarlo en pantalla."""
    # Se mantiene el mismo umbral que la heurística para que la interpretación
    # del porcentaje sea homogénea en los tres modos de análisis.
    config = SimpleNamespace(threshold=45, heur_weight=heur_weight, neural_weight=neural_weight)
    resultado = combinar_resultados(resultado_heur, resultado_neural, config)
    return {
        "is_phishing": resultado["is_phishing"],
        "risk_score": resultado["risk_score"],
        "description": resultado["description"],
        "urls": resultado["urls"],
        "anchors": resultado["anchors"],
        "headers": resultado["headers"],
    }


def _normalizar_payload_analisis(entrada, texto_modelo: str, remitente: str, subject: str) -> dict:
    """Convierte texto pegado o .eml parseado en el payload común del backend."""
    if isinstance(entrada, dict):
        return {
            "subject": subject,
            "from": remitente,
            "body": entrada.get("body", ""),
            "html_body": entrada.get("html_body", ""),
            "headers": entrada.get("headers", {}),
            "anchors": entrada.get("anchors", []),
            "attachments": entrada.get("attachments", []),
            "urls": entrada.get("urls", []),
            "full_text": texto_modelo,
        }
    return {
        "subject": subject,
        "from": remitente,
        "body": str(entrada),
        "html_body": "",
        "headers": {},
        "anchors": [],
        "attachments": [],
        "urls": [],
        "full_text": texto_modelo,
    }


def cargar_detector(idioma: str) -> NeuralPhishingDetector:
    """Carga el modelo del idioma detectado y usa alternativas si no existe."""
    path = MODEL_PATH_EN if idioma == "en" else MODEL_PATH_ES
    storage = ModelStorage(path)
    classifier = storage.load()
    if classifier is None:
        # Si falta el modelo del idioma detectado, reutiliza el otro modelo
        # entrenado antes de recurrir al dataset sintético.
        path_alt = MODEL_PATH_ES if idioma == "en" else MODEL_PATH_EN
        storage_alt = ModelStorage(path_alt)
        classifier = storage_alt.load()
    if classifier is None:
        # Último recurso para que la demo siga funcionando en un clon limpio.
        classifier = NeuralPhishingClassifier()
        classifier.fit_default()
    return NeuralPhishingDetector(classifier)


def analizar_entrada(entrada, texto_modelo: str, remitente: str, subject: str, heur_weight: int, neural_weight: int):
    """Ejecuta análisis heurístico, neuronal y combinado sobre una entrada."""
    payload = _normalizar_payload_analisis(entrada, texto_modelo, remitente, subject)

    def _analisis_local(local_payload):
        idioma_local = detectar_idioma_correo(local_payload.get("full_text", ""))
        detector = cargar_detector(idioma_local)
        datos_locales = entrada if isinstance(entrada, dict) else str(entrada)
        resultado_heur = analizar_correo(datos_locales)
        resultado_neur = detector.analyze(local_payload.get("full_text", ""), remitente, subject)
        return {
            "source": "local",
            "idioma": idioma_local,
            "heuristico": resultado_heur,
            "neural": resultado_neur,
            "combinado": construir_resultado_combinado(
                resultado_heur,
                resultado_neur,
                heur_weight,
                neural_weight,
            ),
        }

    resultado_backend = analyze_via_backend(payload, fallback=_analisis_local)
    if resultado_backend.get("source") == "local":
        return (
            resultado_backend["idioma"],
            resultado_backend["heuristico"],
            resultado_backend["neural"],
            resultado_backend["combinado"],
        )
    return "backend", resultado_backend, resultado_backend, resultado_backend


def seleccionar_resultado_principal(tipo_analisis: str, resultado_heur, resultado_neural, resultado_combinado):
    """Elige el resultado que gobierna la clasificación visible."""
    if tipo_analisis == "Heurístico":
        return resultado_heur
    if tipo_analisis == "Red neuronal":
        return resultado_neural
    return resultado_combinado


def analizar_correos_gmail(correos_gmail, tipo_analisis: str, heur_weight: int, neural_weight: int):
    """Analiza correos de Gmail y devuelve datos listos para la interfaz."""
    registros = []
    barra = st.progress(0)

    for indice, correo_gmail in enumerate(correos_gmail, start=1):
        try:
            datos_email = parsear_eml_bytes(correo_gmail.raw_bytes)
            texto_modelo = construir_texto_para_analisis(datos_email)
            idioma, resultado_heur, resultado_neural, resultado_combinado = analizar_entrada(
                datos_email,
                texto_modelo,
                datos_email.get("from", ""),
                datos_email.get("subject", ""),
                heur_weight,
                neural_weight,
            )
            resultado_principal = seleccionar_resultado_principal(
                tipo_analisis,
                resultado_heur,
                resultado_neural,
                resultado_combinado,
            )
            registros.append({
                "ok": True,
                "gmail_id": correo_gmail.gmail_id,
                "snippet": correo_gmail.snippet,
                "datos_email": datos_email,
                "idioma": idioma,
                "resultado_heur": resultado_heur,
                "resultado_neural": resultado_neural,
                "resultado_combinado": resultado_combinado,
                "resultado_principal": resultado_principal,
            })
        except Exception as exc:
            registros.append({
                "ok": False,
                "gmail_id": correo_gmail.gmail_id,
                "error": str(exc),
            })
        barra.progress(indice / len(correos_gmail))
    barra.empty()
    return registros


def _texto_corto(texto: str, limite: int = 90) -> str:
    """Recorta texto largo para etiquetas de la interfaz."""
    texto = texto.strip() or "(sin datos)"
    return texto if len(texto) <= limite else f"{texto[: limite - 3]}..."


def mostrar_resultados_gmail(registros, tipo_analisis: str):
    """Muestra resultados de Gmail en formato vertical y detalle individual."""
    st.markdown("### Resumen de correos analizados")
    for indice, registro in enumerate(registros, start=1):
        if not registro["ok"]:
            with st.container(border=True):
                st.error(f"Correo {indice}: {registro['error']}")
            continue

        datos_email = registro["datos_email"]
        resultado = registro["resultado_principal"]
        clasificacion = "Phishing probable" if resultado["is_phishing"] else "No parece phishing"
        color = _color_riesgo(resultado["risk_score"])

        with st.container(border=True):
            col_riesgo, col_texto, col_estado = st.columns([1, 4, 2])
            col_riesgo.metric("Riesgo", f"{resultado['risk_score']:.1f}%")
            col_texto.markdown(f"**{_texto_corto(datos_email.get('subject', '(sin asunto)'), 110)}**")
            col_texto.caption(_texto_corto(datos_email.get("from", "(sin remitente)"), 120))
            col_estado.markdown(f"**{clasificacion}**")
            col_estado.caption(f"Modo: {tipo_analisis}")
            render_html(
                f"""
                <div style='width: 100%; background: #e6e6e6; border-radius: 8px; height: 10px;'>
                    <div style='width: {resultado["risk_score"]}%; height: 10px; border-radius: 8px; background: {color};'></div>
                </div>
                """
            )

    registros_ok = [registro for registro in registros if registro["ok"]]
    if not registros_ok:
        return

    st.markdown("### Detalle individual")
    seleccionado = st.selectbox(
        "Correo",
        options=list(range(len(registros_ok))),
        format_func=lambda idx: (
            f"{idx + 1}. "
            f"{_texto_corto(registros_ok[idx]['datos_email'].get('subject', '(sin asunto)'), 70)}"
        ),
    )
    registro = registros_ok[seleccionado]
    datos_email = registro["datos_email"]

    st.markdown(f"#### {_texto_corto(datos_email.get('subject', '(sin asunto)'), 120)}")
    st.write({
        "Gmail ID": registro["gmail_id"],
        "From": datos_email.get("from", ""),
        "To": datos_email.get("to", ""),
        "Idioma": "Español" if registro["idioma"] == "es" else "Inglés",
    })
    if registro["snippet"]:
        st.write(f"**Vista previa:** {registro['snippet']}")

    resultado_principal = registro["resultado_principal"]
    st.metric("Riesgo", f"{resultado_principal['risk_score']:.1f}%")

    if tipo_analisis == "Red neuronal":
        st.write(
            "**Clasificación:** "
            f"{'Phishing probable' if resultado_principal['is_phishing'] else 'No parece phishing'}"
        )
        return

    if tipo_analisis == "Combinado":
        st.markdown("### Ponderación aplicada")
        col1, col2 = st.columns(2)
        col1.write("Heurística: incluida en el resultado combinado")
        col2.write("Red neuronal: incluida en el resultado combinado")

    tab_senales, tab_enlaces, tab_cabeceras = st.tabs(["Señales", "Enlaces", "Cabeceras"])
    with tab_senales:
        for item in registro["resultado_heur"].get("explanation", []):
            st.write(f"- {item}")
    with tab_enlaces:
        urls = registro["resultado_heur"].get("urls", [])
        anchors = registro["resultado_heur"].get("anchors", [])
        if not urls and not anchors:
            st.info("No se detectaron enlaces en este correo.")
        for url in urls:
            st.write(f"- {url}")
        for anchor in anchors:
            st.write(f"- Texto: {anchor['text']} / URL: {anchor['href']}")
    with tab_cabeceras:
        st.write({
            key: value
            for key, value in registro["resultado_heur"].get("headers", {}).items()
            if key.lower() in ["from", "to", "subject", "reply-to", "return-path", "message-id"]
        })


def cargar_email_gmail_desde_token() -> None:
    """Carga en sesión el correo autenticado si ya existe token OAuth."""
    if st.session_state.get("gmail_email"):
        return
    if not os.path.exists(GMAIL_TOKEN_PATH) or not dependencias_disponibles():
        return
    try:
        servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
        perfil = obtener_perfil_gmail(servicio)
        st.session_state["gmail_email"] = perfil.get("emailAddress", "")
    except Exception:
        # Si el token local está caducado o revocado, el botón de conectar
        # permitirá repetir el flujo OAuth sin bloquear la interfaz.
        st.session_state.pop("gmail_email", None)


def main():
    """Construye la pantalla de detección y ejecuta el análisis seleccionado."""
    aplicar_estilos_deteccion()
    st.title("Detección de phishing")
    st.caption("Analiza correos pegados, archivos .eml o mensajes importados desde Gmail.")

    es_disponible = ModelStorage(MODEL_PATH_ES).exists()
    en_disponible = ModelStorage(MODEL_PATH_EN).exists()

    if es_disponible and en_disponible:
        st.success("Modelos en español e inglés cargados. El idioma se detectará automáticamente.")
    elif es_disponible:
        st.info("Solo hay modelo en español. Se usará para todos los correos.")
    elif en_disponible:
        st.info("Solo hay modelo en inglés. Se usará para todos los correos.")
    else:
        st.warning("No hay modelos entrenados en disco. Se usa el modelo sintético por defecto.")

    modo = st.radio(
        "Modo de entrada",
        ["Pegar texto del correo", "Subir archivo .eml", "Analizar correos de Gmail"],
        index=0,
    )
    texto_para_analisis = ""
    datos_email = None

    if modo == "Pegar texto del correo":
        # En modo texto se trabaja con una representación plana: cabeceras y
        # cuerpo pegados por el usuario en el mismo campo.
        texto_para_analisis = st.text_area("Pega aquí el contenido del correo (cabeceras + cuerpo):")
    elif modo == "Subir archivo .eml":
        archivo = st.file_uploader("Sube un archivo .eml", type=["eml"])
        if archivo is not None:
            # El parser devuelve una estructura rica: texto plano para el modelo
            # y HTML/anclas/adjuntos para las heurísticas.
            datos_email = parsear_eml_bytes(archivo.getvalue())
            texto_para_analisis = construir_texto_para_analisis(datos_email)
            st.markdown("#### Correo cargado")
            st.write({
                "From": datos_email["from"],
                "To": datos_email["to"],
                "Subject": datos_email["subject"],
            })
    else:
        st.markdown("#### Conexión con Gmail")
        st.write("Usa permisos de solo lectura y analiza los mensajes sin modificarlos.")
        if not dependencias_disponibles():
            st.warning("Faltan las dependencias de Google. Ejecuta `pip install -r requirements.txt`.")
        st.caption(f"Credenciales esperadas: `{GMAIL_CREDENTIALS_PATH}`")
        cargar_email_gmail_desde_token()
        if st.session_state.get("gmail_email"):
            st.success(f"Cuenta conectada: {st.session_state['gmail_email']}")
            if st.button("Cambiar cuenta de Gmail"):
                if os.path.exists(GMAIL_TOKEN_PATH):
                    os.remove(GMAIL_TOKEN_PATH)
                st.session_state.pop("gmail_email", None)
                st.session_state.pop("gmail_resultados", None)
                st.session_state.pop("gmail_tipo_analisis", None)
                st.info("Sesión de Gmail eliminada. Vuelve a conectar para elegir otra cuenta.")
                st.rerun()
        else:
            st.info("No hay ninguna cuenta de Gmail conectada todavía.")
        limite_gmail = st.number_input("Número de correos a analizar", min_value=1, max_value=50, value=10)

        # Campo de consulta + botón de ayuda (❓) con los operadores de
        # búsqueda de Gmail más habituales. Se usan columnas para que el
        # popover quede alineado a la derecha del campo de texto, y un
        # pequeño espaciador para bajarlo a la altura del input (el popover
        # se posiciona donde está el botón, no donde está la etiqueta).
        col_query, col_ayuda = st.columns([6, 1])
        with col_query:
            query_gmail = st.text_input("Consulta de Gmail", value="in:inbox")
        with col_ayuda:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("❓", use_container_width=True):
                st.markdown(GMAIL_QUERY_HELP_MD)

    tipo_analisis = st.radio("Tipo de análisis", ["Heurístico", "Red neuronal", "Combinado"], index=2)
    heur_weight = 60
    neural_weight = 40
    if tipo_analisis == "Combinado":
        # El peso neuronal se calcula como complemento para evitar que la suma
        # de ponderaciones pueda superar o quedarse por debajo del 100%.
        heur_weight = st.slider("Peso heurístico (%)", 0, 100, 60)
        neural_weight = 100 - heur_weight

    if modo == "Analizar correos de Gmail":
        if st.button("Conectar Gmail y analizar"):
            try:
                with st.spinner("Conectando con Gmail..."):
                    servicio = construir_servicio_gmail(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
                    perfil = obtener_perfil_gmail(servicio)
                    st.session_state["gmail_email"] = perfil.get("emailAddress", "")
                    correos_gmail = obtener_ultimos_correos(
                        servicio,
                        limite=int(limite_gmail),
                        query=query_gmail,
                    )
                if not correos_gmail:
                    st.info("Gmail no devolvió correos para esa consulta.")
                else:
                    st.session_state["gmail_resultados"] = analizar_correos_gmail(
                        correos_gmail,
                        tipo_analisis,
                        heur_weight,
                        neural_weight,
                    )
                    st.session_state["gmail_tipo_analisis"] = tipo_analisis
            except GmailIntegrationError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"No se pudo completar la integración con Gmail: {exc}")
        if st.session_state.get("gmail_resultados"):
            mostrar_resultados_gmail(
                st.session_state["gmail_resultados"],
                st.session_state.get("gmail_tipo_analisis", tipo_analisis),
            )
        return

    if st.button("Analizar correo"):
        if not texto_para_analisis.strip():
            st.warning("Introduce texto o sube un archivo .eml antes de analizar.")
        else:
            if datos_email:
                # Para .eml se conserva el diccionario parseado, porque contiene
                # campos que no aparecen en un texto pegado manualmente.
                entrada = datos_email
                texto_modelo = construir_texto_para_analisis(datos_email)
                remitente = datos_email.get("from", "")
                subject = datos_email.get("subject", "")
            else:
                entrada = texto_para_analisis
                texto_modelo = texto_para_analisis
                remitente = ""
                subject = ""

            idioma, resultado_heuristico, resultado_neural, resultado_combinado = analizar_entrada(
                entrada,
                texto_modelo,
                remitente,
                subject,
                heur_weight,
                neural_weight,
            )
            st.caption(f"Idioma detectado: {'Español 🇪🇸' if idioma == 'es' else 'Inglés 🇬🇧'}")

            if tipo_analisis == "Heurístico":
                mostrar_resultado_heuristico(resultado_heuristico)
            elif tipo_analisis == "Red neuronal":
                mostrar_resultado_neural(resultado_neural)
            else:
                mostrar_resultado_basico(resultado_combinado, "Resultado combinado")
                st.markdown("### Ponderación aplicada")
                st.write(f"Peso heurístico: {heur_weight}%")
                st.write(f"Peso neuronal: {neural_weight}%")


if __name__ == "__main__":
    main()
