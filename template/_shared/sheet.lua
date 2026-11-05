-- Template file: do not edit it in a module (see "Template and module files" in README.md).
-- Shortcode {{< sheet key >}}: a setting for the current sheet from _module.yml.
-- It looks in the sheet's own entry first, then in the kind's `defaults`:
--
--   assignments:
--     defaults:
--       submission: "Upload a single PDF via Moodle."
--     assignment-1:
--       deadline: 2026-10-15 12:00
--
--   {{< sheet deadline >}}    -> Thursday 15 October 2026, 12:00 (plus `deadline-label`)
--   {{< sheet submission >}}  -> Upload a single PDF via Moodle.

local common = dofile(quarto.utils.resolve_path("common.lua"))

local function sheet(args)
  local key = pandoc.utils.stringify(args[1] or "")
  local info = common.doc_info()
  if not info then
    quarto.log.warning("{{< sheet " .. key .. " >}} only works in sheets/<kind>/<id>/ files")
    return pandoc.Inlines({})
  end
  local value = common.setting(info, key)
  if value == nil then
    quarto.log.warning(info.id .. ": no setting '" .. key .. "' in _module.yml")
    return pandoc.Strong(pandoc.Str("[" .. key .. " missing]"))
  end
  if key == "deadline" then
    local text = common.format_date(value, true)
    local label = common.setting(info, "deadline-label")
    if label then text = text .. " (" .. common.str(label) .. ")" end
    return pandoc.Str(text)
  end
  if key == "release-date" then
    return pandoc.Str(common.format_date(value, false))
  end
  local t = pandoc.utils.type(value)
  if t == "Inlines" or t == "Blocks" then return value end
  return pandoc.Str(common.str(value))
end

-- Shortcode {{< notes label >}}: a reference to the lecture notes, where `label` is a
-- cross-reference label there (sec-..., thm-..., eq-..., fig-...):
--
--   see {{< notes thm-FTC >}} of the lecture notes
--     PDF:  see Theorem 2.1 of the lecture notes
--     HTML: the same, with "Theorem 2.1" linking to the theorem in the notes on Moodle
--
-- Numbers and pages come from _shared/generated/notes-xref.json, written by
-- scripts/notes_xref.py after every render of the notes. The link needs `notes: url:`
-- in _module.yml (the address of the notes on Moodle).

local xref_cache = nil

local function notes_xref()
  if xref_cache then return xref_cache end
  local path = quarto.utils.resolve_path("generated/notes-xref.json")
  local f = io.open(path, "r")
  if not f then
    quarto.log.warning("No " .. path .. ": render the notes first")
    xref_cache = {}
    return xref_cache
  end
  local text = f:read("a")
  f:close()
  xref_cache = pandoc.json.decode(text, false) or {}
  return xref_cache
end

-- Base address of the notes: "https://.../notes/index.html" -> "https://.../notes/"
local function notes_base()
  local notes = common.config()["notes"]
  local url = pandoc.utils.type(notes) == "table" and common.str(notes["url"]) or nil
  if not url or url == "" then return nil end
  if url:match("view%.php") then
    quarto.log.warning("notes: url: in _module.yml is a view.php address; use the address "
      .. "of the notes page itself (with pluginfile.php), see the comment there")
  end
  url = url:gsub("[^/]*%.html?$", "")
  if not url:match("/$") then url = url .. "/" end
  return url
end

local warned_no_url = false

local function notes(args)
  local label = pandoc.utils.stringify(args[1] or ""):gsub("^[@#]", "")
  local entry = notes_xref()[label]
  if not entry then
    quarto.log.warning("{{< notes " .. label .. " >}}: no label '" .. label
      .. "' in the notes (render the notes to update the labels)")
    return pandoc.Strong(pandoc.Str("[" .. label .. "?]"))
  end
  local text = pandoc.Inlines({ pandoc.Str(entry.name .. "\u{a0}" .. entry.number) })
  if not quarto.doc.is_format("html") then return text end
  local base = notes_base()
  if not base then
    if not warned_no_url then
      quarto.log.warning("{{< notes >}}: set notes: url: in _module.yml to link to the notes")
      warned_no_url = true
    end
    return text
  end
  return pandoc.Link(text, base .. entry.page .. "#" .. label)
end

return { ["sheet"] = sheet, ["notes"] = notes }
