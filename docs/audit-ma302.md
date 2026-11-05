# Audit of MA302 (light, before the port)

For #9. What in MA302 does not fit the template yet, and what the port (#11) will involve.
Lighter than `audit-ma147.md`: the template now exists, so this only lists differences.

**Sources** (read-only; nothing in `reference/` was modified, built or rendered):

| Folder | What it is |
|---|---|
| `Lecture notes/` | Quarto **book**, 9 chapters (3,500 lines), `macros.qmd`, 16 TikZ figures, GitHub Pages workflows, `CHANGELOG.md` |
| `Problem Sheets/` | **LaTeX**: PS1 to PS8, each with a `_Solution.tex`, one `preamble.tex`, 3 Python scripts for PNG figures |
| `Slides/`, `Vevox/` | PowerPoint and quiz images: outside the template's scope, not audited |
| Top-level PDFs | `Given information.pdf` and two `MA302-Electromagnetism …pdf` files: **not opened** (possibly exam-related) |

An `Exam/` folder was in the first copy; the author removed it before any file was read.

---

## 1. Summary

1. **The notes fit the template almost as they are.** Same project type (book, `scrbook`,
   flatly/darkly), and the same Quarto features the template already supports: theorem-type
   divs (`def`, `thm`, `prp`, `exm`, `rem`, `cor`, `lem`, `proof`), `callout-tip` ("Aims of the
   chapter"), cross-references (148 to equations), `layout-ncol` figures, two Python cells,
   `freeze: auto`. The port is mechanical (section 3).
2. **The problem sheets are LaTeX, not Quarto.** 16 files to convert. This is the bulk of the
   port, and the one place where a tool would pay off (section 4, question 1).
3. **No template feature is missing for MA302.** The gaps are conversions (macros, figures,
   sheet format), not new features. The `physics` package worry from #10 does not arise
   (section 2).
4. **There are no assignments** in the reference copy, only problem sheets (question 2).

## 2. Maths and macros

- Notes: `macros.qmd` (a hidden div, included at the top of every chapter) defines 99 macros
  with `\providecommand`; **31 are used**: mostly bold vectors (`\bfr` 596 times, `\bfE`,
  `\bfB`, ...) and `\dd` (287). The sheets' `preamble.tex` repeats the bold vectors and `\dd`.
  → One `_shared/macros.tex` for both, with `\newcommand` (the format `macros.tex` documents);
  drop the `{{< include macros.qmd >}}` lines. Decide whether to keep the 68 unused macros
  (question 3).
- The notes use KaTeX; the template uses MathJax. Only `aligned` and `cases` environments and
  common commands are used, so no change is expected; check the rendered notes once.
- Sheets load `physics`, but of its commands they only use `\dd`, and because `physics` is
  loaded first, the preamble's own `\dd` never takes effect. With `\dd` in `macros.tex`,
  `physics` is not needed. `\sgn` (`\DeclareMathOperator`, used 10 times) becomes
  `\newcommand{\sgn}{\operatorname{sgn}}`. `marvosym` is only for the difficulty icon.
- Risk: a macro name that LaTeX already defines makes `\newcommand` fail in the PDF (the notes
  used `\providecommand`, which hides this). The first PDF build will show any; none of the
  31 used names looks like a clash.

## 3. Notes: what changes in the port

| MA302 | Template | Change |
|---|---|---|
| `{{< include macros.qmd >}}` in every chapter | `_shared/macros.tex`, injected by the filter | delete the includes |
| `![](./figs/x.svg)`, built by `make_svg.bat` (Windows only) | `figs/*.tex` → .pdf + .svg by `scripts/tikz.py`; images without extension | drop `.svg` from 17 image paths; delete the `.bat`. The PDF then uses vector PDFs instead of converting SVGs (no more `rsvg-convert`) |
| TikZ figures: `standalone`, `tikz`, `pgfplots`, `amsmath` | same | none expected; they use none of the note macros |
| Python cells set `text.usetex = True` | `moduletools.apply_style()` (mathtext, no LaTeX needed) | replace in the 2 cells |
| KaTeX, blue links, plain flatly/darkly | MathJax, palette accent | config only |
| `output-dir: docs`, GitHub Pages publish + test workflows | `_build/`, Moodle upload, leak check | question 4 |
| `CHANGELOG.md` (dated list of corrections) | nothing | question 5 |
| `_extensions/dialoa/imagify` | nothing | not used by any chapter: drop |
| `.vscode` cSpell word list | nothing | module-owned; spelling checks are parked in #16 |

## 4. Problem sheets: what changes in the port

The sheets are LaTeX articles with a shared preamble:

- Title block made by `\maketitle` from `\sheetnumber` and `\issolution`, plus the difficulty
  key → the template's title and `header-problem-sheet.qmd`.
- Questions are the items of a top-level `enumerate`, parts a nested `enumerate` (92 in all)
  → `## Question N` headings and `(a)` parts (the list rules from #5).
- Difficulty: `\easy`, `\medium`, `\hard` = 1 to 3 lightning bolts (`marvosym`) → `[1]{.difficulty}`
  etc. Keep the bolts with `difficulty-icon` (a small TikZ figure) or switch to stars
  (question 6).
- Solutions repeat the question numbering with the question text removed (`\item` then the
  parts) → solutions `.qmd` with the same headings.
- **About 18 hand-written references to the notes** in the solutions ("Definition 2.12 of the
  lecture notes", "equation (3.1) in the lecture notes", "Fig 5.2") → `{{< notes label >}}`,
  which keeps them right when the notes are renumbered. Needs the target labels in the notes
  (most exist: the notes already cross-reference definitions and equations).
- Figures: 4 PNGs in two solutions, made by `PS2-Q2.py` and `PS7-Q4.py` → Python code cells
  in the solutions (with `moduletools`), or TikZ. `Quizz2.py` belongs to the Vevox quizzes.
- Unused flag `\showanswers`; no marks (unassessed), no release dates: release flags go in
  `_module.yml` as for any module.
- Display maths: `$$ ... $$`, `align*`, `multline*`, `aligned`, `cases`, `pmatrix`: all fine
  in Quarto. One stray URL comment (PS3) should not be carried over.

## 5. Questions for the author

1. **Convert the sheets by hand or with a script?** Pandoc reads LaTeX and can do most of it
   (keeping the macros unexpanded); a short script would then turn top-level items into
   headings and `\easy` etc. into difficulty spans, leaving a review pass. If colleagues also
   have LaTeX sheets, the script could become a template tool (`scripts/import_latex.py`)
   rather than a one-off in `_scratch/`.
2. **Assignments**: does MA302 have assessed assignments that should move to the template too,
   or problem sheets only?
3. **Unused macros**: keep all 99 for future material, or only the 31 in use?
4. **Publishing**: the notes are published to GitHub Pages on every push to `main`. Keep that
   (the template would need a publish step for the notes only, never the sheets), or move to
   Moodle only like the template?
5. **Changelog**: worth a template feature (e.g. a "Changes" appendix in the notes, from a
   module-owned file), or keep it as a plain file in the module?
6. **Difficulty icon**: lightning bolts (custom icon) or the template's stars?
