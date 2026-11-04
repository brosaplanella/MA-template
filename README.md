# Module template (Quarto)

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
| [uv](https://docs.astral.sh/uv/) | runs the build scripts (Python) | see the uv website |

Then, once, in the repository folder: `uv sync`.

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
```

| Folder | Contents | Upload? |
|---|---|---|
| `_build/student/` | what students may see | via `_build/upload/` |
| `_build/staff/` | everything, with solutions, marker notes and a red "staff copy" banner; every file name ends in `-STAFF` | **never** |
| `_build/upload/` | made from the student build **after the leak check passes** | yes |

While writing, preview one document with live reload:

```
cd sheets
quarto preview problem-sheets/problem-sheet-1/problem-sheet-1.qmd
quarto preview assignments/assignment-1/assignment-1-solutions.qmd --profile staff
```

Unreleased solutions show only a placeholder unless you add `--profile staff`.

### Uploading to Moodle

- **Notes**: in Moodle, *Add an activity or resource → File*, upload `_build/upload/MA000-notes.zip`,
  click it, choose *Unzip*, open the `notes` folder, click `index.html` and choose
  *Set main file*. Next time, upload and unzip the new zip in the same place.
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
  macros.tex                your maths macros (PDF and HTML)
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
| `## Question 1: Title [2]{.difficulty}` | difficulty icons (stars by default; numbers or your own image via `difficulty-icon` in `_module.yml`) |
| `## Question 1 [8]{.marks}` and `... [2]{.marks}` | marks, right-aligned; a warning if the parts do not add up |
| `[note]{.marking}` or `::: {.marking}` | notes for markers (staff build only) |
| `::: {.infobox}` | a framed box |
| `{{< sheet deadline >}}` | a setting from `_module.yml` for this sheet |

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

## Credits

The placeholder lecture notes are *Quarto Lecture Notes* by Thomas Hudson (MIT licence,
see [notes/CREDITS.md](notes/CREDITS.md)). The PDF font choice (Domitian) follows his template.
