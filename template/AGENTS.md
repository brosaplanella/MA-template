# AGENTS.md

Guidance for coding agents working in this repository. Read README.md for the user view.

## What this is

A module's teaching materials in Quarto: lecture notes (book), problem sheets and assignments,
each rendered to PDF and HTML, sharing one style layer. Assignment solutions are the only
sensitive material. Created from the MA-template copier template
(https://github.com/brosaplanella/MA-template); `.copier-answers.yml` records the setup.

## Repository map

```
_module.yml        module settings, deadlines, release flags (committed)
_local.yml         per-machine overrides (gitignored, optional)
_shared/
  template.lua     main filter: macros, marks, marking, difficulty, release control, banner, marker
  sheet.lua        {{< sheet key >}} and {{< notes label >}} shortcodes
  common.lua       config loading + sheet identification (used by both .lua files)
  macros-template.tex  shipped maths macros (\dd, \dv, \pdv, \bfx...); template-owned
  macros.tex       the module's maths macros; a name defined here replaces the template's.
                   Both are injected into PDF and HTML by template.lua
  palette.yml      brand colours + roles (accent, alert); source for generated/
  generated/       palette.tex, theme-light.scss, theme-dark.scss (from scripts/palette.py);
                   notes-xref.json (from scripts/notes_xref.py); committed, do not edit
  preamble*.tex    LaTeX (common / notes / sheet); partials/before-body.tex = sheet title block
  style.css        HTML styling (uses --accent, --brand-* from generated/)
  header-*.qmd     editable header boxes, included by sheets
notes/             Quarto book project -> _build/student/notes
  _freeze/         stored code-cell results (freeze: auto; committed)
sheets/            Quarto default project; profiles: student (default), staff
  _quarto-student.yml / _quarto-staff.yml   output dirs and post-render hooks
src/moduletools/   figure helpers (apply_style, set_zero_axes, colours, tint); installed
                   editable by `uv sync`, so `import moduletools` works in any code cell
<project>/**/figs/*.tex   standalone TikZ figures -> .pdf/.svg (committed, reproducible)
scripts/
  moduleconf.py    Python twin of common.lua (keep in sync)
  leak_check.py    checks _build/student for staff/unreleased material
  post_render_student.py / post_render_staff.py   Quarto hooks
  build.py, make_upload.py
  palette.py       palette.yml -> _shared/generated/ (pre-render hook of both projects)
  tikz.py          figs/*.tex -> .pdf + .svg when changed (pre-render hook of both projects)
  notes_xref.py    notes/.quarto/xref (Quarto internal) -> label map for {{< notes >}}
                   (post-render hook of the notes)
```

Template-owned files start with a "Template file: do not edit it in a module" line; the list
of module-owned files is in README.md ("Template and module files"). **In a module, do not edit
template-owned files**: `uvx copier update` would overwrite or conflict with the change.
If template behaviour must change, describe the change for an issue on the template
repository instead.

## Commands

```
uv sync                                   # once
uv run scripts/build.py                   # student build + leak check + _build/upload
uv run scripts/build.py staff             # staff build
uv run scripts/build.py student --only sheets
uv run scripts/leak_check.py              # check _build/student
uv run scripts/build.py --refresh         # clear notes/_freeze, re-run all notes code
uv run scripts/tikz.py --force            # rebuild all TikZ figures
cd sheets && uv run quarto preview <file> # preview (uv run: project Python for code cells)
```

Rendering the sheets takes about a minute; the PDF engine is pdflatex. `build.py` empties each
output folder before rendering (Quarto does not clean output dirs outside the project) and sets
QUARTO_PYTHON to the project environment. Images are referenced without extension
(`default-image-extension`: pdf for PDF, svg for HTML).

## How release control works

- A sheet is identified by its path: `sheets/<kind>/<id>/<id>[-solutions].qmd`.
- `template.lua` in a student build (any profile other than `staff`) replaces the content of
  unreleased solutions with a placeholder; `post_render_student.py` deletes the placeholder,
  then runs the leak check and fails the render on any problem.
- Every sheet carries a marker (`ma-template-doc kind=… id=… role=… build=…`) in an HTML
  `<meta>` tag and the PDF info dictionary; `leak_check.py` reads it.
- Do not use per-profile `render:` lists to exclude files: Quarto then treats an excluded file as
  a standalone document, and rendering it by name skips the project filters.

## Hard rules

1. Never weaken the leak check, the withholding in `template.lua`, or the student default profile
   without the author's explicit approval.
2. Never commit build outputs (`_build/`), `_local.yml`, or anything from `_scratch/`.
3. Never read, list or search outside this repository. Exam material lives elsewhere and must
   never be accessed. Ask the author if a task seems to need it.
4. Never edit `.copier-answers.yml` or template-owned files (see above).
5. Cross-platform: Python with `pathlib` and explicit UTF-8; no bash/PowerShell-only logic, no
   symlinks. Watch file-name case.
6. Keep `common.lua` and `moduleconf.py` consistent.
7. Keep migration separate from content changes. Work in small reviewable commits; verify both
   builds and the leak check before handing over.
