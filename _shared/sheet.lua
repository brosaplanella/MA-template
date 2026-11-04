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

return { ["sheet"] = sheet }
