# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Check that a student build contains nothing staff-only.

    uv run scripts/leak_check.py [folder]     (default: _build/student)

Every sheet carries a hidden marker (see moduleconf.MARKER_RE) saying what it
is. The check fails if, anywhere in the folder:

* a file name ends in -STAFF, or a file comes from a staff build;
* a file holds the solutions of a sheet whose solutions are not released in
  _module.yml (by marker, or by its <id>-solutions name if it has no marker);
* a placeholder for withheld solutions was left behind.

It runs automatically after every student render of the sheets
(post_render_student.py) and before the upload folder is made.
"""

from __future__ import annotations

import re
import sys
import zlib
from pathlib import Path

import moduleconf

SOLUTIONS_NAME_RE = re.compile(r"^(?P<id>.+)-solutions$")
STREAM_RE = re.compile(rb"stream\r?\n(.*?)endstream", re.S)
# The PDF info entry: a literal (...) or hex <...> string, often UTF-16 with escapes
PDF_INFO_RE = re.compile(rb"/MATemplate\s*(?:\(((?:\\.|[^\\)])*)\)|<([0-9A-Fa-f\s]*)>)", re.S)
PDF_ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}


def _pdf_literal(raw: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(raw):
        if raw[i : i + 1] == b"\\" and i + 1 < len(raw):
            octal = re.match(rb"[0-7]{1,3}", raw[i + 1 : i + 4])
            if octal:
                out.append(int(octal.group(), 8) & 0xFF)
                i += 1 + len(octal.group())
                continue
            out += PDF_ESCAPES.get(raw[i + 1 : i + 2], raw[i + 1 : i + 2])
            i += 2
        else:
            out += raw[i : i + 1]
            i += 1
    return bytes(out)


def _pdf_text(data: bytes) -> bytes:
    """The PDF info entries written by template.lua, decoded to UTF-8."""
    texts = []
    for literal, hexstr in PDF_INFO_RE.findall(data):
        raw = _pdf_literal(literal) if literal else bytes.fromhex(hexstr.decode())
        if raw.startswith(b"\xfe\xff"):
            raw = raw[2:].decode("utf-16-be", errors="replace").encode()
        texts.append(raw)
    return b"\n".join(texts)


def markers(path: Path) -> list[tuple[str, str, str, str]]:
    """The markers in a file (HTML/PDF), including inside compressed PDF streams."""
    data = path.read_bytes()
    found = moduleconf.MARKER_RE.findall(data)
    if path.suffix.lower() == ".pdf":
        chunks = [data]
        for match in STREAM_RE.finditer(data):
            try:
                chunks.append(zlib.decompress(match.group(1)))
            except zlib.error:
                pass
        for chunk in chunks:
            found += moduleconf.MARKER_RE.findall(_pdf_text(chunk))
    return sorted({tuple(part.decode() for part in m) for m in found})


def check(folder: Path, conf: dict | None = None) -> list[str]:
    """Problems found in a student build folder (empty list: all fine)."""
    conf = moduleconf.load() if conf is None else conf
    problems = []
    if not folder.exists():
        return problems
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        rel = path.relative_to(folder).as_posix()
        if path.stem.upper().endswith("-STAFF"):
            problems.append(f"{rel}: staff file in the student build")
        if path.suffix.lower() not in (".html", ".pdf"):
            continue
        found = markers(path)
        for kind, sheet_id, role, build in found:
            if build != "student":
                problems.append(f"{rel}: comes from a {build} build")
            if role == "withheld":
                problems.append(f"{rel}: placeholder for unreleased solutions was not deleted")
            if role == "solutions" and not moduleconf.is_released(conf, kind, sheet_id):
                problems.append(
                    f"{rel}: solutions of {kind}/{sheet_id}, which are not released "
                    "(solutions-released in _module.yml)"
                )
        name = SOLUTIONS_NAME_RE.match(path.stem)
        if name and not found:
            sheet_id = name.group("id")
            kinds = [k for k in moduleconf.KINDS if k in path.parts] or list(moduleconf.KINDS)
            if not any(moduleconf.is_released(conf, k, sheet_id) for k in kinds):
                problems.append(
                    f"{rel}: looks like unreleased solutions and has no marker "
                    "(rendered outside the template?)"
                )
    return problems


def main_for(folder: Path) -> int:
    """Run the check, print the result, and return an exit code."""
    problems = check(folder.resolve())
    if problems:
        print(f"LEAK CHECK FAILED for {folder}:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("Do not upload this folder. Fix the problem and build again.", file=sys.stderr)
        return 1
    print(f"Leak check passed: {folder}")
    return 0


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else moduleconf.BUILD / "student"
    sys.exit(main_for(folder))
