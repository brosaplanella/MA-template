# AGENTS.md

Guidance for coding agents working on the **template** repository. Read README.md for the
maintainer view.

## What this is

A copier template for a module's teaching materials in Quarto: lecture notes (book), problem
sheets and assignments, each rendered to PDF and HTML, sharing one style layer. Modules are
created with `uvx copier copy` and updated with `uvx copier update`.

## Repository map

```
copier.yml                 setup questions; _envops ([[ ]] / [% %] markers), _skip_if_exists
template/                  copied into every module; see template/AGENTS.md for its own map,
                           commands and release-control rules (they apply to the template too)
  *.jinja                  filled in from the answers (_module.yml, notes/_quarto.yml, ...)
  sheets/<kind>/[% yield ... %]...   one folder per sheet, via copier's yield tag
scripts/test_template.py   generate modules into _scratch/test-template/, build, leak check
docs/                      brief, audits, decisions log (docs/decisions.md)
reference/                 read-only reference modules (gitignored); never modify
```

The plan and to-do list are the GitHub issues (by milestone), not a file.

## Commands

```
uv run scripts/test_template.py            # all answer sets
uv run scripts/test_template.py small      # one set
```

`template/` itself cannot be built (its sheet folders are named with copier markers): test by
generating a module. In a generated module, the commands in template/AGENTS.md apply.

## Hard rules

1. Never weaken the leak check, the withholding in `template.lua`, or the student default
   profile without the author's explicit approval.
2. Never commit build outputs (`_build/`), `_local.yml`, or anything from `_scratch/`.
3. Never read, list or search outside this repository. Exam material lives elsewhere and must
   never be accessed. Ask the author if a task seems to need it.
4. Never modify `reference/`.
5. Cross-platform: Python with `pathlib` and explicit UTF-8; no bash/PowerShell-only logic, no
   symlinks. Watch file-name case.
6. Keep `template/_shared/common.lua` and `template/scripts/moduleconf.py` consistent.
7. Template-owned files start with the "Template file" marker line; mark new ones the same
   way. Module-owned files go in `_skip_if_exists` in `copier.yml` and in the module README's
   list. No module content in template files.
8. Work in small reviewable commits; run `scripts/test_template.py` before handing over.
