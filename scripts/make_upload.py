# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Prepare the student build for Moodle, in _build/upload/:

* <code>-notes.zip: the HTML notes (with the PDF). On Moodle: add a File resource,
  upload the zip, unzip it, and set notes/index.html as the main file.
* sheets/: every sheet PDF and HTML, side by side, ready to upload one by one.

Runs the leak check first and refuses to continue if it fails. Only ever reads
_build/student, never the staff build.

    uv run scripts/make_upload.py
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import leak_check
import moduleconf

STUDENT = moduleconf.BUILD / "student"
UPLOAD = moduleconf.BUILD / "upload"


def zip_folder(folder: Path, archive: Path, root_name: str) -> None:
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            zf.write(path, f"{root_name}/{path.relative_to(folder).as_posix()}")


def main() -> int:
    if leak_check.main_for(STUDENT) != 0:
        return 1
    code = str((moduleconf.load().get("module") or {}).get("code") or "module")
    if UPLOAD.exists():
        shutil.rmtree(UPLOAD)
    UPLOAD.mkdir(parents=True)

    notes = STUDENT / "notes"
    if (notes / "index.html").exists():
        archive = UPLOAD / f"{code}-notes.zip"
        zip_folder(notes, archive, "notes")
        print(f"Notes for Moodle: {archive.relative_to(moduleconf.ROOT).as_posix()}")

    sheets = STUDENT / "sheets"
    if sheets.exists():
        target = UPLOAD / "sheets"
        target.mkdir()
        for path in sorted(sheets.rglob("*")):
            if path.is_file() and path.suffix.lower() in (".pdf", ".html"):
                if (target / path.name).exists():
                    print(f"Two sheets are called {path.name}; rename one.", file=sys.stderr)
                    return 1
                shutil.copy2(path, target / path.name)
        print(f"Sheets for Moodle: {target.relative_to(moduleconf.ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
