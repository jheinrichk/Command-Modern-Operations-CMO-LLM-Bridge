"""
conn.status_lua  -  the scenario status report the model works from.

One generated Lua script, read-only, indexed symbols only, wrapped in pcall
so a missing field on this build prints a marker rather than killing the
report. It prints, for one side (a commander) or for every side (a
scenario author):

    SCENARIO   title, tick, zulu, local time, elapsed, remaining
    SCORE      the side's score (a commander sees only its own)
    LOSSES     units of the side destroyed, from the side wrapper when the
               build exposes it, else from a baseline the bridge keeps
    KILLS      enemy units this side destroyed, same sources
    OOB        every unit: name, class, position, course, speed, altitude,
               fuel, damage, mission, weapon mounts, in-flight weapons
    CONTACTS   what the side currently holds on the other sides
    MISSIONS   name, type, active, assigned units, targets

The message log itself is CMO's AALog.txt and is delivered separately by
conn.cmologs, so it is not repeated here.
"""

STATUS_LUA = r'''-- CONN status report (read only, indexed symbols only)
local WANT = {side_filter}
local MAXU, MAXC = {max_units}, {max_contacts}
local S = function(v) if v == nil then return "-" end return tostring(v) end
local N = function(v, d) v = tonumber(v) if v == nil then return "-" end return string.format("%." .. (d or 2) .. "f", v) end
local g = function(f) local o, r = pcall(f) if o then return r end return nil end
local function count(t) local n = 0 if type(t) == "table" then for _ in pairs(t) do n = n + 1 end end return n end

print("=== STATUS REPORT ===")
-- ---------- scenario and time ----------
local sc = g(function() return VP_GetScenario() end)
local tick = g(function() return ScenEdit_CurrentTime() end)
print("TITLE: " .. S(sc and (sc.Title or sc.title)))
print("TICK: " .. S(tick))
print("ZULU: " .. S(g(function() return os.date("!%Y-%m-%d %H:%M:%SZ", tonumber(tick)) end)))
print("LOCAL_TIME: " .. S(g(function() return ScenEdit_CurrentLocalTime() end)))
do
  local st = tonumber(sc and (sc.StartTimeNum or sc.starttimenum))
  local du = tonumber(sc and (sc.DurationNum or sc.durationnum))
  local cu = tonumber(sc and (sc.CurrentTimeNum or sc.currenttimenum)) or tonumber(tick)
  if st and cu then
    local el = cu - st
    print(string.format("ELAPSED: %ds (%.2fh)", el, el / 3600))
    if du then print(string.format("REMAINING: %ds (%.2fh)", du - el, (du - el) / 3600)) end
  end
end

-- ---------- per side ----------
local sides = g(function() return VP_GetSides() end) or {}
for _, sd in ipairs(sides) do
  local name = S(sd.name)
  local mine = (WANT == nil) or (name == WANT)
  if mine then
    print("")
    print("=== SIDE: " .. name .. " ===")
    print("SCORE: " .. S(g(function() return ScenEdit_GetScore(name) end)))
    local side = g(function() return VP_GetSide({ side = name }) end)
    -- losses / kills / expenditures when the build exposes them on the wrapper
    for _, key in ipairs({ "losses", "kills", "expenditures" }) do
      local tbl = g(function() return side and side[key] end)
      if type(tbl) == "table" then
        print(string.upper(key) .. ": " .. count(tbl))
        local shown = 0
        for _, e in pairs(tbl) do
          shown = shown + 1
          if shown <= 40 then
            if type(e) == "table" then
              print(string.format("  %s|%s|%s|%s", string.upper(string.sub(key, 1, 4)),
                S(e.name or e.Name), S(e.classname or e.type or e.Class), S(e.side or e.Side or e.dbid)))
            else
              print("  " .. string.upper(string.sub(key, 1, 4)) .. "|" .. S(e))
            end
          end
        end
      else
        print(string.upper(key) .. ": (not exposed on this build; see the message log digest)")
      end
    end
    -- order of battle
    local units = (side and side.units) or {}
    local bytype = {}
    print("OOB_TOTAL: " .. count(units))
    local shown = 0
    for _, e in pairs(units) do
      if type(e) == "table" and e.guid then
        local u = g(function() return ScenEdit_GetUnit({ guid = e.guid }) end)
        if u then
          local ty = S(u.type)
          bytype[ty] = (bytype[ty] or 0) + 1
          if ty ~= "Weapon" then
            shown = shown + 1
            if shown <= MAXU then
              local fuel = "-"
              local fo = g(function() return u.fuel end)
              if type(fo) == "table" then
                for _, fv in pairs(fo) do
                  if type(fv) == "table" and fv.current then
                    local cur, mx = tonumber(fv.current), tonumber(fv.max)
                    fuel = (cur and mx and mx > 0) and string.format("%d%%", math.floor(100 * cur / mx)) or S(cur)
                    break
                  end
                end
              end
              local dmg = "-"
              local d = g(function() return u.damage end)
              if type(d) == "table" then dmg = S(d.percent) elseif d ~= nil then dmg = S(d) end
              local mis = g(function() local m = u.mission return m and (m.name or m) end)
              local mounts = g(function() return count(u.mounts) end)
              local wpn = g(function() return count(u.weapons) end)
              local base = g(function() local b = u.base return b and (b.name or b) end)
              print(string.format("UNIT|%s|%s|%s|%s,%s|crs=%s|spd=%s|alt=%s|fuel=%s|dmg=%s|mission=%s|mounts=%s|weapons=%s|base=%s",
                S(u.name), ty, S(u.classname), N(u.latitude, 3), N(u.longitude, 3),
                N(u.heading, 0), N(u.speed, 0), N(u.altitude, 0), fuel, dmg,
                S(mis), S(mounts), S(wpn), S(base)))
            end
          end
        end
      end
    end
    local parts = {}
    for ty, n in pairs(bytype) do parts[#parts + 1] = ty .. "=" .. n end
    table.sort(parts)
    print("OOB_BY_TYPE: " .. table.concat(parts, " "))
    if shown > MAXU then print("OOB_TRUNCATED: " .. (shown - MAXU) .. " more units not listed") end
    -- contacts held by this side
    local cs = g(function() return ScenEdit_GetContacts(name) end)
    if type(cs) == "table" then
      print("CONTACTS: " .. count(cs))
      local cshown = 0
      for _, c in pairs(cs) do
        if type(c) == "table" then
          cshown = cshown + 1
          if cshown <= MAXC then
            print(string.format("CONTACT|%s|%s|%s|%s|%s,%s|spd=%s|alt=%s|age=%s",
              S(c.name), S(c.type), S(c.classificationlevel or c.classification),
              S(c.posture), N(c.latitude, 3), N(c.longitude, 3), N(c.speed, 0),
              N(c.altitude, 0), S(c.age)))
          end
        end
      end
    else
      print("CONTACTS: (not readable)")
    end
    -- missions
    local ms = (side and side.missions) or {}
    print("MISSIONS: " .. count(ms))
    for _, e in pairs(ms) do
      if type(e) == "table" then
        local m = g(function() return ScenEdit_GetMission(name, e.name or e.guid) end) or e
        print(string.format("MISSION|%s|%s|active=%s|units=%s|targets=%s",
          S(m.name or e.name), S(m.typeS or m.type), S(m.isactive),
          count(g(function() return m.unitlist end)), count(g(function() return m.targetlist end))))
      end
    end
  end
end
print("=== END STATUS ===")
'''


def status_lua(side=None, max_units=120, max_contacts=60):
    """Lua for a status report. side=None reports every side (scenario
    author); a side name limits the report to that side (commander)."""
    side_filter = "nil" if not side else '"{}"'.format(str(side).replace('"', '\\"'))
    return STATUS_LUA.replace("{side_filter}", side_filter) \
                     .replace("{max_units}", str(int(max_units))) \
                     .replace("{max_contacts}", str(int(max_contacts)))
