# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Test the copier template: generate modules from the working copy and build them.

    uv run scripts/test_template.py            all answer sets
    uv run scripts/test_template.py small      one set (defaults, small, no-assignments)

Modules are generated into _scratch/test-template/<set>/ (cleared first, kept afterwards
for inspection: cd there and `uv run quarto preview ...`). Uncommitted changes to the
template are included. Needs uv; copier is run with uvx.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "_scratch" / "test-template"

BASE = {"module_code": "MA999", "module_title": "Test Module", "lecturer": "A. Lecturer"}

# name: (answers, builds to run)
SETS = {
    "defaults": ({}, []),
    "small": ({"n_problem_sheets": 2, "n_assignments": 1}, ["student", "staff"]),
    "no-assignments": ({"n_problem_sheets": 1, "n_assignments": 0}, ["student"]),
}


def run(cmd: list[str], cwd: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    print("  $", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stdout[-4000:], result.stderr[-4000:], sep="\n")
        raise SystemExit(f"FAILED: {' '.join(cmd)} (in {cwd})")


def check_layout(dest: Path, answers: dict) -> list[str]:
    """Problems with the generated files: sheet folders and _module.yml entries."""
    problems = []
    conf = yaml.safe_load((dest / "_module.yml").read_text(encoding="utf-8"))
    for kind, stem, key, default in [("problem-sheets", "problem-sheet", "n_problem_sheets", 10),
                                     ("assignments", "assignment", "n_assignments", 4)]:
        n = answers.get(key, default)
        folder = dest / "sheets" / kind
        found = sorted(p.name for p in folder.iterdir()) if folder.exists() else []
        expected = sorted(f"{stem}-{i}" for i in range(1, n + 1))
        if found != expected:
            problems.append(f"{kind}: folders {found}, expected {expected}")
        for i in range(1, n + 1):
            for suffix in ("", "-solutions"):
                if not (folder / f"{stem}-{i}" / f"{stem}-{i}{suffix}.qmd").exists():
                    problems.append(f"missing {stem}-{i}{suffix}.qmd")
        entries = sorted(k for k in (conf.get(kind) or {}) if k != "defaults")
        if entries != expected:
            problems.append(f"_module.yml {kind}: {entries}, expected {expected}")
    for path in dest.rglob("*"):
        if path.is_file() and (path.suffix == ".jinja" or "[[" in path.name or "[%" in path.name):
            problems.append(f"unrendered file {path.relative_to(dest)}")
    return problems


def test(name: str) -> list[str]:
    answers, builds = SETS[name]
    dest = OUT / name
    print(f"\n== {name}: {answers or 'default answers'}")
    data = []
    for key, value in {**BASE, **answers}.items():
        data += ["--data", f"{key}={value}"]
    run(["uvx", "copier", "copy", "--defaults", "--vcs-ref", "HEAD", *data,
         str(REPO), str(dest)], REPO)
    problems = check_layout(dest, answers)
    if builds:
        run(["uv", "sync"], dest)
        for profile in builds:
            run(["uv", "run", "scripts/build.py", profile], dest)  # includes the leak check
    return problems


def main() -> None:
    names = sys.argv[1:] or list(SETS)
    unknown = [n for n in names if n not in SETS]
    if unknown:
        raise SystemExit(f"Unknown set(s) {unknown}; choose from {list(SETS)}")
    for name in names:
        shutil.rmtree(OUT / name, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    failed = {}
    for name in names:
        problems = test(name)
        if problems:
            failed[name] = problems
    print()
    for name, problems in failed.items():
        print(f"{name}:", *problems, sep="\n  ")
    if failed:
        raise SystemExit("Template test FAILED")
    print(f"Template test passed: {', '.join(names)} (modules in {OUT.relative_to(REPO)})")


if __name__ == "__main__":
    main()
