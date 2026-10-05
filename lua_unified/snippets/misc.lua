-- CMO CommandLua recipes: topic 'misc'

-- --- Platform focused lookup ---
local db = dofile("cmo_lookup_library_platforms_v2.lua")

local rec = db.lookup_exact("Structure Naval Dock")
if rec then
    print(rec.name, rec.type, rec.cost, rec.key)
end

local ships = db.get_type("Ship")
print(#ships)

-- --- All record lookup ---
local db = dofile("cmo_lookup_library_all_v2.lua")

local rec = db.lookup("single unit port")
if rec then
    print(rec.name, rec.type, rec.key)
end

local facilities = db.get_type("Facility")
print(#facilities)

-- --- 7.1 Altitude ---
{altitude = '100 FT'}
--or
{altitude = '100 M'}
--or
{altitude = '100'} -- same as 100 M

-- --- 12.2 `ScenEdit_AddUnit(table)` ---
ScenEdit_AddUnit({type ='Air', unitname ='F-15C Eagle', loadoutid =16934, dbid =3500, side ='NATO', Lat="5.123",Lon="-12.51",alt=5000})
ScenEdit_AddUnit({type ='Ship', unitname ='GOE II Det C', dbid =3127, side ='USN', latitude="5.123",longitude="-12.51",proficiency='Veteran'})

-- --- 12.2 `ScenEdit_AddUnit(table)` ---
ScenEdit_AddUnit({type ='Aircraft', name ='F-15C Eagle', loadoutid =16934, heading =0, dbid =3500, side ='NATO', Latitude="N46.00.00",Longitude="E25.00.00", altitude="5000 ft",autodetectable="false",holdfire="true",proficiency=4})

-- --- 12.2 `ScenEdit_AddUnit(table)` ---
local red_sub = ScenEdit_AddUnit({
    type = 'Submarine',
    unitname = 'Kilo 01',
    side = 'RED',
    dbid = 402,
    latitude = '25.0000',
    longitude = '122.0000',
    depth = 40,
    proficiency = 'Veteran',
    autodetectable = false
})

if red_sub == nil then
    print('AddUnit failed: ' .. tostring(_errmsg_))
else
    print('Created unit: ' .. red_sub.name .. ' / ' .. red_sub.guid)
end

-- --- 12.3 `ScenEdit_SetUnit(table)` ---
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5})
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5, lon ="N50.20.10"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", newname="USS Barack Obama"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", heading=0, HoldPosition=1, HoldFire=1,Proficiency="Ace", Autodetectable="yes"})

-- --- 12.3 `ScenEdit_SetUnit(table)` ---
local updated = ScenEdit_SetUnit({
    side = 'BLUE',
    unitname = 'USS Test',
    desiredHeading = 270,
    holdPosition = false,
    holdFire = false,
    proficiency = 'Veteran',
    sprintDrift = true
})

if updated == nil then
    print('SetUnit failed: ' .. tostring(_errmsg_))
end

-- --- 12.4 `ScenEdit_GetUnit(table)` ---
local u = ScenEdit_GetUnit({side='BLUE', unitname='USS Test'})
if u then
    print(u.name)
    print(u.guid)
    print(u.speed)
    print(u.heading)
end

-- --- 12.6 `ScenEdit_SelectedUnits()` ---
local selected = ScenEdit_SelectedUnits()
print(selected.units) -- list of selected units

-- --- 12.6 `ScenEdit_SelectedUnits()` ---
local selected = ScenEdit_SelectedUnits()

if selected.units then
    for i, u in pairs(selected.units) do
        print('UNIT', i, u.name, u.guid)
    end
end

if selected.contacts then
    for i, c in pairs(selected.contacts) do
        print('CONTACT', i, c.name, c.guid)
    end
end

-- --- 12.7 `ScenEdit_QueryDB(objectType, DBID)` ---
local w = ScenEdit_QueryDB('weapon', 51)
if w then
    print(w.name)
    print(w.dbid)
end

-- --- 12.13 `ScenEdit_AssignUnitAsTarget()` and `ScenEdit_RemoveUnitAsTarget()` ---
ScenEdit_AssignUnitAsTarget('Strike East', 'Enemy Radar Site')
-- later
ScenEdit_RemoveUnitAsTarget('Strike East', 'Enemy Radar Site')

-- --- 12.14 `ScenEdit_AddReferencePoint(table)` ---
local rp = ScenEdit_AddReferencePoint({
    side = 'BLUE',
    name = 'CAP-1',
    latitude = '24.9500',
    longitude = '121.9000'
})

-- --- 12.14 `ScenEdit_AddReferencePoint(table)` ---
ScenEdit_AddReferencePoint({
    side = 'BLUE',
    area = {
        {name='CAP-1', latitude='24.95', longitude='121.90'},
        {name='CAP-2', latitude='25.05', longitude='121.90'},
        {name='CAP-3', latitude='25.05', longitude='122.05'},
        {name='CAP-4', latitude='24.95', longitude='122.05'}
    }
})

-- --- 12.15 `ScenEdit_SetReferencePoint(table)` ---
ScenEdit_SetReferencePoint({
    side = 'BLUE',
    name = 'CAP-1',
    highlighted = true,
    locked = false
})

-- --- 12.15 `ScenEdit_SetReferencePoint(table)` ---
ScenEdit_SetReferencePoint({
    side = 'BLUE',
    area = {'CAP-1','CAP-2','CAP-3','CAP-4'},
    highlighted = true
})

-- --- 12.25 `ScenEdit_SetKeyValue()`, `ScenEdit_GetKeyValue()`, `ScenEdit_ClearKeyValue()` ---
ScenEdit_SetKeyValue('BLUE_CAP_STATE', 'launched')

local v = ScenEdit_GetKeyValue('BLUE_CAP_STATE')
print(v)

ScenEdit_ClearKeyValue('BLUE_CAP_STATE')

-- --- 12.29 `ScenEdit_QueryDB()` ---
local sensor = ScenEdit_QueryDB('sensor', 1234)
if sensor then
    print(sensor.name)
end

-- --- 12.32 `ScenEdit_SetEMCON()` ---
ScenEdit_SetEMCON('Unit', 'BLUE', 'E-2D #1', 'Radar=Active')
ScenEdit_SetEMCON('Unit', 'BLUE', 'E-2D #1', 'OECM=Passive')

-- --- 13.1 Altitude examples ---
{altitude = '100 FT'}
{altitude = '100 M'}
{altitude = '100'}

-- --- 13.3 Add unit ---
ScenEdit_AddUnit({type ='Aircraft', name ='F-15C Eagle', loadoutid =16934, heading =0, dbid =3500, side ='NATO', Latitude="N46.00.00",Longitude="E25.00.00", altitude="5000 ft",autodetectable="false",holdfire="true",proficiency=4})
ScenEdit_AddUnit({type ='Air', unitname ='F-15C Eagle', loadoutid =16934, dbid =3500, side ='NATO', Lat="5.123",Lon="-12.51",alt=5000})
ScenEdit_AddUnit({type ='Ship', unitname ='GOE II Det C', dbid =3127, side ='USN', latitude="5.123",longitude="-12.51",proficiency='Veteran'})

-- --- 13.4 Set unit ---
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5})
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5, lon ="N50.20.10"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", newname="USS Barack Obama"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", heading=0, HoldPosition=1, HoldFire=1,Proficiency="Ace", Autodetectable="yes"})

-- --- 13.14 Selected units ---
local selected = ScenEdit_SelectedUnits()
print(selected.units)

-- --- 13.18 Satellite orbit update ---
theSat = ScenEdit_GetUnit({guid='56f830c1-d0e2-430a-985e-0e301cc01eff'})
theTLE = 'Resurs P1\n1 39186U 13030A 17013.12537468 .00000446 00000-0 16942-4 0 9992\n2 39186 97.3847 79.3911 0015157 247.7411 195.8488 15.31966970198820'
theSat:updateorbit({TLE=theTLE})

-- --- 3. Error handling pattern ---
local mission = ScenEdit_AddMission('USA', 'Marker strike', 'strike', { type = 'land' })

if mission == nil then
    if _errnum_ ~= 0 then
        print('Failed to add mission: ' .. tostring(_errmsg_))
        print('Function: ' .. tostring(_errfnc_))
        print('Error number: ' .. tostring(_errnum_))
    else
        print('Mission creation returned nil without a documented CommandLua error.')
    end
else
    print('Created mission: ' .. mission.name)
end

-- --- 4.1 Unit selector ---
local selector_by_name = {
    side = 'Blue',
    unitname = 'USS Test'
}

local selector_by_guid = {
    guid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
}

-- --- 4.5 New unit selector ---
local new_aircraft = {
    type = 'Aircraft',
    unitname = 'Eagle #1',
    side = 'Blue',
    dbid = 3500,
    loadoutid = 16934,
    lat = 'N46.00.00',
    lon = 'E25.00.00',
    altitude = '5000 ft',
    heading = 0,
    proficiency = 4
}

