# Decisions log

Answers from the author to the questions in `audit-ma147.md`, plus the brief's open decisions.
Newest first. Each entry: date, decision, and any consequence for the template.

## 2026-11-05: template and module files (#10)

- `_shared/module.lua` is renamed `_shared/template.lua`: it is template code, the same in
  every module.
- Module-owned: `_module.yml`, `_shared/macros.tex`, `_shared/palette.yml`,
  `_shared/header-*.qmd`, notes content and `notes/_quarto.yml`, sheets and figures,
  `pyproject.toml` (extra packages). Everything else in `_shared/`, `scripts/`,
  `src/moduletools/` and `sheets/_quarto*.yml` is template-owned and starts with a
  one-line marker. The list is in the README, for the copier wizard (#7) to follow.

## 2026-11-05: lists (#5)

- Parts are written `(a)`, `(i)`, ...; labels show as written in PDF and HTML, with a hanging
  indent. Indentation alone decides: indented by 4 spaces = in the part; unindented = context
  at the margin, and numbering continues. No warning and no extra markup.

## 2026-11-04: planning

- The plan and to-do list live in the GitHub issues, grouped by milestone (with the dates from
  the brief's schedule). This log keeps the decisions only.
- Editor agents come after the MA302 port (#14). Conventions in two layers: general ones in a
  separate Claude Code plugin repository, module-specific ones in `docs/conventions.md`.
- Plugin evals run locally on the author's Claude Pro allowance; no eval in CI for now.
- Copier wizard before the MA302 port, so MA302 is created with it (#7); updating existing
  modules with `copier update` later (#13).

## 2026-11-04: Python

- All Python dependencies (build scripts, Jupyter for code cells, numpy, matplotlib, qrcode) are
  regular dependencies in `pyproject.toml`: one `uv sync` sets up everything. Chapter 3 of the
  placeholder notes (code, QR codes) is now rendered.
- Notes use `freeze: auto`; `notes/_freeze/` is committed. `build.py --refresh` clears it.
  Sheets are not frozen (they are small).
- Figure helpers are a package, `src/moduletools`, installed editable by uv (replaces the
  `sys.path` hack). Generic parts of MA147's `utils.py` only (`apply_style`, `set_zero_axes`),
  plus palette access; the dynamics helpers stay with MA147/MA302. Figures use a Palatino-like
  serif with Computer Modern maths, to match the PDF. Brand colour cycle is opt-in
  (`apply_style(brand_cycle=True)`) because most brand colours are light.
- TikZ: `figs/*.tex` anywhere in notes/ or sheets/, built to .pdf + .svg by `scripts/tikz.py`
  (pre-render hook, only when changed, reproducible output; committed). Images are written
  without extension and `default-image-extension` picks .pdf (PDF) or .svg (HTML), replacing
  MA147's duplicated `content-visible` blocks.

## 2026-11-04: palette

- Brand colours in `_shared/palette.yml` (purple, lavender, coral, blue, green, yellow, black),
  given at 100%. Tints = mix with white in sRGB (matches the brand guide to within rounding).
- "Aubergine" is called purple, as in the brand guide.
- Body text keeps the default black (not brand black `#0C0C0C`).
- Accent: purple; dark-mode accent: brand lavender (6.4:1 on darkly), replacing the
  provisional `#BB99E6`. Alert red stays non-brand (`#B00020` / `#FF6B81`).
- LaTeX/CSS names are prefixed `brand-`, because xcolor already defines blue, green, purple, black.
- `scripts/palette.py` generates `_shared/generated/` (committed) and runs as a pre-render hook.

## 2026-11-04: implementation choices in v0.1-core (for review)

- **Layout**: two Quarto projects, `notes/` (book) and `sheets/` (problem sheets and
  assignments together), sharing `_shared/`. A sheet is identified by its path
  `sheets/<kind>/<id>/<id>[-solutions].qmd`; no front-matter flags needed.
- **Release control** is done by the filter, not by per-profile render lists: Quarto treats a
  file excluded from `render:` as a standalone document, so rendering it by name would skip the
  filters and write unmarked output next to the source. In a student build, unreleased solutions
  render as a placeholder that the post-render hook deletes, so solution text never reaches
  `_build/student/`.
- **Setting names** are kebab-case (`solutions-released`, `release-date`) to match Quarto's own
  options, instead of the brief's `solutions_released`.
- **Staff build marks every file** `-STAFF` (question sheets too) with a red banner: simpler
  rule, "nothing from `_build/staff` is ever uploaded".
- **Student build strips marks and marker notes** from released solutions.
- **Entry point** is `uv run scripts/build.py` (Python), with Quarto post-render hooks doing the
  leak check, so plain `quarto render` in `sheets/` is also safe.
- **CI** only checks that the repository is private (via the API, also weekly).
- **Fonts**: Domitian (Palatino-like) in PDF needs pdflatex, set explicitly. HTML keeps
  flatly/darkly fonts. Headings serif in aubergine in both notes and sheets (the MA147 sheets
  used sans headings).
- **Dark mode accent**: `#BB99E6` (6.7:1 on darkly's background); the aubergine is 1.2:1.

## 2026-11-04 (later): follow-up answers

- **Builds are local.** CI does not need to build the documents. This replaces the brief's
  ubuntu/windows/macos build matrix. CI keeps only cheap checks (the private-repo guard).
  Cross-platform support still matters, because colleagues build on their own machines.
- **Accent colour**: Warwick aubergine `#440379` is the default accent. The author will provide
  the full university brand palette for other uses. Dark mode needs a lighter variant for
  contrast.
- **Old material folder**: not an archive but a local scratch area for old versions kept at hand
  while rewriting, then deleted. Gitignored, outside the render scope, no backup expected.
- **Release**: manual flag only (`solutions_released`). No automatic release by date; the date
  is display-only. The student build and leak check still run locally.
- **Maths engine**: MathJax.
- **GitHub repo** `brosaplanella/MA-template` is private.

## 2026-11-04: answers to the Phase 1 audit

### Brief's open decisions
- **Hosting**: Moodle. Outputs are zipped and uploaded (MA147 used `make_zip.bat`).
  Streamlining this matters: the template gets a cross-platform Python zip step that only ever
  packages the **student** build.
- **GitHub organisation**: none in the department (may come later). Repos live on personal
  accounts, so there is no org policy that blocks making a repo public. The private-repo CI
  guard is therefore the only automated safeguard.

### Audit questions
1. **Repo layout**: one private repo per module containing notes, problem sheets and
   assignments. The notes source is no longer public.
2. **Problem-sheet solutions**: the author releases them one week after the sheet; other
   lecturers release them with the sheet. The template must support both, with the release
   policy set per module and overridable per sheet.
3. **Deadlines and release dates**: move into `_module.yml` as a per-document list
   (date + optional label such as "week 2"). The release flag and leak check were explained to
   the author on 2026-11-04.
4. **Old LaTeX folders**: removed from the module repos. Author suggested an empty gitignored
   `archive/` folder in the template. Open point: a gitignored folder in a repo that lives
   outside OneDrive has no backup at all (see "Open").
5. **Look and feel**: one unified style across notes, problem sheets and assignments. Use
   `reference/QuartoLectureNotesTemplate` (T. Hudson, MIT licence) as an input for the style.
6. **Cross-references from sheets to notes**: wanted. Design for it in v0.1.
7. **Macros**: the template ships an empty `macros.tex` (the mechanism works, the content is
   up to each lecturer).
8. **Maths engine**: author asked for pros and cons; recommendation given (MathJax), awaiting
   confirmation.
9. **Difficulty glyph**: neutral default (stars), overridable per module (MA147/MA302: springs).
   The template ships stars and numbers only; a module supplies its own icon as an image
   (MA147/MA302: a spring TikZ figure in the module repo, not in the template).
10. **Other document types**: not for now. Occasional Jupyter notebooks live in the repo;
    suggest light integration. Embedded interactive tools may come later (already parked).

### Open (awaiting the author)
- Full university brand palette (the author will send it).
- Resolved on 2026-11-04 (later): old-material folder, maths engine, release by flag only.
