# Decisions log

Answers from the author to the questions in `audit-ma147.md`, plus the brief's open decisions.
Newest first. Each entry: date, decision, and any consequence for the template.

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
10. **Other document types**: not for now. Occasional Jupyter notebooks live in the repo;
    suggest light integration. Embedded interactive tools may come later (already parked).

### Open (awaiting the author)
- Full university brand palette (the author will send it).
- Resolved on 2026-11-04 (later): old-material folder, maths engine, release by flag only.
