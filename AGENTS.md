# AGENTS.md

Guidance for coding agents working in this repository. Read README.md for the user view.

## What this is

A Quarto module template: lecture notes (book), problem sheets and assignments, each rendered to
PDF and HTML, sharing one style layer. Assignment solutions are the only sensitive material.

## Repository map

```
_module.yml        module settings, deadlines, release flags (committed)
_local.yml         per-machine overrides (gitignored, optional)
_shared/
  module.lua       main filter: macros, marks, marking, difficulty, release control, banner, marker
  sheet.lua        {{< sheet key >}} shortcode
  common.lua       config loading + sheet identification (used by both .lua files)
  macros.tex       maths macros, injected into PDF and HTML
  palette.yml      brand colours + roles (accent, alert); source for generated/
  generated/       palette.tex, theme-light.scss, theme-dark.scss (from scripts/palette.py; committed, do not edit)
  preamble*.tex    LaTeX (common / notes / sheet); partials/before-body.tex = sheet title block
  style.css        HTML styling (uses --accent, --brand-* from generated/)
  header-*.qmd     editable header boxes, included by sheets
notes/             Quarto book project -> _build/student/notes
sheets/            Quarto default project; profiles: student (default), staff
  _quarto-student.yml / _quarto-staff.yml   output dirs and post-render hooks
scripts/
  moduleconf.py    Python twin of common.lua (keep in sync)
  leak_check.py    checks _build/student for staff/unreleased material
  post_render_student.py / post_render_staff.py   Quarto hooks
  build.py, make_upload.py
  palette.py       palette.yml -> _shared/generated/ (pre-render hook of both projects)
docs/              development notes for the template (brief, audit, decisions)
reference/         read-only reference modules (gitignored); never modify
```

## Commands

```
uv sync                                   # once
uv run scripts/build.py                   # student build + leak check + _build/upload
uv run scripts/build.py staff             # staff build
uv run scripts/build.py student --only sheets
uv run scripts/leak_check.py              # check _build/student
```

Rendering the sheets takes about a minute; the PDF engine is pdflatex.

## How release control works

- A sheet is identified by its path: `sheets/<kind>/<id>/<id>[-solutions].qmd`.
- `module.lua` in a student build (any profile other than `staff`) replaces the content of
  unreleased solutions with a placeholder; `post_render_student.py` deletes the placeholder,
  then runs the leak check and fails the render on any problem.
- Every sheet carries a marker (`ma-template-doc kind=… id=… role=… build=…`) in an HTML
  `<meta>` tag and the PDF info dictionary; `leak_check.py` reads it.
- Do not use per-profile `render:` lists to exclude files: Quarto then treats an excluded file as
  a standalone document, and rendering it by name skips the project filters.

## Hard rules

1. Never weaken the leak check, the withholding in `module.lua`, or the student default profile
   without the author's explicit approval.
2. Never commit build outputs (`_build/`), `_local.yml`, or anything from `_scratch/`.
3. Never read, list or search outside this repository. Exam material lives elsewhere and must
   never be accessed. Ask the author if a task seems to need it.
4. Never modify `reference/`.
5. Cross-platform: Python with `pathlib` and explicit UTF-8; no bash/PowerShell-only logic, no
   symlinks. Watch file-name case.
6. Keep `common.lua` and `moduleconf.py` consistent.
7. Keep migration separate from content changes. Work in small reviewable commits; verify both
   builds and the leak check before handing over.
