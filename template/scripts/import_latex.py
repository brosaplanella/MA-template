# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Import a LaTeX problem sheet or assignment (questions or solutions) into this module.

    uv run scripts/import_latex.py sheet OLD.tex sheets/problem-sheets/problem-sheet-3/problem-sheet-3.qmd
    uv run scripts/import_latex.py sheet OLD.tex .../problem-sheet-3/problem-sheet-3-solutions.qmd --force

What it does (Pandoc does the conversion):

- the body (between \\begin{document} and \\end{document}) becomes Markdown; maths is kept as
  written, with macros unexpanded
- top-level \\begin{enumerate} items become "## Question N", the next level (a), (b), ...
  and the level below (i), (ii), ...; other layouts are converted as they are
- title and header box come from the destination (as in the sheets the wizard creates)
- layout commands with no meaning in Quarto (\\maketitle, \\vskip, \\newpage, ...) are dropped
- figures (\\includegraphics) are copied into a figs/ folder next to the sheet
- macro definitions (\\newcommand, \\def, \\DeclareMathOperator, also in \\input files) that the
  sheet uses are added to _scratch/imported-macros.tex, to review and copy into
  _shared/macros.tex; those the template already provides are skipped

Anything else that Pandoc does not know stays in the output as raw LaTeX (`\\cmd`{=latex}),
so nothing is lost, and the report at the end lists it with line numbers: that is the review
to-do list. Existing files are only replaced with --force. The output is a starting point:
always read it and build the sheet before committing.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET_PATH = re.compile(r"^sheets/(problem-sheets|assignments)/([^/]+)/\2(-solutions)?\.qmd$")
TITLES = {"problem-sheets": "Problem Sheet", "assignments": "Assignment"}
HEADERS = {  # (kind, solutions?) -> header box, as in the stubs
    ("problem-sheets", False): "header-problem-sheet.qmd",
    ("assignments", False): "header-assignment.qmd",
    ("assignments", True): "header-assignment-solutions.qmd",
}

# Commands that only lay out the page; dropped (with any {argument}) and counted.
LAYOUT = ("maketitle", "newpage", "clearpage", "pagebreak", "pagestyle", "thispagestyle",
          "vskip", "vspace", "hspace", "hfill", "vfill", "smallskip", "medskip", "bigskip",
          "noindent", "indent", "centering", "setlength", "addtolength", "parindent",
          "tiny", "scriptsize", "footnotesize", "small", "normalsize", "large", "Large",
          "LARGE", "huge", "Huge", "linebreak", "nolinebreak")

DEFINITION = re.compile(
    r"\\(?:(?:re|provide)?newcommand\*?|DeclareMathOperator\*?|def)\s*\{?\\([A-Za-z]+)\}?")

LUA_FILTER = r"""
local layout = {}
for name in (os.getenv("IMPORT_LAYOUT") or ""):gmatch("%S+") do layout[name] = true end

local function command(text) return text:match("^%s*\\(%a+)") end

local function report(kind, value) io.stderr:write(kind .. "\t" .. value .. "\n") end

local function raw(el)
  if el.format ~= "latex" and el.format ~= "tex" then return nil end
  local name = command(el.text)
  if name and layout[name] then
    report("DROPPED", name)
    return {}
  end
  return nil
end

local function image(el)
  report("IMAGE", el.src)
  el.src = "figs/" .. el.src:gsub("^.*/", "")
  return el
end

-- Display maths: environments that cannot sit inside $$ ... $$ become their inner forms
local math_envs = { ["align*"] = "aligned", align = "aligned", ["eqnarray*"] = "aligned",
  eqnarray = "aligned", ["gather*"] = "gathered", gather = "gathered" }

local function display_math(el)
  if el.mathtype ~= "DisplayMath" then return nil end
  local text = el.text
  for env, inner in pairs(math_envs) do
    text = text:gsub("\\begin%{" .. env:gsub("%*", "%%*") .. "%}", "\\begin{" .. inner .. "}")
    text = text:gsub("\\end%{" .. env:gsub("%*", "%%*") .. "%}", "\\end{" .. inner .. "}")
  end
  text = text:gsub("\\begin%{equation%*?%}", ""):gsub("\\end%{equation%*?%}", "")
  if text ~= el.text then
    report("MATH", "environment")
    el.text = text
    return el
  end
end

-- Figures: Quarto's own syntax ![Caption](figs/x){#fig-label}, so they are numbered in PDF
-- and HTML; \ref{label} to a figure becomes @fig-label. Other \ref stay raw (reported).
local figure_ids = {}

local function figure(el)
  local label = el.identifier
  local id = ""
  if label ~= "" then
    id = "fig-" .. label:gsub("^fig[:%-_]", ""):gsub("[^%w%-]", "-")
    figure_ids[label] = id
    report("FIGURE", label .. " -> " .. id)
  end
  el.attr = pandoc.Attr(id, {}, {})
  return el
end

local function figure_ref_id(el)
  if el.t ~= "RawInline" or (el.format ~= "latex" and el.format ~= "tex") then return nil end
  local label = el.text:match("^\\[cC]?ref%{([^}]+)%}$")
  return label and figure_ids[label]
end

-- "Figure~\ref{fig:a}" -> "@fig-a" (Quarto writes "Figure 1" itself)
local function figure_refs(inlines)
  local out = pandoc.Inlines({})
  for _, el in ipairs(inlines) do
    local id = figure_ref_id(el)
    if id then
      local last = out[#out]
      if last and (last.t == "Space" or (last.t == "Str" and last.text == "\u{a0}")) then
        local word = out[#out - 1]
        if word and word.t == "Str" and word.text:match("^[Ff]ig[ure%.]*$") then
          out:remove(#out)
          out:remove(#out)
        end
      elseif last and last.t == "Str" and last.text:match("^[Ff]ig[ure%.]*\u{a0}$") then
        out:remove(#out)
      end
      out:insert(pandoc.Cite({ pandoc.Str("@" .. id) }, { pandoc.Citation(id, "AuthorInText") }))
    else
      out:insert(el)
    end
  end
  return out
end

local function header(el)
  el.identifier = ""
  el.classes = {}
  return el
end

-- Nested lists inside a question: (a), then (i), then 1.
local styles = {
  { "LowerAlpha", "TwoParens" }, { "LowerRoman", "TwoParens" }, { "Decimal", "Period" } }

local function restyle(blocks, depth)
  return blocks:walk({
    OrderedList = function(list)
      local s = styles[math.min(depth, #styles)]
      list.listAttributes = pandoc.ListAttributes(list.listAttributes.start, s[1], s[2])
      for i, item in ipairs(list.content) do
        list.content[i] = restyle(pandoc.Blocks(item), depth + 1)
      end
      return list, false
    end,
  })
end

function Pandoc(doc)
  doc = doc:walk({ RawBlock = raw, RawInline = raw, Image = image, Header = header,
                   Math = display_math, Figure = figure })
  doc = doc:walk({ Inlines = figure_refs })
  local out = pandoc.Blocks({})
  local n = 0
  for _, block in ipairs(doc.blocks) do
    if block.t == "OrderedList" then
      for _, item in ipairs(block.content) do
        n = n + 1
        out:insert(pandoc.Header(2, "Question " .. n))
        out:extend(restyle(pandoc.Blocks(item), 1))
      end
    else
      out:insert(block)
    end
  end
  report("QUESTIONS", tostring(n))
  doc.blocks = out
  return doc
end
"""


def read_with_inputs(path: Path, seen: set[Path] | None = None) -> str:
    """The file's text with \\input{...} / \\include{...} files inlined (for macro definitions)."""
    seen = seen or set()
    path = path.resolve()
    if path in seen or not path.exists():
        return ""
    seen.add(path)
    text = path.read_text(encoding="utf-8", errors="replace")

    def inline(match: re.Match) -> str:
        name = match.group(1)
        target = path.parent / (name if name.endswith(".tex") else name + ".tex")
        return read_with_inputs(target, seen)

    return re.sub(r"\\(?:input|include)\{([^}]+)\}", inline, text)


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def body_of(text: str) -> str:
    match = re.search(r"\\begin\{document\}(.*?)(\\end\{document\}|\Z)", text, re.S)
    return match.group(1) if match else text


def definitions(text: str) -> dict[str, str]:
    """name -> one-line definition, rewritten as \\newcommand (what macros.tex expects)."""
    found = {}
    for line in strip_comments(text).splitlines():
        match = DEFINITION.search(line)
        if not match:
            continue
        name, stmt = match.group(1), line.strip()
        op = re.match(r"\\DeclareMathOperator\*?\s*\{?\\[A-Za-z]+\}?\s*\{(.*)\}\s*$", stmt)
        if op:
            stmt = f"\\newcommand{{\\{name}}}{{\\operatorname{{{op.group(1)}}}}}"
        elif stmt.startswith("\\def"):
            stmt = re.sub(r"^\\def\s*\\([A-Za-z]+)", r"\\newcommand{\\\1}", stmt)
        else:
            stmt = re.sub(r"^\\(?:re|provide)newcommand\*?", r"\\newcommand", stmt)
        found[name] = stmt
    return found


def defined_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {m.group(1) for m in DEFINITION.finditer(strip_comments(path.read_text(encoding="utf-8")))}


def find_image(src: str, folder: Path) -> Path | None:
    candidate = folder / src
    if candidate.is_file():
        return candidate
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"):
        if candidate.with_suffix(ext).is_file():
            return candidate.with_suffix(ext)
    return None


def import_sheet(source: Path, dest: Path, force: bool) -> int:
    rel = dest.resolve().relative_to(ROOT).as_posix() if dest.resolve().is_relative_to(ROOT) else ""
    match = SHEET_PATH.match(rel)
    if not match:
        sys.exit(f"The destination must be sheets/<kind>/<id>/<id>.qmd or <id>-solutions.qmd "
                 f"inside this module (kind: problem-sheets or assignments), not {dest}")
    kind, sheet_id, solutions = match.group(1), match.group(2), bool(match.group(3))
    if dest.exists() and not force:
        sys.exit(f"{rel} exists; use --force to replace it")
    if not source.is_file():
        sys.exit(f"No such file: {source}")

    full = read_with_inputs(source)
    body = strip_comments(body_of(full))
    # Definitions inside the body would otherwise come out as raw LaTeX
    body = "\n".join(line for line in body.splitlines() if not DEFINITION.search(line))

    with tempfile.TemporaryDirectory() as tmp:
        lua = Path(tmp) / "import.lua"
        lua.write_text(LUA_FILTER, encoding="utf-8")
        result = subprocess.run(
            # -raw_tex on output: leftover LaTeX is written as `...`{=latex} or a fenced
            # {=latex} block, so it is visible and the report can find it exactly
            ["quarto", "pandoc", "-f", "latex-latex_macros+raw_tex", "-t", "markdown-raw_tex",
             "--wrap=none", f"--resource-path={source.parent}", "--lua-filter", str(lua)],
            input=body, capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "IMPORT_LAYOUT": " ".join(LAYOUT)},
        )
    if result.returncode != 0:
        sys.exit(f"Pandoc failed:\n{result.stderr}")

    events = [line.split("\t", 1) for line in result.stderr.splitlines() if "\t" in line]
    dropped = Counter(v for k, v in events if k == "DROPPED")
    images = [v for k, v in events if k == "IMAGE"]
    questions = next((int(v) for k, v in events if k == "QUESTIONS"), 0)
    adapted = sum(1 for k, _ in events if k == "MATH")
    figures = [v for k, v in events if k == "FIGURE"]

    number = re.search(r"(\d+)$", sheet_id)
    title = f"{TITLES[kind]} {number.group(1) if number else sheet_id}"
    if solutions:
        title += " -- Solutions"
    head = ["---", f'title: "{title}"', "---", ""]
    header = HEADERS.get((kind, solutions))
    if header:
        head += [f"{{{{< include ../../../_shared/{header} >}}}}", ""]
    text = "\n".join(head) + "\n" + result.stdout.strip() + "\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")

    copied, missing = [], []
    for src in dict.fromkeys(images):
        found = find_image(src, source.parent)
        if found:
            (dest.parent / "figs").mkdir(exist_ok=True)
            shutil.copy2(found, dest.parent / "figs" / found.name)
            copied.append(found.name)
        else:
            missing.append(src)

    # Macros: those defined anywhere in the source (preamble, \input files) and used in the body
    defs = definitions(full)
    used = {name for name in defs if re.search(r"\\" + name + r"(?![A-Za-z])", body)}
    template = defined_names(ROOT / "_shared" / "macros-template.tex")
    module = defined_names(ROOT / "_shared" / "macros.tex")
    target = ROOT / "_scratch" / "imported-macros.tex"
    already = defined_names(target)
    new = sorted(used - template - module - already)
    if new:
        target.parent.mkdir(exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as f:
            if not already:
                f.write("% Macros found by scripts/import_latex.py. Review them, then copy the ones\n"
                        "% you want into _shared/macros.tex (and delete this file).\n")
            f.write(f"\n% from {source.name}\n" + "".join(defs[n] + "\n" for n in new))

    # Report: raw LaTeX left in the output, by command, with line numbers
    leftovers: dict[str, list[int]] = {}
    in_block = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") and "{=latex}" in stripped:
            in_block = True
            continue
        if in_block and stripped.startswith("```"):
            in_block = False
            continue
        raws = [line] if in_block else re.findall(r"`([^`]*)`\{=latex\}", line)
        for raw in raws:
            for name in re.findall(r"\\([A-Za-z]+)", raw) or ["(raw)"]:
                leftovers.setdefault(name, []).append(lineno)

    print(f"Imported {source.name} -> {rel}")
    print(f"  {questions} question(s)" if questions else
          "  no top-level enumerate: no Question headings were made")
    if dropped:
        print("  layout commands dropped: " + ", ".join(f"\\{k} ({v})" for k, v in dropped.items()))
    if adapted:
        print(f"  displayed maths: {adapted} align/gather/equation environment(s) "
              "turned into aligned/gathered")
    if figures:
        print("  labelled figures (\\ref -> @): " + ", ".join(figures))
    if copied:
        print("  figures copied to figs/: " + ", ".join(copied))
    if missing:
        print("  FIGURES NOT FOUND (copy them by hand): " + ", ".join(missing))
    if new:
        print(f"  macros added to {target.relative_to(ROOT).as_posix()}: "
              + ", ".join("\\" + n for n in new))
    if leftovers:
        print("  raw LaTeX left in the output (review these):")
        for name, lines in sorted(leftovers.items(), key=lambda kv: -len(kv[1])):
            shown = ", ".join(map(str, lines[:8])) + (", ..." if len(lines) > 8 else "")
            print(f"    \\{name}: {len(lines)} (lines {shown})")
    else:
        print("  no raw LaTeX left")
    if not (ROOT / "_module.yml").read_text(encoding="utf-8").count(f"{sheet_id}:"):
        print(f"  note: add an entry for {sheet_id} under {kind}: in _module.yml")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    sheet = sub.add_parser("sheet", help="a problem sheet or assignment (questions or solutions)")
    sheet.add_argument("source", type=Path, help="the LaTeX file")
    sheet.add_argument("dest", type=Path, help="sheets/<kind>/<id>/<id>[-solutions].qmd")
    sheet.add_argument("--force", action="store_true", help="replace an existing file")
    args = parser.parse_args()
    return import_sheet(args.source, args.dest, args.force)


if __name__ == "__main__":
    sys.exit(main())
