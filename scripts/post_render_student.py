# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Quarto post-render hook for the student build of the sheets.

1. Delete the placeholders that template.lua renders instead of unreleased solutions.
2. Run the leak check on the whole student build; fail the render if it finds anything.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import leak_check  # noqa: E402
import moduleconf  # noqa: E402


def main() -> int:
    out = os.environ.get("QUARTO_PROJECT_OUTPUT_DIR")
    sheets_dir = Path(out).resolve() if out else moduleconf.BUILD / "student" / "sheets"
    for path in sorted(sheets_dir.rglob("*")):
        if path.is_file() and any(m[2] == "withheld" for m in leak_check.markers(path)):
            path.unlink()
            print(f"Withheld (solutions not released): {path.relative_to(sheets_dir).as_posix()}")
    # Remove folders left empty by the deletions
    for folder in sorted((p for p in sheets_dir.rglob("*") if p.is_dir()), reverse=True):
        if not any(folder.iterdir()):
            folder.rmdir()
    return leak_check.main_for(sheets_dir.parent)


if __name__ == "__main__":
    sys.exit(main())
