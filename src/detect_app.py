"""Interfaz Streamlit para analizar correos con heurísticas y modelo neuronal."""

import os

import streamlit as st

from sistema_phishing.backend_client import (
    BackendClient,
    BackendClientError,
    BackendUnavailableError,
)
from sistema_phishing.gmail_client import (
    GmailIntegrationError,
    construir_servicio_gmail,
    dependencias_disponibles,
    obtener_perfil_gmail,
    obtener_ultimos_correos,
)
from ui_components import aplicar_estilos_base, render_html

# La interfaz solo necesita rutas de OAuth; los modelos pertenecen al backend.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GMAIL_CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
GMAIL_TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")
ANALYSIS_MODES = {
    "Heurístico": "heuristico",
    "Red neuronal": "neural",
    "Combinado": "combinado",
}

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
        r = 255
        g = int(235 - (128 * ratio))
        b = int(0 + (0 * ratio))
    else:
        # Tramo alto: transición de naranja a rojo intenso.
        ratio = (score - 70.0) / 30.0
        r = 255
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
    risk_score = max(0, min(100, round(resultado["risk_score"])))
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


def analizar_entrada(
    entrada,
    texto_modelo: str = "",
    remitente: str = "",
    subject: str = "",
    heur_weight: int = 60,
    neural_weight: int = 40,
    backend_client: BackendClient | None = None,
):
    """Envía la entrada al backend; la UI no ejecuta modelos ni heurísticas."""
    del texto_modelo, remitente, subject
    response = (backend_client or BackendClient()).analyze(
        entrada,
        mode="combinado",
        threshold=45,
        heur_weight=heur_weight,
        neural_weight=neural_weight,
        include_all=True,
    )
    resultados = response["results"]
    return (
        response["language"],
        resultados["heuristico"],
        resultados["neural"],
        resultados["combinado"],
    )


def seleccionar_resultado_principal(tipo_analisis: str, resultado_heur, resultado_neural, resultado_combinado):
    """Elige el resultado que gobierna la clasificación visible."""
    if tipo_analisis == "Heurístico":
        return resultado_heur
    if tipo_analisis == "Red neuronal":
        return resultado_neural
    return resultado_combinado


def analizar_correos_gmail(
    correos_gmail,
    tipo_analisis: str,
    heur_weight: int,
    neural_weight: int,
    backend_client: BackendClient | None = None,
):
    """Envía los EML de Gmail al backend y prepara únicamente la presentación."""
    registros = []
    client = backend_client or BackendClient()
    barra = st.progress(0)

    for indice, correo_gmail in enumerate(correos_gmail, start=1):
        try:
            response = client.analyze(
                correo_gmail.raw_bytes,
                mode=ANALYSIS_MODES[tipo_analisis],
                threshold=45,
                heur_weight=heur_weight,
                neural_weight=neural_weight,
                include_all=True,
            )
            resultados = response["results"]
            datos_email = response["email"]
            resultado_heur = resultados["heuristico"]
            resultado_neural = resultados["neural"]
            resultado_combinado = resultados["combinado"]
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
                "idioma": response["language"],
                "model": response.get("model", {}),
                "resultado_heur": resultado_heur,
                "resultado_neural": resultado_neural,
                "resultado_combinado": resultado_combinado,
                "resultado_principal": resultado_principal,
            })
        except Exception as exc:  # noqa: BLE001 - un correo no debe cortar el lote
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
            col_texto.write(_texto_corto(datos_email.get("subject", "(sin asunto)"), 110))
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

    st.subheader(_texto_corto(datos_email.get("subject", "(sin asunto)"), 120))
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
    except Exception:  # noqa: BLE001 - token inválido se resuelve desde la UI
        # Si el token local está caducado o revocado, el botón de conectar
        # permitirá repetir el flujo OAuth sin bloquear la interfaz.
        st.session_state.pop("gmail_email", None)


def main():
    """Construye la pantalla de detección y ejecuta el análisis seleccionado."""
    aplicar_estilos_deteccion()
    st.title("Detección de phishing")
    st.caption(
        "Cliente web: envía correos al backend central y se limita a mostrar su respuesta."
    )

    client = BackendClient()
    try:
        client.health()
        models_response = client.models()
    except BackendUnavailableError as exc:
        st.error(str(exc))
        st.code("python src/backend_server.py", language="powershell")
        st.stop()
    except BackendClientError as exc:
        st.error(f"El backend no está preparado: {exc}")
        st.stop()

    models = models_response.get("models", {})
    es_disponible = bool(models.get("es", {}).get("valid"))
    en_disponible = bool(models.get("en", {}).get("valid"))
    st.success(f"Backend central conectado: `{client.base_url}`")

    artefactos_invalidos = [
        idioma.upper()
        for idioma in ("es", "en")
        if models.get(idioma, {}).get("available")
        and not models.get(idioma, {}).get("valid")
    ]
    if artefactos_invalidos:
        st.warning(
            "El backend ha descartado artefactos no válidos para: "
            f"{', '.join(artefactos_invalidos)}. Usará el respaldo sintético."
        )

    if es_disponible and en_disponible:
        st.success("Modelos activos en español e inglés. El idioma se detectará automáticamente.")
    elif es_disponible:
        st.info(
            "Solo hay un modelo activo en español. Para correos en inglés se "
            "creará un modelo sintético inglés de respaldo; no se mezclan idiomas."
        )
    elif en_disponible:
        st.info(
            "Solo hay un modelo activo en inglés. Para correos en español se "
            "creará un modelo sintético español de respaldo; no se mezclan idiomas."
        )
    else:
        st.warning("No hay modelos entrenados en disco. Se usa el modelo sintético por defecto.")

    modo = st.radio(
        "Modo de entrada",
        ["Pegar texto del correo", "Subir archivo .eml", "Analizar correos de Gmail"],
        index=0,
    )
    texto_para_analisis = ""
    entrada_backend = None

    if modo == "Pegar texto del correo":
        # En modo texto se trabaja con una representación plana: cabeceras y
        # cuerpo pegados por el usuario en el mismo campo.
        texto_para_analisis = st.text_area("Pega aquí el contenido del correo (cabeceras + cuerpo):")
    elif modo == "Subir archivo .eml":
        archivo = st.file_uploader("Sube un archivo .eml", type=["eml"])
        if archivo is not None:
            entrada_backend = archivo.getvalue()
            texto_para_analisis = archivo.name
            st.markdown("#### Correo cargado")
            st.write({"Archivo": archivo.name, "Tamaño": f"{len(entrada_backend)} bytes"})
            st.caption("El EML se parseará y analizará exclusivamente en el backend.")
    else:
        st.markdown("#### Conexión con Gmail")
        st.write("Usa permisos de solo lectura y analiza los mensajes sin modificarlos.")
        if not dependencias_disponibles():
            st.warning(
                "Faltan las dependencias de Google. Ejecuta "
                "`python -m pip install -r requirements.txt -c constraints.txt`."
            )
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
                        client,
                    )
                    st.session_state["gmail_tipo_analisis"] = tipo_analisis
            except GmailIntegrationError as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 - límite de la integración UI
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
            entrada = entrada_backend if entrada_backend is not None else texto_para_analisis
            try:
                idioma, resultado_heuristico, resultado_neural, resultado_combinado = (
                    analizar_entrada(
                        entrada,
                        heur_weight=heur_weight,
                        neural_weight=neural_weight,
                        backend_client=client,
                    )
                )
            except BackendClientError as exc:
                st.error(f"No se pudo analizar el correo: {exc}")
                return
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
