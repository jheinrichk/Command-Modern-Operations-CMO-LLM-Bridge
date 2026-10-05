Tool_EmulateNoConsole(true)

local function sval(v)
    if v == nil then return "" end
    return tostring(v)
end

local function cmo_error(tag)
    print(
        "CMO_ERROR|TAG=" .. sval(tag) ..
        "|FUNCTION=" .. sval(_errfnc_) ..
        "|NUMBER=" .. sval(_errnum_) ..
        "|MESSAGE=" .. sval(_errmsg_)
    )
end

local sides = VP_GetSides()
if type(sides) ~= "table" then
    cmo_error("VP_GetSides")
    Tool_EmulateNoConsole(false)
    return
end

print("CMO_DUMP_BEGIN|SIDES=" .. tostring(#sides))

local unitCount = 0
local missionCount = 0

for _, sideObj in ipairs(sides) do
    local sideName = sideObj.name or sideObj.guid or "Unknown Side"
    local units = sideObj.units or {}
    local missions = sideObj.missions or {}

    print(
        "CMO_SIDE|NAME=" .. sval(sideName) ..
        "|GUID=" .. sval(sideObj.guid) ..
        "|UNITS=" .. tostring(#units) ..
        "|MISSIONS=" .. tostring(#missions)
    )

    for _, u in ipairs(units) do
        if u then
            unitCount = unitCount + 1
            print(
                "CMO_UNIT|SIDE=" .. sval(sideName) ..
                "|NAME=" .. sval(u.name) ..
                "|GUID=" .. sval(u.guid) ..
                "|TYPE=" .. sval(u.type) ..
                "|CLASS=" .. sval(u.classname or u.class) ..
                "|DBID=" .. sval(u.dbid) ..
                "|LAT=" .. sval(u.latitude or u.lat) ..
                "|LON=" .. sval(u.longitude or u.lon) ..
                "|ALT=" .. sval(u.altitude or u.alt)
            )
        end
    end

    for _, m in ipairs(missions) do
        if m then
            missionCount = missionCount + 1
            local assignedCount = 0
            if type(m.unitlist) == "table" then
                assignedCount = #m.unitlist
            end

            print(
                "CMO_MISSION|SIDE=" .. sval(sideName) ..
                "|NAME=" .. sval(m.name) ..
                "|GUID=" .. sval(m.guid) ..
                "|TYPE=" .. sval(m.typeS or m.type) ..
                "|ACTIVE=" .. sval(m.isactive) ..
                "|ASSIGNED=" .. tostring(assignedCount)
            )
        end
    end
end

print("CMO_DUMP_END|UNITS=" .. tostring(unitCount) .. "|MISSIONS=" .. tostring(missionCount))
Tool_EmulateNoConsole(false)
