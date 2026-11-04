-- Module filter, used by the notes and the sheets.
--
-- Everywhere:
--  * injects the macros in _shared/macros.tex into both PDF and HTML output
--  * makes ::: {.center} and ::: {.infobox} divs work in PDF too
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
--  * hidden marker (HTML <meta>, PDF info) read by scripts/leak_check.py

local common = dofile(quarto.utils.resolve_path("common.lua"))

local info = nil      -- which sheet this is (nil for the notes)
local staff = false   -- staff or student build
local withheld = false

-- Difficulty icons -----------------------------------------------------------

-- Spring icon: a vertical coil (a prolate cycloid) with straight leads, in a
-- 12 x 24 box. The same points are used for the PDF (TikZ) and HTML (SVG).
local spring_points = (function()
  local pts = { { 6, 0 } }
  local loops, n, b, c = 3, 200, 2.4, 4.5
  local a = (20.5 - 3.5) / (2 * math.pi * loops)
  for i = 0, n do
    -- start/end at t = pi/2 (mod 2 pi), where the coil crosses the centre line
    local s = 2 * math.pi * loops * i / n
    local t = s + math.pi / 2
    table.insert(pts, { 6 - c * math.cos(t), 3.5 + a * s + b * (1 - math.sin(t)) })
  end
  table.insert(pts, { 6, 24 })
  return pts
end)()

local function spring_latex()
  local coords = {}
  for _, p in ipairs(spring_points) do
    table.insert(coords, string.format("(%.2f,%.2f)", p[1], 24 - p[2]))
  end
  return "\\springicon{" .. table.concat(coords) .. "}"
end

local function spring_svg()
  local coords = {}
  for _, p in ipairs(spring_points) do
    table.insert(coords, string.format("%.2f,%.2f", p[1], p[2]))
  end
  return '<svg class="spring" viewBox="0 -0.5 12 25" aria-hidden="true">'
    .. '<polyline points="' .. table.concat(coords, " ") .. '"/></svg>'
end

-- Each style: one icon in LaTeX and HTML, and the separator between icons
local icon_styles = {
  stars = {
    latex = function() return "\\difficultystar" end, latex_sep = "",
    html = function() return '<span class="star" aria-hidden="true">★</span>' end,
  },
  springs = {
    latex = spring_latex, latex_sep = "\\,",
    html = spring_svg,
  },
}

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
  if style_name == "numbers" then
    if quarto.doc.is_format("latex") then
      return pandoc.RawInline("latex", "\\texorpdfstring{\\difficultynumber{" .. n .. "}}{}")
    end
    return pandoc.RawInline("html", '<span class="difficulty difficulty-number" title="'
      .. label .. '">(' .. n .. ")</span>")
  end
  local style = icon_styles[style_name]
  if not style then
    quarto.log.warning("Unknown difficulty-icon '" .. style_name
      .. "' (use stars, springs or numbers); using stars")
    style = icon_styles.stars
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

local function read_macros()
  local path = quarto.utils.resolve_path("macros.tex")
  local f = io.open(path, "r")
  if not f then
    quarto.log.warning("Could not open " .. path)
    return ""
  end
  local lines = {}
  for line in f:lines() do
    if line:match("%S") and not line:match("^%s*%%") then
      table.insert(lines, line)
    end
  end
  f:close()
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

local function HorizontalRule()
  if info and quarto.doc.is_format("latex") then
    return pandoc.RawBlock("latex", "\\medskip\\hrule\\bigskip")
  end
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
  { Header = Header },  -- before Span, so heading totals get their own style
  { Span = Span, Div = Div, HorizontalRule = HorizontalRule,
    Pandoc = Pandoc },
}
