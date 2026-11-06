# Module template (Quarto)

A [copier](https://copier.readthedocs.io/) template for a university module: **lecture notes**,
**problem sheets** and **assignments**, each produced as **PDF and HTML** from one source, with
one shared style. Solutions live in the module's repository but never reach students by
accident: unreleased solutions are left out of the student build, and a leak check verifies it.

## Create a module

You need [Quarto](https://quarto.org/docs/get-started/), a TeX distribution (`quarto install
tinytex`) and [uv](https://docs.astral.sh/uv/). Then:

```
uvx copier copy gh:brosaplanella/MA-template MA302
```

It asks six questions: module code, title, term, lecturer, and how many problem sheets
(default 10) and assignments (default 4). The new folder is a complete module with stub
notes and sheets. Its `README.md` starts with a short checklist ("Setting up a new module":
private GitHub repository, deadlines, first Moodle upload), then explains how to build, write
and release solutions. For a worked example, see the
[Warwick Quarto Manual](https://github.com/brosaplanella/warwick-quarto-manual).

A module gets template fixes and features later with `uvx copier update --defaults` (see the
module README, "Template updates").

## What is in this repository

```
copier.yml                 the setup questions and copier settings
template/                  what is copied into a module (files ending .jinja are filled in)
scripts/test_template.py   generates modules from the working copy and builds them
docs/                      design notes: brief, audits, decisions log
```

The plan and to-do list are the [GitHub issues](https://github.com/brosaplanella/MA-template/issues),
grouped by milestone.

## Working on the template

Edit the files in `template/`, then generate and build test modules:

```
uv run scripts/test_template.py            # all answer sets (several minutes)
uv run scripts/test_template.py small      # one set: 2 problem sheets, 1 assignment
```

The modules are left in `_scratch/test-template/<set>/` for inspection; preview a document
there with `uv run quarto preview ...` from its `notes/` or `sheets/` folder. Uncommitted
changes to the template are included.

- Files under `template/` that end in `.jinja` are filled in from the answers, with the
  markers `[[ ... ]]` and `[% ... %]` (so Quarto's `{{< ... >}}` shortcodes are left alone).
  All other files are copied as they are.
- Template-owned files start with a "Template file: do not edit it in a module" line;
  module-owned files are listed under `_skip_if_exists` in `copier.yml`, so `copier update`
  never touches them. Keep that list and the module README ("Template and module files")
  in step.
- **On GitHub**, the same test runs on Ubuntu and macOS for every pull request that touches
  the template (and by hand: Actions > Test template > Run workflow). Windows is tested
  locally.
- **Releases** are git tags (`v0.1.0`, `v0.1.1`, ...); `copier update` moves a module to the
  latest one. Tag only after `test_template.py` passes.

## Credits

The PDF font choice (Domitian) follows *Quarto Lecture Notes* by Thomas Hudson (MIT licence).
