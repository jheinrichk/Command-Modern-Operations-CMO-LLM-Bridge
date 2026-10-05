-- CMO CommandLua recipes: topic 'units'

-- --- 12.1 `ScenEdit_AddSide({name=...})` ---
ScenEdit_AddSide({name='OPFOR'})

-- --- 12.5 `ScenEdit_GetContact(table)` and `ScenEdit_GetContacts(side)` ---
local con = ScenEdit_GetContacts('south korea')

-- --- 12.5 `ScenEdit_GetContact(table)` and `ScenEdit_GetContacts(side)` ---
local contacts = ScenEdit_GetContacts('BLUE')
if contacts then
    for i, con in pairs(contacts) do
        print(i, con.name, con.guid, con.type)
    end
end

-- --- 12.10 `ScenEdit_AddMission(side, missionName, missionType, missionOptions)` ---
local patrol = ScenEdit_AddMission('BLUE', 'Barrier CAP', 'Patrol', {
    type = 'AAW',
    zone = {'CAP-1', 'CAP-2', 'CAP-3', 'CAP-4'}
})

if patrol == nil then
    print('AddMission failed: ' .. tostring(_errmsg_))
end

-- --- 12.10 `ScenEdit_AddMission(side, missionName, missionType, missionOptions)` ---
local strike = ScenEdit_AddMission('BLUE', 'Strike East', 'Strike', {
    type = 'land'
})

-- --- 12.11 `ScenEdit_SetMission(side, missionNameOrID, missionOptions)` ---
local mission = ScenEdit_SetMission('BLUE', 'Barrier CAP', {
    isactive = true,
    oneThirdRule = false,
    flightSize = 2
})

-- --- 12.16 `ScenEdit_AddZone(sideName, zoneType, table)` ---
ScenEdit_AddZone('BLUE', 'Exclusion', {
    description = 'No Entry Box',
    area = {'CAP-1','CAP-2','CAP-3','CAP-4'},
    hidden = 1
})

-- --- 12.17 `ScenEdit_SetZone(sideName, zoneType, table)` ---
ScenEdit_SetZone('BLUE', 'Exclusion', {
    description = 'No Entry Box',
    isactive = true
})

-- --- 12.34 `ScenEdit_SetSidePosture()` ---
ScenEdit_SetSidePosture('BLUE', 'RED', 'H')

-- --- 12.35 `ScenEdit_GetSideOptions()` and `ScenEdit_SetSideOptions()` ---
ScenEdit_SetSideOptions({
    side = 'BLUE',
    awareness = 'Normal',
    proficiency = 'Veteran'
})

-- --- 13.2 Add side ---
ScenEdit_AddSide({name='OPFOR'})

-- --- 13.16 Side wrapper area query ---
local u = side:unitsInArea({
    Area = {'RP-3137', 'RP-3139', 'RP-3136', 'RP-3138'},
    TargetFilter = {TargetType = 'Ship'}
})

-- --- 13.17 Side wrapper filtering ---
local u = side:unitsBy('Ship') -- all ships
u = side:unitsBy('Ship', 2002, 3003) -- ships filtered for subtype and class

-- --- 14.2 Recipe: create sides and posture ---
ScenEdit_AddSide({name='BLUE'})
ScenEdit_AddSide({name='RED'})

ScenEdit_SetSidePosture('BLUE', 'RED', 'H')
ScenEdit_SetSidePosture('RED', 'BLUE', 'H')

ScenEdit_SetSideOptions({
    side = 'BLUE',
    awareness = 'Normal',
    proficiency = 'Veteran'
})

ScenEdit_SetSideOptions({
    side = 'RED',
    awareness = 'Normal',
    proficiency = 'Regular'
})

-- --- 5.1 Add an aircraft at a location ---
local u = ScenEdit_AddUnit({
    type = 'Aircraft',
    unitname = 'F 15C Eagle #1',
    side = 'NATO',
    dbid = 3500,
    loadoutid = 16934,
    heading = 0,
    lat = 'N46.00.00',
    lon = 'E25.00.00',
    altitude = '5000 ft',
    autodetectable = 'false',
    holdfire = 'true',
    proficiency = 4
})

print(u.name)

-- --- 5.2 Add an aircraft with numeric lat lon shorthand ---
local u = ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'F 15C Eagle #2',
    side = 'NATO',
    dbid = 3500,
    loadoutid = 16934,
    lat = 5.123,
    lon = -12.51,
    alt = 5000
})

-- --- 5.3 Add a ship ---
local ship = ScenEdit_AddUnit({
    type = 'Ship',
    unitname = 'USS Example',
    side = 'Blue',
    dbid = 52,
    lat = 'N24.45.00',
    lon = 'E054.22.00',
    heading = 90,
    proficiency = 'Regular'
})

-- --- 5.4 Add a submarine ---
local sub = ScenEdit_AddUnit({
    type = 'Submarine',
    unitname = 'SSN Sample',
    side = 'Blue',
    dbid = 2215,
    lat = 'N24.10.00',
    lon = 'E054.00.00',
    depth = 'Periscope',
    heading = 45,
    proficiency = 'Veteran'
})

-- --- 5.5 Rename a unit ---
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    newname = 'USS Barack Obama'
})

-- --- 5.6 Change position only ---
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    lat = 5
})

-- --- 5.7 Change position with latitude and longitude ---
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    lat = 5,
    lon = 'N50.20.10'
})

-- --- 5.8 Change heading and tactical flags ---
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    heading = 0,
    HoldPosition = 1,
    HoldFire = 1,
    Proficiency = 'Ace',
    Autodetectable = 'yes'
})

-- --- 5.9 Move a unit to another side ---
ScenEdit_SetUnitSide({
    side = 'Old Side',
    name = 'Eagle #1',
    newside = 'New Side'
})

-- --- 5.10 Get a unit wrapper safely ---
local unit = Tool_EmulateNoConsole(true)
unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
Tool_EmulateNoConsole(false)

if unit then
    print(unit.name)
    print(unit.guid)
    print(unit.latitude)
    print(unit.longitude)
end

-- --- 5.11 Update from wrapper values and then commit with setter ---
local unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
if unit then
    ScenEdit_SetUnit({
        guid = unit.guid,
        heading = 120,
        desiredSpeed = 18
    })
end

-- --- 8.1 Set side level doctrine ---
ScenEdit_SetDoctrine({
    side = 'Soviet Union'
}, {
    kinematic_range_for_torpedoes = 'AutomaticAndManualFire',
    use_nuclear_weapons = 'yes'
})

-- --- 10.2 Get all contacts for a side ---
local contacts = ScenEdit_GetContacts('Blue')
for i, c in ipairs(contacts) do
    print(i, c.name, c.guid)
end

-- --- 13.1 Add a side ---
ScenEdit_AddSide({
    side = 'Neutral Shipping'
})

-- --- 13.2 Remove a side ---
ScenEdit_RemoveSide('Neutral Shipping')

-- --- 13.3 Set side posture ---
ScenEdit_SetSidePosture('Blue', 'Red', 'H')
ScenEdit_SetSidePosture('Red', 'Blue', 'H')

-- --- 13.4 Get side posture ---
local p = ScenEdit_GetSidePosture('Blue', 'Red')
print(p)

-- --- 13.5 Set side options ---
ScenEdit_SetSideOptions({
    side = 'Blue',
    awareness = 1,
    proficiency = 3
})

-- --- 16.3 Special message to a side ---
ScenEdit_SpecialMessage('Blue', 'Enemy raid detected from the north east')

