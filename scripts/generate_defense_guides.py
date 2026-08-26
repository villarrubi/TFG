"""Genera las tres guías locales de defensa del TFG.

Las guías no forman parte del producto desplegable y se ignoran desde Git.
Este script es deliberadamente determinista para poder regenerarlas al cambiar
el flujo o las decisiones tecnológicas del proyecto.
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
MUTED = "64748B"
TABLE_FILL = "E8EEF5"
CALLOUT_FILL = "F4F6F9"
WHITE = "FFFFFF"
TEXT = "1F2937"
TABLE_WIDTH = 9360
TABLE_INDENT = 120


def _set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.first_child_found_in("w:shd")
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_width(cell, width):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.first_child_found_in("w:tcW")
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(width))
    tc_w.set(qn("w:type"), "dxa")


def _set_table_geometry(table, widths):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.first_child_found_in("w:tblInd")
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT))
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            _set_cell_width(cell, widths[index])
            _set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP


def _repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def _set_run_font(run, *, size=11, color=TEXT, bold=False, italic=False):
    run.font.name = "Calibri"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Calibri")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Calibri")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.bold = bold
    run.italic = italic


def _set_style(style, *, size=11, color=TEXT, bold=False, before=0, after=6, line=1.25):
    style.font.name = "Calibri"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string(color)
    style.font.bold = bold
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)
    style.paragraph_format.line_spacing = line


def _add_page_field(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, separate, text, end))


def _setup_document(title):
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    _set_style(doc.styles["Normal"], after=6, line=1.25)
    _set_style(doc.styles["Title"], size=30, color="203748", bold=True, after=8, line=1.0)
    _set_style(doc.styles["Subtitle"], size=15, color="2B5163", after=18, line=1.1)
    _set_style(doc.styles["Heading 1"], size=16, color=BLUE, bold=True, before=18, after=10, line=1.1)
    _set_style(doc.styles["Heading 2"], size=13, color=BLUE, bold=True, before=14, after=7, line=1.1)
    _set_style(doc.styles["Heading 3"], size=12, color=DARK_BLUE, bold=True, before=10, after=5, line=1.1)
    _set_style(doc.styles["List Bullet"], after=4, line=1.25)
    _set_style(doc.styles["List Number"], after=4, line=1.25)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _set_run_font(header.add_run("TFG · Guía de defensa"), size=9, color=MUTED)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _set_run_font(footer.add_run("Página "), size=9, color=MUTED)
    _add_page_field(footer)
    doc.core_properties.title = title
    doc.core_properties.author = "Proyecto TFG"
    doc.core_properties.subject = "Preparación de defensa del TFG"
    return doc


def _cover(doc, kicker, title, subtitle):
    for _ in range(5):
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(8)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    _set_run_font(p.add_run(kicker.upper()), size=10, color="B4862C", bold=True)
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run_font(p.add_run(title), size=30, color="203748", bold=True)
    p = doc.add_paragraph(style="Subtitle")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run_font(p.add_run(subtitle), size=15, color="2B5163")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(24)
    _set_run_font(p.add_run("Proyecto TFG · versión alineada con el código actual"), size=10, color=MUTED, italic=True)
    doc.add_page_break()


def _heading(doc, text, level=1):
    return doc.add_paragraph(text, style=f"Heading {level}")


def _para(doc, text, *, bold_prefix=None):
    p = doc.add_paragraph()
    if bold_prefix and text.startswith(bold_prefix):
        _set_run_font(p.add_run(bold_prefix), bold=True)
        _set_run_font(p.add_run(text[len(bold_prefix):]))
    else:
        _set_run_font(p.add_run(text))
    return p


def _bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    _set_run_font(p.add_run(text))
    return p


def _number(doc, text):
    p = doc.add_paragraph(style="List Number")
    _set_run_font(p.add_run(text))
    return p


def _callout(doc, label, text, fill=CALLOUT_FILL):
    table = doc.add_table(rows=1, cols=1)
    _set_table_geometry(table, [TABLE_WIDTH])
    _repeat_header(table.rows[0])
    cell = table.cell(0, 0)
    _set_cell_shading(cell, fill)
    p = cell.paragraphs[0]
    _set_run_font(p.add_run(f"{label}: "), bold=True, color=DARK_BLUE)
    _set_run_font(p.add_run(text))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def _table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    _set_table_geometry(table, widths)
    header = table.rows[0]
    _repeat_header(header)
    for index, value in enumerate(headers):
        cell = header.cells[index]
        _set_cell_shading(cell, TABLE_FILL)
        p = cell.paragraphs[0]
        _set_run_font(p.add_run(value), bold=True, color=DARK_BLUE)
    for row_data in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row_data):
            p = cells[index].paragraphs[0]
            _set_run_font(p.add_run(str(value)))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def flujo():
    doc = _setup_document("Flujo y funcionamiento · TFG Phishing")
    _cover(doc, "Guía 01 · mapa del sistema", "Flujo y funcionamiento", "Qué ocurre desde que entra un correo hasta que se explica el riesgo")
    _heading(doc, "1. Idea general", 1)
    _para(doc, "El sistema recibe un correo desde cuatro entradas: texto pegado o fichero EML en Streamlit, mensaje leído desde Gmail, correo visible en la extensión de Chrome o mensaje obtenido por el monitor periódico. Todas las entradas convergen en una representación normalizada y pasan por el mismo servicio de análisis.")
    _callout(doc, "Frase para la defensa", "No hay cuatro detectores diferentes: hay varios adaptadores de entrada y un caso de uso central que decide el modo, selecciona el modelo lingüístico y construye la explicación.")
    _heading(doc, "2. Flujo completo", 1)
    for text in [
        "Entrada y límites: se recibe texto, JSON o bytes EML; el parser rechaza entradas vacías y mensajes mayores de 10 MiB.",
        "Normalización: se extraen remitente, asunto, cuerpo, HTML, cabeceras completas, URLs, anclas y adjuntos.",
        "Señales: se revisan autenticación, coherencia de dominios, URLs, punycode, acortadores, HTML, formularios, lenguaje urgente y adjuntos.",
        "Puntuación heurística: RiskScorer pondera las señales activas y produce un riesgo de 0 a 100; ExplanationBuilder conserva el motivo.",
        "Idioma y modelo: EmailAnalysisService detecta español o inglés por mensaje y reutiliza un detector neuronal cacheado por idioma.",
        "Decisión: el modo combinado calcula una media ponderada; el umbral configurado se aplica de forma uniforme en heurístico, neuronal y combinado.",
        "Salida: se devuelve clasificación, puntuación, explicación, señales y artefactos útiles para UI, API, monitor y Telegram.",
    ]:
        _number(doc, text)
    _heading(doc, "3. Piezas y responsabilidades", 1)
    _table(doc, ["Capa", "Módulo", "Responsabilidad", "Resultado"], [
        ("Entrada", "analizador_email.py", "Parseo MIME seguro y extracción de partes", "Correo normalizado"),
        ("Dominio", "correo.py", "Contrato común para texto, diccionario o EML", "CorreoAnalizado"),
        ("Señales", "header_signals, url_utils, html_signals, content_signals", "Reglas pequeñas y comprobables", "Diccionario de señales"),
        ("Orquestación", "analysis_service.py", "Modo, idioma, cacheado y umbral", "Resultado único"),
        ("ML", "modelo_neural.py", "TF-IDF, MLP, entrenamiento y persistencia", "Probabilidad phishing"),
        ("Presentación", "app.py, monitor, extensión, API", "Adaptación al canal", "UI, JSON o alerta"),
    ], [1500, 2350, 3150, 2360])
    _heading(doc, "4. Cómo se analiza un EML", 1)
    _para(doc, "El parser usa email.parser.BytesParser con una política MIME estándar. Conserva todas las cabeceras repetidas, no solo la última, y serializa las cabeceras originales junto al cuerpo para que SPF, DKIM, DMARC, Received, Return-Path y Message-ID sean visibles a las reglas.")
    for text in [
        "Texto plano: se decodifica respetando el charset declarado y se conserva como cuerpo analizable.",
        "HTML: se guarda separado para revisar formularios, meta refresh, iframes, base href y javascript/data URLs.",
        "Adjuntos: se anotan nombre y tipo sin ejecutar ni abrir contenido potencialmente peligroso.",
        "URLs: se deduplican, se limpian de puntuación y se extraen también de enlaces HTML.",
    ]:
        _bullet(doc, text)
    _heading(doc, "5. Monitor y persistencia", 1)
    _para(doc, "El monitor consulta Gmail, carga el conjunto de IDs vistos y procesa solo mensajes nuevos. La instancia de EmailAnalysisService se crea una vez por lote, de modo que los modelos no se recargan para cada correo. El estado se escribe después de cada mensaje completado mediante fichero temporal y os.replace.")
    _para(doc, "Si un EML está corrupto o falla una alerta de Telegram, ese mensaje queda reportado con error y el resto del lote continúa. Un fallo de entrada no se convierte en una caída global del proceso.")
    _heading(doc, "6. API y extensión", 1)
    _table(doc, ["Endpoint", "Entrada", "Respuesta", "Controles"], [
        ("GET /health", "Sin cuerpo", "Estado y disponibilidad sin rutas locales", "Sin información sensible"),
        ("POST /analyze", "JSON de hasta 1 MiB", "Riesgo, etiqueta y explicación", "Content-Type, tamaño y CORS"),
    ], [1800, 2500, 2800, 2260])
    _para(doc, "La extensión de Gmail no ejecuta Python dentro del navegador: el content script recoge el correo visible y lo envía al servidor local del puerto 8765. El servidor y el backend general comparten la misma infraestructura HTTP y el mismo servicio de análisis.")
    _heading(doc, "7. Ejemplo de extremo a extremo", 1)
    for index, text in enumerate([
        "El usuario abre un correo con asunto urgente y un enlace que aparenta ser de una marca conocida.",
        "El adaptador extrae From, Subject, cuerpo, anclas y URL.",
        "Las reglas detectan urgencia, dominio externo, anchor distinto y posible incoherencia de cabeceras.",
        "El modelo neuronal calcula una probabilidad sobre el texto completo.",
        "El modo combinado pondera ambos resultados y aplica el umbral; la explicación muestra qué señales activaron el riesgo.",
        "La UI pinta la tarjeta, la extensión la inserta en Gmail y el monitor podría notificar por Telegram.",
    ], 1):
        _para(doc, f"{index}. {text}")
    _heading(doc, "8. Límites que conviene decir", 1)
    _bullet(doc, "La lista de dominios y señales es local; no se afirma que exista reputación online en tiempo real.")
    _bullet(doc, "El análisis es apoyo a la decisión, no sustituto de una pasarela antispam ni garantía absoluta.")
    _bullet(doc, "El MLP necesita datos representativos y evaluación separada; una accuracy de entrenamiento no demuestra generalización.")
    _para(doc, "La suite automatizada actual tiene 47 pruebas y el benchmark de arranque se repite en procesos limpios; estas comprobaciones validan el comportamiento y el rendimiento del prototipo, no su eficacia estadística en producción.")
    doc.save(ROOT / "Guia_01_Flujo_y_funcionamiento.docx")


def tecnologias():
    doc = _setup_document("Tecnologías y decisiones · TFG Phishing")
    _cover(doc, "Guía 02 · decisiones técnicas", "Tecnologías y decisiones", "Cómo funciona cada elección y cómo justificarla frente a alternativas")
    _heading(doc, "1. Criterio de selección", 1)
    _para(doc, "La arquitectura prioriza reproducibilidad local, facilidad de defensa, separación de responsabilidades y coste operativo bajo. Las decisiones no intentan convertir el TFG en un servicio de producción multiusuario: delimitan un detector demostrable, auditable y extensible.")
    _heading(doc, "2. Comparativa de tecnologías", 1)
    _table(doc, ["Tecnología", "Cómo se usa", "Por qué se elige", "Alternativa y límite"], [
        ("Python", "Integra parser, reglas, ML, API y automatizaciones", "Ecosistema científico, lectura clara y buena trazabilidad", "Java/Node serían válidos; añadirían complejidad para este alcance"),
        ("Streamlit", "Construye las vistas de detección, configuración y entrenamiento", "Permite validar el flujo sin frontend separado", "React + FastAPI daría más control de despliegue, pero exigiría dos stacks"),
        ("scikit-learn", "TF-IDF vectoriza y MLPClassifier clasifica", "Pipeline reproducible, API madura y métricas estándar", "TensorFlow sería más flexible para deep learning, pero sobredimensionado para texto tabular"),
        ("TF-IDF", "Convierte palabras y bigramas en variables", "Explicable, rápido y adecuado para corpus moderados", "Transformers mejorarían contexto, con más coste y menor explicabilidad local"),
        ("email estándar", "Parsea MIME y cabeceras EML", "No añade dependencia para la parte esencial del formato", "Librerías externas pueden aportar atajos, pero no son necesarias"),
        ("BeautifulSoup", "Inspecciona HTML y formularios", "Tolera HTML imperfecto de correos", "Parser regex puro sería frágil; un navegador sería inseguro e innecesario"),
        ("Gmail API + OAuth", "Obtiene mensajes con consentimiento del usuario", "Permisos oficiales y flujo revocable", "IMAP sería más genérico, pero no aporta el mismo control API"),
        ("HTTP stdlib", "Expone /health y /analyze localmente", "Cero framework extra, contrato pequeño y fácil de auditar", "FastAPI facilitaría OpenAPI y validación; no es necesario para una API local"),
        ("joblib", "Persiste pipeline TF-IDF + MLP", "Guarda vectorizador y modelo como una unidad", "ONNX sería más portable; exige conversión y no elimina el requisito de confiar en artefactos"),
        ("unittest + Ruff", "Prueba comportamiento y calidad estática", "Incluidos en Python y rápidos en CI/local", "pytest aporta fixtures más ricas; el conjunto actual es suficiente y directo"),
    ], [1500, 2500, 2800, 2560])
    _heading(doc, "3. Por qué dos modelos lingüísticos", 1)
    _para(doc, "El detector identifica idioma por mensaje, no por sesión. Mantiene un modelo español y otro inglés porque las palabras, stopwords y corpus tienen distribuciones distintas. EmailAnalysisService cachea un detector por idioma para combinar corrección con rendimiento.")
    _callout(doc, "Respuesta breve", "La alternativa de un único modelo multilingüe simplificaría ficheros, pero mezclaría vocabularios y haría más difícil justificar qué datos explican cada predicción.")
    _heading(doc, "4. SOLID aplicado", 1)
    _table(doc, ["Principio", "Aplicación en el código", "Beneficio demostrable"], [
        ("Responsabilidad única", "Parser, señales, scorer, explicaciones, ML, monitor y transporte están separados", "Un cambio en URLs no obliga a tocar Gmail o Streamlit"),
        ("Abierto/cerrado", "EmailAnalysisService recibe analyzer, detector loader y detector de idioma inyectables", "Se prueban estrategias y se añaden modelos sin reescribir el coordinador"),
        ("Sustitución", "Los consumidores dependen del contrato de servicio y de MonitorConfig", "API, extensión y monitor consumen el mismo caso de uso"),
        ("Segregación", "El almacenamiento, el análisis y el transporte tienen superficies pequeñas", "Cada prueba necesita solo la interfaz que utiliza"),
        ("Inversión", "NeuralModelTrainer depende de ModelStorage, no de una ruta fija", "Facilita memoria, disco y dobles de prueba"),
    ], [1700, 4300, 3360])
    _heading(doc, "5. Decisiones de seguridad", 1)
    for text in [
        "El parser limita EML a 10 MiB y la API a 1 MiB para evitar cargas accidentales desproporcionadas.",
        "La API no acepta CORS *; permite Gmail y orígenes chrome-extension://, y no devuelve trazas internas.",
        "El modelo no ejecuta archivos adjuntos; solo registra metadatos y señales.",
        "Los nuevos joblib no conservan textos brutos de entrenamiento. Los modelos antiguos se sanean al cargarse y guardarse con el formato actual.",
        "Credenciales, tokens, estados y documentación privada se mantienen fuera del índice Git mediante .gitignore.",
    ]:
        _bullet(doc, text)
    _heading(doc, "6. Reproducibilidad y evaluación", 1)
    _para(doc, "Los hiperparámetros se concentran en HiperparametrosModelo y pueden leerse desde .env.local. Cada ejecución de entrenamiento comienza con los CSV seleccionados, registra procedencia y estadísticas, y no mezcla silenciosamente sesiones previas. La evaluación usa un CSV separado y comunica precision, recall, F1, accuracy balanceada y matriz de confusión.")
    _para(doc, "El benchmark reproducible separa arranque e inferencia. La carga diferida redujo la importación fría de heurísticas de 1098,5 ms a 37,0 ms y el arranque de la aplicación de 1326,6 ms a 315,1 ms, mientras que la inferencia se mantuvo estable dentro de una variación de ±3 %.")
    _para(doc, "La suite automatizada actual reúne 47 pruebas con unittest; las advertencias de convergencia pertenecen a dos pruebas neuronales rápidas con pocas iteraciones y no indican un fallo funcional.")
    _heading(doc, "7. Diferencias con la propuesta inicial", 1)
    _table(doc, ["Propuesta", "Implementación actual", "Cómo explicarlo"], [
        ("TensorFlow", "scikit-learn MLP", "Se eligió una red suficiente para el corpus y más reproducible/ligera en el entorno académico"),
        ("Blacklists/reputación", "Señales locales de dominio, URL, punycode y acortadores", "Se evita depender de red externa y se mantiene privacidad; reputación online queda como extensión"),
        ("Certificados", "No se inspecciona TLS desde el correo", "El EML no prueba por sí mismo el certificado del destino; se prioriza análisis estático seguro"),
        ("Interfaz simple", "Streamlit más API y extensión opcionales", "La interfaz base sigue siendo simple; las integraciones amplían la demostración sin cambiar el núcleo"),
    ], [2400, 3000, 3960])
    _heading(doc, "8. Qué no prometer", 1)
    _bullet(doc, "No decir que se consulta una blacklist online si no se ha configurado una fuente externa.")
    _bullet(doc, "No presentar el accuracy de entrenamiento como precisión en producción.")
    _bullet(doc, "No llamar a la extensión un producto publicado: actualmente se carga en modo desarrollador y usa un servidor local.")
    doc.save(ROOT / "Guia_02_Tecnologias_y_decisiones.docx")


def guion():
    doc = _setup_document("Guion de defensa · TFG Phishing")
    _cover(doc, "Guía 03 · exposición oral", "Guion de defensa", "Qué decir, qué enseñar y cómo responder preguntas sin sobreprometer")
    _heading(doc, "1. Marco de tiempo", 1)
    _callout(doc, "Regla práctica", "La regulación pública UEMC del TFG contempla una exposición de hasta 20 minutos y un turno posterior de preguntas; confirma siempre el tiempo exacto indicado por tu centro y convocatoria.")
    _para(doc, "Referencia para preparar la defensa: Reglamento UEMC de TFG 4/2022 (documento institucional) y la ficha pública de la asignatura de Trabajo Fin de Grado. La memoria y la defensa deben contar la misma historia: problema, objetivos, método, evidencia y límites.")
    _heading(doc, "2. Estructura recomendada de 20 minutos", 1)
    _table(doc, ["Tiempo", "Bloque", "Mensaje que debe quedar"], [
        ("0:00–1:00", "Apertura", "Qué problema resuelvo y qué entrego"),
        ("1:00–3:00", "Motivación y objetivos", "El phishing combina señales técnicas y lingüísticas; se necesita apoyo explicable"),
        ("3:00–5:00", "Alcance y requisitos", "Texto/EML, heurística, ML, explicación, Gmail, evaluación y límites"),
        ("5:00–9:00", "Arquitectura y flujo", "Entradas -> normalización -> señales/modelo -> decisión -> explicación"),
        ("9:00–12:00", "Tecnologías", "Por qué Python, Streamlit, scikit-learn, Gmail API y servidor local"),
        ("12:00–15:00", "Demostración", "Un correo sospechoso, señales activas y resultado combinado"),
        ("15:00–17:00", "Pruebas y resultados", "47 pruebas, benchmark, matriz de confusión y métricas de un CSV de prueba"),
        ("17:00–19:00", "Limitaciones y futuro", "Qué no hace hoy y qué ampliaría con evidencia"),
        ("19:00–20:00", "Cierre", "Aportación, mantenibilidad y conclusión"),
    ], [1500, 2500, 5360])
    _heading(doc, "3. Texto de apertura", 1)
    _para(doc, "Buenos días. Mi TFG presenta un sistema local de apoyo a la detección de phishing en correos electrónicos. La idea central es combinar señales que una persona puede inspeccionar —cabeceras, autenticación, dominios, URLs, HTML y lenguaje— con un clasificador TF-IDF más MLP. El resultado no es solo una etiqueta: es una puntuación y una explicación que permiten revisar por qué el sistema ha elevado el riesgo.")
    _para(doc, "He separado las entradas del núcleo de análisis. Por eso el mismo caso de uso sirve para Streamlit, Gmail, una extensión de navegador, una API local y un monitor con Telegram. Esta separación facilita probar cada pieza, cambiar el modelo y mantener el sistema reproducible.")
    _heading(doc, "4. Qué enseñar en la demo", 1)
    for text in [
        "Abrir la aplicación y mostrar el modo combinado y el umbral configurado.",
        "Pegar o cargar un EML de ejemplo controlado, evitando enseñar credenciales o datos personales.",
        "Señalar la puntuación, las señales activas, la URL sospechosa y la explicación generada.",
        "Cambiar a modo heurístico para demostrar que el resultado puede auditarse sin modelo.",
        "Mostrar la pestaña de evaluación con un CSV de prueba separado y las métricas, no solo accuracy.",
        "Si el tiempo lo permite, enseñar /health o la extensión local como integración opcional.",
    ]:
        _number(doc, text)
    _callout(doc, "Plan B", "Lleva capturas o una salida guardada. Si Gmail, OAuth o el servidor local fallan durante la defensa, explica el flujo y demuestra la parte offline, que es el núcleo evaluable.")
    _heading(doc, "5. Cómo explicar los resultados", 1)
    _para(doc, "La matriz de confusión separa VP, VN, FP y FN. En phishing, un FN puede ser especialmente costoso porque un correo malicioso se presenta como legítimo; por eso no basta con optimizar accuracy y se muestran precision, recall, F1 y accuracy balanceada. Aclara siempre si una cifra procede del entrenamiento o de un CSV de prueba independiente.")
    _para(doc, "En rendimiento, presenta solo mejoras medidas: la importación fría de heurísticas bajó un 96,6 % y el arranque de la aplicación un 76,2 %. Las rutas de inferencia variaron menos de un 3 %, por lo que no se atribuye una mejora que no esté respaldada por la medición.")
    _heading(doc, "6. Preguntas previsibles y respuestas", 1)
    _table(doc, ["Pregunta", "Respuesta breve y defendible"], [
        ("¿Por qué no usar deep learning más grande?", "El corpus y el alcance no lo justificaban. TF-IDF + MLP ofrece rapidez, reproducibilidad y una línea base explicable; la arquitectura permite sustituir el modelo."),
        ("¿Qué ocurre con un correo en inglés?", "El idioma se detecta por mensaje y se cachea un modelo específico por idioma; no se fija el idioma para toda la sesión."),
        ("¿Cómo evitas falsos positivos?", "Se combinan señales, pesos y umbral configurables; se muestran FP/FN y el usuario conserva la explicación para revisar el caso."),
        ("¿Consulta una blacklist externa?", "No en la versión actual. Hay comprobaciones locales de dominios, URLs, punycode y acortadores; una reputación online sería una ampliación con dependencia y privacidad adicionales."),
        ("¿Es seguro cargar joblib?", "Solo se cargan artefactos propios y verificados, porque joblib usa deserialización Python. No se deben aceptar modelos arbitrarios."),
        ("¿Qué pasa si Gmail está caído?", "La detección manual y los tests offline siguen funcionando; la integración externa se trata como adaptador y muestra un error controlado."),
        ("¿Por qué no guardas todos los correos de entrenamiento?", "Para reducir exposición de datos y hacer el artefacto más limpio. Se conservan procedencia y estadísticas, no el texto bruto."),
        ("¿Qué falta para producción?", "Autenticación del backend, despliegue gestionado, monitorización, dataset más representativo, calibración y pruebas externas; el TFG delimita explícitamente ese alcance."),
    ], [3300, 6060])
    _heading(doc, "7. Cierre", 1)
    _para(doc, "La aportación principal es una solución completa y mantenible: parser seguro, señales especializadas, modelo neuronal reproducible, explicación, evaluación y varias integraciones sobre un mismo núcleo. El sistema no pretende sustituir a un producto antispam; demuestra cómo diseñar, probar y comunicar un detector local de phishing con decisiones técnicas justificadas.")
    _heading(doc, "8. Checklist de la víspera", 1)
    for text in [
        "Ejecutar la suite automatizada completa y guardar la salida.",
        "Comprobar que la demo funciona sin credenciales reales y que los modelos están en la raíz.",
        "Preparar un CSV de prueba pequeño con ambas clases y métricas entendibles.",
        "Ensayar el guion con cronómetro y dejar dos minutos de margen.",
        "Memorizar tres límites: sin reputación online, extensión local y necesidad de datos representativos.",
        "Llevar capturas del flujo y de la matriz de confusión como respaldo.",
    ]:
        _bullet(doc, text)
    doc.save(ROOT / "Guia_03_Guion_defensa.docx")


if __name__ == "__main__":
    flujo()
    tecnologias()
    guion()
