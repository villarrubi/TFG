"""Compila la fuente editorial TFG.tex y prepara el paquete de Overleaf."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="tectonic", help="Tectonic o ruta al ejecutable.")
    parser.add_argument("--package-only", action="store_true", help="Solo crea el ZIP de fuentes.")
    parser.add_argument("--guides", action="store_true", help="Compila también las dos guías LaTeX públicas.")
    args = parser.parse_args()
    if args.package_only and args.guides:
        parser.error("--package-only no se combina con --guides.")
    if not args.package_only:
        engine = shutil.which(args.engine)
        if engine is None:
            raise SystemExit("No se encontró Tectonic. Instálalo o indica --engine con su ruta.")
        with tempfile.TemporaryDirectory(prefix="tfg-latex-") as temporary:
            sources = ["TFG"]
            if args.guides:
                sources += ["Guia_01_Flujo_y_funcionamiento", "Guia_02_Tecnologias_y_decisiones"]
            for name in sources:
                subprocess.run(
                    [engine, f"{name}.tex", "--outdir", temporary, "--keep-logs"],
                    cwd=ROOT,
                    check=True,
                )
            # Publicar los PDF solo si todos los documentos solicitados compilan.
            for name in sources:
                shutil.copyfile(Path(temporary) / f"{name}.pdf", ROOT / f"{name}.pdf")
    package = ROOT / "TFG_LaTeX.zip"
    with ZipFile(package, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(ROOT / "TFG.tex", "TFG.tex")
        for folder in ("memoria", "latex_figures"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(ROOT))
        archive.writestr(
            "LEEME.txt",
            "Fuente principal: TFG.tex. En Overleaf seleccionar XeLaTeX o pdfLaTeX.\n"
            "Conservar memoria/ y latex_figures/. No se necesita TFG.docx.\n"
            "Compilación local: tectonic TFG.tex\n",
        )
    print(f"Paquete editable: {package}")


if __name__ == "__main__":
    main()
