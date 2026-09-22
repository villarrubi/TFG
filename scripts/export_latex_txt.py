"""Exporta la memoria DOCX a una fuente LaTeX guardada como archivo TXT.

El resultado puede copiarse a Overleaf o renombrarse a ``main.tex``. Las
imágenes se extraen a ``latex_figures/`` con nombres derivados de sus pies.
"""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = REPO_ROOT / "TFG.docx"
OUTPUT_PATH = REPO_ROOT / "TFG_para_LaTeX.txt"
ZIP_PATH = REPO_ROOT / "TFG_LaTeX.zip"
FIGURES_DIR = REPO_ROOT / "latex_figures"

URL_PATTERN = re.compile(r"https?://[^\s]+")
FIGURE_PATTERN = re.compile(r"^Figura\s+(\d+\.\d+):\s*(.+)$", re.DOTALL)
TABLE_PATTERN = re.compile(r"^Tabla\s+(\d+\.\d+):?\s*(.+)$", re.DOTALL)
CHAPTER_PATTERN = re.compile(r"^Capítulo\s+\d+\.\s*(.+)$", re.DOTALL)
ANNEX_PATTERN = re.compile(r"^Anexo\s+[A-Z]:\s*(.+)$", re.DOTALL)
ANNEX_SECTION_PATTERN = re.compile(r"^[A-Z]\.\d+\.\s*(.+)$", re.DOTALL)


def normalize(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def escape_plain(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    latex_unicode = {
        "\u00a0": " ",
        "\u2011": "-",
        "\u2013": "--",
        "\u2014": "---",
        "\u2192": r"\(\rightarrow\)",
        "\u2264": r"\(\leq\)",
        "\u2265": r"\(\geq\)",
        "\u2248": r"\(\approx\)",
        "\u0430": r"\textit{a cirílica}",
    }
    return "".join(
        latex_unicode.get(char, replacements.get(char, char)) for char in text
    )


def latex_text(text: str) -> str:
    """Escapa texto normal y conserva las URL mediante el comando LaTeX de URL."""

    output: list[str] = []
    position = 0
    for match in URL_PATTERN.finditer(text):
        output.append(escape_plain(text[position : match.start()]))
        url = match.group(0)
        suffix = ""
        while url and url[-1] in ".,;":
            suffix = url[-1] + suffix
            url = url[:-1]
        output.append(r"\url{" + url.replace("}", r"\}") + "}")
        output.append(escape_plain(suffix))
        position = match.end()
    output.append(escape_plain(text[position:]))
    return "".join(output).replace("\n", r"\\ ")


def paragraph_latex(paragraph: Paragraph) -> str:
    if not paragraph.runs:
        return latex_text(paragraph.text)

    parts: list[str] = []
    for run in paragraph.runs:
        if not run.text:
            continue
        value = latex_text(run.text)
        if run.bold:
            value = r"\textbf{" + value + "}"
        if run.italic:
            value = r"\emph{" + value + "}"
        parts.append(value)
    rendered = "".join(parts)
    return rendered or latex_text(paragraph.text)


def strip_caption_source(caption: str) -> tuple[str, str | None]:
    parts = re.split(r"\s+Fuente:\s*", caption, maxsplit=1)
    if len(parts) == 2:
        return parts[0].rstrip(), parts[1].strip()
    return caption.rstrip(), None


def numbering_formats(document: Document) -> dict[str, str]:
    root = document.part.numbering_part.element
    abstract_numbers = {
        element.get(qn("w:abstractNumId")): element
        for element in root.findall(qn("w:abstractNum"))
    }
    formats: dict[str, str] = {}
    for number in root.findall(qn("w:num")):
        number_id = number.get(qn("w:numId"))
        abstract_id = number.find(qn("w:abstractNumId")).get(qn("w:val"))
        level = abstract_numbers[abstract_id].find(qn("w:lvl"))
        formats[number_id] = level.find(qn("w:numFmt")).get(qn("w:val"))
    return formats


class LatexExporter:
    def __init__(self, document: Document) -> None:
        self.document = document
        self.lines: list[str] = []
        self.number_formats = numbering_formats(document)
        self.started = False
        self.skip_static_indices = False
        self.indices_emitted = False
        self.list_environment: str | None = None
        self.code_open = False
        self.description_open = False
        self.description_mode: str | None = None
        self.bibliography_open = False
        self.bibliography_index = 0
        self.in_appendices = False
        self.pending_figure_caption: str | None = None
        self.pending_image_id: str | None = None
        self.pending_table_caption: str | None = None
        self.figure_count = 0
        self.table_count = 0

    def add(self, *values: str) -> None:
        self.lines.extend(values)

    def close_list(self) -> None:
        if self.list_environment:
            self.add(rf"\end{{{self.list_environment}}}", "")
            self.list_environment = None

    def close_code(self) -> None:
        if self.code_open:
            self.add(r"\end{lstlisting}", "")
            self.code_open = False

    def close_description(self) -> None:
        if self.description_open:
            self.add(r"\end{description}", "")
            self.description_open = False
            self.description_mode = None

    def close_bibliography(self) -> None:
        if self.bibliography_open:
            self.add(r"\end{thebibliography}", "")
            self.bibliography_open = False

    def close_flow_environments(self) -> None:
        self.close_list()
        self.close_code()

    def emit_indices(self) -> None:
        if self.indices_emitted:
            return
        self.add(
            r"\clearpage",
            r"\tableofcontents",
            r"\clearpage",
            r"\listoffigures",
            r"\clearpage",
            r"\listoftables",
            r"\clearpage",
            "",
        )
        self.indices_emitted = True

    def image_name(self, relationship_id: str, caption: str) -> str:
        match = FIGURE_PATTERN.match(normalize(caption))
        number = match.group(1).replace(".", "_") if match else str(self.figure_count + 1)
        relationship = self.document.part.rels[relationship_id]
        extension = Path(relationship.target_ref).suffix.lower() or ".png"
        return f"figura_{number}{extension}"

    def emit_figure(self, relationship_id: str, caption: str) -> None:
        self.close_flow_environments()
        self.figure_count += 1
        match = FIGURE_PATTERN.match(normalize(caption))
        number = match.group(1) if match else str(self.figure_count)
        caption_text = match.group(2) if match else normalize(caption)
        short_caption, source = strip_caption_source(caption_text)
        filename = self.image_name(relationship_id, caption)
        relationship = self.document.part.rels[relationship_id]
        (FIGURES_DIR / filename).write_bytes(relationship.target_part.blob)

        full_caption = short_caption
        if source:
            full_caption = short_caption.rstrip(". ") + ". Fuente: " + source
        self.add(
            r"\begin{figure}[H]",
            r"  \centering",
            rf"  \includegraphics[width=0.92\textwidth]{{latex_figures/{filename}}}",
            "  "
            + r"\caption["
            + latex_text(short_caption)
            + "]{"
            + latex_text(full_caption)
            + "}",
            rf"  \label{{fig:{number.replace('.', '-')}}}",
            r"\end{figure}",
            "",
        )
        self.pending_image_id = None
        self.pending_figure_caption = None

    def emit_table(self, table: Table) -> None:
        self.close_flow_environments()
        self.table_count += 1
        caption = self.pending_table_caption or f"Tabla {self.table_count}"
        match = TABLE_PATTERN.match(normalize(caption))
        number = match.group(1) if match else str(self.table_count)
        caption_text = match.group(2) if match else normalize(caption)
        column_count = max(len(row.cells) for row in table.rows)
        columns = "|" + "|".join("X" for _ in range(column_count)) + "|"

        self.add(
            r"\begingroup",
            r"  \arrayrulecolor{uemcgreen}",
            r"\begin{table}[H]",
            r"  \centering",
            r"  \small",
            rf"  \caption{{{latex_text(caption_text)}}}",
            rf"  \label{{tab:{number.replace('.', '-')}}}",
            rf"  \begin{{tabularx}}{{\textwidth}}{{{columns}}}",
            r"    \hline",
        )
        for row_index, row in enumerate(table.rows):
            values = [latex_text(normalize(cell.text)) for cell in row.cells]
            while len(values) < column_count:
                values.append("")
            if row_index == 0:
                self.add(r"    \rowcolor{uemcgreen}")
                values = [
                    r"\textcolor{white}{\textbf{" + value + "}}" for value in values
                ]
            elif row_index % 2 == 0:
                self.add(r"    \rowcolor{tablelight}")
            self.add("    " + " & ".join(values) + r" \\", r"    \hline")
        self.add(
            r"  \end{tabularx}",
            r"\end{table}",
            r"\endgroup",
            "",
        )
        self.pending_table_caption = None

    def emit_heading(self, paragraph: Paragraph) -> None:
        self.close_flow_environments()
        text = normalize(paragraph.text)
        style = paragraph.style.name

        if style == "Heading 1":
            self.close_description()
            if text == "Referencias":
                self.add(
                    r"\clearpage",
                    r"\addcontentsline{toc}{chapter}{Referencias}",
                    r"\begin{thebibliography}{99}",
                )
                self.bibliography_open = True
                return
            if text == "Anexos":
                self.close_bibliography()
                self.in_appendices = True
                self.add(
                    r"\appendix",
                    r"\chapter*{Anexos}",
                    r"\addcontentsline{toc}{chapter}{Anexos}",
                    "",
                )
                return

            chapter = CHAPTER_PATTERN.match(text)
            if chapter:
                self.add(rf"\chapter{{{latex_text(chapter.group(1))}}}", "")
                return

            self.add(
                rf"\chapter*{{{latex_text(text)}}}",
                rf"\addcontentsline{{toc}}{{chapter}}{{{latex_text(text)}}}",
                "",
            )
            if text in {"Abreviaturas", "Glosario"}:
                self.description_open = True
                self.description_mode = text
                self.add(r"\begin{description}[style=nextline,leftmargin=3.3cm]", "")
            return

        if self.in_appendices and style == "Heading 2":
            annex = ANNEX_PATTERN.match(text)
            if annex:
                self.add(rf"\chapter{{{latex_text(annex.group(1))}}}", "")
                return
            annex_section = ANNEX_SECTION_PATTERN.match(text)
            if annex_section:
                self.add(rf"\section{{{latex_text(annex_section.group(1))}}}", "")
                return

        command = "section" if style == "Heading 2" else "subsection"
        self.add(rf"\{command}{{{latex_text(text)}}}", "")

    def emit_list_item(self, paragraph: Paragraph) -> bool:
        number_ids = paragraph._p.xpath(
            './/*[local-name()="numPr"]/*[local-name()="numId"]/'
            '@*[local-name()="val"]'
        )
        checklist = paragraph.style.name == "Lista de comprobación TFG"
        if not number_ids and not checklist:
            return False
        number_format = self.number_formats.get(number_ids[0], "bullet") if number_ids else "bullet"
        environment = "enumerate" if number_format != "bullet" else "itemize"
        if self.list_environment != environment:
            self.close_list()
            self.add(rf"\begin{{{environment}}}")
            self.list_environment = environment
        self.add(r"  \item " + paragraph_latex(paragraph))
        return True

    def emit_paragraph(self, paragraph: Paragraph) -> None:
        text = normalize(paragraph.text)
        style = paragraph.style.name
        blips = paragraph._p.xpath(
            './/*[local-name()="blip"]/@*[local-name()="embed"]'
        )

        if not self.started:
            if text != "Resumen":
                return
            self.started = True

        if text == "Índice de figuras":
            self.emit_indices()
            self.skip_static_indices = True
            return
        if self.skip_static_indices:
            if text != "Abreviaturas":
                return
            self.skip_static_indices = False

        if blips:
            if text.startswith("Figura "):
                self.emit_figure(blips[0], text)
            elif self.pending_figure_caption:
                self.emit_figure(blips[0], self.pending_figure_caption)
            else:
                self.pending_image_id = blips[0]
            return

        if text.startswith("Figura "):
            if self.pending_image_id:
                self.emit_figure(self.pending_image_id, text)
            else:
                self.pending_figure_caption = text
            return
        if text.startswith("Tabla "):
            self.pending_table_caption = text
            return

        if style.startswith("Heading"):
            self.emit_heading(paragraph)
            return
        if not text:
            return

        if self.bibliography_open:
            self.close_flow_environments()
            self.bibliography_index += 1
            self.add(
                rf"\bibitem{{ref{self.bibliography_index}}} "
                + paragraph_latex(paragraph),
                "",
            )
            return

        if self.description_open:
            self.close_flow_environments()
            label, separator, definition = text.partition(":")
            if separator:
                self.add(
                    rf"  \item[{latex_text(label.strip())}] "
                    + latex_text(definition.strip())
                )
            else:
                self.add(r"  \item " + paragraph_latex(paragraph))
            return

        if style == "Código TFG":
            self.close_list()
            if not self.code_open:
                self.add(r"\begin{lstlisting}")
                self.code_open = True
            code_text = (
                paragraph.text.rstrip()
                .replace("├──", "|--")
                .replace("└──", "`--")
                .replace("│", "|")
                .replace("─", "-")
            )
            self.add(code_text)
            return
        self.close_code()

        if self.emit_list_item(paragraph):
            return
        self.close_list()

        if style == "Fuente TFG":
            self.add(
                r"\begin{center}",
                r"  \footnotesize " + paragraph_latex(paragraph),
                r"\end{center}",
                "",
            )
            return

        self.add(paragraph_latex(paragraph), "")

    def export(self) -> str:
        FIGURES_DIR.mkdir(exist_ok=True)
        self.add(*preamble())
        for child in self.document.element.body.iterchildren():
            tag = child.tag.split("}")[-1]
            if tag == "sdt":
                if self.started:
                    self.close_flow_environments()
                    self.emit_indices()
                continue
            if tag == "p":
                self.emit_paragraph(Paragraph(child, self.document._body))
            elif tag == "tbl" and self.started:
                self.emit_table(Table(child, self.document._body))

        if self.pending_image_id and self.pending_figure_caption:
            self.emit_figure(self.pending_image_id, self.pending_figure_caption)
        self.close_flow_environments()
        self.close_description()
        self.close_bibliography()
        self.add(r"\end{document}", "")
        return "\n".join(self.lines)


def preamble() -> list[str]:
    return [
        "% Fuente LaTeX generada automáticamente desde TFG.docx.",
        "% Renombra este archivo como main.tex y conserva latex_figures/ al mismo nivel.",
        "% Compatible con pdfLaTeX, XeLaTeX y LuaLaTeX. Xe/Lua usa Trebuchet MS si está disponible.",
        r"\documentclass[11pt,a4paper,oneside]{report}",
        r"\usepackage{iftex}",
        r"\ifPDFTeX",
        r"  \usepackage[utf8]{inputenc}",
        r"  \usepackage[T1]{fontenc}",
        r"  \usepackage{tgheros}",
        r"  \renewcommand{\familydefault}{\sfdefault}",
        r"\else",
        r"  \usepackage{fontspec}",
        r"  \IfFontExistsTF{Trebuchet MS}{\setmainfont{Trebuchet MS}[Ligatures=TeX]}{\setmainfont{TeX Gyre Heros}[Ligatures=TeX]}",
        r"\fi",
        r"\usepackage[spanish,es-nodecimaldot,shorthands=off]{babel}",
        r"\usepackage[a4paper,margin=2.5cm]{geometry}",
        r"\usepackage{setspace}",
        r"\usepackage{ragged2e}",
        r"\usepackage{csquotes}",
        r"\usepackage{footmisc}",
        r"\usepackage{microtype}",
        r"\usepackage[table]{xcolor}",
        r"\usepackage{graphicx}",
        r"\usepackage{float}",
        r"\usepackage{booktabs}",
        r"\usepackage{array}",
        r"\usepackage{tabularx}",
        r"\usepackage{enumitem}",
        r"\usepackage{caption}",
        r"\usepackage{titlesec}",
        r"\usepackage{tocloft}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{xurl}",
        r"\usepackage{hyperref}",
        r"\usepackage{listings}",
        r"\definecolor{uemcgreen}{HTML}{004C3F}",
        r"\definecolor{uemcgold}{HTML}{E5B93F}",
        r"\definecolor{tfgblue}{HTML}{20566B}",
        r"\definecolor{coverink}{HTML}{1F2937}",
        r"\definecolor{tablelight}{HTML}{E7F1EE}",
        r"\titleformat{\chapter}[display]{\normalfont\bfseries\color{uemcgreen}}{\Large\color{uemcgold}\chaptername\ \thechapter}{0.4ex}{\Huge}[\vspace{0.6ex}{\color{uemcgold}\titlerule}]",
        r"\titleformat{\section}{\normalfont\Large\bfseries\color{uemcgreen}}{\thesection}{0.75em}{}",
        r"\titleformat{\subsection}{\normalfont\large\bfseries\color{uemcgreen}}{\thesubsection}{0.75em}{}",
        r"\titlespacing*{\chapter}{0pt}{-15pt}{24pt}",
        r"\captionsetup{labelfont={bf,color=uemcgreen},textfont={small,color=coverink},justification=centering}",
        r"\renewcommand{\cftchapfont}{\bfseries\color{uemcgreen}}",
        r"\renewcommand{\cftchappagefont}{\bfseries\color{uemcgreen}}",
        r"\renewcommand{\cftsecfont}{\color{coverink}}",
        r"\renewcommand{\cftsecpagefont}{\color{coverink}}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\fancyhead[L]{\small\color{uemcgreen}Trabajo Fin de Grado}",
        r"\fancyhead[R]{\small\color{uemcgreen}UEMC}",
        r"\fancyfoot[C]{\color{uemcgreen}\thepage}",
        r"\renewcommand{\headrulewidth}{0.4pt}",
        r"\renewcommand{\headrule}{\hbox to\headwidth{\color{uemcgold}\leaders\hrule height \headrulewidth\hfill}}",
        r"\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\color{uemcgreen}\thepage}\renewcommand{\headrulewidth}{0pt}}",
        r"\lstset{basicstyle=\ttfamily\footnotesize,breaklines=true,breakatwhitespace=false,columns=fullflexible,frame=single,showstringspaces=false,literate={á}{{\'a}}1 {é}{{\'e}}1 {í}{{\'i}}1 {ó}{{\'o}}1 {ú}{{\'u}}1 {Á}{{\'A}}1 {É}{{\'E}}1 {Í}{{\'I}}1 {Ó}{{\'O}}1 {Ú}{{\'U}}1 {ñ}{{\~n}}1 {Ñ}{{\~N}}1 {ü}{{\"u}}1 {Ü}{{\"U}}1 {¿}{{?`}}1 {¡}{{!`}}1}",
        r"\renewcommand{\bibname}{Referencias}",
        r"\renewcommand{\arraystretch}{1.18}",
        r"\setlength{\parindent}{0pt}",
        r"% El cuerpo usa 6 pt de separación entre párrafos (antes/después); la portada conserva su composición propia.",
        r"\setlength{\parskip}{0pt}",
        r"% Citas breves dentro del texto; las extensas pueden pasarse a una nota al pie.",
        r"\newcommand{\citaCorta}[1]{\enquote{#1}}",
        r"\newcommand{\citaLarga}[1]{\footnote{\small\begin{quote}#1\end{quote}}}",
        r"% Referencias formalmente nombradas en un formato autor-año compatible con APA.",
        r"\hypersetup{colorlinks=true,linkcolor=uemcgreen,urlcolor=tfgblue,citecolor=uemcgreen,pdftitle={Phishing. Técnicas y métodos de ataque y cómo detectarlos},pdfauthor={Alejandro Villarrubia García}}",
        r"\begin{document}",
        r"\begin{titlepage}",
        r"  \thispagestyle{empty}",
        r"  \centering",
        r"  \color{coverink}",
        r"  \vspace*{0.45cm}",
        r"  {\fontsize{17}{22}\selectfont UNIVERSIDAD EUROPEA\par}",
        r"  \vspace{0.35cm}",
        r"  {\fontsize{17}{22}\selectfont MIGUEL DE CERVANTES\par}",
        r"  \vspace{1.25cm}",
        r"  {\fontsize{15}{19}\selectfont ESCUELA POLITÉCNICA SUPERIOR\par}",
        r"  \vspace{0.42cm}",
        r"  {\fontsize{12.5}{16}\selectfont TITULACIÓN: GRADO EN INGENIERÍA INFORMÁTICA\par}",
        r"  \vspace{0.9cm}",
        r"  \includegraphics[height=4.25cm]{latex_figures/escudo_uemc.png}\par",
        r"  \vspace{0.85cm}",
        r"  {\fontsize{15}{19}\selectfont TRABAJO FIN DE GRADO\par}",
        r"  \vspace{0.48cm}",
        r"  {\fontsize{20}{27}\selectfont\bfseries Phishing. Técnicas y métodos\\[0.18cm]de ataque y cómo detectarlos\par}",
        r"  \vspace{0.62cm}",
        r"  {\fontsize{13}{17}\selectfont AUTOR\par}",
        r"  \vspace{0.22cm}",
        r"  {\fontsize{12.5}{16}\selectfont ALEJANDRO VILLARRUBIA GARCÍA\par}",
        r"  \vspace{0.42cm}",
        r"  {\fontsize{13}{17}\selectfont DIRECTOR\par}",
        r"  \vspace{0.22cm}",
        r"  {\fontsize{12.5}{16}\selectfont CARMELO GONZÁLEZ GARCÍA\par}",
        r"  \vfill",
        r"  {\fontsize{12.5}{16}\selectfont VALLADOLID, SEPTIEMBRE 2026\par}",
        r"  \vspace*{0.35cm}",
        r"\end{titlepage}",
        r"\pagenumbering{arabic}",
        r"\onehalfspacing",
        r"\justifying",
        r"\setlength{\parskip}{6pt}",
        "",
    ]


def validate_output(source: str, exporter: LatexExporter) -> None:
    """Comprueba la integridad estructural de la fuente generada."""

    stack: list[str] = []
    for kind, name in re.findall(r"\\(begin|end)\{([^}]+)\}", source):
        if kind == "begin":
            stack.append(name)
        else:
            if not stack or stack[-1] != name:
                raise RuntimeError(f"Entorno LaTeX mal cerrado: {name}; pila={stack}")
            stack.pop()
    if stack:
        raise RuntimeError(f"Entornos LaTeX sin cerrar: {stack}")

    image_paths = re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", source)
    missing_images = [
        image_path
        for image_path in image_paths
        if not (REPO_ROOT / image_path).is_file()
    ]
    if missing_images:
        raise RuntimeError(f"Imágenes LaTeX ausentes: {missing_images}")

    expected_counts = {
        "figuras": 10,
        "tablas": 16,
        "referencias": 39,
        "imágenes": 11,  # Diez figuras y el escudo de portada.
    }
    actual_counts = {
        "figuras": source.count(r"\begin{figure}[H]"),
        "tablas": source.count(r"\begin{table}[H]"),
        "referencias": source.count(r"\bibitem{"),
        "imágenes": len(image_paths),
    }
    if actual_counts != expected_counts:
        raise RuntimeError(
            f"Recuento LaTeX inesperado: {actual_counts}; esperado={expected_counts}"
        )
    if exporter.figure_count != 10 or exporter.table_count != 16:
        raise RuntimeError("El exportador no recorrió todas las figuras y tablas del DOCX")

    required_fragments = (
        r"\definecolor{uemcgreen}{HTML}{004C3F}",
        r"\titleformat{\chapter}",
        r"\rowcolor{uemcgreen}",
        r"\includegraphics[height=4.25cm]{latex_figures/escudo_uemc.png}",
        "VALLADOLID, SEPTIEMBRE 2026",
    )
    missing_fragments = [item for item in required_fragments if item not in source]
    if missing_fragments:
        raise RuntimeError(f"Faltan elementos visuales LaTeX: {missing_fragments}")


def main() -> None:
    document = Document(DOCX_PATH)
    exporter = LatexExporter(document)
    output = exporter.export()
    validate_output(output, exporter)
    OUTPUT_PATH.write_text(output, encoding="utf-8", newline="\n")
    with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("main.tex", output)
        archive.writestr("TFG_para_LaTeX.txt", output)
        for image_path in sorted(FIGURES_DIR.iterdir()):
            if image_path.is_file():
                archive.write(image_path, arcname=f"latex_figures/{image_path.name}")
    print(f"Fuente LaTeX: {OUTPUT_PATH}")
    print(f"Paquete Overleaf: {ZIP_PATH}")
    print(f"Figuras: {exporter.figure_count} en {FIGURES_DIR}")
    print(f"Tablas: {exporter.table_count}")
    print(f"Referencias: {exporter.bibliography_index}")
    print("Validación estructural y visual declarativa: correcta")


if __name__ == "__main__":
    main()
