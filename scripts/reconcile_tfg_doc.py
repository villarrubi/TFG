"""Migración histórica que alineó la memoria DOCX con la rama web original.

No debe ejecutarse sobre la entrega actual; usa ``sync_delivery_docs.py``.
Este script solo
reemplaza párrafos identificados por su comienzo y actualiza los extractos de
código del anexo para que no sobrevivan afirmaciones de versiones anteriores.
"""

from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "TFG.docx"
CODE_STYLE = "Código TFG"


def _paragraphs(doc):
    return list(doc.paragraphs)


def replace_prefix(doc, prefix: str, replacement: str) -> int:
    """Reemplaza el párrafo completo que empieza por ``prefix``."""
    changed = 0
    for paragraph in _paragraphs(doc):
        if paragraph.text.startswith(prefix):
            paragraph.text = replacement
            changed += 1
    return changed


def replace_exact(doc, old: str, new: str) -> int:
    changed = 0
    for paragraph in _paragraphs(doc):
        if paragraph.text == old:
            paragraph.text = new
            changed += 1
    return changed


def insert_before(doc, prefix: str, lines: list[str], style: str = CODE_STYLE) -> None:
    """Inserta líneas una sola vez antes del párrafo indicado."""
    paragraphs = _paragraphs(doc)
    target = next((p for p in paragraphs if p.text.startswith(prefix)), None)
    if target is None:
        return
    marker = lines[0]
    if any(marker in paragraph.text for paragraph in paragraphs):
        return
    for line in reversed(lines):
        paragraph = target.insert_paragraph_before(line)
        paragraph.style = style


def reorder_code_lines(doc, lines: list[str]) -> None:
    """Reordena un bloque de líneas ya insertado conservando sus párrafos."""
    wanted = set(lines)
    matches = [paragraph for paragraph in _paragraphs(doc) if paragraph.text in wanted]
    if len(matches) != len(lines):
        return
    for paragraph, line in zip(matches, lines):
        paragraph.text = line
        paragraph.style = CODE_STYLE


def rewrite_code_section(doc, heading: str, next_heading: str, lines: list[str]) -> None:
    """Sustituye un bloque de extracto sin cambiar su posición en la memoria."""
    paragraphs = _paragraphs(doc)
    start = next((i for i, p in enumerate(paragraphs) if p.text == heading), None)
    end = next(
        (i for i, p in enumerate(paragraphs) if i > (start or -1) and p.text == next_heading),
        None,
    )
    if start is None or end is None:
        return
    slots = paragraphs[start + 1 : end]
    for paragraph, line in zip(slots, lines):
        paragraph.text = line
        paragraph.style = CODE_STYLE
    for paragraph in slots[len(lines) :]:
        paragraph.text = ""
        paragraph.style = CODE_STYLE


def compact_empty_code_paragraphs(doc, heading: str, next_heading: str) -> None:
    """Elimina huecos heredados de bloques de código ya sustituidos."""
    paragraphs = _paragraphs(doc)
    start = next((i for i, p in enumerate(paragraphs) if p.text == heading), None)
    end = next(
        (i for i, p in enumerate(paragraphs) if i > (start or -1) and p.text == next_heading),
        None,
    )
    if start is None or end is None:
        return
    for paragraph in list(paragraphs[start + 1 : end]):
        if paragraph.text == "":
            parent = paragraph._element.getparent()
            if parent is not None:
                parent.remove(paragraph._element)


def reconcile_prose(doc) -> None:
    replacements = [
        (
            "El phishing se ha consolidado como una de las ciberamenazas más persistentes y dañinas del panorama actual de la ciberseguridad. Este Trabajo Fin de Grado",
            "El phishing se ha consolidado como una de las ciberamenazas más persistentes y dañinas del panorama actual de la ciberseguridad. Este Trabajo Fin de Grado aborda el diseño, la implementación y la evaluación de una aplicación web local para detectar phishing en correos electrónicos. La solución combina un sistema heurístico explicable con un clasificador neuronal basado en TF-IDF y perceptrón multicapa (MLP). Desarrollada en Python con Streamlit, permite analizar texto pegado, archivos .eml y mensajes importados mediante la API de Gmail, además de entrenar y evaluar modelos en español e inglés. El análisis puede ejecutarse dentro de la aplicación mediante módulos reutilizables y, de forma opcional, exponerse a la extensión de Gmail o a clientes locales mediante una API HTTP; ninguna de esas interfaces envía el correo a un servicio externo. La memoria estudia el fenómeno del phishing desde su base psicológica y su evolución reciente, revisa el estado del arte en machine learning y deep learning, y presenta los resultados obtenidos durante la validación del prototipo. Los resultados confirman que combinar reglas explicables y aprendizaje supervisado constituye una base funcional y extensible para la detección de este tipo de amenazas.",
        ),
        (
            "Phishing has become one of the most persistent",
            "Phishing has become one of the most persistent and damaging threats in today's cybersecurity landscape. This Bachelor's Thesis presents the design, implementation and evaluation of a local web application for detecting phishing emails. The solution combines an explainable heuristic system with a neural classifier based on TF-IDF and a multilayer perceptron (MLP). Built in Python with Streamlit, it can analyse pasted text, .eml files and messages imported through the Gmail API, as well as train and evaluate Spanish and English models. The analysis runs through reusable local modules and can optionally be exposed to the Gmail extension or local clients through an HTTP API; email content is not sent to an external service. The document examines phishing from its psychological foundations and recent evolution, reviews the state of the art in machine learning and deep learning, and reports the results obtained during prototype validation. The results show that combining explainable rules with supervised learning provides a functional and extensible basis for detecting this type of threat.",
        ),
        (
            "La metodología seguida ha combinado",
            "La metodología seguida ha combinado una revisión bibliográfica de fuentes académicas y de industria con un desarrollo iterativo del prototipo. El sistema se ha implementado en Python como una aplicación web modular con un núcleo local compartido: la interfaz Streamlit invoca los servicios de análisis directamente y, opcionalmente, el mismo caso de uso se expone mediante una API HTTP local y una extensión de Gmail. La validación se ha realizado mediante pruebas automatizadas, pruebas funcionales de los flujos principales y evaluación del clasificador sobre datos sintéticos controlados en español e inglés.",
        ),
        (
            "La carga de trabajo del segundo cuatrimestre",
            "La carga de trabajo del segundo cuatrimestre se concentró en el motor heurístico, el clasificador neuronal y la interfaz web, por ser los componentes que reúnen la lógica central del prototipo. Las integraciones con Gmail y Telegram se incorporaron posteriormente reutilizando el mismo servicio de análisis; además, se añadió una API HTTP local y un adaptador para la extensión de Gmail sin duplicar las reglas del dominio.",
        ),
        (
            "El prototipo se centra en el análisis de mensajes",
            "El prototipo se centra en el análisis de mensajes de correo electrónico desde una aplicación web y varias entradas locales. El origen puede ser texto pegado, un archivo .eml, un mensaje importado mediante Gmail, el correo visible en la extensión de navegador o un JSON enviado a la API local. A partir de la entrada, el sistema extrae cabeceras, remitente, asunto, cuerpo en texto plano, contenido HTML, enlaces, anclas y adjuntos, y genera una evaluación de riesgo mediante reglas heurísticas, modelo neuronal o una combinación ponderada.",
        ),
        (
            "El alcance del prototipo se ha delimitado",
            "El alcance del prototipo se ha delimitado al análisis estático del correo electrónico y de las URLs contenidas en él. El sistema no navega activamente hacia las páginas enlazadas, no descarga contenido externo ni consulta servicios de reputación en tiempo real. La API, la extensión y las aplicaciones de escritorio se mantienen en el entorno local y no convierten el proyecto en un servicio remoto multiusuario.",
        ),
        (
            "RiskScorer asigna una ponderación",
            "RiskScorer asigna una ponderación a cada señal activa y calcula una puntuación final entre 0 y 100. Si la puntuación supera el umbral configurado, el mensaje se clasifica como phishing probable. ExplanationBuilder transforma las señales en explicaciones comprensibles. El mismo servicio puede producir el resultado desde Streamlit, la API local, la extensión o el monitor; si se supera el umbral, la monitorización puede enviar una alerta por Telegram y registrar el identificador del mensaje para evitar duplicados.",
        ),
        (
            "Los modelos entrenados se almacenan",
            "Los modelos entrenados se almacenan en disco mediante joblib, diferenciando entre el modelo en español (modelo_neural_es.joblib) y el modelo en inglés (modelo_neural_en.joblib). Durante el análisis, el sistema detecta el idioma del correo con langdetect y reutiliza un detector cacheado por idioma, no uno fijado para toda la sesión. Si el modelo del idioma esperado no existe, está corrupto o tiene metadatos incompatibles, se entrena un modelo sintético del mismo idioma; nunca se reutiliza silenciosamente el modelo de la lengua opuesta.",
        ),
        (
            "La revisión actual de la rama web ejecuta correctamente 44 pruebas",
            "La rama main ejecuta 72 pruebas automatizadas que protegen los componentes, el contrato cliente-servidor y sus integraciones.",
        ),
        (
            "La revisión actual de la rama web ejecuta 44 pruebas unitarias",
            "La rama main ejecuta 72 pruebas unitarias y de integración mediante unittest. Cubren EML, combinación, configuración, Gmail, monitor, heurísticas, clasificador, persistencia, cliente y API HTTP, seguridad, extensión, evaluación y Telegram. Todas finalizaron correctamente; los avisos corresponden a iteraciones reducidas del MLP en pruebas rápidas.",
        ),
        (
            "En segundo lugar, se evaluó el clasificador neuronal",
            "En segundo lugar, la aplicación permite evaluar el clasificador neuronal con un CSV de prueba independiente, separado del conjunto de entrenamiento. La interfaz calcula exactitud, precisión, recall, F1, accuracy balanceada y la matriz de confusión; no se fija una partición automática 70/30 ni se presentan resultados estadísticos sin indicar el conjunto utilizado. En tercer lugar, se comprobaron los flujos funcionales de la aplicación web: análisis de texto pegado y archivos .eml, selección del modelo por idioma, importación mediante Gmail y navegación entre las vistas de detección y entrenamiento. Los resultados reproducibles se presentan en la sección de pruebas y discusión.",
        ),
        (
            "Para probar el flujo completo de entrenamiento",
            "Para probar el arranque del clasificador sin depender de información personal, el repositorio incluye un dataset sintético mínimo generado bajo demanda: cinco ejemplos de phishing y cinco legítimos por idioma (español e inglés). Los ejemplos cubren urgencia, solicitud de credenciales, enlaces sospechosos y mensajes legítimos de confirmación, reuniones o boletines. No pretende ser un corpus de producción; sirve para demostrar el flujo y mantener una ejecución reproducible cuando todavía no se ha cargado un CSV real.",
        ),
        (
            "Para obtener una estimación realista del comportamiento",
            "La evaluación cuantitativa de un modelo entrenado debe realizarse desde la vista de Entrenamiento con un CSV de prueba independiente. El sistema separa los datos de entrenamiento y prueba cuando el usuario proporciona ambos conjuntos y muestra accuracy, precisión, recall, F1, accuracy balanceada y la matriz VP/VN/FP/FN. Los ejemplos sintéticos incluidos en el repositorio son deliberadamente pequeños y no permiten afirmar métricas generalizables; por ello, cualquier cifra debe acompañarse del tamaño, el idioma y el origen del conjunto evaluado.",
        ),
        (
            "Se realizó una prueba funcional del análisis",
            "Se realizaron comprobaciones funcionales sobre mensajes sintéticos en español e inglés y sobre un correo legítimo de control. Las comprobaciones verificaron los tres modos, el umbral, la selección por idioma y las explicaciones. La suite de 72 pruebas añade contrato HTTP, límites, caché, artefactos inválidos y entradas malformadas; no se presenta como evaluación estadística de producción.",
        ),
        (
            "Los resultados confirman el diseño",
            "Los resultados confirman el diseño como una base funcional: la heurística aporta señales comprensibles sobre contenido y cabeceras, el clasificador neuronal reconoce patrones aprendidos y el modo combinado equilibra ambas perspectivas. La principal limitación es el tamaño del conjunto sintético de demostración y la ausencia de un corpus de producción representativo, que pueden provocar sobreajuste y métricas poco generalizables. Para una evaluación rigurosa será necesario entrenar con datasets públicos amplios y recientes y comparar con métodos del estado del arte. Aun así, el prototipo demuestra la viabilidad de integrar reglas explicables y aprendizaje supervisado en una aplicación local con varias interfaces.",
        ),
        (
            "El Trabajo Fin de Grado ha alcanzado",
            "El Trabajo Fin de Grado ha alcanzado los objetivos planteados. Se ha estudiado el phishing desde su base psicológica y su evolución reciente, se ha revisado el estado del arte en machine learning y deep learning y se ha desarrollado una aplicación web funcional que combina análisis heurístico explicable con un clasificador neuronal TF-IDF + MLP. La aplicación permite analizar texto pegado, archivos .eml y correos importados mediante Gmail, mientras que el mismo núcleo se reutiliza opcionalmente desde una API HTTP local, una extensión de Gmail y un monitor con Telegram.",
        ),
        (
            "El sexto objetivo, evaluar el comportamiento",
            "El sexto objetivo, evaluar el comportamiento del sistema mediante pruebas unitarias, de integración y funcionales, se aborda con la suite actual de 44 casos, la evaluación del clasificador con un conjunto de prueba independiente cuando se proporciona y la comprobación de mensajes sospechosos y legítimos en español e inglés.",
        ),
        (
            "Entre los logros principales destacan",
            "Entre los logros principales destacan la modularidad del código, la selección del modelo por idioma, la API local compartida, la extensión de Gmail, la integración de Gmail y Telegram y la incorporación de métricas de exactitud, precisión, recall, F1 y accuracy balanceada en la vista de entrenamiento. El prototipo demuestra la viabilidad de un detector de phishing explicable y extensible dentro del alcance de un Trabajo Fin de Grado.",
        ),
        (
            "La aplicación web ofrece tres fuentes de entrada",
            "La aplicación ofrece varias entradas: texto pegado, archivos .eml y correos importados mediante Gmail desde la vista Detección; la extensión de Gmail envía además el mensaje visible al servidor local. La API acepta un objeto JSON con asunto, remitente, cuerpo, enlaces, anclas y cabeceras, y devuelve la misma estructura de riesgo que consume la extensión y otros clientes locales.",
        ),
        (
            "Para cada correo, el sistema devuelve",
            "Para cada correo, el sistema devuelve una puntuación global de riesgo, una clasificación y un desglose de señales. Se revisan autenticación SPF/DKIM/DMARC, coherencia del remitente, urgencia en el asunto, URLs sospechosas, IPs, punycode, acortadores, redirecciones, adjuntos y técnicas de ingeniería social. Las señales activadas se acompañan de explicaciones para interpretar por qué se ha clasificado un mensaje como phishing.",
        ),
        (
            "Un caso de uso habitual:",
            "Un caso de uso habitual consiste en cargar un .eml, pegar el contenido, abrir el correo en Gmail o enviarlo a la API local. El sistema procesa la entrada en el entorno local y muestra las señales detectadas, permitiendo decidir con criterio si es seguro o debe reportarse; el tiempo de respuesta depende del tamaño del mensaje y de si es necesario entrenar un modelo sintético de sustitución.",
        ),
    ]
    for prefix, replacement in replacements:
        replace_prefix(doc, prefix, replacement)

    replace_exact(
        doc,
        "API: Conjunto de operaciones que permite integrar la aplicación con servicios externos, como Gmail o Telegram.",
        "API: Interfaz de operaciones que permite a un cliente local enviar datos al backend mediante un contrato HTTP; Gmail y Telegram son integraciones externas distintas.",
    )
    replace_exact(
        doc,
        "Aplicación web autocontenida: Aplicación que integra la interfaz y la lógica de análisis en un mismo entorno de ejecución.",
        "Aplicación web local: Interfaz Streamlit que integra la presentación y el núcleo de análisis en el mismo entorno; el proyecto también ofrece API y extensión locales opcionales.",
    )


def main() -> None:
    # Compatibilidad: este migrador histórico contenía textos de la antigua
    # arquitectura híbrida. El sincronizador vigente es la única fuente.
    from sync_delivery_docs import main as sync_delivery_docs

    sync_delivery_docs()
    return

    doc = Document(DOC_PATH)
    reconcile_prose(doc)
    rewrite_code_section(
        doc,
        "B.1. Fachada del análisis heurístico (heuristicas.py)",
        "B.2. Servicio común de análisis (analysis_service.py)",
        [
            "heuristicas.py",
            "\"\"\"Fachada de heurísticas para el sistema de detección de phishing.\"\"\"",
            "from .analyzer import PhishingAnalyzer",
            "from .correo import CorreoAnalizado",
            "from .url_utils import extraer_urls",
            "__all__ = [\"analizar_correo\", \"extraer_urls\"]",
            "def analizar_correo(correo):",
            "    \"\"\"Normaliza la entrada y delega el análisis en PhishingAnalyzer.\"\"\"",
            "    correo_analizado = CorreoAnalizado.from_input(correo)",
            "    return PhishingAnalyzer(correo_analizado).analyze()",
        ],
    )
    rewrite_code_section(
        doc,
        "B.2. Servicio común de análisis (analysis_service.py)",
        "B.3. Núcleo del clasificador neuronal (modelo_neural.py)",
        [
            "analysis_service.py (extracto actualizado)",
            "from collections.abc import Callable",
            "from threading import Lock",
            "from typing import Protocol",
            "from .analizador_email import construir_texto_para_analisis",
            "from .heuristicas import analizar_correo",
            "from .idioma import detectar_idioma_correo",
            "from .modelo_neural import ModelStorage, NeuralPhishingClassifier, NeuralPhishingDetector",
            "MODO_HEURISTICO = \"heuristico\"",
            "MODO_NEURAL = \"neural\"",
            "MODO_COMBINADO = \"combinado\"",
            "def cargar_detector_neural(config, idioma=\"es\"):",
            "    ruta_principal = config.model_path_en if idioma == \"en\" else config.model_path_es",
            "    classifier = ModelStorage(ruta_principal).load()",
            "    idioma_esperado = \"english\" if idioma == \"en\" else \"spanish\"",
            "    if classifier is not None and getattr(classifier, \"language\", None) != idioma_esperado:",
            "        classifier = None  # No reutilizar silenciosamente otro idioma.",
            "    if classifier is None:",
            "        classifier = NeuralPhishingClassifier(language=idioma_esperado)",
            "        classifier.fit_default()",
            "    return NeuralPhishingDetector(classifier)",
            "class EmailAnalysisService:",
            "    def __init__(self, config, heuristic_analyzer=None, detector_loader=None, language_detector=None):",
            "        validar_configuracion(config)",
            "        self.config = config",
            "        self._heuristic_analyzer = heuristic_analyzer or analizar_correo",
            "        self._detector_loader = detector_loader or cargar_detector_neural",
            "        self._language_detector = language_detector or detectar_idioma_correo",
            "        self._detectores = {}",
            "        self._detector_lock = Lock()",
            "    # _aplicar_umbral y construir_resultado_combinado validan el contrato y los pesos.",
            "    def analyze(self, datos_email):",
            "        if self.config.mode == MODO_HEURISTICO:",
            "            return _aplicar_umbral(self._heuristic_analyzer(datos_email), self.config.threshold)",
            "        resultado_neural = self._analyze_neural(datos_email)",
            "        if self.config.mode == MODO_NEURAL:",
            "            return _aplicar_umbral(resultado_neural, self.config.threshold)",
            "        resultado_heur = self._heuristic_analyzer(datos_email)",
            "        return construir_resultado_combinado(resultado_heur, resultado_neural, self.config)",
            "    def analyze_all(self, datos_email):",
            "        resultado_heur = _aplicar_umbral(self._heuristic_analyzer(datos_email), self.config.threshold)",
            "        resultado_neural = _aplicar_umbral(self._analyze_neural(datos_email), self.config.threshold)",
            "        resultado_combinado = construir_resultado_combinado(resultado_heur, resultado_neural, self.config)",
            "        return {\"heuristico\": resultado_heur, \"neural\": resultado_neural, \"combinado\": resultado_combinado}",
            "    def _analyze_neural(self, datos_email):",
            "        texto = construir_texto_para_analisis(datos_email)",
            "        idioma = self._language_detector(texto)",
            "        detector = self._detectores.get(idioma)",
            "        if detector is None:",
            "            with self._detector_lock:",
            "                detector = self._detectores.get(idioma)",
            "                if detector is None:",
            "                    detector = self._detector_loader(self.config, idioma)",
            "                    self._detectores[idioma] = detector",
            "        return detector.analyze(texto, datos_email.get(\"from\", \"\"), datos_email.get(\"subject\", \"\"))",
        ],
    )
    rewrite_code_section(
        doc,
        "B.3. Núcleo del clasificador neuronal (modelo_neural.py)",
        "Anexo C: Guía resumida de instalación y uso",
        [
            "modelo_neural.py (extracto actualizado)",
            "class NeuralPhishingClassifier:",
            "    def __init__(self, language=\"spanish\", hiperparametros=None):",
            "        self.language = language",
            "        hp = hiperparametros or cargar_hiperparametros_desde_env()",
            "        self.pipeline = Pipeline([",
            "            (\"vectorizer\", TfidfVectorizer(ngram_range=hp.tfidf_ngram_range, ...)),",
            "            (\"classifier\", MLPClassifier(hidden_layer_sizes=hp.mlp_hidden_layer_sizes, ...)),",
            "        ])",
            "    def fit(self, textos, etiquetas):",
            "        # Valida las etiquetas y entrena una ejecución nueva.",
            "        self.pipeline.fit(textos, etiquetas)",
            "    def predict_proba(self, texts):",
            "        proba = self.pipeline.predict_proba(texts)",
            "        clases = self.pipeline.named_steps[\"classifier\"].classes_.tolist()",
            "        indice_phishing = clases.index(1)",
            "        return [float(fila[indice_phishing]) for fila in proba]",
            "    def __getstate__(self):",
            "        state = self.__dict__.copy()",
            "        state[\"training_texts\"] = []",
            "        state[\"training_labels\"] = []",
            "        return state",
            "class NeuralPhishingDetector:",
            "    def __init__(self, classifier):",
            "        self.classifier = classifier",
            "    def analyze(self, texto, remitente=\"\", subject=\"\"):",
            "        probability = self.classifier.predict_proba([texto])[0]",
            "        return {",
            "            \"is_phishing\": probability >= 0.5,",
            "            \"risk_score\": round(probability * 100, 1),",
            "            \"description\": \"Clasificación basada en una red neuronal entrenada.\",",
            "            \"from\": remitente,",
            "            \"subject\": subject,",
            "        }",
        ],
    )

    insert_before(
        doc,
        "├── tests/                            # Suite unittest",
        [
            "├── backend_server.py # API HTTP local (/health y /analyze)",
            "├── gmail_extension_server.py # Adaptador local de la extensión Gmail",
            "└── sistema_phishing/http_api.py # Transporte HTTP compartido",
        ],
    )
    insert_before(
        doc,
        "├── modelo_neural_es.joblib",
        [
            "├── metrics.py # Métricas de clasificación y matriz de confusión",
        ],
    )
    insert_before(
        doc,
        "# 4. Ejecutar la suite de pruebas",
        [
            "# 3b. Opcional: API HTTP local",
            "$env:PYTHONPATH=\"src\"; python src/backend_server.py",
            "# 3c. Opcional: servidor de la extensión Gmail",
            "$env:PYTHONPATH=\"src\"; python src/gmail_extension_server.py",
        ],
    )
    reorder_code_lines(
        doc,
        [
            "# 3b. Opcional: API HTTP local",
            "$env:PYTHONPATH=\"src\"; python src/backend_server.py",
            "# 3c. Opcional: servidor de la extensión Gmail",
            "$env:PYTHONPATH=\"src\"; python src/gmail_extension_server.py",
        ],
    )
    replace_prefix(
        doc,
        "El sistema permite entrenar modelos en español",
        "El sistema permite entrenar modelos en español e inglés, utilizando stopwords específicas para cada idioma. La aplicación de entrenamiento acepta uno o varios archivos CSV, permite configurar las columnas de texto, asunto, cuerpo y etiqueta, y admite formatos habituales de datasets públicos. Durante la evaluación se muestran la matriz de confusión, accuracy, precisión, recall, F1 y accuracy balanceada. También es posible entrenar hasta tres redes en memoria, compararlas sobre un conjunto de prueba independiente y combinar varios CSV de entrenamiento.",
    )
    replace_prefix(
        doc,
        "Este anexo resume los pasos necesarios",
        "Este anexo resume los pasos necesarios para ejecutar la aplicación web y sus adaptadores locales. Streamlit se inicia con src/app.py; la API HTTP local escucha por defecto en 127.0.0.1:8766 y expone /health y /analyze, mientras que el servidor de la extensión Gmail utiliza 127.0.0.1:8765. La guía ampliada, la configuración de credenciales y la solución de problemas se mantienen en el archivo README del repositorio.",
    )
    replace_prefix(
        doc,
        "☐ Evaluación con separación de entrenamiento",
        "☐ Evaluación con un CSV de prueba independiente y métricas documentadas.",
    )
    replace_exact(
        doc,
        "├── metrics.py # Métricas de clasificación y matriz de confusión",
        "",
    )
    insert_before(
        doc,
        "│   ├── config_app.py",
        [
            "│   ├── backend_server.py              # API HTTP local",
            "│   ├── gmail_extension_server.py      # Adaptador de la extensión Gmail",
        ],
    )
    insert_before(
        doc,
        "│       ├── analyzer.py",
        [
            "│       ├── http_api.py                # Transporte HTTP y validación",
        ],
    )
    insert_before(
        doc,
        "│       ├── modelo_neural.py",
        [
            "│       ├── metrics.py                  # Métricas y matriz de confusión",
        ],
    )
    rewrite_code_section(
        doc,
        "Estructura de directorios del repositorio",
        "Anexo B: Fragmentos de código fuente",
        [
            "TFG/",
            "├── src/",
            "│   ├── app.py                       # Entrada principal de Streamlit",
            "│   ├── backend_server.py             # API HTTP local",
            "│   ├── config_app.py                 # Configuración de Gmail, Telegram y modelos",
            "│   ├── detect_app.py                 # Detección desde texto, EML y Gmail",
            "│   ├── gmail_extension_server.py     # Adaptador de la extensión Gmail",
            "│   ├── monitor_app.py                # Vista de monitorización de Gmail",
            "│   ├── monitor_gmail.py              # Monitorización periódica opcional",
            "│   ├── train_app.py                  # Entrenamiento y evaluación",
            "│   ├── ui_components.py              # Componentes visuales compartidos",
            "│   └── sistema_phishing/",
            "│       ├── analizador_email.py       # Parseo y normalización de correos",
            "│       ├── analysis_service.py       # Coordinación del análisis local",
            "│       ├── analyzer.py               # Orquestador heurístico",
            "│       ├── backend_service.py        # Compatibilidad con el backend",
            "│       ├── configuracion.py           # Configuración del dominio",
            "│       ├── content_signals.py        # Señales de texto y adjuntos",
            "│       ├── correo.py                 # Representación interna común",
            "│       ├── dataset.py                # Normalización de CSV",
            "│       ├── env_loader.py             # Variables locales de entorno",
            "│       ├── explanations.py           # Explicaciones del riesgo",
            "│       ├── gmail_client.py            # Integración OAuth con Gmail",
            "│       ├── gmail_monitor.py           # Lógica de monitorización",
            "│       ├── header_signals.py          # Cabeceras y autenticación",
            "│       ├── heuristicas.py             # Fachada heurística",
            "│       ├── html_signals.py            # Señales HTML",
            "│       ├── http_api.py                # Transporte HTTP y validación",
            "│       ├── idioma.py                  # Detección de idioma",
            "│       ├── metrics.py                 # Métricas y matriz de confusión",
            "│       ├── modelo_neural.py           # Pipeline TF-IDF + MLP",
            "│       ├── neural.py                  # Fachada neuronal",
            "│       ├── scorer.py                  # Cálculo de puntuación",
            "│       ├── signal_builder.py          # Construcción de señales",
            "│       ├── signals.py                 # Utilidades de señales",
            "│       ├── telegram_notifier.py       # Alertas por Telegram",
            "│       └── url_utils.py               # Análisis de URLs",
            "├── tests/                            # Suite unittest",
            "├── scripts/                          # Automatización y experimentos",
            "├── requirements.txt",
            "├── credentials.example.json",
            "└── .env.example",
        ],
    )
    compact_empty_code_paragraphs(
        doc,
        "Estructura de directorios del repositorio",
        "Anexo B: Fragmentos de código fuente",
    )
    compact_empty_code_paragraphs(
        doc,
        "B.1. Fachada del análisis heurístico (heuristicas.py)",
        "B.2. Servicio común de análisis (analysis_service.py)",
    )
    compact_empty_code_paragraphs(
        doc,
        "B.2. Servicio común de análisis (analysis_service.py)",
        "B.3. Núcleo del clasificador neuronal (modelo_neural.py)",
    )
    compact_empty_code_paragraphs(
        doc,
        "B.3. Núcleo del clasificador neuronal (modelo_neural.py)",
        "Anexo C: Guía resumida de instalación y uso",
    )
    doc.save(DOC_PATH)


if __name__ == "__main__":
    main()
