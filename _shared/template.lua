-- Template file: do not edit it in a module (see "Template and module files" in README.md).
-- Template filter, used by the notes and the sheets.
--
-- Everywhere:
--  * injects the macros in _shared/macros-template.tex and _shared/macros.tex (the
--    module's, which win over the template's) into both PDF and HTML output
--  * makes ::: {.center} and ::: {.infobox} divs work in PDF too
--  * lists: keeps (a) / a) labels in HTML (see style.css)
--
-- Sheets (problem sheets and assignments) only:
--  * module code/title and term from _module.yml, for the headers
--  * marks: [2]{.marks} shows a right-aligned [2]; in a heading, [8 marks]
--  * marking notes: [text]{.marking} inline, or ::: {.marking} as a block
--  * warns when the marks of the parts do not add up to the question total
--  * marks and marking notes are removed in student builds (and whenever
--    `hide-marking: true` is set)
--  * difficulty: [2]{.difficulty} shows 2 icons (1 easy, 2 medium, 3 hard);
--    the icon is set by `difficulty-icon` in _module.yml
--  * draws `---` horizontal rules full width in PDF
--  * release control: in a student build, the content of unreleased solutions
--    is replaced by a placeholder, which scripts/post_render_student.py deletes
--  * banner: "staff copy" (staff build) or "released on" (released solutions)
--  * changes after release: `changes:` in the front matter gives one
--    "Updated <date>: ..." line per entry under the header box (none: nothing)
--  * hidden marker (HTML <meta>, PDF info) read by scripts/leak_check.py

local common = dofile(quarto.utils.resolve_path("common.lua"))

local info = nil      -- which sheet this is (nil for the notes)
local staff = false   -- staff or student build
local withheld = false

-- Difficulty icons -----------------------------------------------------------

-- Built-in style: one icon in LaTeX and HTML, and the separator between icons
local icon_styles = {
  stars = {
    latex = function() return "\\difficultystar" end, latex_sep = "",
    html = function() return '<span class="star" aria-hidden="true">★</span>' end,
  },
}

-- A module's own icon: difficulty-icon is a path (relative to the repository
-- root, without extension) to an image with a .pdf (for PDF) and an .svg (for
-- HTML), for example a TikZ figure sheets/figs/bolt.tex built by
-- scripts/tikz.py. The SVG is inlined, so it also works in self-contained HTML.
local function read_file(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local content = f:read("a")
  f:close()
  return content
end

local function image_style(name)
  local base = pandoc.path.join({ quarto.utils.resolve_path(".."), name })
  if quarto.doc.is_format("latex") then
    local pdf = base .. ".pdf"
    if not read_file(pdf) then return nil end
    local path = pdf:gsub("\\", "/")
    return { latex = function() return "\\difficultyimage{" .. path .. "}" end,
             latex_sep = "\\," }
  end
  local svg = read_file(base .. ".svg")
  if not svg then return nil end
  svg = svg:gsub("^.-<svg", "<svg", 1)   -- drop the XML declaration and comments
  return { html = function()
    return '<span class="difficulty-image" aria-hidden="true">' .. svg .. "</span>"
  end }
end

local difficulty_names = { "easy", "medium", "hard" }

local function difficulty_level(span)
  local n = tonumber(pandoc.utils.stringify(span))
  if not n or n < 1 or n > 3 or n % 1 ~= 0 then
    quarto.log.warning("Difficulty should be 1, 2 or 3, not '"
      .. pandoc.utils.stringify(span) .. "'")
    n = math.max(1, math.min(3, math.floor(n or 1)))
  end
  return n
end

local function difficulty_icons(span)
  local n = difficulty_level(span)
  local style_name = common.str(common.config()["difficulty-icon"]) or "stars"
  local label = "Difficulty: " .. difficulty_names[n]
  local style = icon_styles[style_name] or image_style(style_name)
  if not style then
    error("difficulty-icon '" .. style_name .. "' in _module.yml: no such image. Use "
      .. "stars, or the path of an image with .pdf and .svg versions (no extension, "
      .. "relative to the repository root).", 0)
  end
  if quarto.doc.is_format("latex") then
    -- \texorpdfstring keeps the icons out of the PDF bookmarks
    local icons = {}
    for _ = 1, n do table.insert(icons, style.latex()) end
    return pandoc.RawInline("latex", "\\texorpdfstring{\\mbox{("
      .. table.concat(icons, style.latex_sep) .. ")}}{}")
  end
  return pandoc.RawInline("html",
    '<span class="difficulty" role="img" aria-label="' .. label
    .. '" title="' .. label .. '">(' .. string.rep(style.html(), n) .. ")</span>")
end

-- Macros ---------------------------------------------------------------------

-- Definitions in a macros file: its non-empty, non-comment lines.
local function macro_lines(name)
  local path = quarto.utils.resolve_path(name)
  local f = io.open(path, "r")
  if not f then
    quarto.log.warning("Could not open " .. path)
    return {}
  end
  local lines = {}
  for line in f:lines() do
    if line:match("%S") and not line:match("^%s*%%") then
      table.insert(lines, line)
    end
  end
  f:close()
  return lines
end

-- The macro a line defines: \newcommand{\bfx}..., \def\bfx..., etc. give "bfx".
local function defined_name(line)
  return line:match("^%s*\\%a+%*?%s*{?%s*\\(%a+)")
end

-- macros-template.tex, then the module's macros.tex. A name the module defines
-- replaces the template's definition, so the module never needs \renewcommand.
local function read_macros()
  local own = macro_lines("macros.tex")
  local mine = {}
  for _, line in ipairs(own) do
    local name = defined_name(line)
    if name then mine[name] = true end
  end
  local lines = {}
  for _, line in ipairs(macro_lines("macros-template.tex")) do
    local name = defined_name(line)
    if not (name and mine[name]) then table.insert(lines, line) end
  end
  for _, line in ipairs(own) do table.insert(lines, line) end
  return table.concat(lines, "\n")
end

-- Marks ----------------------------------------------------------------------

local function is_marks(el)
  return el.classes:includes("marks")
end

local function marks_value(span)
  return tonumber(pandoc.utils.stringify(span))
end

local function marks_label(span, in_heading)
  local text = pandoc.utils.stringify(span)
  local n = tonumber(text)
  if in_heading and n then
    return "[" .. text .. (n == 1 and " mark]" or " marks]")
  end
  return "[" .. text .. "]"
end

-- Pass 0: work out what is being rendered; withhold unreleased solutions.
local function setup(doc)
  info = common.doc_info()
  staff = common.is_staff()
  if not info then return nil end
  if info.role == "solutions" and not staff and not common.released(info) then
    withheld = true
    doc.blocks = pandoc.Blocks({ pandoc.Para(
      "These solutions have not been released. This placeholder is deleted after "
      .. "the build; if you can see it, do not upload it.") })
    return doc
  end
end

-- Pass 1: drop marks and marking notes (student builds, or `hide-marking`).
local function strip_marking(doc)
  if not info or not (doc.meta["hide-marking"] or not staff) then return nil end
  return doc:walk({
    Span = function(s)
      if is_marks(s) or s.classes:includes("marking") then return {} end
    end,
    Div = function(d)
      if d.classes:includes("marking") then return {} end
    end,
  })
end

-- Pass 2: check that the part marks add up to the total in each heading.
local function check_totals(doc)
  if not info then return nil end
  local name, expected, sum = nil, nil, 0
  local function finish()
    if name and expected and sum > 0 and math.abs(sum - expected) > 1e-9 then
      quarto.log.warning(string.format(
        "%s: the parts add up to %g marks, but the heading says %g",
        name, sum, expected))
    end
  end
  for _, blk in ipairs(doc.blocks) do
    if blk.t == "Header" then
      finish()
      local text = pandoc.utils.stringify(blk)
      name = text:match("^Question%s+%d+") or text
      expected, sum = nil, 0
      blk:walk({ Span = function(s)
        if is_marks(s) then expected = marks_value(s) end
      end })
    else
      blk:walk({ Span = function(s)
        if is_marks(s) then sum = sum + (marks_value(s) or 0) end
      end })
    end
  end
  finish()
end

-- Pass 3: formatting.
local function Header(el)
  return el:walk({ Span = function(s)
    if s.classes:includes("difficulty") then return difficulty_icons(s) end
    if not is_marks(s) then return nil end
    local label = marks_label(s, true)
    if quarto.doc.is_format("latex") then
      return pandoc.RawInline("latex",
        "\\texorpdfstring{\\hfill\\mbox{\\color{accent}" .. label .. "}}{}")
    end
    s.content = { pandoc.Str(label) }
    s.classes = { "marks", "marks-total" }
    s.attributes["data-done"] = "1"
    return s
  end })
end

local function Span(el)
  if el.classes:includes("difficulty") then return difficulty_icons(el) end
  if is_marks(el) and not el.attributes["data-done"] then
    local label = marks_label(el, false)
    if quarto.doc.is_format("latex") then
      return pandoc.RawInline("latex", "\\marksbox{" .. label .. "}")
    end
    el.content = { pandoc.Str(label) }
    return el
  end
  if el.classes:includes("marking") and quarto.doc.is_format("latex") then
    local out = pandoc.Inlines({ pandoc.RawInline("latex", "{\\markingfont{}") })
    out:extend(el.content)
    out:insert(pandoc.RawInline("latex", "}"))
    return out
  end
end

local latex_envs = { center = "center", infobox = "infobox", marking = "markingbox" }

local function Div(el)
  if not quarto.doc.is_format("latex") then return nil end
  for class, env in pairs(latex_envs) do
    if el.classes:includes(class) then
      el.content:insert(1, pandoc.RawBlock("latex", "\\begin{" .. env .. "}"))
      el.content:insert(pandoc.RawBlock("latex", "\\end{" .. env .. "}"))
      return el
    end
  end
end

-- Lists ------------------------------------------------------------------------

-- Pandoc's HTML drops the delimiter of ordered lists: (a), a) and a. all become
-- <ol type="a">. Keep delimiter and numbering as classes on a wrapper, for the
-- labels in style.css (CSS cannot tell type="a" from type="A").
local delimiter_class = { TwoParens = "list-parens", OneParen = "list-paren" }
local style_class = {
  LowerAlpha = "list-lower-alpha", UpperAlpha = "list-upper-alpha",
  LowerRoman = "list-lower-roman", UpperRoman = "list-upper-roman",
}

local function OrderedList(el)
  if not quarto.doc.is_format("html") then return nil end
  local a = el.listAttributes
  local classes = (delimiter_class[a.delimiter] or "list-period") .. " "
    .. (style_class[a.style] or "list-decimal")
  return pandoc.Div(el, { class = classes })
end

local function HorizontalRule()
  if info and quarto.doc.is_format("latex") then
    return pandoc.RawBlock("latex", "\\medskip\\hrule\\bigskip")
  end
end

-- Changes after release -------------------------------------------------------

-- `changes:` in a sheet's front matter (a list of date + text): one line per entry,
-- newest first, "Updated 12 February 2027: ...", under the header box. Nothing is
-- shown without entries; withheld solutions keep only their placeholder.
local function add_changes(doc)
  if not info or withheld then return nil end
  local list = doc.meta.changes
  if not list or pandoc.utils.type(list) ~= "List" or #list == 0 then return nil end

  local entries = {}
  for _, e in ipairs(list) do
    local date = e.date and common.str(e.date)
    if not date or not e.text then
      quarto.log.warning(info.id .. ": an entry in `changes` needs both `date` and `text`.")
    else
      if common.in_future(date) then
        quarto.log.warning(info.id .. ": the change dated " .. date .. " is in the future.")
      end
      local text = pandoc.utils.type(e.text) == "Inlines" and e.text
        or pandoc.Inlines(pandoc.utils.stringify(e.text))
      table.insert(entries, { date = date, text = text })
    end
  end
  if #entries == 0 then return nil end
  table.sort(entries, function(a, b) return a.date > b.date end)

  local paras = pandoc.Blocks({})
  for _, e in ipairs(entries) do
    local line = pandoc.Inlines({
      pandoc.Strong("Updated " .. common.format_date(e.date, false) .. ":"), pandoc.Space() })
    line:extend(e.text)
    paras:insert(pandoc.Para(line))
  end

  -- After the header box (and marker notes at the top), else at the very top.
  local at = 1
  while doc.blocks[at] and doc.blocks[at].t == "Div"
      and (doc.blocks[at].classes:includes("infobox")
        or doc.blocks[at].classes:includes("marking")) do
    at = at + 1
  end
  doc.blocks:insert(at, pandoc.Div(paras, { class = "doc-changes" }))
  return doc
end

-- Banner text for this document, and whether it is a warning (red).
local function banner()
  if staff then
    if info.role == "solutions" then
      return "STAFF COPY – CONTAINS SOLUTIONS. DO NOT DISTRIBUTE TO STUDENTS.", true
    end
    return "STAFF COPY – DO NOT DISTRIBUTE. Upload the student build instead.", true
  end
  if info.role == "solutions" and not withheld then
    local date = common.setting(info, "release-date")
    if date and common.in_future(date) then
      quarto.log.warning(info.id .. ": solutions are marked as released, but the "
        .. "release date " .. common.str(date) .. " is in the future.")
    end
    if date then
      return "Solutions released on " .. common.format_date(date, false) .. ".", false
    end
    return "Solutions released.", false
  end
  return nil
end

local function marker()
  return string.format("ma-template-doc kind=%s id=%s role=%s build=%s",
    info.kind, info.id, withheld and "withheld" or info.role,
    staff and "staff" or "student")
end

local function Pandoc(doc)
  local macros = read_macros()
  if quarto.doc.is_format("latex") then
    if macros ~= "" then quarto.doc.include_text("in-header", macros) end
  elseif quarto.doc.is_format("html") and macros ~= "" then
    doc.blocks:insert(1, pandoc.RawBlock("html",
      '<div style="display:none">\n\\(\n' .. macros .. '\n\\)\n</div>'))
  end
  if not info then return doc end

  local conf = common.config()
  local module = conf.module or {}
  local module_name = common.str(module.code) or ""
  if module.title then module_name = module_name .. " " .. common.str(module.title) end
  doc.meta.module = module_name
  if module.term then doc.meta.term = common.str(module.term) end

  local text, alert = banner()
  local mark = marker()
  if quarto.doc.is_format("latex") then
    -- Running header: title without a trailing "-- Solutions"
    if doc.meta.title then
      local t = pandoc.utils.stringify(doc.meta.title)
      t = t:gsub("%s+–%s+Solutions%s*$", ""):gsub("%s+%-%-?%s+Solutions%s*$", "")
      doc.meta["header-title"] = t
    end
    if text then
      doc.meta.banner = text
      doc.meta["banner-alert"] = alert
    end
    quarto.doc.include_text("in-header",
      "\\AtBeginDocument{\\hypersetup{pdfinfo={MATemplate={" .. mark .. "}}}}")
  elseif quarto.doc.is_format("html") then
    quarto.doc.include_text("in-header", '<meta name="ma-template" content="' .. mark .. '">')
    if text then
      doc.blocks:insert(1, pandoc.Div(pandoc.Para(text),
        { class = alert and "doc-banner doc-banner-alert" or "doc-banner" }))
    end
    if not doc.meta.subtitle then
      local s = module_name
      if doc.meta.term then s = s .. " · " .. pandoc.utils.stringify(doc.meta.term) end
      doc.meta.subtitle = s
    end
  end
  return doc
end

return {
  { Pandoc = setup },
  { Pandoc = strip_marking },
  { Pandoc = check_totals },
  { Pandoc = add_changes },
  { Header = Header },  -- before Span, so heading totals get their own style
  { Span = Span, Div = Div, HorizontalRule = HorizontalRule,
    OrderedList = OrderedList, Pandoc = Pandoc },
}
