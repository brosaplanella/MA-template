# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Test the copier template: generate modules from the working copy and build them.

Sets: defaults (generate only), small (2 + 1 sheets, with a TikZ figure and a code cell
added; both builds; a planted leak must make the leak check fail), no-assignments
(student build). Also run on Ubuntu and macOS by .github/workflows/test-template.yml.

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

# name: (answers, builds to run). "small" also gets a TikZ figure, a Python code cell and
# a planted leak (see add_extras and check_leak_detected).
SETS = {
    "defaults": ({}, []),
    "small": ({"n_problem_sheets": 2, "n_assignments": 1}, ["student", "staff"]),
    "no-assignments": ({"n_problem_sheets": 1, "n_assignments": 0}, ["student"]),
}

TIKZ = r"""\documentclass[tikz, border=2pt]{standalone}
\begin{document}
\begin{tikzpicture}
  \draw (0, 0) circle (1);
  \node at (0, 0) {$x^2$};
\end{tikzpicture}
\end{document}
"""

CODE_CELL = """
```{python}
#| label: fig-test-cell
#| fig-cap: "A test figure from a code cell."
import matplotlib.pyplot as plt
from moduletools import apply_style
apply_style()
fig, ax = plt.subplots(figsize=(3, 2))
ax.plot([0, 1], [0, 1])
plt.show()
```
"""


def run(cmd: list[str], cwd: Path, expect_failure: bool = False) -> None:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    print("  $", " ".join(cmd), "(expecting failure)" if expect_failure else "")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if expect_failure and result.returncode == 0:
        raise SystemExit(f"FAILED: {' '.join(cmd)} succeeded, but should have failed (in {cwd})")
    if not expect_failure and result.returncode != 0:
        print(result.stdout[-4000:], result.stderr[-4000:], sep="\n")
        raise SystemExit(f"FAILED: {' '.join(cmd)} (in {cwd})")


def add_extras(dest: Path) -> None:
    """A TikZ figure (pdflatex, dvisvgm, Ghostscript) and a code cell (Jupyter, moduletools)."""
    figs = dest / "sheets" / "problem-sheets" / "problem-sheet-1" / "figs"
    figs.mkdir(parents=True, exist_ok=True)
    (figs / "test-figure.tex").write_text(TIKZ, encoding="utf-8")
    chapter = dest / "notes" / "chapter1.qmd"
    chapter.write_text(chapter.read_text(encoding="utf-8") + CODE_CELL, encoding="utf-8")


def check_extras(dest: Path) -> list[str]:
    figs = dest / "sheets" / "problem-sheets" / "problem-sheet-1" / "figs"
    return [f"TikZ figure not built: {name}" for name in ("test-figure.pdf", "test-figure.svg")
            if not (figs / name).exists()]


def check_leak_detected(dest: Path) -> None:
    """Plant a staff copy of a solution in the student build: the leak check must fail."""
    staff = dest / "_build" / "staff" / "sheets" / "problem-sheets" / "problem-sheet-1"
    planted = dest / "_build" / "student" / "sheets" / "problem-sheets" / "problem-sheet-1"
    copy = planted / "problem-sheet-1-solutions-STAFF.html"
    shutil.copy(staff / copy.name, copy)
    run(["uv", "run", "scripts/leak_check.py"], dest, expect_failure=True)
    copy.unlink()
    run(["uv", "run", "scripts/leak_check.py"], dest)


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
    if name == "small":
        add_extras(dest)
    if builds:
        run(["uv", "sync"], dest)
        for profile in builds:
            run(["uv", "run", "scripts/build.py", profile], dest)  # includes the leak check
    if name == "small":
        problems += check_extras(dest)
        check_leak_detected(dest)
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
