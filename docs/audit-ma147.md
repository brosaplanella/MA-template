# Audit of MA147 (Phase 1, second pass)

**Sources** (all read-only; nothing in `reference/` was modified, built or rendered):

| Folder | What it is | Tracked by git? |
|---|---|---|
| `reference/MA147` | Lecture notes. Quarto **book** at `3791ced`, 29 files. Public GitHub repo. | Yes (own repo) |
| `reference/Assignments` | 4 assessed assignments. Quarto **default** project, 8 `.qmd` files, plus `Old assignments/` (the LaTeX originals). | No (no `.git`; only `.quarto/` and `_output/` build state) |
| `reference/Problem sheets` | 10 unassessed problem sheets (6 written, 4 stubs). Quarto **default** project, 20 `.qmd` files, plus `Old problem sheets/` (LaTeX). | No |

**Categories:**

- **Generic**: goes into the template.
- **Module**: specific to MA147 and stays behind.
- **Content**: lecture material; the template gets a small placeholder that shows the same pattern.
- **Shared**: generic *and* needed by more than one document type. This is the new category in
  this pass, because "consistent across templates" is decided here.

---

## 1. Summary

1. **There are three separate Quarto projects with two separate design lineages.**
   - The **notes** are a book: `scrbook`, Bootswatch flatly/darkly, KaTeX, blue links, no
     shared filter.
   - The **sheets** (assignments + problem sheets) are articles: `fancyhdr` running header,
     sans-serif headings, an aubergine accent colour, the default HTML math engine (MathJax),
     a Lua filter, self-contained HTML.
   - The two sheet projects are near-copies of each other, kept in sync **by hand**
     ("If you change the macros or styling in one project, copy the file to the other"), and
     they have already drifted: difficulty icons exist only in the problem sheets.
2. **The sheets are the more generalised half.** Their `_shared/` folder is close to what the
   template needs:
   - one macro file injected into both PDF and HTML;
   - a filter for marks, marker notes and centred/info boxes;
   - a `hide-marking` switch;
   - a mark-total checker;
   - a "CONFIDENTIAL" banner driven by a `solutions: true` flag;
   - module/term metadata set once in `_quarto.yml`.

   The notes have **none** of this. Their `macros.qmd` (99 macros from another module) is
   entirely unused.
3. **There is still no release mechanism, but there are the building blocks for one.**
   - Assignment solutions are separate files with `solutions: true`, which adds the banner.
   - `hide-marking: true` strips the marks and marker notes.

   Together these are almost exactly the "student build of a released solution": turn off the
   confidential banner, strip the marking, add a "released on" banner. What is missing is the
   per-assignment flag, the student/staff split of the *outputs*, and the leak check. Right
   now `_output/assignment-1/` holds `assignment-1.pdf` and `assignment-1-solutions.pdf` side
   by side, so the brief's main risk ("distributing the wrong build") is live today.
4. **The three projects are coupled through the author's local folder layout.** Two assignment
   solutions do `sys.path.insert(0, "../../Lecture notes")` to import `utils.py`. Sheets refer
   to "Example 4.4", "Example 2.13", "Algorithm 2.1" **of the notes by hard-coded number**.
   Both break silently when the notes move or are renumbered. This is a strong argument for
   one repo holding all three types.

---

## 2. What is shared vs. per type (the consistency map)

This is the core input for the template design.

| Concern | Notes today | Sheets today | Template proposal |
|---|---|---|---|
| Module metadata (code, title, term, author) | Hard-coded in `_quarto.yml` + `index.qmd` | `module`, `module-code`, `term` in each `_quarto.yml` (duplicated ×2) | **Shared**: one `_module.yml` |
| Maths macros | `macros.qmd` (unused), hand-typed `\mathrm{d}` ×482 | `_shared/macros.tex` (9 macros; `\dv` used 141×, `\dd` 71×, `\eps` 29×), injected by the filter into PDF + HTML | **Shared**: one `macros.tex` via the sheets' mechanism, for all types |
| Macro names | `\bbR`, `\dd`, `\bfx` | `\mbR`, `\dd`, `\dv` | Pick one set (they clash: `\bbR` vs `\mbR`) |
| HTML math engine | KaTeX | MathJax (Quarto default) | **Shared**: one engine; macros must work in it |
| Colours / visual identity | Bootswatch + blue links | `ma147accent` aubergine + `ma147alert` red | **Shared** palette, defined once for LaTeX and CSS |
| Lua filter | none | `_shared/ma147.lua`, two diverged copies | **Shared**: one filter (or a few small ones), features switched by metadata |
| Figure style (matplotlib) | `utils.apply_style()` (sans, no serif) | inline `rcParams.update({"font.family": "serif", "mathtext.fontset": "cm"})` in 9 places, *plus* `apply_style()` in 2 | **Shared**: one style function, imported normally (no `sys.path` hack) |
| Figure helpers | `utils.py` | reached via `../../Lecture notes` | **Shared** Python package |
| TikZ figures | `figs/*.tex`; `make_svg.bat` makes PDF + SVG; `.svg` referenced (PDF goes through rsvg-convert) | `.tex` next to the sheet; compile commands are in a comment; `.content-visible when-format` used to pick `.pdf` vs `.svg` | **Shared**: one Python build script, and one way to reference a figure so each format picks its own file |
| Cross-references between documents | n/a | "Example 4.4 of the lecture notes" typed by hand | **Shared**: needs a mechanism (see Q6) |
| Output layout | `docs/` (book) | `_output/<sheet>/` with student and marker files mixed | **Shared**: `_build/student/`, `_build/staff/` (brief) |
| HTML packaging | Folder of files, zipped by `make_zip.bat` for Moodle | `embed-resources: true` (one `.html` per sheet, "easy to upload to Moodle") | Per type (book can't be single-file) |
| Banner for sensitive content | none | `solutions: true` → red "CONFIDENTIAL – FOR MARKERS ONLY" (PDF + HTML) | **Shared**: the brief's banner, `-STAFF` suffix |
| Document class / layout | `scrbook`, chapters, TOC | `article`, 25 mm margins, 11pt, running header "module – title | term", "Page x of y" | **Per type** |
| Question structure | n/a | `## Question N: Title`, parts as `(a)` lines, nested parts indented 4 spaces | **Shared** between all sheet-like types |
| Marks | n/a | `[2]{.marks}` (right-aligned), `## Question 1 [8]{.marks}` → "[8 marks]", total checked | Assignments (and future exams-style sheets) |
| Marker notes | n/a | `[..]{.marking}` / `::: {.marking}`, removed by `hide-marking` | Assignments |
| Difficulty | n/a | `[1–3]{.difficulty}` → 1–3 spring icons (TikZ in PDF, SVG in HTML) | Problem sheets; the icon is MA147 flavour (see §5) |
| Header box | n/a | `_shared/header-sheet.qmd` (deadline + Moodle submission / "not for credit") | Per type, text from settings |
| Marker instructions | n/a | `_shared/header-solutions.qmd` (hard-codes "20 marks + 5 for clarity") | Assignments; numbers from settings |
| "Examinable" box | `callout-important` | n/a | Notes |
| Theorem-like blocks | `#def-`, `#thm-`, `#lem-`, `#exm-`, `#rem-`, `#alg-`, `.proof` | none | Notes (could be available to sheets) |

---

## 3. File-by-file

### 3a. Lecture notes (`reference/MA147`)

Unchanged from the first pass, condensed here.

| File | Category | Notes |
|---|---|---|
| `_quarto.yml` | Generic skeleton, Module values | book, `output-dir: docs`, `freeze: auto` + `cache: true`, KaTeX, flatly/darkly, `scrbook` A4 pdflatex. |
| `index.qmd` | Module + Content | Preface. The *section skeleton* (about, where to find, changelog, reading list, aims, structure) is generic. |
| `1-introduction.qmd` | Content, partly generic | Explains the "boxed = examinable" convention. |
| `2-…` to `6-*.qmd` | Content | 7,100 lines. |
| `macros.qmd` | Drop | 99 macros, 0 used. Replace with the shared `macros.tex`. |
| `utils.py` | Shared | `apply_style`, `set_zero_axes` (generic); bifurcation, cobweb, Euler and phase-portrait helpers (generic for dynamics, already used by assignments); `plot_covid_data` (Module). `usetex=True` in `plot_phase_portrait`. |
| `styles.css` | Generic | One rule. |
| `make_svg.bat`, `make_zip.bat` | Shared, rewrite in Python | Windows only. |
| `coffee_cup.ipynb` | Content | Companion notebook, not in the book. |
| `figs/*` | Content | `centre.png` is an orphan. `ukhsa-covid-data.csv` is read with `"figs\\…"` (a Windows-only path, 7×). |
| `CHANGELOG.md` | Generic practice | Dated, student-facing. |
| `README.md` | Module, **wrong** | Says MA302. |
| `.gitignore` | Generic | |
| `.github/workflows/*` | Rewrite / Drop | The CI installs no Python. The publish workflow targets gh-pages (commented out). |
| `.nojekyll`, `_freeze/site_libs/…` | Drop | Leftovers from MA302. |

### 3b. Sheets (`reference/Assignments`, `reference/Problem sheets`)

| File | Category | Notes |
|---|---|---|
| `_quarto.yml` (×2) | Generic skeleton, Module values | `type: default`, `output-dir: _output`, `render:` glob limited to `assignment-*/*.qmd` / `problem-sheet-*/*.qmd` (so old `.tex` and READMEs are skipped). `module`/`module-code`/`term` (the comment says "update once per year"). The problem-sheets copy sets `hide-marking: true`. PDF: `article` A4 11pt 25 mm, `template-partials: before-body.tex`, `include-in-header: preamble.tex`. HTML: `embed-resources`, `css`, no TOC. No `html-math-method`. |
| `README.md` (×2) | Generic (excellent) | Already colleague-friendly: commands, the shared-file table, "LaTeX → Quarto" writing tips. This is the seed for the template's author guide. |
| `_shared/ma147.lua` | **Shared, generalised** | Features: injects macros into PDF and HTML; builds the HTML subtitle from module + term; makes `.center`/`.infobox`/`.marking` divs work in PDF; full-width `---` rules; marks formatting; total check (warns); `hide-marking`; HTML confidential banner. The problem-sheets copy adds difficulty icons. MA147-named, but the logic is generic. It relies on the title convention `"… -- Solutions"` to build the running header. |
| `_shared/macros.tex` | Shared mechanism, Module list | `\newcommand` one per line, `%` comments skipped. Read by the filter, so it works in both formats. **This answers the first pass's open question about macros in PDF.** |
| `_shared/preamble.tex` | Shared (rename colours) | amsthm, fancyhdr, lastpage, sectsty, tcolorbox; `infobox`, `markingbox`, `\marksbox`; spring icon (problem sheets only). Starts with a UTF-8 BOM (harmless, but strip it). |
| `_shared/before-body.tex` | Shared | Replaces `\maketitle`: running header/footer, coloured title, red confidential line if `solutions`. |
| `_shared/style.css` | Shared | HTML equivalents of the above. Colours are duplicated as hex (`#3b2d66`, `#9c95b3`, `#f7f6fa`, `#b00020`). |
| `_shared/header-sheet.qmd` | Per type, Module text | Assignments: deadline + "upload via Moodle … single PDF" + `{{< meta instructions >}}`. Problem sheets: "not for credit" + difficulty legend. |
| `_shared/header-solutions.qmd` | Per type, Module text | Marker instructions with `{{< meta marked-questions >}}`, but "total: 20 marks, plus 5 for clarity" is hard-coded. |
| `assignment-N/assignment-N.qmd` | Content | YAML: `title`, `deadline` (free text, e.g. "15/10/2026, Thursday (week 2), 12 noon (UK time)."), `instructions` (same text in all 4). Questions only, **no marks shown to students**. |
| `assignment-N/assignment-N-solutions.qmd` | Content (**sensitive**) | YAML: `title`, `marked-questions`, `solutions: true`, sometimes `jupyter: python3`. Holds solutions only (the question text is not repeated) under `## Question N [marks]`. Uses `.marks`/`.marking`. Two files reach `../../Lecture notes/utils.py`. |
| `problem-sheet-N/*.qmd` | Content | Same pair structure. Solutions are student-facing (no flag). Sheets 7–10 are 9–13 line stubs. Sheet 6 has TikZ `.tex` + committed `.pdf`/`.svg` and uses `.content-visible` to pick the format. |
| `problem-sheet-zz/` | Drop | Empty folder. Its freeze cache (`problem-sheet-zz/t`) shows it was a scratch test. |
| `Old assignments/`, `Old problem sheets/` | Module (archive) | The LaTeX originals with `.aux`/`.log`/`.synctex.gz`/`.pdf` and raster images (`.jpg` and `.png` duplicates). Their preambles define the same macro *names* as the sheets (`\mbR`, `\eps`, …), which is where those names come from. They are not template material, and probably not repo material either (see Q4). |
| `_output/`, `.quarto/` | Drop (gitignore) | Build output and cache. `_output` currently contains the **marker solutions**. |

---

## 4. Already generalised (flag list)

| Item | Where | State |
|---|---|---|
| Macros in both formats | sheets `macros.tex` + filter | **Working and generic.** Adopt for all types. |
| Mark formatting + total check | sheets filter | Generic. Keep. |
| Marker notes + `hide-marking` | sheets filter | Generic, and it is the core of the "released solutions" student build. |
| Confidential banner via `solutions: true` | sheets filter + `before-body.tex` | Generic. Needs the `-STAFF` suffix, a staff-only output dir and the "released on" variant. |
| Module metadata in config | sheets `_quarto.yml` | Generic, but duplicated. Move it to `_module.yml`. |
| Info box / centred div with PDF parity | sheets filter + preamble + CSS | Generic. |
| Difficulty rating | problem-sheet filter | Generic *idea*; the spring icon is MA147 flavour. |
| Figure style + helpers | notes `utils.py` | Generic, but the sheets don't use it consistently. |
| TikZ → PDF + SVG | notes `make_svg.bat`, sheet `.tex` comments | Two ad-hoc versions; one uses `--no-fonts --exact-bbox`. Unify. |
| Single-file HTML for Moodle | sheets `embed-resources` | Generic for sheet-type documents. |
| Zip of book HTML for Moodle | notes `make_zip.bat` | Generic; rewrite. |
| Render scope via `project.render` globs | sheets | Generic. It keeps archives and READMEs out of the build. |
| Author docs ("writing tips") | sheets README | Generic. Seed for the template docs. |
| Release mechanism (`solutions_released`, `release_date`) | — | **Does not exist.** |
| Student/staff profiles, leak check, private-repo guard | — | **Do not exist.** |

---

## 5. Things that quietly assume first-year maths (or MA147)

- **Notes**:
  - the "boxed = examinable" promise;
  - A-Level references;
  - "Week 6 breathing week";
  - module URLs with the year in them;
  - hand-typed notation;
  - `usetex=True`.
- **Assignment rubric**: "two of three questions marked, out of 20, plus 5 for clarity", hard-coded in a shared header. Other modules (and MA302) will differ, so it needs to come from settings.
- **Submission text**: "upload via Moodle … single PDF … typed or scanned". This is Warwick-specific; make it a setting with this as the default.
- **Deadlines**: free text with Warwick week numbers ("Thursday (week 2), 12 noon (UK time)"). Fine to display, but it should be *data* (a date plus an optional label), so release dates and checks can use it.
- **Question shape**: `## Question N` with `(a)`, `(b)` parts. This assumes short-answer calculus-style questions; it's fine for most maths. Sheets have no theorem/proof environments; a proof-heavy (pure) module would want `.proof` and theorem blocks in sheets too.
- **Difficulty icons are springs**: a mechanics joke that suits MA147/MA302. Make the glyph configurable (default: stars or plain numbers).
- **Figure style**: serif + Computer Modern mathtext in the sheets versus sans in the notes. Neither is wrong, but the two document types will look different side by side.
- **Python everywhere**: every sheet that plots needs `jupyter: python3` (it's a default project, so there is no auto-detection). A module with no figures should need no Python.
- **"Solutions" in the title**: the running header strips `-- Solutions` / `– Solutions` from titles with a regex. This assumes English titles and that exact convention.

---

## 6. Beyond the three types ("and even more")

The same infrastructure (macros, filter, palette, figure style, banners, release flags) covers
these with little extra work. Listed only so the design leaves room for them, not for v0.1:

- **Worksheets / class handouts**: like problem sheets, possibly with gaps to fill in.
- **Formula sheet / cheat sheet**: single page, no solutions.
- **Computer labs / companion notebooks** (`coffee_cup.ipynb`): `.ipynb` or `.qmd` rendered to HTML.
- **Mock / practice exams**: *sheet-type with marks* (same filter as assignments), but **real
  exams stay out** per the brief, so a "mock" type must not become a back door.
- **Slides**: the brief puts PowerPoints outside, but Quarto `revealjs`/`beamer` would reuse the
  macros and palette if you ever want them.

A useful way to frame it: there are **two layouts** (book, sheet), **one shared style
layer**, and **per-type switches** (marks, marker notes, difficulty, header box, solutions
audience). A new type should be "a new switch combination", not a new copy of `_shared/`.

---

## 7. Risks, surprises and questions

### Risks

1. **Wrong build distributed: this is live today.** `_output/assignment-N/` mixes
   `assignment-N.pdf` and `assignment-N-solutions.pdf` (with self-contained HTML of both).
   Uploading a folder, or picking the wrong file, sends the marker solutions. The banner
   helps, but the filenames don't differ enough (`-solutions` is what the brief reserves for
   *released* student solutions, so the staff ones need `-STAFF`).
2. **The sheets have no version control.** Neither sheet folder is a git repo (there's no `.git`
   in either; they're only visible as ignored paths of MA-template). If that's true for your
   real copies too, the only history of the assignment solutions is OneDrive.
3. **Copy-and-sync drift.** The two `_shared/` folders have already diverged. A third copy for
   notes, and a fourth for MA302, would make this worse. The template should make sharing
   structural (one repo, or one shared folder), not manual.
4. **Breakable coupling**: the `../../Lecture notes` path hack and hard-coded "Example 4.4"
   references. Folder names with **spaces** ("Lecture notes", "Problem sheets", "Old
   assignments") also invite quoting bugs in scripts and CI on all three OSes.
5. **Public notes vs. private solutions.** You confirmed the MA147 GitHub repo is the lecture
   notes only, and it is public and linked to students. The brief wants the template repo
   private because it holds assignment solutions. Putting all three types in one repo (good
   for consistency) means the notes source stops being public. See Q1.
6. **Carried over from the first pass**:
   - The notes CI likely can't pass on Linux (no Python step; `figs\\…` paths).
   - `freeze` + `cache` won't notice changes to `utils.py`.
   - MA147's git history still contains MA302 files, including a file named
     `figs/short_term_academic_leave_form.pdf`. You said the repo is just lecture notes; it
     may be worth a one-minute check that this file is a blank form, since the history is
     public.

### Surprises

- The sheets already solve the problem the brief calls "macros in both formats". The notes
  should adopt the sheets' approach, not the other way round.
- `hide-marking` already turns an assignment solution into a student-safe document. The release
  feature is maybe 70% there.
- Students never see per-question marks in the assignment *sheets*; marks live only in the
  solutions.
- Problem-sheet solutions are student-facing but currently have no "released" notion at all.
  Are they released with the sheet, or a week later?

### Questions for you

1. **One repo or several?** I'd recommend one private repo per module containing notes, problem
   sheets and assignments (shared settings, macros, filter, utils; real cross-references). The
   cost is that the notes source is no longer public; students get the built notes via Moodle
   as now. Is that acceptable, or must the notes source stay public (which means two repos:
   public notes + private sheets, sharing a template)?
2. **Problem-sheet solutions**: do they need release control too (released per sheet, like
   assignments), or are they always public once written? Do they ever contain anything
   staff-only?
3. **Settings format**: is it OK to move `deadline` and `release_date` into `_module.yml` as a
   per-assignment list (date + optional "week N" label), so the sheet header, the release flag
   and the leak check all read the same entry?
4. **Old LaTeX folders**: should they go in the repo (e.g. an `archive/` folder outside the render
   scope), or stay in OneDrive with the exams?
5. **One look or two?** Should the notes adopt the sheets' visual identity (accent colour, sans
   headings, serif figures), should the sheets adopt the notes', or should each keep its
   layout but share palette, macros and figure style?
6. **Cross-references to the notes** from sheets ("Example 4.4"): worth solving in v0.1 (only
   feasible in a single repo, e.g. via a generated label→number map), or park it and keep
   hand-typed numbers?
7. **Macro names**: adopt the sheets' set (`\mbR`, `\dv`, `\dd`, `\eps`; they also match your old
   LaTeX), drop the notes' unused `macros.qmd`, and leave the notes' hand-typed `\mathrm{d}`
   as is (converting it would be a content change)?
8. **Math engine**: standardise on MathJax (the sheets' current default, more LaTeX-compatible)
   or KaTeX (the notes, faster)?
9. **Difficulty glyph**: keep springs as the default, or make the template neutral (stars or
   numbers) with springs as MA147's override?
10. Are there other document types you already produce, or plan to, that should be in the first
    design (worksheets, formula sheet, labs, mock exams)?

Still not building anything until you've reviewed this.
