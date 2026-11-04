"""Build the module.

    uv run scripts/build.py              student build: notes + sheets, leak check,
                                         then _build/upload/ ready for Moodle
    uv run scripts/build.py staff        staff build of the sheets (_build/staff/)
    uv run scripts/build.py student --only sheets     (or --only notes)

Outputs:
    _build/student/   what students may see (the default)
    _build/staff/     everything, every file marked -STAFF: never upload
    _build/upload/    copied from _build/student after the leak check
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import make_upload
import moduleconf


def render(project: str, profile: str) -> None:
    quarto = shutil.which("quarto")
    if not quarto:
        sys.exit("Quarto is not installed (or not on the PATH): see README.md.")
    print(f"\n=== Rendering {project} ({profile} build) ===", flush=True)
    # Make Quarto use this Python (the project environment) for hooks and code cells
    env = {**os.environ, "QUARTO_PYTHON": sys.executable}
    result = subprocess.run(
        [quarto, "render", "--profile", profile], cwd=moduleconf.ROOT / project, env=env
    )
    if result.returncode != 0:
        sys.exit(f"Rendering {project} failed (see the messages above).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("profile", nargs="?", default="student", choices=["student", "staff"])
    parser.add_argument("--only", choices=["notes", "sheets"])
    args = parser.parse_args()

    if args.profile == "staff":
        if args.only == "notes":
            sys.exit("The notes have no staff build.")
        render("sheets", "staff")
        print("\nStaff build in _build/staff/. Do not upload anything from it.")
        return 0

    for project in ("notes", "sheets"):
        if args.only in (None, project):
            render(project, "student")
    print()
    return make_upload.main()


if __name__ == "__main__":
    sys.exit(main())
