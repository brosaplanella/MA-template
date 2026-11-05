# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Write the map of cross-reference labels in the notes, for {{< notes label >}} in sheets.

Runs after every render of the notes (post-render hook in notes/_quarto.yml), or by hand:

    uv run scripts/notes_xref.py

It reads Quarto's cross-reference index (notes/.quarto/xref/) and writes
_shared/generated/notes-xref.json (committed, so the sheets build without the notes):

    {"thm-FTC": {"name": "Theorem", "number": "2.1", "page": "chapter2.html"}, ...}

The index is internal to Quarto, so this script checks its shape and fails with a clear
message if a Quarto update changes it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XREF = ROOT / "notes" / ".quarto" / "xref"
HTML = ROOT / "_build" / "student" / "notes"  # output-dir in notes/_quarto.yml
OUT = ROOT / "_shared" / "generated" / "notes-xref.json"

# Label prefix -> name, as in Quarto's own cross-references ("Theorem 2.1")
NAMES = {
    "sec": "Section",
    "eq": "Equation",
    "fig": "Figure",
    "tbl": "Table",
    "lst": "Listing",
    "thm": "Theorem",
    "lem": "Lemma",
    "cor": "Corollary",
    "prp": "Proposition",
    "cnj": "Conjecture",
    "def": "Definition",
    "exm": "Example",
    "exr": "Exercise",
    "sol": "Solution",
    "rem": "Remark",
    "alg": "Algorithm",
}


def number(key: str, entry: dict, chapters: bool) -> tuple[str, str]:
    """(name, number) for one index entry, e.g. ("Section", "2.3")."""
    prefix = key.split("-", 1)[0]
    section = list(entry["order"]["section"])
    if prefix == "sec":
        while section and section[-1] == 0:
            section.pop()
        if len(section) == 1 and chapters:
            return "Chapter", str(section[0])
        return "Section", ".".join(str(n) for n in section)
    name = NAMES.get(prefix, prefix.capitalize())
    n = str(entry["order"]["number"])
    if chapters and section and section[0]:
        n = f"{section[0]}.{n}"
    return name, n


def build() -> dict:
    index_file = XREF / "INDEX"
    if not index_file.exists():
        raise ValueError(f"{index_file.relative_to(ROOT).as_posix()} not found: render the notes first")
    index = json.loads(index_file.read_text(encoding="utf-8"))
    labels: dict[str, dict] = {}
    for source, outputs in sorted(index.items()):
        for output, xref_id in outputs.items():
            # Skip chapters no longer in the book: Quarto keeps their index entries
            if not output.endswith(".html") or not (HTML / output).exists():
                continue
            data = json.loads((XREF / xref_id).read_text(encoding="utf-8"))
            chapters = bool(data.get("options", {}).get("chapters"))
            for entry in data["entries"]:
                key = entry["key"]
                name, n = number(key, entry, chapters)
                if key in labels:
                    print(f"notes_xref: label {key} appears twice ({source})", file=sys.stderr)
                labels[key] = {"name": name, "number": n, "page": Path(output).as_posix()}
    return dict(sorted(labels.items()))


def main() -> int:
    try:
        labels = build()
    except (OSError, ValueError, KeyError, TypeError, IndexError) as err:
        print(f"notes_xref: could not read Quarto's cross-reference index ({err!r}).\n"
              "Links from sheets to the notes are not updated.", file=sys.stderr)
        return 1
    text = json.dumps(labels, indent=1, ensure_ascii=False) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"notes_xref: {len(labels)} labels -> {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
