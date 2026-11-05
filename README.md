# Module template (Quarto)

> **Moving to copier (#7):** the module now lives in [`template/`](template/); build it from
> there (`cd template`, then the commands below). This README is being split into a module
> README and one for template maintainers.

A template for a university module: **lecture notes**, **problem sheets** and **assignments**,
each produced as **PDF and HTML** from one source, with one shared style. Assignment solutions
live in the same repository but never reach students by accident.

> **Keep this repository private.** It holds assignment solutions. Git history is forever: a
> solution that was ever committed stays in the history even after you delete the file.

## What you need (once)

| Tool | Why | Install |
|---|---|---|
| [Quarto](https://quarto.org/docs/get-started/) | builds everything | installer from the website |
| A TeX distribution | PDF output | `quarto install tinytex`, or TeX Live / MiKTeX |
| [uv](https://docs.astral.sh/uv/) | Python: build scripts, code cells, figure helpers | see the uv website |

Then, once, in the repository folder: `uv sync`. This installs everything the build and the
code cells need (numpy, matplotlib, Jupyter, ...) into a project environment (`.venv/`).
On macOS/Linux, TikZ figures also need Ghostscript (`brew install ghostscript`, or your
package manager); TeX Live on Windows includes it.

Everything works on Windows, macOS and Linux.

### Where to keep this folder (OneDrive users)

Keep the repository **outside** OneDrive/SharePoint-synced folders (for example `C:\dev\MA000`).
Syncing clashes with Quarto's temporary files and with git. GitHub (private) is the backup:
commit and push at the end of every working session.

Material that is not Quarto (exams, scans, handwritten notes, slides) stays in your OneDrive
module folder, for example:

```
OneDrive/.../MA000/
  exams/        never in this repository
  slides/
  ...
C:/dev/MA000/   this repository (notes, problem sheets, assignments)
```

## Build

From the repository folder:

```
uv run scripts/build.py          # student build: notes + sheets, then the upload folder
uv run scripts/build.py staff    # staff build: everything, every file marked -STAFF
uv run scripts/build.py --refresh  # also re-run all code in the notes (see "Code and figures")
```

| Folder | Contents | Upload? |
|---|---|---|
| `_build/student/` | what students may see | via `_build/upload/` |
| `_build/staff/` | everything, with solutions, marker notes and a red "staff copy" banner; every file name ends in `-STAFF` | **never** |
| `_build/upload/` | made from the student build **after the leak check passes** | yes |

While writing, preview one document with live reload:

```
cd sheets
uv run quarto preview problem-sheets/problem-sheet-1/problem-sheet-1.qmd
uv run quarto preview assignments/assignment-1/assignment-1-solutions.qmd --profile staff
```

Unreleased solutions show only a placeholder unless you add `--profile staff`. Keep the
`uv run` in front of `quarto` so code cells use the project's Python.

### Uploading to Moodle

- **Notes**: in Moodle, *Add an activity or resource → File*, upload `_build/upload/MA000-notes.zip`,
  click it, choose *Unzip*, open the `notes` folder, click `index.html` and choose
  *Set main file*. Next time, upload and unzip the new zip in the same place.
  After the first release of the year, add an entry to `notes/changes.qmd` (the last page of
  the notes) for every new upload, so students can see what changed.
- **Sheets**: upload the files in `_build/upload/sheets/` (each HTML file is self-contained).

## Releasing solutions

Every sheet has an entry in [`_module.yml`](_module.yml):

```yaml
assignments:
  assignment-1:
    deadline: 2026-10-15 12:00
    solutions-released: false   # set to true when students may see the solutions
    release-date: 2026-10-22    # shown as "Solutions released on 22 October 2026"
```

- `false` (the default): the student build leaves the solutions out completely.
- `true`: the student build includes them, without marks and marker notes, with a
  "Solutions released on …" line.

Problem sheets work the same way. If you always publish problem-sheet solutions together with
the sheet, set `solutions-released: true` under `problem-sheets: defaults:` once.

**Leak check.** After every student build a check reads the same flags and looks through
`_build/student/`. It fails the build (and refuses to make the upload folder) if it finds a
staff file or the solutions of a sheet that is not released. You can run it on its own with
`uv run scripts/leak_check.py`.

## Writing

```
_module.yml                 module code/title/term, deadlines, release flags
_shared/                    shared by everything: macros, style, filter, header boxes
  macros.tex                your maths macros (PDF and HTML); the template's are in macros-template.tex
notes/                      lecture notes (a Quarto book): add chapters in notes/_quarto.yml
sheets/
  problem-sheets/<id>/<id>.qmd, <id>-solutions.qmd
  assignments/<id>/<id>.qmd, <id>-solutions.qmd
scripts/                    build, leak check, upload (Python)
_scratch/                   your old material while rewriting (not committed, not backed up)
```

To add a sheet, copy a folder (e.g. `problem-sheet-1` to `problem-sheet-2`), rename both files
to match the folder, and add an entry for it in `_module.yml`.

Sheet features (see the examples):

| You write | You get |
|---|---|
| `## Question 1: Title [2]{.difficulty}` | difficulty icons (stars by default, or your own image via `difficulty-icon` in `_module.yml`) |
| `## Question 1 [8]{.marks}` and `... [2]{.marks}` | marks, right-aligned; a warning if the parts do not add up |
| `[note]{.marking}` or `::: {.marking}` | notes for markers (staff build only) |
| `::: {.infobox}` | a framed box |
| `{{< sheet deadline >}}` | a setting from `_module.yml` for this sheet |
| `see {{< notes thm-FTC >}} of the lecture notes` | "see Theorem 2.1 of the lecture notes"; in HTML, a link to it in the notes on Moodle (see below) |

**Corrections after release.** List them in the front matter of the sheet (or its solutions)
you corrected; each shows as an "Updated 14 October 2026: ..." line under the header,
newest first. Without `changes`, nothing is shown. For an assignment, also post a Moodle
announcement.

```yaml
---
title: "Problem Sheet 1"
changes:
  - date: 2026-10-14
    text: "Question 2(a): the upper limit of the integral is $1$, not $2$."
---
```

The rationale behind having them in the frontmatter rather than directly in the text
is that the frontmatter is easier to find and edit, and helps with clean-up when rolling
the project over to a new year.

### Parts of a question (lists)

Write parts as `(a)`, `(b)`, ... (or `(i)`, `1.`, `-`); the label shows as written in both PDF
and HTML. Everything after the first paragraph of a part (more paragraphs, displayed
equations, code cells, nested lists) is indented by 4 spaces, so it lines up with the text
after `(a) `:

```
(a) The integrating factor is $\mathrm{e}^{2t}$. [1]{.marks}

    Integrating gives
    $$
    x(t) = \mathrm{e}^{-t} + C \, \mathrm{e}^{-2t}.
    $$ [2]{.marks}

    (i) A nested part, indented by 4 more spaces.

(b) Next part.
```

Every paragraph of a part then lines up with its first line, with the label hanging to the
left. A paragraph that is not indented is not part of any part: it sits at the margin, and
the next part continues the numbering. Use this for context that holds from that point on:

```
(b) Find the equilibrium.

Now assume that each year we remove $c$ adults from the population.

(c) Find the new equilibrium.
```

### References to the notes

`{{< notes label >}}` takes any cross-reference label from the notes (`sec-…`, `thm-…`,
`eq-…`, `fig-…`, ...) and gives its name and number, e.g. "Section 2.3" or "Chapter 2". The
numbers come from the last build of the notes (in `_shared/generated/notes-xref.json`, which
you commit with the notes), so after changing the notes, rebuild them before the sheets;
`uv run scripts/build.py` does this. An unknown label gives a warning and shows as
**[label?]**.

For links in the HTML sheets, upload the notes to Moodle once, open them there and copy the
address of the page (it contains `pluginfile.php`) into `notes: url:` in `_module.yml`. The
address stays the same when you upload new versions of the notes to the same File resource.
The PDF sheets show the number only.

### Code and figures

**Python figures.** Code cells (```` ```{python} ````) run in the project environment. Shared
helpers are in `src/moduletools/` and can be imported from any chapter or sheet:

```python
from moduletools import apply_style, colours, set_zero_axes
apply_style()                                   # module-wide figure style
ax.plot(x, y, color=colours["purple"])          # palette colours
```

In the notes, code results are stored in `notes/_freeze/` (committed), and a chapter runs
again only when it changes. If you change `src/moduletools`, rebuild with `--refresh`.

**TikZ figures.** Put a standalone LaTeX file in a `figs/` folder (see
`sheets/problem-sheets/problem-sheet-1/figs/unit-circle.tex`). Before every render it is
compiled to `.pdf` and `.svg`. Include it **without an extension**, and the PDF output uses
the `.pdf` while the HTML uses the `.svg`:

```markdown
![Caption.](figs/unit-circle){#fig-unit-circle width=40% fig-alt="Description."}
```

Figures can use the palette colours after `\input{palette.tex}`.

### Maths and LaTeX packages

The HTML shows maths with MathJax, which understands maths-mode LaTeX (including the AMS
packages) but cannot load packages: `\usepackage` works in the PDF only. So:

- **Notation:** define it in `_shared/macros.tex` with `\newcommand` instead of loading a
  package. It works in PDF and HTML. The template already provides `\dd`, `\dv`, `\pdv`
  (instead of the `physics` package) and bold vectors `\bfx`, `\bfE`, ..., `\bfzero` (see
  `_shared/macros-template.tex`). To change one, define it again in `macros.tex`: your
  version replaces the template's.
- **Figures:** standalone `figs/*.tex` files are compiled by LaTeX on their own, so they can
  load any package (`tikz`, `pgfplots`, `siunitx`, ...).
- **Layout** (boxes, marks, parts): use the features above, which look the same in both.

If you need a package that none of these covers, open an issue on the template repository.

### Colours

All colours are defined once in [`_shared/palette.yml`](_shared/palette.yml) (Warwick brand
colours at 100%; tints of 80, 60, 40 and 20% are generated). Use them as `\color{brand-coral-60}`
in LaTeX or `var(--brand-coral-60)` in CSS. The `roles` section sets what the template uses:
the accent (headings, marks, boxes, links) is purple, and lavender in dark mode. Only purple
is dark enough for text on white; use the other colours for fills and highlights.

### Settings on your computer only

Create `_local.yml` (not committed) to override anything in `_module.yml` on your machine.
Do not put release flags there: the committed `_module.yml` is the record of what was released.

### Old material

Put old versions you want at hand while rewriting (old LaTeX sheets, etc.) in `_scratch/`.
It is ignored by git and by Quarto, and it is **not backed up**: delete it when you are done.

## Template and module files

Some files belong to the template and work the same in every module; others are yours to edit.
Keeping to this split means template updates can be applied to your module without
overwriting your work.

**Yours (edit freely):**

- `_module.yml`: module code, title, term, deadlines, release flags
- `_shared/macros.tex`, `_shared/palette.yml`, `_shared/header-*.qmd`
- the notes chapters, `notes/changes.qmd` (changes for students), `notes/_quarto.yml`
  (title, chapter list) and `notes/refs.bib`
- the sheets in `sheets/problem-sheets/` and `sheets/assignments/`, and all `figs/`
- `pyproject.toml`: add the Python packages your code cells need (then `uv sync`)

**Template (do not edit in a module):** everything else in `_shared/`, `scripts/` and
`src/moduletools/`, and `sheets/_quarto*.yml`. Each of these files starts with a line saying
so. `_shared/generated/` is made by the scripts: never edit it by hand. If a template file
does not do what you need, open an issue on the template repository instead.

## Credits

The placeholder lecture notes are *Quarto Lecture Notes* by Thomas Hudson (MIT licence,
see [notes/CREDITS.md](notes/CREDITS.md)). The PDF font choice (Domitian) follows his template.
