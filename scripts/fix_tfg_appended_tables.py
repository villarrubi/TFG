"""Corrige la geometría DXA de las tablas añadidas a la memoria actualizada."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def set_width(cell, width):
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.first_child_found_in("w:tcW")
    if node is None:
        node = OxmlElement("w:tcW")
        tc_pr.append(node)
    node.set(qn("w:w"), str(width))
    node.set(qn("w:type"), "dxa")


def fix(table, widths):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table_pr = table._tbl.tblPr
    table_width = table_pr.first_child_found_in("w:tblW")
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        table_pr.append(table_width)
    table_width.set(qn("w:w"), str(sum(widths)))
    table_width.set(qn("w:type"), "dxa")
    table_indent = table_pr.first_child_found_in("w:tblInd")
    if table_indent is None:
        table_indent = OxmlElement("w:tblInd")
        table_pr.append(table_indent)
    table_indent.set(qn("w:w"), "120")
    table_indent.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            set_width(cell, widths[index])


def main():
    path = Path(__file__).resolve().parents[1] / "TFG.docx"
    document = Document(path)
    content_width = 8384  # Ancho útil menos la sangría de tabla de 120 twips.
    for table in document.tables:
        grid = [int(node.get(qn("w:w"))) for node in table._tbl.tblGrid]
        total = sum(grid) or content_width
        widths = [content_width * width // total for width in grid]
        widths[-1] += content_width - sum(widths)
        fix(table, widths)
    document.save(path)


if __name__ == "__main__":
    main()
