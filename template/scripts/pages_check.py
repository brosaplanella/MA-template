# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Check that a folder about to be published on the web holds the notes and nothing else.

    uv run scripts/pages_check.py [folder]     (default: _build/student/notes)

Used by .github/workflows/publish-notes.yml before it publishes anything. Stricter than
the leak check (which it also runs): a published site is public, so it fails on any
sheet at all, released or not:

* the folder is not the student build of the notes, or has no index.html;
* a file name ends in -solutions or -STAFF;
* an HTML or PDF file carries a sheet marker (every rendered sheet does);
* the leak check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import leak_check
import moduleconf

NOTES = moduleconf.BUILD / "student" / "notes"


def check(folder: Path) -> list[str]:
    """Problems that stop the folder from being published (empty list: all fine)."""
    folder = folder.resolve()
    if folder != NOTES.resolve():
        return [f"{folder}: only the student notes ({NOTES}) may be published"]
    if not (folder / "index.html").is_file():
        return [f"{folder}: no index.html (build the notes first)"]
    problems = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        rel = path.relative_to(folder).as_posix()
        stem = path.stem.lower()
        if stem.endswith("-solutions") or stem.endswith("-staff"):
            problems.append(f"{rel}: solutions or staff file")
        if path.suffix.lower() in (".html", ".pdf") and leak_check.markers(path):
            problems.append(f"{rel}: a sheet (only the notes may be published)")
    problems += leak_check.check(folder)
    return problems


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else NOTES
    problems = check(folder)
    if problems:
        print(f"NOT PUBLISHING {folder}:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"Pages check passed: {folder} holds only the notes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
