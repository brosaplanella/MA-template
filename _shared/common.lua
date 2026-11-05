-- Template file: do not edit it in a module (see "Template and module files" in README.md).
-- Helpers shared by template.lua (filter) and sheet.lua (shortcode):
--  * read the module settings: _module.yml, then _local.yml on top (if present)
--  * work out which sheet is being rendered from its path:
--      sheets/<kind>/<id>/<id>.qmd            questions
--      sheets/<kind>/<id>/<id>-solutions.qmd  solutions
--    where <kind> is "problem-sheets" or "assignments"
--  * look up per-sheet settings, falling back to the kind's `defaults`
-- scripts/moduleconf.py implements the same rules in Python (for the leak check);
-- keep the two in sync.

local M = {}

M.kinds = { ["problem-sheets"] = true, ["assignments"] = true }

local function read_yaml(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local text = f:read("a")
  f:close()
  if not text:match("%S") then return {} end
  -- Let pandoc parse the YAML: values come back as pandoc metadata
  return pandoc.read("---\n" .. text .. "\n---\n", "markdown").meta
end

local function is_map(v)
  return pandoc.utils.type(v) == "table"
end

local function merge(base, top)
  for k, v in pairs(top) do
    if is_map(v) and is_map(base[k]) then
      merge(base[k], v)
    else
      base[k] = v
    end
  end
  return base
end

local config_cache = nil

function M.config()
  if config_cache then return config_cache end
  local root = quarto.utils.resolve_path("..")
  local conf = read_yaml(pandoc.path.join({ root, "_module.yml" }))
  if not conf then
    quarto.log.warning("Could not read _module.yml in " .. root)
    conf = {}
  end
  local localconf = read_yaml(pandoc.path.join({ root, "_local.yml" }))
  if localconf then merge(conf, localconf) end
  config_cache = conf
  return conf
end

function M.str(v)
  if v == nil then return nil end
  if type(v) == "boolean" then return tostring(v) end
  return pandoc.utils.stringify(v)
end

-- Which sheet is this? Returns nil for documents outside sheets/<kind>/<id>/.
function M.doc_info()
  local input = quarto.doc.input_file
  if not input then return nil end
  local parts = pandoc.path.split(pandoc.path.normalize(input))
  local n = #parts
  if n < 3 then return nil end
  local kind, id = parts[n - 2], parts[n - 1]
  if not M.kinds[kind] then return nil end
  local base = pandoc.path.split_extension(parts[n])
  local role
  if base == id then
    role = "questions"
  elseif base == id .. "-solutions" then
    role = "solutions"
  else
    quarto.log.warning(parts[n] .. " does not follow the naming convention <id>.qmd / "
      .. "<id>-solutions.qmd for folder " .. id .. "; treating it as solutions.")
    role = "solutions"
  end
  return { kind = kind, id = id, role = role }
end

-- Setting for one sheet: its own entry first, then the kind's `defaults`.
function M.setting(info, key)
  local section = M.config()[info.kind]
  if not is_map(section) then return nil end
  local entry = section[info.id]
  if is_map(entry) and entry[key] ~= nil then return entry[key] end
  local defaults = section["defaults"]
  if is_map(defaults) then return defaults[key] end
  return nil
end

function M.released(info)
  return M.setting(info, "solutions-released") == true
end

-- The staff profile must be asked for explicitly; anything else is a student build.
function M.is_staff()
  local profiles = quarto.project.profile or {}
  for _, p in ipairs(profiles) do
    if p == "staff" then return true end
  end
  return false
end

-- "2026-10-15" or "2026-10-15 12:00" -> os.time value (and whether a time was given)
local function parse_date(s)
  local y, m, d = s:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)")
  if not y then return nil end
  local hh, mm = s:match("[T ](%d%d?):(%d%d)")
  local t = os.time({ year = tonumber(y), month = tonumber(m), day = tonumber(d),
    hour = tonumber(hh or 12), min = tonumber(mm or 0) })
  return t, hh ~= nil
end

-- "Thursday 15 October 2026" (+ ", 12:00" when a time was given)
function M.format_date(value, with_weekday)
  local s = M.str(value)
  if not s then return nil end
  local t, has_time = parse_date(s)
  if not t then return s end  -- free text: show as written
  local out = os.date((with_weekday and "%A " or "") .. "%d %B %Y", t)
  out = out:gsub(" 0(%d) ", " %1 "):gsub("^0", "")
  if has_time then out = out .. os.date(", %H:%M", t) end
  return out
end

-- Is the date (YYYY-MM-DD...) in the future?
function M.in_future(value)
  local s = M.str(value)
  local day = s and s:match("^(%d%d%d%d%-%d%d%-%d%d)")
  return day ~= nil and day > os.date("%Y-%m-%d")
end

return M
