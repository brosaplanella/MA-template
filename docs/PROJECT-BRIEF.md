# Project brief: Quarto module template

## Goal
A template repo for university lecture modules written in Quarto (PDF + HTML from
one source), usable by non-coder colleagues and a vehicle for good practice.
Author: a lecturer at the University of Warwick. Reference modules (in reference/,
gitignored, read-only):
- MA147 (more mature; the starting point for the template)
- MA302 (earlier stage; will be ported onto the template as the real test)

## Principles
- Build the minimum first. Extract the template from MA147, don't design in the abstract.
- Repo holds only the Quarto part: text-based, reproducible. Exams, scans, handwritten
  notes and PowerPoints live outside (recommended local layout: MODULE/quarto/,
  MODULE/exams/, MODULE/slides/). Final student-facing PDFs go in a `static/` folder.
- Exams are NOT in this repo (separate LaTeX template, separate access control).
- Assignment solutions are the only sensitive material in this repo (exams live elsewhere).
  Safeguards are deliberately proportionate: `student`/`staff` profiles with separate
  output dirs, a post-build leak check on the student output, a repo-must-be-private CI
  guard, and a README note that git history is forever. Do not build vault-style
  protections (no `restricted/` folder). Avoid GitHub Pages for this repo. Main risk to
  design against is distributing the wrong build: staff outputs must be visibly marked
  (filename suffix `-STAFF`, "do not distribute" banner), and the default build must be
  the student one.
- Solutions may be released after the deadline, decided per assignment. Do not add a
  third profile. Instead, each assignment has `solutions_released` (default false) and an
  optional `release_date` in `_module.yml`. The student build includes solutions only for
  released assignments, with a distinct filename suffix (`-solutions`) and a "released
  on <date>" banner. The leak check reads the same flags and fails if solutions appear
  in the student output for an unreleased assignment. Check whether MA147 already has a
  release mechanism.
- Layered settings: _module.yml (committed) and _local.yml (gitignored). Start with the
  solutions banner (red text when solutions are not meant to be shared) and the release flags.
- Shared Python utils and TikZ build: include only if MA147 already has them, generalised.
- Widgets (interactive JS) shown in HTML, replaced by a reference box in PDF: later.
- Agent-ready: AGENTS.md with repo map, commands, hard rules (written early).
- Never edit MA147 or MA302 in place; work in new repos.
- Cross-platform: the template must work on Windows, Linux and macOS. Development is
  on Windows (PowerShell). All helper scripts (leak check, TikZ build, etc.) are written
  in Python using pathlib and explicit UTF-8, invoked via Quarto pre/post-render hooks
  (a justfile is an optional convenience only). Include .gitattributes forcing LF
  endings. No symlinks, no bash/PowerShell-only logic, no pdf2svg (use dvisvgm).
  Recommend TinyTeX and uv. CI builds on an ubuntu/windows/macos matrix (macOS only on
  main/release to save minutes). Watch for case-sensitivity bugs in file references.
- Repo location: the working copy lives outside OneDrive/SharePoint-synced folders
  (C:\dev\MA-template). GitHub (private) is the backup, so commit and push at the end
  of every session. Exams and other non-Quarto material stay in the author's OneDrive
  module folders, outside this repo and outside the agent's working directory. The
  template README must explain this for colleagues who use OneDrive.
- Exam material must never be accessed by the agent. Work is launched from
  C:\dev\MA-template only. Do not read, list, search or reference paths outside this
  repo, and do not use bash or PowerShell to reach parent or sibling directories. Ask
  the author if a task seems to require it.

## Working style
- Author has plenty of review time, little hands-on time. Work in small reviewable
  chunks (one branch/commit each), self-verify before handing over (both profiles
  build, leak check fails when a solution is planted in student output), and write a
  short summary: what changed, how to check, what you're unsure about.
- Batch questions for the author instead of interrupting.
- Keep migration separate from content changes.

## Schedule
- 2-20 Nov: Phase 1 audit of MA147, Phase 2 template v0.1
- 23 Nov-4 Dec: port MA302 as a pure migration (identical content, output compared to old repo)
- 1 Dec: go/no-go. If MA302 doesn't build on the template, abort and keep the old repo.
- 7-14 Dec: fix generic issues, freeze v0.1, write handover note
- 15 Dec-8 Jan: author away. Template frozen afterwards except tiny fixes.

## Open decisions (ask the author)
- Where is the student build hosted today (Moodle, Pages, other)?
- Does the department have a GitHub org that can restrict public repos?

## Parked for later
Copier wizard, Quarto extension packaging, department widget repo + compiled JS,
devcontainer, accessibility/spell/link checks in CI, question bank, yearly rollover,
licence guidance, agent skills (proofreading etc.).