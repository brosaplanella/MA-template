# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Build TikZ (or any standalone LaTeX) figures to PDF (for the PDF) and SVG (for the HTML).

    uv run scripts/tikz.py            build figures whose .tex changed
    uv run scripts/tikz.py --force    rebuild all figures

A figure is any figs/<name>.tex under notes/ or sheets/ (use the standalone class, e.g.
\\documentclass[tikz, border=2pt]{standalone}). It becomes figs/<name>.pdf and figs/<name>.svg
next to it. Include it without an extension, and each format picks its own file:

    ![Caption.](figs/<name>){#fig-name width=40%}

Figures can use the module colours with \\input{palette.tex} (e.g. \\color{brand-purple}).
Runs before every render (Quarto pre-render hook). Needs pdflatex and dvisvgm (both in
TeX Live/TinyTeX). To read PDFs, dvisvgm needs mutool (MuPDF) or a Ghostscript older than
10.01: TeX Live on Windows includes one; on macOS/Linux install MuPDF's tools
(`brew install mupdf-tools` / `sudo apt install mupdf-tools`).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ("notes", "sheets")
GENERATED = ROOT / "_shared" / "generated"
PDF_READER_HINT = ("dvisvgm cannot read PDFs: install MuPDF's tools "
                   "(macOS: brew install mupdf-tools; Linux: sudo apt install mupdf-tools)")


def figures() -> list[Path]:
    found = []
    for project in PROJECTS:
        for tex in (ROOT / project).rglob("figs/*.tex"):
            rel = tex.relative_to(ROOT)
            if not any(part.startswith(("_", ".")) for part in rel.parts):
                found.append(tex)
    return sorted(found)


def outdated(tex: Path) -> bool:
    sources = [tex, GENERATED / "palette.tex"]
    newest = max(p.stat().st_mtime for p in sources if p.exists())
    for out in (tex.with_suffix(".pdf"), tex.with_suffix(".svg")):
        if not out.exists() or out.stat().st_mtime < newest:
            return True
    return False


def build(tex: Path) -> bool:
    # A fixed date makes the PDF identical when nothing changed (no noise in git)
    env = {**os.environ, "TEXINPUTS": f"{GENERATED}{os.pathsep}",
           "SOURCE_DATE_EPOCH": "1767225600", "FORCE_SOURCE_DATE": "1"}
    with tempfile.TemporaryDirectory() as tmp:
        # \pdftrailerid{} drops the PDF ID, which pdfTeX derives from the (temporary) path
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={tmp}", f"-jobname={tex.stem}",
             f"\\pdftrailerid{{}}\\input{{{tex.name}}}"],
            cwd=tex.parent, env=env, capture_output=True, text=True, errors="replace",
        )
        pdf = Path(tmp) / tex.with_suffix(".pdf").name
        if result.returncode != 0 or not pdf.exists():
            log = Path(tmp) / tex.with_suffix(".log").name
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
            errors = [line for line in lines if line.startswith("!")] or lines[-5:]
            print(f"FAILED {tex.relative_to(ROOT).as_posix()}:", *errors[:5], sep="\n  ")
            return False
        shutil.copy2(pdf, tex.with_suffix(".pdf"))
    svg = tex.with_suffix(".svg")
    result = subprocess.run(
        ["dvisvgm", "--pdf", "--no-fonts", "--exact-bbox", "-o", svg.name,
         tex.with_suffix(".pdf").name],
        cwd=tex.parent, capture_output=True, text=True, errors="replace",
    )
    if result.returncode != 0 or not svg.exists():
        message = result.stderr.strip()[-500:]
        if "mutool" in message or "Ghostscript" in message or "number of pages" in message:
            message += f"\n  -> {PDF_READER_HINT}"
        print(f"FAILED {svg.relative_to(ROOT).as_posix()} (dvisvgm):\n  {message}")
        return False
    # dvisvgm writes CRLF on Windows; use LF everywhere so git sees no change
    svg.write_bytes(svg.read_bytes().replace(b"\r\n", b"\n"))
    print(f"Figure: {tex.relative_to(ROOT).as_posix()} -> .pdf, .svg")
    return True


def main() -> int:
    force = "--force" in sys.argv[1:]
    todo = [tex for tex in figures() if force or outdated(tex)]
    if not todo:
        return 0
    for tool in ("pdflatex", "dvisvgm"):
        if not shutil.which(tool):
            print(f"{tool} not found: install TeX Live or TinyTeX (see README.md)")
            return 1
    ok = all([build(tex) for tex in todo])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
