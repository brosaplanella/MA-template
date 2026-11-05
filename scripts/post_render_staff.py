# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Quarto post-render hook for the staff build of the sheets.

Adds -STAFF to the name of every output file (assignment-1.pdf becomes
assignment-1-STAFF.pdf), so a staff copy is obvious wherever it ends up.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import moduleconf  # noqa: E402


def main() -> int:
    out = os.environ.get("QUARTO_PROJECT_OUTPUT_DIR")
    staff_dir = Path(out).resolve() if out else moduleconf.BUILD / "staff" / "sheets"
    for path in sorted(p for p in staff_dir.rglob("*") if p.is_file()):
        if path.stem.endswith("-STAFF"):
            continue
        target = path.with_name(f"{path.stem}-STAFF{path.suffix}")
        path.replace(target)
        print(f"Staff copy: {target.relative_to(staff_dir).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
