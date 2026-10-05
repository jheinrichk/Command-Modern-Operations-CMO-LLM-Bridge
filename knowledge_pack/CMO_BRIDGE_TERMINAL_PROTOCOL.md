# CMO Bridge Terminal Protocol

## Purpose
A local-first workflow for operating the CMO Lua terminal without trial-and-error API guessing.

## Required knowledge files
- `cmo_bridge_master_reference_v4.md`
- `cmo_known_api_index.json`
- `cmo_lookup_library_platforms.lua`
- `cmo_lookup_library_all.lua`
- DBID/loadout lookup modules generated from the installed CMO SQLite DB when available

## Bridge cycle
1. Inspect
2. Resolve GUIDs / DBIDs / loadout IDs
3. Validate API symbols and fields
4. Execute one bounded Lua payload
5. Capture console output
6. Repair from actual errors and the local reference

## Machine-readable output
Prefer:
- `CMO_OK|`
- `CMO_INFO|`
- `CMO_SIDE|`
- `CMO_UNIT|`
- `CMO_MISSION|`
- `CMO_ERROR|`

## Side enumeration
`VP_GetSides()` returns Side wrappers. Use `sideObj.name` and `sideObj.guid`.

Do not treat the returned entries as strings.

## Unit enumeration
Use Side wrapper collections where documented. Do not invent `ScenEdit_GetUnits()`.

```lua
local sides = VP_GetSides() or {}
for _, sideObj in ipairs(sides) do
    local sideName = sideObj.name or sideObj.guid or "Unknown Side"
    local units = sideObj.units or {}
    for _, u in ipairs(units) do
        if u then
            print(
                "CMO_UNIT|SIDE=" .. tostring(sideName) ..
                "|NAME=" .. tostring(u.name) ..
                "|GUID=" .. tostring(u.guid) ..
                "|TYPE=" .. tostring(u.type) ..
                "|DBID=" .. tostring(u.dbid) ..
                "|LAT=" .. tostring(u.latitude or u.lat) ..
                "|LON=" .. tostring(u.longitude or u.lon)
            )
        end
    end
end
```

## Mission enumeration
Prefer the Side wrapper's `missions` collection when available.

```lua
local sides = VP_GetSides() or {}
for _, sideObj in ipairs(sides) do
    local sideName = sideObj.name or sideObj.guid or "Unknown Side"
    local missions = sideObj.missions or {}
    for _, m in ipairs(missions) do
        if m then
            print(
                "CMO_MISSION|SIDE=" .. tostring(sideName) ..
                "|NAME=" .. tostring(m.name) ..
                "|GUID=" .. tostring(m.guid) ..
                "|TYPE=" .. tostring(m.typeS or m.type)
            )
        end
    end
end
```

## Error capture helper
```lua
local function cmo_error(tag)
    print(
        "CMO_ERROR|TAG=" .. tostring(tag) ..
        "|FUNCTION=" .. tostring(_errfnc_) ..
        "|NUMBER=" .. tostring(_errnum_) ..
        "|MESSAGE=" .. tostring(_errmsg_)
    )
end
```

## DBID rule
Never reuse or invent a DBID because an earlier script happened to contain it. Resolve the exact class from an authoritative SQLite-derived lookup first.

## Console export
Because some CMO Lua environments expose `io=nil`, print machine-readable rows and let the bridge host save them to CSV/TXT.

## Preflight checklist
- [ ] Every CMO API symbol exists locally
- [ ] Selector/table field names checked
- [ ] Wrapper properties checked
- [ ] Enum values checked
- [ ] DBIDs/loadout IDs verified
- [ ] Side wrappers treated as objects
- [ ] GUIDs used after discovery
- [ ] Failure output includes CMO error globals
- [ ] Script is bounded and self-contained
