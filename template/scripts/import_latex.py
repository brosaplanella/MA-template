# Template file: do not edit it in a module (see "Template and module files" in README.md).
"""Import LaTeX into this module: a problem sheet or assignment, or a set of lecture notes.

    uv run scripts/import_latex.py sheet OLD.tex sheets/problem-sheets/problem-sheet-3/problem-sheet-3.qmd
    uv run scripts/import_latex.py sheet OLD.tex .../problem-sheet-3/problem-sheet-3-solutions.qmd --force
    uv run scripts/import_latex.py notes OLD/main.tex [--force]

What it does (Pandoc does the conversion):

- the body (between \\begin{document} and \\end{document}, with \\input and \\include files
  inlined) becomes Markdown; maths is kept as written, with macros unexpanded
- sheet: top-level \\begin{enumerate} items become "## Question N", the next level (a), (b),
  ... and the level below (i), (ii), ...; title and header box come from the destination
- notes: one notes/chapterN.qmd per \\chapter (per \\section for article-class notes); the
  text before the first chapter goes to _scratch/imported-preface.md; the chapter list for
  notes/_quarto.yml is printed (that file is not edited)
- theorem-like environments (theorem, lemma, corollary, proposition, conjecture, definition,
  example, exercise, remark, solution, and those declared with \\newtheorem under these
  names) become Quarto's numbered blocks (::: {#thm-...}); proof becomes ::: {.proof}
- \\label / \\ref / \\eqref / \\cref become Quarto cross-references (@eq-..., @thm-...,
  @sec-..., @fig-...); an align with several labels gets one number for the whole block
- \\cite stays a citation ([@key]); .bib files are copied to _scratch/ (merge them into
  notes/refs.bib by hand)
- \\ifdefined\\x, \\iftrue and \\iffalse keep the branch LaTeX would typeset
- layout commands with no meaning in Quarto (\\maketitle, \\vskip, \\newpage, ...) are dropped;
  boxes (mdframed, framed, tcolorbox) and subequations are unwrapped
- figures (\\includegraphics, also via \\graphicspath) are copied into a figs/ folder
- macro definitions (\\newcommand, \\def, \\DeclareMathOperator, also in \\input files) that the
  text uses are added to _scratch/imported-macros.tex, to review and copy into
  _shared/macros.tex; those the template already provides are skipped

Anything else that Pandoc does not know stays in the output as raw LaTeX (`\\cmd`{=latex}),
so nothing is lost, and the report at the end lists it with line numbers: that is the review
to-do list. Existing files are only replaced with --force. The output is a starting point:
always read it and build before committing.
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
SCRATCH = ROOT / "_scratch"
SHEET_PATH = re.compile(r"^sheets/(problem-sheets|assignments)/([^/]+)/\2(-solutions)?\.qmd$")
TITLES = {"problem-sheets": "Problem Sheet", "assignments": "Assignment"}
HEADERS = {  # (kind, solutions?) -> header box, as in the stubs
    ("problem-sheets", False): "header-problem-sheet.qmd",
    ("assignments", False): "header-assignment.qmd",
    ("assignments", True): "header-assignment-solutions.qmd",
}

# Commands that only lay out the page (or the book); dropped (with any {argument}) and counted.
LAYOUT = ("maketitle", "newpage", "clearpage", "cleardoublepage", "pagebreak", "pagestyle",
          "thispagestyle", "vskip", "vspace", "hspace", "hfill", "vfill", "smallskip",
          "medskip", "bigskip", "noindent", "indent", "centering", "setlength", "addtolength",
          "parindent", "tiny", "scriptsize", "footnotesize", "small", "normalsize", "large",
          "Large", "LARGE", "huge", "Huge", "linebreak", "nolinebreak", "frontmatter",
          "mainmatter", "backmatter", "tableofcontents", "listoffigures", "listoftables",
          "pagenumbering", "setcounter", "bibliographystyle", "bibliography",
          "printbibliography", "title", "author", "date", "FloatBarrier", "afterpage",
          "rowcolor", "rowcolors", "arraystretch")

# Theorem-like environments Quarto numbers, by their printed name: -> id prefix
QUARTO_KINDS = {"theorem": "thm", "lemma": "lem", "corollary": "cor", "proposition": "prp",
                "conjecture": "cnj", "definition": "def", "example": "exm", "exercise": "exr",
                "remark": "rem", "solution": "sol"}
# Packages Quarto or the template already load, or that only affect the layout: not reported
KNOWN_PACKAGES = {
    "amsmath", "amssymb", "amsfonts", "amsthm", "amsopn", "amsxtra", "amscd", "latexsym",
    "graphicx", "graphics", "xcolor", "color", "hyperref", "url", "geometry", "fontenc",
    "inputenc", "babel", "lmodern", "times", "palatino", "mathpazo", "fancyhdr", "fncychap",
    "titlesec", "titling", "enumerate", "enumitem", "float", "caption", "subcaption",
    "subfig", "subfigure", "wrapfig", "booktabs", "longtable", "array", "tabularx",
    "multirow", "tcolorbox", "mdframed", "framed", "verbatim", "comment", "showkeys",
    "placeins", "afterpage", "rotating", "setspace", "parskip", "microtype", "natbib", "cite",
    "biblatex", "fullpage", "a4wide", "a4", "csquotes", "lipsum", "xspace", "ifthen", "etoolbox",
}
# Environments that only draw a box or group equations: their content is kept, unwrapped
UNWRAP = ("mdframed", "framed", "tcolorbox", "subequations")

DEFINITION = re.compile(
    r"\\(?:(?:re|provide)?newcommand\*?|DeclareMathOperator\*?|def)\s*\{?\\([A-Za-z]+)\}?")
NEWTHEOREM = re.compile(r"\\newtheorem\*?\s*\{([^}]+)\}\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")

LUA_FILTER = r"""
local function set(var)
  local s = {}
  for name in (os.getenv(var) or ""):gmatch("%S+") do s[name] = true end
  return s
end
local mode = os.getenv("IMPORT_MODE") or "sheet"
local layout, unwrap = set("IMPORT_LAYOUT"), set("IMPORT_UNWRAP")
local theorems = {}  -- environment -> Quarto prefix
for env, prefix in (os.getenv("IMPORT_THEOREMS") or ""):gmatch("([^%s=]+)=(%S+)") do
  theorems[env] = prefix
end
local others = {}  -- other \newtheorem environments -> printed name (no Quarto equivalent)
for env, printed in (os.getenv("IMPORT_OTHERS") or ""):gmatch("([^%s=]+)=(%S+)") do
  others[env] = printed:gsub("_", " ")
end
local READER = "latex-latex_macros-auto_identifiers+raw_tex"

local function report(kind, value) io.stderr:write(kind .. "\t" .. value .. "\n") end
local function is_tex(el) return el.format == "latex" or el.format == "tex" end
local function esc(s) return (s:gsub("%p", "%%%0")) end

-- Labels: LaTeX label -> Quarto id (prefix-name, unique)
local labels, taken, auto = {}, {}, {}
local function new_id(prefix, label)
  local base
  if label then
    base = label:gsub("^[^:]*:", ""):gsub("[^%w_%-]", "-")
    if base == "" then base = "x" end
  else
    auto[prefix] = (auto[prefix] or 0) + 1
    base = "imported-" .. auto[prefix]
  end
  local id, n = prefix .. "-" .. base, 1
  while taken[id] do
    n = n + 1
    id = prefix .. "-" .. base .. "-" .. n
  end
  taken[id] = true
  if label then labels[label] = id end
  return id
end

local pass1 = {}
local function convert(text)
  return pandoc.read(text, READER).blocks:walk(pass1)
end

local function environment(text)
  local env = text:match("^%s*\\begin%{([%w%*]+)%}")
  if not env then return nil end
  local body = text:match("^%s*\\begin%{" .. esc(env) .. "%}(.*)\\end%{" .. esc(env) .. "%}%s*$")
  return env, body
end

-- \begin{thm}[Name]\label{thm:x} ... \end{thm} -> ::: {#thm-x} ## Name ... :::
local function theorem(prefix, body)
  local name
  local opt = body:match("^%s*(%b[])")
  if opt then
    name = opt:sub(2, -2)
    body = body:gsub("^%s*%b[]", "", 1)
  end
  local label = body:match("^%s*\\label%s*%{([^}]+)%}")
  if label then body = body:gsub("^%s*\\label%s*%b{}", "", 1) end
  local content = convert(body)
  if name and name ~= "" then
    local title = pandoc.read(name, READER).blocks[1]
    if title and title.content then content:insert(1, pandoc.Header(2, title.content)) end
  end
  report("THEOREM", prefix)
  return pandoc.Div(content, pandoc.Attr(new_id(prefix, label), {}, {}))
end

-- Other \newtheorem environments: a plain block starting with the bold name (not numbered,
-- so references to them stay unresolved)
local function other_theorem(env, printed, body)
  local name
  local opt = body:match("^%s*(%b[])")
  if opt then
    name = opt:sub(2, -2)
    body = body:gsub("^%s*%b[]", "", 1)
  end
  body = body:gsub("^%s*\\label%s*%b{}", "", 1)
  local content = convert(body)
  local title = pandoc.Inlines({ pandoc.Str(printed) })
  if name and name ~= "" then
    title:extend({ pandoc.Space(), pandoc.Str("(") })
    local parsed = pandoc.read(name, READER).blocks[1]
    if parsed and parsed.content then title:extend(parsed.content) end
    title:insert(pandoc.Str(")"))
  end
  title:insert(pandoc.Str("."))
  local lead = { pandoc.Strong(title), pandoc.Space() }
  if content[1] and content[1].t == "Para" then
    content[1].content = pandoc.Inlines(lead) .. content[1].content
  else
    content:insert(1, pandoc.Para(lead))
  end
  report("OTHER", env)
  return pandoc.Div(content, pandoc.Attr("", { (env:gsub("[^%w%-]", "")) }, {}))
end

local function raw_block(el)
  if not is_tex(el) then return nil end
  local env, body = environment(el.text)
  if env and body and theorems[env] then return theorem(theorems[env], body) end
  if env and body and others[env] then return other_theorem(env, others[env], body) end
  if env and body and unwrap[env] then
    report("UNWRAPPED", env)
    return convert((body:gsub("^%s*%b[]", "", 1)))
  end
  local name = el.text:match("^%s*\\(%a+)")
  if name and layout[name] then
    report("DROPPED", name)
    return {}
  end
end

local function raw_inline(el)
  if not is_tex(el) then return nil end
  local name = el.text:match("^%s*\\(%a+)")
  if name and layout[name] then
    report("DROPPED", name)
    return {}
  end
end

local function image(el)
  report("IMAGE", el.src)
  el.src = "figs/" .. el.src:gsub("^.*/", "")
  return el
end

-- Display maths: environments that cannot sit inside $$ ... $$ become their inner forms;
-- labels become the equation's id ($$ ... $$ {#eq-x}), one per block
local math_envs = { ["align*"] = "aligned", align = "aligned", ["eqnarray*"] = "aligned",
  eqnarray = "aligned", ["gather*"] = "gathered", gather = "gathered",
  ["multline*"] = "gathered", multline = "gathered", ["flalign*"] = "aligned",
  flalign = "aligned", ["alignat*"] = "alignedat", alignat = "alignedat" }

local function display_math(el)
  if el.mathtype ~= "DisplayMath" then return nil end
  local text = el.text
  for env, inner in pairs(math_envs) do
    text = text:gsub("\\begin%{" .. esc(env) .. "%}", "\\begin{" .. inner .. "}")
    text = text:gsub("\\end%{" .. esc(env) .. "%}", "\\end{" .. inner .. "}")
  end
  text = text:gsub("\\begin%{equation%*?%}", ""):gsub("\\end%{equation%*?%}", "")
  local found = {}
  text = text:gsub("\\label%s*(%b{})", function(l)
    found[#found + 1] = l:sub(2, -2)
    return ""
  end)
  text = text:gsub("\\nonumber%s*", ""):gsub("\\notag%s*", "")
  text = text:gsub("\\intertext%s*{", "\\text{")  -- not allowed inside aligned
  if text == el.text then return nil end
  -- a blank line would end the maths in Markdown
  text = text:gsub("\n[ \t]*\n[%s]*", "\n"):gsub("^%s+", ""):gsub("%s+$", "")
  report("MATH", "environment")
  el.text = text
  if #found == 0 then return el end
  local id = new_id("eq", found[1])
  for i = 2, #found do labels[found[i]] = id end
  if #found > 1 then report("MULTILABEL", tostring(#found)) end
  return { el, pandoc.RawInline("markdown", " {#" .. id .. "}") }
end

local function figure(el)
  -- one image, perhaps inside \begin{center}: keep only the image, so the figure can be
  -- written in Quarto's syntax (otherwise Pandoc writes raw HTML)
  local images = {}
  el.content:walk({ Image = function(img) images[#images + 1] = img end })
  local id = ""
  if el.identifier ~= "" then id = new_id("fig", el.identifier) end
  if #images <= 1 then
    if #images == 1 then el.content = { pandoc.Plain({ images[1] }) } end
    el.attr = pandoc.Attr(id, {}, {})
    return el
  end
  -- several images (subfigures): ::: {#fig-x layout-ncol=n} ![a](...){#fig-a} ... caption :::
  local subs = pandoc.Blocks({})
  local inner = 0
  el.content:walk({ Figure = function(sub)
    inner = inner + 1
    local img
    sub.content:walk({ Image = function(i) img = img or i end })
    if img then
      local cap = sub.caption.long[1]
      img.caption = cap and cap.content or {}
      img.identifier = sub.identifier
      subs:insert(pandoc.Para({ img }))
    end
  end })
  if inner == 0 then
    for _, img in ipairs(images) do subs:insert(pandoc.Para({ img })) end
  end
  subs:extend(el.caption.long)
  report("SUBFIGURES", tostring(#images))
  return pandoc.Div(subs, pandoc.Attr(id, {}, { { "layout-ncol", tostring(math.min(#images, 3)) } }))
end

local function header(el)
  -- \section{Title\label{x}}: the label is inside the title
  for i, inline in ipairs(el.content) do
    local label = inline.t == "RawInline" and inline.text:match("^\\label%s*%{([^}]+)%}$")
    if label then
      el.content:remove(i)
      if el.identifier == "" then el.identifier = label end
      break
    end
  end
  if mode == "notes" and el.identifier ~= "" then
    el.identifier = new_id("sec", el.identifier)
  else
    el.identifier = ""
  end
  if mode ~= "notes" then el.classes = {} end
  return el
end

-- Pandoc's proof: drop its "Proof." and end mark (Quarto adds its own)
local function proof(el)
  if not el.classes:includes("proof") then return nil end
  local first = el.content[1]
  if first and first.t == "Para" and first.content[1] and first.content[1].t == "Emph"
      and pandoc.utils.stringify(first.content[1]) == "Proof." then
    first.content:remove(1)
    if first.content[1] and first.content[1].t == "Space" then first.content:remove(1) end
  end
  local last = el.content[#el.content]
  if last and last.t == "Para" then
    local mark = last.content[#last.content]
    if mark and mark.t == "Str" and mark.text == "\u{a0}\u{25fb}" then last.content:remove() end
  end
  el.attr = pandoc.Attr("", { "proof" }, {})
  return el
end

pass1.RawBlock = raw_block
pass1.RawInline = raw_inline
pass1.Image = image
pass1.Math = display_math
pass1.Figure = figure
pass1.Header = header
pass1.Div = proof
pass1.Table = function(el)
  if el.identifier ~= "" then el.identifier = new_id("tbl", el.identifier) end
  return el
end

-- References: \ref{x}, \eqref{x}, \cref{x,y} -> @id (Quarto writes "Figure 1" itself, so a
-- word like "Figure" or "Theorem" just before is removed). Unknown labels stay raw.
local words = {}
for w in ("figure figures fig fig. figs figs. table tables tab tab. theorem theorems thm thm. "
  .. "lemma lemmas lem lem. corollary corollaries cor cor. proposition propositions prop prop. "
  .. "conjecture definition definitions def def. defn defn. example examples ex ex. exercise "
  .. "exercises remark remarks section sections sec sec. sect sect. chapter chapters ch ch. "
  .. "chap chap. equation equations eq eq. eqs eqs. eqn eqn. eqns eqns. solution"):gmatch("%S+") do
  words[w] = true
end

local function ref_ids(el)
  if el.t ~= "RawInline" or not is_tex(el) then return nil end
  local cmd, arg = el.text:match("^\\(%a+)%*?%s*%{([^}]*)%}$")
  if not (cmd == "ref" or cmd == "eqref" or cmd == "cref" or cmd == "Cref"
          or cmd == "autoref") then return nil end
  local ids = {}
  for label in arg:gmatch("[^,%s]+") do
    if not labels[label] then
      report("UNRESOLVED", label)
      return nil
    end
    ids[#ids + 1] = labels[label]
  end
  return ids
end

local function is_word(el, nbsp)
  if not el or el.t ~= "Str" then return false end
  local text = el.text
  if nbsp then
    text = text:match("^(.-)\u{a0}$")
    if not text then return false end
  end
  return words[text:lower()] or false
end

local function refs(inlines)
  local out = pandoc.Inlines({})
  for k, el in ipairs(inlines) do
    local ids = ref_ids(el)
    if ids then
      local last = out[#out]
      if last and (last.t == "Space" or last.t == "SoftBreak"
                   or (last.t == "Str" and last.text == "\u{a0}"))
          and is_word(out[#out - 1]) then
        out:remove(#out)
        out:remove(#out)
      elseif is_word(last, true) then
        out:remove(#out)
      end
      -- "\ref{fig:x}c": [@fig-x]c, since @fig-xc would be another label
      local next = inlines[k + 1]
      local glued = next and next.t == "Str" and next.text:match("^[%w_]")
      for i, id in ipairs(ids) do
        if i > 1 then out:extend({ pandoc.Str(","), pandoc.Space() }) end
        local mode = (glued and i == #ids) and "NormalCitation" or "AuthorInText"
        out:insert(pandoc.Cite({ pandoc.Str("@" .. id) }, { pandoc.Citation(id, mode) }))
      end
      report("REF", ids[1])
    else
      out:insert(el)
    end
  end
  return out
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

-- For the check that the Markdown writer loses nothing: the first four plain words in a row
-- (letters only, so Markdown writes them as they are) of every paragraph, and after every
-- line break
local function sample(el)
  local run, done = {}, false
  for _, inline in ipairs(el.content) do
    if inline.t == "LineBreak" then
      run, done = {}, false
    elseif done then
    elseif inline.t == "Str" and inline.text:match("^%a+$") then
      run[#run + 1] = inline.text
      if #run == 4 then
        report("PARA", table.concat(run, " "))
        done = true
      end
    elseif inline.t ~= "Space" and inline.t ~= "SoftBreak" then
      run = {}
    end
  end
end

function Pandoc(doc)
  doc.blocks = doc.blocks:walk(pass1)
  doc = doc:walk({ Inlines = refs })
  local out = pandoc.Blocks({})
  local n = 0
  for _, block in ipairs(doc.blocks) do
    if mode == "sheet" and block.t == "OrderedList" then
      for _, item in ipairs(block.content) do
        n = n + 1
        out:insert(pandoc.Header(2, "Question " .. n))
        out:extend(restyle(pandoc.Blocks(item), 1))
      end
    elseif mode == "notes" and block.t == "Header" and block.level == 1 then
      n = n + 1
      out:insert(pandoc.RawBlock("markdown", "<!-- import:chapter -->"))
      out:insert(block)
    else
      out:insert(block)
    end
  end
  report(mode == "sheet" and "QUESTIONS" or "CHAPTERS", tostring(n))
  doc.blocks = out
  doc:walk({ Para = sample, Plain = sample })
  return doc
end
"""

CHAPTER_MARK = "<!-- import:chapter -->"


# --- Reading the LaTeX source ----------------------------------------------------------

def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def read_with_inputs(path: Path, base: Path, seen: set[Path] | None = None) -> str:
    """The file's text, without comments, with \\input / \\include files inlined. As in
    LaTeX, names are relative to the main file's folder (base), else to the including file."""
    seen = seen if seen is not None else set()
    path = path.resolve()
    if path in seen or not path.is_file():
        return ""
    seen.add(path)
    text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))

    def inline(match: re.Match) -> str:
        name = match.group(1).strip()
        name = name if name.endswith(".tex") else name + ".tex"
        for folder in (base, path.parent):
            if (folder / name).is_file():
                return read_with_inputs(folder / name, base, seen)
        return match.group(0)  # not found: left as it is (reported as raw LaTeX)

    return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", inline, text)


def body_of(text: str) -> str:
    match = re.search(r"\\begin\{document\}(.*?)(\\end\{document\}|\Z)", text, re.S)
    return match.group(1) if match else text


IF_TOKEN = re.compile(r"\\(?:(ifdefined)\s*\\([A-Za-z@]+)|(if[A-Za-z@]*)|(else)|(fi))(?![A-Za-z@])")
# TeX conditionals (not \iff, which is maths); \newif ones are added
IF_PRIMITIVES = {"if", "ifx", "ifnum", "ifdim", "ifodd", "ifcase", "ifmmode", "ifvmode",
                 "ifhmode", "ifinner", "ifcat", "ifvoid", "ifeof", "iftrue", "iffalse",
                 "ifcsname", "ifthenelse"}


def resolve_conditionals(text: str, defined: set[str], ifs: set[str] = IF_PRIMITIVES
                         ) -> tuple[str, int]:
    """Keep the branch LaTeX would typeset for \\ifdefined\\x, \\iftrue and \\iffalse (others
    are left alone). Returns the text and the number of conditionals resolved."""
    out, pos, resolved = [], 0, 0
    tokens = [t for t in IF_TOKEN.finditer(text) if not t.group(3) or t.group(3) in ifs]
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        opening = tok.group(1) or tok.group(3)
        if not opening:
            i += 1
            continue
        # find this conditional's \else and \fi
        depth, else_at, j = 0, None, i + 1
        while j < len(tokens):
            t = tokens[j]
            if t.group(1) or t.group(3):
                depth += 1
            elif t.group(4) and depth == 0 and else_at is None:
                else_at = j
            elif t.group(5):
                if depth == 0:
                    break
                depth -= 1
            j += 1
        if j == len(tokens):  # no \fi: leave the rest alone
            break
        if tok.group(1):
            keep = tok.group(2) in defined
        elif opening in ("iftrue", "iffalse"):
            keep = opening == "iftrue"
        else:
            i = j + 1  # another \if...: leave it (and anything inside) as it is
            continue
        then_end = tokens[else_at].start() if else_at is not None else tokens[j].start()
        branch = (text[tok.end():then_end] if keep else
                  text[tokens[else_at].end():tokens[j].start()] if else_at is not None else "")
        inner, n = resolve_conditionals(branch, defined, ifs)
        out += [text[pos:tok.start()], inner]
        pos, resolved = tokens[j].end(), resolved + 1 + n
        i = j + 1
    out.append(text[pos:])
    return "".join(out), resolved


def definitions(text: str) -> dict[str, str]:
    """name -> one-line definition, rewritten as \\newcommand (what macros.tex expects)."""
    found = {}
    for line in strip_comments(text).splitlines():
        match = DEFINITION.search(line)
        if not match:
            continue
        name, stmt = match.group(1), line.strip()
        op = re.match(r"\\DeclareMathOperator\*?\s*\{?\\[A-Za-z]+\}?\s*\{(.*)\}\s*$", stmt)
        df = re.match(r"\\def\s*\\([A-Za-z]+)((?:#\d)*)\s*(\{.*)$", stmt)
        if op:
            stmt = f"\\newcommand{{\\{name}}}{{\\operatorname{{{op.group(1)}}}}}"
        elif df:
            args = len(df.group(2)) // 2
            stmt = f"\\newcommand{{\\{name}}}" + (f"[{args}]" if args else "") + df.group(3)
        else:
            stmt = re.sub(r"^\\(?:re|provide)newcommand\*?", r"\\newcommand", stmt)
        found[name] = stmt
    return found


def defined_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {m.group(1) for m in DEFINITION.finditer(strip_comments(path.read_text(encoding="utf-8")))}


def theorem_kinds(full: str) -> tuple[dict[str, str], dict[str, str]]:
    """Environment -> Quarto prefix, and the other \\newtheorem environments -> printed name."""
    kinds = {name: prefix for name, prefix in QUARTO_KINDS.items()}
    kinds.update({name + "*": prefix for name, prefix in QUARTO_KINDS.items()})
    others = {}
    for env, printed in NEWTHEOREM.findall(full):
        env, printed = env.strip(), printed.strip()
        prefix = QUARTO_KINDS.get(printed.lower())
        if prefix:
            kinds[env] = prefix
        else:
            kinds.pop(env, None)
            others[env] = printed
    return kinds, others


def graphics_dirs(full: str, base: Path) -> list[Path]:
    dirs = [base]
    for group in re.findall(r"\\graphicspath\s*\{((?:\s*\{[^}]*\})+)\s*\}", full):
        dirs += [(base / d).resolve() for d in re.findall(r"\{([^}]*)\}", group)]
    return dirs


def pdf_to_svg(pdf: Path, folder: Path) -> bool:
    """folder/<name>.svg for the HTML: the source's own .svg if it has one, else dvisvgm."""
    svg = folder / (pdf.stem + ".svg")
    if pdf.with_suffix(".svg").is_file():
        shutil.copy2(pdf.with_suffix(".svg"), svg)
        return True
    if not shutil.which("dvisvgm"):
        return False
    subprocess.run(["dvisvgm", "--pdf", "--no-fonts", "--exact-bbox", "-o", svg.name, pdf.name],
                   cwd=folder, capture_output=True)
    return svg.is_file()


def find_image(src: str, dirs: list[Path]) -> Path | None:
    for folder in dirs:
        candidate = folder / src
        if candidate.is_file():
            return candidate
        for ext in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"):
            if Path(str(candidate) + ext).is_file():
                return Path(str(candidate) + ext)
    return None


# --- Converting and reporting ----------------------------------------------------------

class Import:
    """One conversion: the Markdown and what the Lua filter reported."""

    def __init__(self, source: Path, mode: str):
        self.source = source
        base = source.resolve().parent
        self.full = read_with_inputs(source, base)
        self.defs = definitions(self.full)
        body = body_of(self.full)
        defined = set(self.defs) | set(re.findall(r"\\newcommand\*?\s*\{?\\([A-Za-z@]+)", self.full))
        ifs = IF_PRIMITIVES | set(re.findall(r"\\newif\s*\\(if[A-Za-z@]+)", self.full))
        body, self.conditionals = resolve_conditionals(body, defined, ifs)
        # enumitem spacing options ([noitemsep], [leftmargin=...]): no meaning in Quarto
        body = re.sub(r"(\\begin\{(?:itemize|description)\})\s*\[[^\]]*\]", r"\1", body)
        # Definitions inside the body would otherwise come out as raw LaTeX
        self.body = "\n".join(line for line in body.splitlines() if not DEFINITION.search(line))
        self.kinds, self.others = theorem_kinds(self.full)
        self.dirs = graphics_dirs(self.full, base)

        with tempfile.TemporaryDirectory() as tmp:
            lua = Path(tmp) / "import.lua"
            lua.write_text(LUA_FILTER, encoding="utf-8")
            env = {**os.environ, "IMPORT_MODE": mode, "IMPORT_LAYOUT": " ".join(LAYOUT),
                   "IMPORT_UNWRAP": " ".join(UNWRAP),
                   "IMPORT_THEOREMS": " ".join(f"{k}={v}" for k, v in self.kinds.items()),
                   "IMPORT_OTHERS": " ".join(f"{k}={re.sub(r'\s+', '_', v)}"
                                             for k, v in self.others.items())}
            result = subprocess.run(
                # -raw_tex on output: leftover LaTeX is written as `...`{=latex} or a fenced
                # {=latex} block, so it is visible and the report can find it exactly
                ["quarto", "pandoc", "-f", "latex-latex_macros-auto_identifiers+raw_tex",
                 # --wrap=preserve keeps the source's lines (--wrap=none loses text after a
                 # \\ line break in Pandoc 3.10)
                 "-t", "markdown-raw_tex", "--wrap=preserve", f"--resource-path={base}",
                 "--reference-location=block",  # footnotes stay in their chapter
                 "--lua-filter", str(lua)],
                input=self.body, capture_output=True, text=True, encoding="utf-8", env=env,
            )
        if result.returncode != 0:
            sys.exit(f"Pandoc failed:\n{result.stderr}")
        # Pandoc writes text-mode \; \quad ... as Unicode spaces, which pdflatex cannot print
        self.markdown = re.sub("[\\u2000-\\u200a\\u202f\\u205f]+", " ", result.stdout.strip())
        self.events = [line.split("\t", 1) for line in result.stderr.splitlines() if "\t" in line]
        # Guard: Pandoc's Markdown writer has lost text before. A few words from every
        # paragraph it was given must be in the Markdown.
        flat = " ".join(self.markdown.split())
        self.lost = [v for v in self.values("PARA") if v not in flat]
        if self.lost:
            print(f"WARNING: {len(self.lost)} paragraph(s) seem to be missing from the output, "
                  "for example the one with: " + " / ".join(f'"{v}"' for v in self.lost[:3])
                  + ". Compare with the source, and please report it.", file=sys.stderr)

    def values(self, kind: str) -> list[str]:
        return [v for k, v in self.events if k == kind]

    def place_images(self, folder: Path) -> None:
        """Copy the figures into folder and point the Markdown at them: PNG/JPG with their
        extension; PDF without (the template picks .pdf for PDF and .svg for HTML), with an
        .svg made by dvisvgm if the source has none."""
        folder = folder.resolve()
        copied, self.missing, self.no_svg = {}, [], []
        for src in dict.fromkeys(self.values("IMAGE")):
            found = find_image(src, self.dirs)
            if not found:
                self.missing.append(src)
                continue
            if found.name in copied and copied[found.name] != found:
                self.missing.append(f"{src} (another figure is also called {found.name})")
                continue
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(found, folder / found.name)
            copied[found.name] = found
            old = "figs/" + src.rsplit("/", 1)[-1]
            new = "figs/" + (found.stem if found.suffix.lower() == ".pdf" else found.name)
            if found.suffix.lower() == ".pdf" and not pdf_to_svg(found, folder):
                self.no_svg.append(found.name)
            if new != old:
                self.markdown = self.markdown.replace(f"]({old})", f"]({new})")
        self.copied = list(copied)
        self.images = folder

    def collect_macros(self) -> list[str]:
        """Macros defined in the source and used in the body, minus those already known."""
        used = {n for n in self.defs if re.search(r"\\" + n + r"(?![A-Za-z])", self.body)}
        known = (defined_names(ROOT / "_shared" / "macros-template.tex")
                 | defined_names(ROOT / "_shared" / "macros.tex"))
        target = SCRATCH / "imported-macros.tex"
        already = defined_names(target)
        new = sorted(used - known - already)
        if new:
            target.parent.mkdir(exist_ok=True)
            with target.open("a", encoding="utf-8", newline="\n") as f:
                if not already:
                    f.write("% Macros found by scripts/import_latex.py. Review them, then copy the "
                            "ones\n% you want into _shared/macros.tex (and delete this file).\n")
                f.write(f"\n% from {self.source.name}\n" + "".join(self.defs[n] + "\n" for n in new))
        return new

    def print_report(self, files: dict[str, str]) -> None:
        dropped = Counter(self.values("DROPPED"))
        if dropped:
            print("  layout commands dropped: " + ", ".join(f"\\{k} ({v})" for k, v in dropped.items()))
        if self.conditionals:
            print(f"  \\ifdefined/\\iftrue/\\iffalse: {self.conditionals} resolved "
                  "(kept what LaTeX typesets)")
        unwrapped = Counter(self.values("UNWRAPPED"))
        if unwrapped:
            print("  unwrapped: " + ", ".join(f"{k} ({v})" for k, v in unwrapped.items()))
        theorems = Counter(self.values("THEOREM"))
        if theorems:
            print("  theorem-like blocks: " + ", ".join(f"{k} ({v})" for k, v in theorems.items()))
        others = Counter(self.values("OTHER"))
        if others:
            print("  \\newtheorem environments with no Quarto equivalent (plain blocks with a "
                  "bold title, not numbered): " + ", ".join(f"{k} ({v})" for k, v in others.items()))
        adapted = len(self.values("MATH"))
        if adapted:
            print(f"  displayed maths: {adapted} environment(s) adapted (align -> aligned, ...)")
        multi = self.values("MULTILABEL")
        if multi:
            print(f"  {len(multi)} equation block(s) had several \\label: Quarto numbers the "
                  "block once, and all their references point to it")
        refs = self.values("REF")
        if refs:
            print(f"  cross-references converted: {len(refs)}")
        unresolved = Counter(self.values("UNRESOLVED"))
        if unresolved:
            print(f"  UNRESOLVED references (left raw): " + ", ".join(sorted(unresolved)))
        if self.copied:
            print(f"  figures copied to {self.images.relative_to(ROOT).as_posix()}/: {len(self.copied)}")
        if self.missing:
            print("  FIGURES NOT FOUND (copy them by hand): " + ", ".join(self.missing))
        if self.no_svg:
            print("  PDF figures with no .svg for the HTML (dvisvgm failed or is missing; see "
                  "README, TikZ figures): " + ", ".join(self.no_svg))
        new = self.collect_macros()
        if new:
            print(f"  macros added to _scratch/imported-macros.tex: " + ", ".join("\\" + n for n in new))
        packages = [p.strip() for group in re.findall(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}",
                                                      self.full) for p in group.split(",")]
        extra = sorted(set(packages) - KNOWN_PACKAGES)
        if extra:
            print("  packages the source loads (commands from them, such as \\bm or physics' "
                  "\\vb, are not available: define them in _shared/macros.tex or replace "
                  "them): " + ", ".join(extra))
        bibs = re.findall(r"\\(?:bibliography|addbibresource)\s*\{([^}]+)\}", self.full)
        for name in (n.strip() for group in bibs for n in group.split(",")):
            bib = self.source.resolve().parent / (name if name.endswith(".bib") else name + ".bib")
            if bib.is_file():
                SCRATCH.mkdir(exist_ok=True)
                shutil.copy2(bib, SCRATCH / f"imported-{bib.name}")
                print(f"  bibliography copied to _scratch/imported-{bib.name}: merge it into notes/refs.bib")
        bibitems = len(re.findall(r"\\bibitem", self.body))
        if bibitems:
            print(f"  thebibliography with {bibitems} \\bibitem entries: write them into "
                  "notes/refs.bib (BibTeX) by hand, then delete the list")
        leftovers: dict[str, list[str]] = {}
        for name, text in files.items():
            for command, line in raw_latex(text):
                leftovers.setdefault(command, []).append(f"{name}:{line}" if len(files) > 1 else str(line))
        if leftovers:
            print("  raw LaTeX left in the output (review these):")
            for command, where in sorted(leftovers.items(), key=lambda kv: -len(kv[1])):
                shown = ", ".join(where[:6]) + (", ..." if len(where) > 6 else "")
                print(f"    \\{command}: {len(where)} ({shown})")
        else:
            print("  no raw LaTeX left")


def raw_latex(text: str):
    """(what, line number) for each piece of raw LaTeX left in the Markdown: a raw block
    once (by its environment or first command), inline pieces by command."""
    in_block = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") and "{=latex}" in stripped:
            in_block, first = True, True
            continue
        if in_block:
            if stripped.startswith("```"):
                in_block = False
            elif first and stripped:
                env = re.match(r"\\begin\{([^}]+)\}", stripped)
                cmd = re.match(r"\\([A-Za-z]+)", stripped)
                yield (f"begin{{{env.group(1)}}}" if env else cmd.group(1) if cmd else "(raw)"), lineno
                first = False
            continue
        for raw in re.findall(r"`([^`]*)`\{=latex\}", line):
            for name in re.findall(r"\\([A-Za-z]+)", raw)[:1] or ["(raw)"]:
                yield name, lineno


# --- The two modes ---------------------------------------------------------------------

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

    imp = Import(source, "sheet")
    imp.place_images(dest.parent / "figs")
    number = re.search(r"(\d+)$", sheet_id)
    title = f"{TITLES[kind]} {number.group(1) if number else sheet_id}"
    if solutions:
        title += " -- Solutions"
    head = ["---", f'title: "{title}"', "---", ""]
    header = HEADERS.get((kind, solutions))
    if header:
        head += [f"{{{{< include ../../../_shared/{header} >}}}}", ""]
    text = "\n".join(head) + "\n" + imp.markdown + "\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")

    questions = int((imp.values("QUESTIONS") or ["0"])[0])
    print(f"Imported {source.name} -> {rel}")
    print(f"  {questions} question(s)" if questions else
          "  no top-level enumerate: no Question headings were made")
    imp.print_report({rel: text})
    if not (ROOT / "_module.yml").read_text(encoding="utf-8").count(f"{sheet_id}:"):
        print(f"  note: add an entry for {sheet_id} under {kind}: in _module.yml")
    return 0


def import_notes(source: Path, force: bool) -> int:
    if not source.is_file():
        sys.exit(f"No such file: {source}")
    imp = Import(source, "notes")
    notes = ROOT / "notes"
    count = imp.markdown.count(CHAPTER_MARK) or 1
    names = [f"chapter{i}.qmd" for i in range(1, count + 1)]
    existing = [n for n in names if (notes / n).exists()]
    if existing and not force:
        sys.exit(f"notes/ already has {', '.join(existing)}; use --force to replace them")
    imp.place_images(notes / "figs")
    parts = imp.markdown.split(CHAPTER_MARK)
    preface, chapters = parts[0].strip(), [p.strip() for p in parts[1:]]
    if not chapters:
        chapters, preface = [preface], ""

    files = {}
    for name, text in zip(names, chapters):
        (notes / name).write_text(text + "\n", encoding="utf-8", newline="\n")
        files[name] = text + "\n"
    print(f"Imported {source.name} -> notes/: {len(chapters)} chapter(s)")
    if preface:
        SCRATCH.mkdir(exist_ok=True)
        (SCRATCH / "imported-preface.md").write_text(preface + "\n", encoding="utf-8", newline="\n")
        print("  text before the first chapter: _scratch/imported-preface.md (move what you "
              "want into notes/index.qmd)")
    imp.print_report(files)
    print("  chapters for notes/_quarto.yml (book: chapters:):")
    print("    - index.qmd")
    for name in names:
        print(f"    - {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    sheet = sub.add_parser("sheet", help="a problem sheet or assignment (questions or solutions)")
    sheet.add_argument("source", type=Path, help="the LaTeX file")
    sheet.add_argument("dest", type=Path, help="sheets/<kind>/<id>/<id>[-solutions].qmd")
    sheet.add_argument("--force", action="store_true", help="replace an existing file")
    notes = sub.add_parser("notes", help="lecture notes: one chapter per file in notes/")
    notes.add_argument("source", type=Path, help="the main LaTeX file")
    notes.add_argument("--force", action="store_true", help="replace existing chapter files")
    args = parser.parse_args()
    if args.mode == "sheet":
        return import_sheet(args.source, args.dest, args.force)
    return import_notes(args.source, args.force)


if __name__ == "__main__":
    sys.exit(main())
