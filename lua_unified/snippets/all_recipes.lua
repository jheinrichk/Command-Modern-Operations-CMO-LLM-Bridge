-- CMO CommandLua recipe corpus (auto-extracted from master library v3)
-- 194 blocks

-- === [misc] Platform focused lookup ===
local db = dofile("cmo_lookup_library_platforms_v2.lua")

local rec = db.lookup_exact("Structure Naval Dock")
if rec then
    print(rec.name, rec.type, rec.cost, rec.key)
end

local ships = db.get_type("Ship")
print(#ships)

-- === [misc] All record lookup ===
local db = dofile("cmo_lookup_library_all_v2.lua")

local rec = db.lookup("single unit port")
if rec then
    print(rec.name, rec.type, rec.key)
end

local facilities = db.get_type("Facility")
print(#facilities)

-- === [misc] 7.1 Altitude ===
{altitude = '100 FT'}
--or
{altitude = '100 M'}
--or
{altitude = '100'} -- same as 100 M

-- === [units] 12.1 `ScenEdit_AddSide({name=...})` ===
ScenEdit_AddSide({name='OPFOR'})

-- === [misc] 12.2 `ScenEdit_AddUnit(table)` ===
ScenEdit_AddUnit({type ='Air', unitname ='F-15C Eagle', loadoutid =16934, dbid =3500, side ='NATO', Lat="5.123",Lon="-12.51",alt=5000})
ScenEdit_AddUnit({type ='Ship', unitname ='GOE II Det C', dbid =3127, side ='USN', latitude="5.123",longitude="-12.51",proficiency='Veteran'})

-- === [misc] 12.2 `ScenEdit_AddUnit(table)` ===
ScenEdit_AddUnit({type ='Aircraft', name ='F-15C Eagle', loadoutid =16934, heading =0, dbid =3500, side ='NATO', Latitude="N46.00.00",Longitude="E25.00.00", altitude="5000 ft",autodetectable="false",holdfire="true",proficiency=4})

-- === [misc] 12.2 `ScenEdit_AddUnit(table)` ===
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

-- === [misc] 12.3 `ScenEdit_SetUnit(table)` ===
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5})
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5, lon ="N50.20.10"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", newname="USS Barack Obama"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", heading=0, HoldPosition=1, HoldFire=1,Proficiency="Ace", Autodetectable="yes"})

-- === [misc] 12.3 `ScenEdit_SetUnit(table)` ===
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

-- === [misc] 12.4 `ScenEdit_GetUnit(table)` ===
local u = ScenEdit_GetUnit({side='BLUE', unitname='USS Test'})
if u then
    print(u.name)
    print(u.guid)
    print(u.speed)
    print(u.heading)
end

-- === [units] 12.5 `ScenEdit_GetContact(table)` and `ScenEdit_GetContacts(side)` ===
local con = ScenEdit_GetContacts('south korea')

-- === [units] 12.5 `ScenEdit_GetContact(table)` and `ScenEdit_GetContacts(side)` ===
local contacts = ScenEdit_GetContacts('BLUE')
if contacts then
    for i, con in pairs(contacts) do
        print(i, con.name, con.guid, con.type)
    end
end

-- === [misc] 12.6 `ScenEdit_SelectedUnits()` ===
local selected = ScenEdit_SelectedUnits()
print(selected.units) -- list of selected units

-- === [misc] 12.6 `ScenEdit_SelectedUnits()` ===
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

-- === [misc] 12.7 `ScenEdit_QueryDB(objectType, DBID)` ===
local w = ScenEdit_QueryDB('weapon', 51)
if w then
    print(w.name)
    print(w.dbid)
end

-- === [loadout_cargo] 12.8 `ScenEdit_AddReloadsToUnit()` ===
ScenEdit_AddReloadsToUnit({unitname='Mech Inf #1', wpn_dbid=773, number=1, w_max=10})

-- === [loadout_cargo] 12.9 `ScenEdit_AddWeaponToUnitMagazine()` ===
ScenEdit_AddWeaponToUnitMagazine({unitname='Ammo', wpn_dbid=773, number=1, w_max=10})

-- === [units] 12.10 `ScenEdit_AddMission(side, missionName, missionType, missionOptions)` ===
local patrol = ScenEdit_AddMission('BLUE', 'Barrier CAP', 'Patrol', {
    type = 'AAW',
    zone = {'CAP-1', 'CAP-2', 'CAP-3', 'CAP-4'}
})

if patrol == nil then
    print('AddMission failed: ' .. tostring(_errmsg_))
end

-- === [units] 12.10 `ScenEdit_AddMission(side, missionName, missionType, missionOptions)` ===
local strike = ScenEdit_AddMission('BLUE', 'Strike East', 'Strike', {
    type = 'land'
})

-- === [units] 12.11 `ScenEdit_SetMission(side, missionNameOrID, missionOptions)` ===
local mission = ScenEdit_SetMission('BLUE', 'Barrier CAP', {
    isactive = true,
    oneThirdRule = false,
    flightSize = 2
})

-- === [missions] 12.12 `ScenEdit_AssignUnitToMission()` ===
ScenEdit_AssignUnitToMission('F-16 #1', 'Barrier CAP')
ScenEdit_AssignUnitToMission('F-16 #2', 'Barrier CAP')

-- === [misc] 12.13 `ScenEdit_AssignUnitAsTarget()` and `ScenEdit_RemoveUnitAsTarget()` ===
ScenEdit_AssignUnitAsTarget('Strike East', 'Enemy Radar Site')
-- later
ScenEdit_RemoveUnitAsTarget('Strike East', 'Enemy Radar Site')

-- === [misc] 12.14 `ScenEdit_AddReferencePoint(table)` ===
local rp = ScenEdit_AddReferencePoint({
    side = 'BLUE',
    name = 'CAP-1',
    latitude = '24.9500',
    longitude = '121.9000'
})

-- === [misc] 12.14 `ScenEdit_AddReferencePoint(table)` ===
ScenEdit_AddReferencePoint({
    side = 'BLUE',
    area = {
        {name='CAP-1', latitude='24.95', longitude='121.90'},
        {name='CAP-2', latitude='25.05', longitude='121.90'},
        {name='CAP-3', latitude='25.05', longitude='122.05'},
        {name='CAP-4', latitude='24.95', longitude='122.05'}
    }
})

-- === [misc] 12.15 `ScenEdit_SetReferencePoint(table)` ===
ScenEdit_SetReferencePoint({
    side = 'BLUE',
    name = 'CAP-1',
    highlighted = true,
    locked = false
})

-- === [misc] 12.15 `ScenEdit_SetReferencePoint(table)` ===
ScenEdit_SetReferencePoint({
    side = 'BLUE',
    area = {'CAP-1','CAP-2','CAP-3','CAP-4'},
    highlighted = true
})

-- === [units] 12.16 `ScenEdit_AddZone(sideName, zoneType, table)` ===
ScenEdit_AddZone('BLUE', 'Exclusion', {
    description = 'No Entry Box',
    area = {'CAP-1','CAP-2','CAP-3','CAP-4'},
    hidden = 1
})

-- === [units] 12.17 `ScenEdit_SetZone(sideName, zoneType, table)` ===
ScenEdit_SetZone('BLUE', 'Exclusion', {
    description = 'No Entry Box',
    isactive = true
})

-- === [events] 12.18 `ScenEdit_SetTrigger(table)` ===
local a = ScenEdit_SetTrigger({
    mode='add',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    targetfilter={SPECIFICUNIT='AOE 421 Sagami'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=true
})

-- === [events] 12.18 `ScenEdit_SetTrigger(table)` ===
local a = ScenEdit_SetTrigger({
    mode='update',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    rename='Any AOE entering hot zone',
    targetfilter={TargetSubType='5023', TargetType='2', TargetSide='sidea'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=false
})

-- === [events] 12.18 `ScenEdit_SetTrigger(table)` ===
local a = ScenEdit_SetTrigger({
    mode='remove',
    type='UnitEntersArea',
    name='Any AOE entering hot zone'
})

-- === [events] 12.18 `ScenEdit_SetTrigger(table)` ===
local trig = ScenEdit_SetTrigger({
    mode = 'add',
    type = 'UnitDetected',
    name = 'BLUE detects hostile ship',
    DetectorSideID = 'BLUE',
    MCL = 2,
    TargetFilter = {
        TargetSide = 'RED',
        TargetType = 'Ship'
    }
})

if trig == nil then
    print('SetTrigger failed: ' .. tostring(_errmsg_))
end

-- === [events] 12.19 `ScenEdit_SetCondition(table)` ===
ScriptTest='--comment\r\nif unit ~= nil then\r\n return true\r\n else\r\n return false\r\n end'

-- === [events] 12.19 `ScenEdit_SetCondition(table)` ===
local a = ScenEdit_SetCondition({
    mode='add',
    type='SidePosture',
    name='sideA hostile to sideB',
    ObserverSideId='sidea',
    TargetSideId='sideb',
    targetposture='hostile'
})

-- === [events] 12.19 `ScenEdit_SetCondition(table)` ===
local cond = ScenEdit_SetCondition({
    mode = 'add',
    type = 'LuaScript',
    name = 'at least one hostile contact exists',
    ScriptText = "local cons = ScenEdit_GetContacts('BLUE')\r\nreturn cons ~= nil and next(cons) ~= nil"
})

-- === [events] 12.20 `ScenEdit_SetAction(table)` ===
local a = ScenEdit_SetAction({
    mode='add',
    type='Points',
    name='sideA loses some ..',
    SideId='sidea',
    PointChange=-10
})

-- === [events] 12.20 `ScenEdit_SetAction(table)` ===
local act = ScenEdit_SetAction({
    mode = 'add',
    type = 'Message',
    name = 'notify blue player',
    SideID = 'BLUE',
    Text = 'Hostile task group detected to the east.'
})

-- === [events] 12.20 `ScenEdit_SetAction(table)` ===
local act2 = ScenEdit_SetAction({
    mode = 'add',
    type = 'LuaScript',
    name = 'spawn reinforcements',
    ScriptText = "ScenEdit_AddUnit({type='Air', unitname='Reinforcement 1', side='BLUE', dbid=3500, loadoutid=16934, latitude='25.0', longitude='121.8', altitude='5000 ft'})"
})

-- === [events] 12.21 `ScenEdit_SetEvent(eventName, options)` ===
local a = ScenEdit_SetEvent('my new event', {mode='add'})

-- === [events] 12.21 `ScenEdit_SetEvent(eventName, options)` ===
local ev = ScenEdit_SetEvent('Blue detection event', {
    mode = 'add',
    isactive = true,
    isrepeatable = true,
    probability = 100
})

-- === [events] 12.22 `ScenEdit_SetEventTrigger`, `ScenEdit_SetEventCondition`, `ScenEdit_SetEventAction` ===
local a = ScenEdit_SetEventAction('test event', {mode='add', name='test action points'})
local a = ScenEdit_SetEventAction('test event', {mode='replace', name='test action message', replaceby='test action points'})

-- === [events] 12.22 `ScenEdit_SetEventTrigger`, `ScenEdit_SetEventCondition`, `ScenEdit_SetEventAction` ===
ScenEdit_SetEvent('Blue detects red surface group', {mode='add'})
ScenEdit_SetEventTrigger('Blue detects red surface group', {mode='add', name='BLUE detects hostile ship'})
ScenEdit_SetEventCondition('Blue detects red surface group', {mode='add', name='sideA hostile to sideB'})
ScenEdit_SetEventAction('Blue detects red surface group', {mode='add', name='notify blue player'})

-- === [sim_control] 12.23 `ScenEdit_SetTime()` ===
ScenEdit_SetTime({Date="2.12.2007", Time="22.46.23"})

-- === [sim_control] 12.23 `ScenEdit_SetTime()` ===
local m = ScenEdit_GetMission('sidea', 'test support')
print(m)
m.starttime = "2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"
print(m.starttime)

-- === [events] 12.24 `ScenEdit_AddSpecialAction()` and `ScenEdit_SetSpecialAction()` ===
local sa = ScenEdit_AddSpecialAction({
    side = 'BLUE',
    name = 'Spawn CAP',
    description = 'Spawn an alert CAP at the player request',
    IsActive = true,
    IsRepeatable = false,
    ScriptText = "ScenEdit_AddUnit({type='Air', unitname='CAP Spawn', side='BLUE', dbid=3500, loadoutid=16934, latitude='25.05', longitude='121.95', altitude='12000 ft'})"
})

-- === [misc] 12.25 `ScenEdit_SetKeyValue()`, `ScenEdit_GetKeyValue()`, `ScenEdit_ClearKeyValue()` ===
ScenEdit_SetKeyValue('BLUE_CAP_STATE', 'launched')

local v = ScenEdit_GetKeyValue('BLUE_CAP_STATE')
print(v)

ScenEdit_ClearKeyValue('BLUE_CAP_STATE')

-- === [ui_messages] 12.26 `ScenEdit_PlaySound()`, `ScenEdit_MsgBox()`, `ScenEdit_InputBox()`, `ScenEdit_SpecialMessage()` ===
ScenEdit_MsgBox('This is a test message')

-- === [scenario_state] 12.27 `Command_SaveScen()` and `SetScenarioTitle()` ===
SetScenarioTitle('Taiwan Strait Escalation')
Command_SaveScen()

-- === [world_tools] 12.28 `Tool_Bearing()`, `Tool_Range()`, `Tool_LOS()`, `World_GetPointFromBearing()`, `World_GetElevation()` ===
local brg = Tool_Bearing({lat='25.0', lon='121.8'}, {lat='25.2', lon='122.1'})
local rng = Tool_Range({lat='25.0', lon='121.8'}, {lat='25.2', lon='122.1'})
print(brg, rng)

-- === [world_tools] 12.28 `Tool_Bearing()`, `Tool_Range()`, `Tool_LOS()`, `World_GetPointFromBearing()`, `World_GetElevation()` ===
local pt = World_GetPointFromBearing('25.0', '121.8', 90, 25)
print(pt.latitude, pt.longitude)

-- === [misc] 12.29 `ScenEdit_QueryDB()` ===
local sensor = ScenEdit_QueryDB('sensor', 1234)
if sensor then
    print(sensor.name)
end

-- === [contacts] 12.30 `ScenEdit_AttackContact()` ===
local contact = ScenEdit_GetContact({side='BLUE', guid='CONTACT-GUID-HERE'})
if contact then
    ScenEdit_AttackContact('BLUE UNIT GUID HERE', contact.guid, {
        mode = 0,
        weapon = 51,
        qty = 2
    })
end

-- === [doctrine] 12.31 `ScenEdit_SetDoctrine()` and `ScenEdit_SetDoctrineWRA()` ===
ScenEdit_SetDoctrine({side='BLUE'}, {use_nuclear_weapons='no', weapon_control_status_air='tight'})
ScenEdit_SetDoctrineWRA({side='BLUE', weapon_id=51, target_type='Aircraft'}, {qty_salvo=2})

-- === [misc] 12.32 `ScenEdit_SetEMCON()` ===
ScenEdit_SetEMCON('Unit', 'BLUE', 'E-2D #1', 'Radar=Active')
ScenEdit_SetEMCON('Unit', 'BLUE', 'E-2D #1', 'OECM=Passive')

-- === [loadout_cargo] 12.33 `ScenEdit_UpdateUnit()` and `ScenEdit_UpdateUnitCargo()` ===
ScenEdit_UpdateUnit({
    guid = 'UNIT-GUID',
    mode = 'add_sensor',
    dbid = 1234
})

-- === [units] 12.34 `ScenEdit_SetSidePosture()` ===
ScenEdit_SetSidePosture('BLUE', 'RED', 'H')

-- === [units] 12.35 `ScenEdit_GetSideOptions()` and `ScenEdit_SetSideOptions()` ===
ScenEdit_SetSideOptions({
    side = 'BLUE',
    awareness = 'Normal',
    proficiency = 'Veteran'
})

-- === [sim_control] 12.36 `Tool_BuildBlankScenario()` ===
Tool_BuildBlankScenario('Sandbox Build Test')
SetScenarioTitle('Sandbox Build Test')

-- === [misc] 13.1 Altitude examples ===
{altitude = '100 FT'}
{altitude = '100 M'}
{altitude = '100'}

-- === [units] 13.2 Add side ===
ScenEdit_AddSide({name='OPFOR'})

-- === [misc] 13.3 Add unit ===
ScenEdit_AddUnit({type ='Aircraft', name ='F-15C Eagle', loadoutid =16934, heading =0, dbid =3500, side ='NATO', Latitude="N46.00.00",Longitude="E25.00.00", altitude="5000 ft",autodetectable="false",holdfire="true",proficiency=4})
ScenEdit_AddUnit({type ='Air', unitname ='F-15C Eagle', loadoutid =16934, dbid =3500, side ='NATO', Lat="5.123",Lon="-12.51",alt=5000})
ScenEdit_AddUnit({type ='Ship', unitname ='GOE II Det C', dbid =3127, side ='USN', latitude="5.123",longitude="-12.51",proficiency='Veteran'})

-- === [misc] 13.4 Set unit ===
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5})
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5, lon ="N50.20.10"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", newname="USS Barack Obama"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", heading=0, HoldPosition=1, HoldFire=1,Proficiency="Ace", Autodetectable="yes"})

-- === [loadout_cargo] 13.5 Add reloads ===
ScenEdit_AddReloadsToUnit({unitname='Mech Inf #1', wpn_dbid=773, number=1, w_max=10})

-- === [loadout_cargo] 13.6 Add weapon to magazine ===
ScenEdit_AddWeaponToUnitMagazine({unitname='Ammo', wpn_dbid=773, number=1, w_max=10})

-- === [events] 13.7 Set trigger ===
local a = ScenEdit_SetTrigger({
    mode='add',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    targetfilter={SPECIFICUNIT='AOE 421 Sagami'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=true
})

-- === [events] 13.7 Set trigger ===
local a = ScenEdit_SetTrigger({
    mode='update',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    rename='Any AOE entering hot zone',
    targetfilter={TargetSubType = '5023',TargetType = '2',TargetSide='sidea'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=false
})

-- === [events] 13.7 Set trigger ===
local a = ScenEdit_SetTrigger({mode='remove',type='UnitEntersArea',name='Any AOE entering hot zone'})

-- === [events] 13.8 Set condition ===
local a = ScenEdit_SetCondition({
    mode='add',
    type='SidePosture',
    name='sideA hostile to sideB',
    ObserverSideId='sidea',
    TargetSideId='sideb',
    targetposture='hostile'
})

-- === [events] 13.9 Condition script text formatting ===
ScriptTest='--comment\r\nif unit ~= nil then\r\n return true\r\n else\r\n return false\r\n end'

-- === [events] 13.10 Set action ===
local a = ScenEdit_SetAction({mode='add', type='Points', name='sideA loses some ..', SideId='sidea', PointChange=-10})

-- === [events] 13.11 Event action linking ===
local a = ScenEdit_SetEventAction('test event', {mode='add', name='test action points'})
local a = ScenEdit_SetEventAction('test event', {mode='replace', name='test action message', replaceby='test action points'})

-- === [events] 13.12 Add event ===
local a = ScenEdit_SetEvent('my new event', {mode='add'})

-- === [sim_control] 13.13 Set time ===
ScenEdit_SetTime({Date="2.12.2007", Time="22.46.23"})

-- === [misc] 13.14 Selected units ===
local selected = ScenEdit_SelectedUnits()
print(selected.units)

-- === [contacts] 13.15 Get contacts ===
local con = ScenEdit_GetContacts('south korea')

-- === [units] 13.16 Side wrapper area query ===
local u = side:unitsInArea({
    Area = {'RP-3137', 'RP-3139', 'RP-3136', 'RP-3138'},
    TargetFilter = {TargetType = 'Ship'}
})

-- === [units] 13.17 Side wrapper filtering ===
local u = side:unitsBy('Ship') -- all ships
u = side:unitsBy('Ship', 2002, 3003) -- ships filtered for subtype and class

-- === [misc] 13.18 Satellite orbit update ===
theSat = ScenEdit_GetUnit({guid='56f830c1-d0e2-430a-985e-0e301cc01eff'})
theTLE = 'Resurs P1\n1 39186U 13030A 17013.12537468 .00000446 00000-0 16942-4 0 9992\n2 39186 97.3847 79.3911 0015157 247.7411 195.8488 15.31966970198820'
theSat:updateorbit({TLE=theTLE})

-- === [sim_control] 13.19 Date/time explicit format ===
local m = ScenEdit_GetMission('sidea', 'test support')
print(m)
m.starttime = "2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"
print(m.starttime)

-- === [sim_control] 14.1 Recipe: build a simple blank scenario and set title ===
Tool_BuildBlankScenario('Test Sandbox')
SetScenarioTitle('Test Sandbox')
ScenEdit_SetTime({Date='06/09/2027', Time='01:30:00'})

-- === [units] 14.2 Recipe: create sides and posture ===
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

-- === [refpoints_zones] 14.3 Recipe: create reference points and an area ===
ScenEdit_AddReferencePoint({
    side = 'BLUE',
    area = {
        {name='BOX-1', latitude='25.00', longitude='121.80'},
        {name='BOX-2', latitude='25.10', longitude='121.80'},
        {name='BOX-3', latitude='25.10', longitude='121.95'},
        {name='BOX-4', latitude='25.00', longitude='121.95'}
    }
})

-- === [missions] 14.4 Recipe: create a patrol mission and assign aircraft ===
local cap = ScenEdit_AddMission('BLUE', 'CAP NORTH', 'Patrol', {
    type = 'AAW',
    zone = {'BOX-1', 'BOX-2', 'BOX-3', 'BOX-4'}
})

ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'F-16A #1',
    side = 'BLUE',
    dbid = 3500,
    loadoutid = 16934,
    latitude = '25.02',
    longitude = '121.82',
    altitude = '12000 ft'
})

ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'F-16A #2',
    side = 'BLUE',
    dbid = 3500,
    loadoutid = 16934,
    latitude = '25.03',
    longitude = '121.83',
    altitude = '12000 ft'
})

ScenEdit_AssignUnitToMission('F-16A #1', 'CAP NORTH')
ScenEdit_AssignUnitToMission('F-16A #2', 'CAP NORTH')

ScenEdit_SetMission('BLUE', 'CAP NORTH', {
    isactive = true,
    flightSize = 2,
    oneThirdRule = false
})

-- === [missions] 14.5 Recipe: create a strike package with target mission ===
local strike = ScenEdit_AddMission('BLUE', 'STRIKE EAST', 'Strike', {
    type = 'land'
})

ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'Strike #1',
    side = 'BLUE',
    dbid = 3500,
    loadoutid = 16934,
    latitude = '24.95',
    longitude = '121.70',
    altitude = '15000 ft'
})

ScenEdit_AssignUnitToMission('Strike #1', 'STRIKE EAST')
ScenEdit_AssignUnitAsTarget('STRIKE EAST', 'Enemy Radar Site')

-- === [scenario_state] 14.6 Recipe: create a detection driven event chain ===
local trig = ScenEdit_SetTrigger({
    mode = 'add',
    type = 'UnitDetected',
    name = 'detect red ships',
    DetectorSideID = 'BLUE',
    MCL = 2,
    TargetFilter = {
        TargetSide = 'RED',
        TargetType = 'Ship'
    }
})

local cond = ScenEdit_SetCondition({
    mode = 'add',
    type = 'SidePosture',
    name = 'blue hostile to red',
    ObserverSideID = 'BLUE',
    TargetSideID = 'RED',
    TargetPosture = 'hostile'
})

local act = ScenEdit_SetAction({
    mode = 'add',
    type = 'Message',
    name = 'alert blue',
    SideID = 'BLUE',
    Text = 'Red surface units detected.'
})

ScenEdit_SetEvent('RED SHIPS DETECTED', {
    mode = 'add',
    isactive = true,
    isrepeatable = true
})

ScenEdit_SetEventTrigger('RED SHIPS DETECTED', {
    mode = 'add',
    description = 'detect red ships'
})

ScenEdit_SetEventCondition('RED SHIPS DETECTED', {
    mode = 'add',
    description = 'blue hostile to red'
})

ScenEdit_SetEventAction('RED SHIPS DETECTED', {
    mode = 'add',
    description = 'alert blue'
})

-- === [scenario_state] 14.7 Recipe: use KeyStore to avoid duplicate spawning ===
local already = ScenEdit_GetKeyValue('REINFORCEMENT_1')

if already ~= 'spawned' then
    local u = ScenEdit_AddUnit({
        type = 'Air',
        unitname = 'Reinforcement 1',
        side = 'BLUE',
        dbid = 3500,
        loadoutid = 16934,
        latitude = '25.10',
        longitude = '121.88',
        altitude = '10000 ft'
    })

    if u then
        ScenEdit_SetKeyValue('REINFORCEMENT_1', 'spawned')
    end
end

-- === [scenario_state] 14.8 Recipe: event safe error handling skeleton ===
Tool_EmulateNoConsole(true)

local mission = ScenEdit_AddMission('BLUE', 'TEST STRIKE', 'Strike', {type='land'})

if mission == nil then
    if _errnum_ ~= 0 then
        print('Failed to add mission: ' .. tostring(_errmsg_))
    else
        print('Mission add returned nil without a reported error')
    end
else
    print('Mission created: ' .. mission.name)
end

-- === [contacts] 14.9 Recipe: query current contacts and attack one ===
local cons = ScenEdit_GetContacts('BLUE')
if cons then
    for i, con in pairs(cons) do
        if con.type == 'Ship' or con.type == 2 then
            print('Attacking contact', con.name, con.guid)
            -- replace unit guid and weapon data as needed
            ScenEdit_AttackContact('ATTACKER-UNIT-GUID', con.guid, {
                mode = 0,
                weapon = 51,
                qty = 2
            })
            break
        end
    end
end

-- === [misc] 3. Error handling pattern ===
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

-- === [misc] 4.1 Unit selector ===
local selector_by_name = {
    side = 'Blue',
    unitname = 'USS Test'
}

local selector_by_guid = {
    guid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
}

-- === [doctrine] 4.2 Doctrine selector ===
local doctrine_side = { side = 'Blue' }
local doctrine_mission = { side = 'Blue', mission = 'BARCAP North' }
local doctrine_unit = { side = 'Blue', unitname = 'Eagle #1' }

-- === [contacts] 4.3 Contact selector ===
local contact_selector = {
    side = 'Blue',
    guid = 'contact-guid-here'
}

-- === [refpoints_zones] 4.4 Reference point selector ===
local rp_selector = {
    side = 'Blue',
    name = 'RP 1'
}

-- === [misc] 4.5 New unit selector ===
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

-- === [units] 5.1 Add an aircraft at a location ===
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

-- === [units] 5.2 Add an aircraft with numeric lat lon shorthand ===
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

-- === [units] 5.3 Add a ship ===
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

-- === [units] 5.4 Add a submarine ===
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

-- === [units] 5.5 Rename a unit ===
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    newname = 'USS Barack Obama'
})

-- === [units] 5.6 Change position only ===
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    lat = 5
})

-- === [units] 5.7 Change position with latitude and longitude ===
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    lat = 5,
    lon = 'N50.20.10'
})

-- === [units] 5.8 Change heading and tactical flags ===
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    heading = 0,
    HoldPosition = 1,
    HoldFire = 1,
    Proficiency = 'Ace',
    Autodetectable = 'yes'
})

-- === [units] 5.9 Move a unit to another side ===
ScenEdit_SetUnitSide({
    side = 'Old Side',
    name = 'Eagle #1',
    newside = 'New Side'
})

-- === [units] 5.10 Get a unit wrapper safely ===
local unit = Tool_EmulateNoConsole(true)
unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
Tool_EmulateNoConsole(false)

if unit then
    print(unit.name)
    print(unit.guid)
    print(unit.latitude)
    print(unit.longitude)
end

-- === [units] 5.11 Update from wrapper values and then commit with setter ===
local unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
if unit then
    ScenEdit_SetUnit({
        guid = unit.guid,
        heading = 120,
        desiredSpeed = 18
    })
end

-- === [loadout_cargo] 6.1 Add weapons to a magazine ===
local added = ScenEdit_AddWeaponToUnitMagazine({
    unitname = 'Ammo',
    wpn_dbid = 773,
    number = 1,
    w_max = 10
})

print('Added: ' .. tostring(added))

-- === [loadout_cargo] 6.2 Add reloads to a unit ===
local ok = ScenEdit_AddReloadsToUnit({
    side = 'Blue',
    unitname = 'Eagle #1'
})

print(ok)

-- === [loadout_cargo] 6.3 Set aircraft loadout ===
ScenEdit_SetLoadout({
    side = 'Blue',
    unitname = 'Eagle #1',
    loadoutid = 16934,
    time_to_ready_minutes = 15
})

-- === [loadout_cargo] 6.4 Fill magazines for a chosen loadout pattern ===
ScenEdit_FillMagsForLoadout({
    side = 'Blue',
    unitname = 'Eagle #1'
})

-- === [loadout_cargo] 6.5 Refuel a unit ===
ScenEdit_RefuelUnit({
    side = 'Blue',
    unitname = 'USS Example'
})

-- === [loadout_cargo] 6.6 Transfer cargo between units ===
ScenEdit_TransferCargo({
    side = 'Blue',
    from = 'Transport #1',
    to = 'Airbase Alpha',
    cargo_guid = 'cargo-guid-here'
})

-- === [loadout_cargo] 6.7 Unload cargo ===
ScenEdit_UnloadCargo({
    side = 'Blue',
    unitname = 'Transport #1',
    cargo_guid = 'cargo-guid-here'
})

-- === [sim_control] 7.1 Add a simple strike mission ===
local mission = ScenEdit_AddMission('USA', 'Marker strike', 'strike', {
    type = 'land'
})

if mission then
    print(mission.name)
end

-- === [missions] 7.2 Add a patrol mission ===
local mission = ScenEdit_AddMission('Blue', 'BARCAP North', 'Patrol', {
    type = 'AAW',
    Zone = { 'RP CAP 1', 'RP CAP 2', 'RP CAP 3', 'RP CAP 4' }
})

-- === [missions] 7.3 Add a support mission ===
local mission = ScenEdit_AddMission('Blue', 'Tanker Track', 'Support', {
    zone = { 'TK 1', 'TK 2', 'TK 3', 'TK 4' }
})

-- === [missions] 7.4 Add a ferry mission ===
local mission = ScenEdit_AddMission('Blue', 'Ferry to Cyprus', 'Ferry', {
    destination = 'Akrotiri'
})

-- === [missions] 7.5 Add a package or task pool category mission ===
local package = ScenEdit_AddMission('Blue', 'Package Alpha', 'Strike', {
    category = 1,
    type = 'land'
})

local taskpool = ScenEdit_AddMission('Blue', 'Task Pool Alpha', 'Strike', {
    category = 2,
    type = 'land'
})

-- === [missions] 7.6 Assign units to a mission ===
ScenEdit_AssignUnitToMission('Eagle #1', 'BARCAP North')
ScenEdit_AssignUnitToMission('Eagle #2', 'BARCAP North')

-- === [missions] 7.7 Assign a unit as a mission target ===
ScenEdit_AssignUnitAsTarget({
    side = 'Blue',
    mission = 'Marker strike',
    target = 'Enemy Radar Site'
})

-- === [missions] 7.8 Remove a unit as a mission target ===
ScenEdit_RemoveUnitAsTarget({
    side = 'Blue',
    mission = 'Marker strike',
    target = 'Enemy Radar Site'
})

-- === [missions] 7.9 Create a mission flight plan ===
ScenEdit_CreateMissionFlightPlan({
    side = 'Blue',
    mission = 'Marker strike',
    plan = 'Ingress Alpha'
})

-- === [missions] 7.10 Get a mission wrapper and modify it later ===
local mission = ScenEdit_GetMission('Blue', 'BARCAP North')
if mission then
    print(mission.name)
end

-- === [missions] 7.11 Update a mission ===
ScenEdit_SetMission('Blue', 'BARCAP North', {
    flightSize = 2,
    flightSizeCheck = false,
    oneThirdRule = false
})

-- === [missions] 7.12 Delete a mission ===
ScenEdit_DeleteMission('Blue', 'Old Mission')

-- === [units] 8.1 Set side level doctrine ===
ScenEdit_SetDoctrine({
    side = 'Soviet Union'
}, {
    kinematic_range_for_torpedoes = 'AutomaticAndManualFire',
    use_nuclear_weapons = 'yes'
})

-- === [missions] 8.2 Set mission level doctrine ===
ScenEdit_SetDoctrine({
    side = 'Soviet Union',
    mission = 'ASW PATROL'
}, {
    kinematic_range_for_torpedoes = 'AutomaticAndManualFire',
    use_nuclear_weapons = 'yes'
})

-- === [doctrine] 8.3 Set unit level doctrine ===
ScenEdit_SetDoctrine({
    side = 'Soviet Union',
    unitname = 'Bear #2'
}, {
    use_nuclear_weapons = 'yes'
})

-- === [doctrine] 8.4 Reset doctrine to inherit ===
ScenEdit_SetDoctrine({
    side = 'Blue',
    mission = 'BARCAP North'
}, {})

-- === [doctrine] 8.5 Read doctrine first, then update selectively ===
local doctrine = ScenEdit_GetDoctrine({
    side = 'Blue',
    mission = 'BARCAP North'
})

if doctrine then
    print(doctrine.weapon_control_status_air)
end

ScenEdit_SetDoctrine({
    side = 'Blue',
    mission = 'BARCAP North'
}, {
    weapon_control_status_air = 0,
    use_refuel_unrep = 1
})

-- === [doctrine] 8.6 Set WRA for a weapon and target type ===
ScenEdit_SetDoctrineWRA({
    side = 'Blue',
    mission = 'BARCAP North',
    weapon_id = 51,
    target_type = 2001
}, {
    qty_salvo = 2,
    firing_range = 'max'
})

-- === [refpoints_zones] 9.1 Add a single reference point ===
local rp = ScenEdit_AddReferencePoint({
    side = 'Blue',
    name = 'RP 1',
    lat = 'N25.00.00',
    lon = 'E055.00.00'
})

-- === [refpoints_zones] 9.2 Add four reference points for a patrol box ===
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 1', lat = 'N25.10.00', lon = 'E055.00.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 2', lat = 'N25.10.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 3', lat = 'N24.50.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 4', lat = 'N24.50.00', lon = 'E055.00.00' })

-- === [refpoints_zones] 9.3 Add a no nav zone ===
local zone = ScenEdit_AddZone('Blue', 'NoNav', {
    description = 'Civilian Exclusion',
    area = { 'RP CAP 1', 'RP CAP 2', 'RP CAP 3', 'RP CAP 4' },
    hidden = 1
})

-- === [refpoints_zones] 9.4 Set zone attributes ===
ScenEdit_SetZone({
    side = 'Blue',
    description = 'Civilian Exclusion',
    isactive = true
})

-- === [refpoints_zones] 9.5 Transform a zone ===
ScenEdit_TransformZone({
    side = 'Blue',
    description = 'Civilian Exclusion',
    scale = 1.2
})

-- === [refpoints_zones] 9.6 Update a reference point ===
ScenEdit_SetReferencePoint({
    side = 'Blue',
    name = 'RP 1',
    lat = 'N25.05.00',
    lon = 'E055.05.00'
})

-- === [contacts] 10.1 Get a known contact ===
local contact = ScenEdit_GetContact({
    side = 'Blue',
    guid = 'contact-guid-here'
})

if contact then
    print(contact.name)
    print(contact.posture)
end

-- === [units] 10.2 Get all contacts for a side ===
local contacts = ScenEdit_GetContacts('Blue')
for i, c in ipairs(contacts) do
    print(i, c.name, c.guid)
end

-- === [contacts] 10.3 Attack a contact ===
ScenEdit_AttackContact('Blue', 'Eagle #1', {
    mode = 0,
    contactguid = 'contact-guid-here'
})

-- === [contacts] 10.4 Attack with explicit mount and weapon choice ===
ScenEdit_AttackContact('Blue', 'Eagle #1', {
    mode = 1,
    contactguid = 'contact-guid-here',
    mount = 12345,
    weapon = 678,
    qty = 2
})

-- === [sim_control] 11.1 Set weather with random values ===
ScenEdit_SetWeather(
    math.random(0, 25),
    math.random(0, 50),
    math.random(0, 10) / 10.0,
    math.random(0, 9)
)

-- === [sim_control] 11.2 Get current weather ===
local wx = ScenEdit_GetWeather()
print(wx.temperature)
print(wx.rainfall)
print(wx.undercloud)
print(wx.seastate)

-- === [sim_control] 11.3 Set scenario time using date and time table ===
ScenEdit_SetTime({
    Date = '2.12.2007',
    Time = '22.46.23'
})

-- === [sim_control] 11.4 Set scenario title ===
SetScenarioTitle('Operation Sample Dawn')

-- === [sim_control] 11.5 Read current title ===
print(GetScenarioTitle())

-- === [sim_control] 11.6 Set score for a side ===
ScenEdit_SetScore('Blue', 250, 'Awarded for successful convoy protection')

-- === [sim_control] 11.7 End the scenario ===
ScenEdit_EndScenario()

-- === [events] 12.1 Add an event ===
ScenEdit_SetEvent('Spawn Enemy Raid', {
    IsActive = true,
    IsShown = true,
    IsRepeatable = false
})

-- === [events] 12.2 Add a trigger to an event ===
ScenEdit_SetEventTrigger('MyEvent', {
    mode = 'add',
    description = 'MyNewTrigger'
})

-- === [events] 12.3 Replace a condition on an event ===
ScenEdit_SetEventCondition('MyEvent', {
    mode = 'replace',
    description = 'MyCondition'
})

-- === [events] 12.4 Add an action to an event ===
ScenEdit_SetEventAction('MyEvent', {
    mode = 'add',
    description = 'SpawnRaidAction'
})

-- === [events] 12.5 Execute an event action manually ===
ScenEdit_ExecuteEventAction('Spawn Enemy Raid', 'SpawnRaidAction')

-- === [events] 12.6 Full event scaffold with trigger, condition, and action placeholders ===
ScenEdit_SetEvent('Spawn Enemy Raid', {
    IsActive = true,
    IsShown = true,
    IsRepeatable = false
})

ScenEdit_SetEventTrigger('Spawn Enemy Raid', {
    mode = 'add',
    description = 'Blue unit enters box'
})

ScenEdit_SetEventCondition('Spawn Enemy Raid', {
    mode = 'add',
    description = 'Scenario has started'
})

ScenEdit_SetEventAction('Spawn Enemy Raid', {
    mode = 'add',
    description = 'SpawnRaidAction'
})

-- === [events] 12.7 Add a special action ===
ScenEdit_AddSpecialAction({
    side = 'Blue',
    name = 'Request Reinforcements',
    description = 'Spawns a reserve CAP pair',
    isactive = true,
    isrepeatable = false,
    scripttext = [[
        ScenEdit_AddUnit({
            type = 'Aircraft',
            unitname = 'Reserve #1',
            side = 'Blue',
            dbid = 3500,
            loadoutid = 16934,
            lat = 'N25.00.00',
            lon = 'E055.00.00',
            altitude = '5000 ft'
        })
    ]]
})

-- === [events] 12.8 Execute a special action ===
ScenEdit_ExecuteSpecialAction('Blue', 'Request Reinforcements')

-- === [units] 13.1 Add a side ===
ScenEdit_AddSide({
    side = 'Neutral Shipping'
})

-- === [units] 13.2 Remove a side ===
ScenEdit_RemoveSide('Neutral Shipping')

-- === [units] 13.3 Set side posture ===
ScenEdit_SetSidePosture('Blue', 'Red', 'H')
ScenEdit_SetSidePosture('Red', 'Blue', 'H')

-- === [units] 13.4 Get side posture ===
local p = ScenEdit_GetSidePosture('Blue', 'Red')
print(p)

-- === [units] 13.5 Set side options ===
ScenEdit_SetSideOptions({
    side = 'Blue',
    awareness = 1,
    proficiency = 3
})

-- === [minefield] 14.1 Add a minefield ===
local mf = ScenEdit_AddMinefield({
    side = 'Blue',
    dbid = 2345,
    number = 100,
    delay = 60000,
    area = { 'rp-1', 'rp-2', 'rp-3', 'rp-4' }
})

-- === [minefield] 14.2 Delete a minefield ===
ScenEdit_DeleteMinefield({
    side = 'Blue',
    guid = 'minefield-guid-here'
})

-- === [minefield] 14.3 Add an explosion ===
ScenEdit_AddExplosion({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    altitude = 0,
    dbid = 2100
})

-- === [keystore] 15.1 Save a persistent key value ===
ScenEdit_SetKeyValue('raid_spawned', 'true')

-- === [keystore] 15.2 Read a persistent key value ===
local value = ScenEdit_GetKeyValue('raid_spawned')
print(value)

-- === [keystore] 15.3 Clear a persistent key value ===
ScenEdit_ClearKeyValue('raid_spawned')

-- === [keystore] 15.4 Store a counter safely ===
local current = tonumber(ScenEdit_GetKeyValue('cap_cycles') or '0')
current = current + 1
ScenEdit_SetKeyValue('cap_cycles', tostring(current))

-- === [ui_messages] 16.1 Popup message box ===
ScenEdit_MsgBox('Enemy raid detected')

-- === [ui_messages] 16.2 Input box ===
local answer = ScenEdit_InputBox('Enter reinforcement callsign', 'Reserve #3')
print(answer)

-- === [units] 16.3 Special message to a side ===
ScenEdit_SpecialMessage('Blue', 'Enemy raid detected from the north east')

-- === [ui_messages] 16.4 Play a sound ===
ScenEdit_PlaySound('alarm.wav')

-- === [ui_messages] 16.5 Bark notification on a unit ===
ScenEdit_CreateBarkNotification_Unit({
    side = 'Blue',
    unitname = 'Eagle #1',
    text = 'Bandits detected'
})

-- === [scenario_state] 17.1 Import scenario from XML string ===
local ok = ScenEdit_ImportScenarioFromXML({
    XML = '<Scenario>...a big XML string...</Scenario>'
})

print(ok)

-- === [scenario_state] 17.2 Import scenario from XML file ===
local ok = ScenEdit_ImportScenarioFromXML({
    filename = 'scenario_fragment.xml'
})

print(ok)

-- === [scenario_state] 17.3 Export scenario to XML ===
local xml = ScenEdit_ExportScenarioToXML()
print(xml)

-- === [doctrine] 17.4 Export doctrine to XML ===
local doctrine_xml = ScenEdit_ExportDoctrineToXML({
    side = 'Blue'
})
print(doctrine_xml)

-- === [world_tools] 18.1 Bearing between two points ===
local brg = Tool_Bearing('N25.00.00', 'E055.00.00', 'N25.30.00', 'E055.20.00')
print(brg)

-- === [world_tools] 18.2 Range between two points ===
local rng = Tool_Range('N25.00.00', 'E055.00.00', 'N25.30.00', 'E055.20.00')
print(rng)

-- === [world_tools] 18.3 LOS between two points ===
local los = Tool_LOS_Points({
    observerlatitude = 'N25.00.00',
    observerlongitude = 'E055.00.00',
    targetlatitude = 'N25.30.00',
    targetlongitude = 'E055.20.00'
})
print(los)

-- === [world_tools] 18.4 Get point from bearing and range ===
local p = World_GetPointFromBearing({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    bearing = 45,
    distance = 50
})

print(p.latitude, p.longitude)

-- === [world_tools] 18.5 Get a circle from point ===
local circle = World_GetCircleFromPoint({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    radius = 25,
    points = 12
})

-- === [world_tools] 18.6 Get elevation ===
local elev = World_GetElevation({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00'
})
print(elev)

-- === [doctrine] 19.1 Unit wrapper inspection ===
local unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
if unit then
    print(unit.guid)
    print(unit.name)
    print(unit.side)
    print(unit.latitude)
    print(unit.longitude)
    print(unit.heading)
    print(unit.altitude)
    print(unit.proficiency)
end

-- === [doctrine] 19.2 Contact wrapper inspection ===
local contact = ScenEdit_GetContact({ side = 'Blue', guid = 'contact-guid-here' })
if contact then
    print(contact.name)
    print(contact.type)
    print(contact.posture)
    print(contact.latitude)
    print(contact.longitude)
end

-- === [missions] 19.3 Mission wrapper inspection ===
local mission = ScenEdit_GetMission('Blue', 'BARCAP North')
if mission then
    print(mission.name)
    print(mission.type)
    print(mission.category)
end

-- === [doctrine] 19.4 Scenario wrapper inspection ===
local scen = VP_GetScenario()
print(scen.Title)

-- === [scenario_state] 20.1 Recipe: spawn a raid package when an event fires ===
local function spawn_raid(side, base_lat, base_lon)
    ScenEdit_AddUnit({
        type = 'Aircraft',
        unitname = 'Raid Lead',
        side = side,
        dbid = 3500,
        loadoutid = 16934,
        lat = base_lat,
        lon = base_lon,
        altitude = '15000 ft',
        heading = 220,
        proficiency = 'Regular'
    })

    ScenEdit_AddUnit({
        type = 'Aircraft',
        unitname = 'Raid Wing',
        side = side,
        dbid = 3500,
        loadoutid = 16934,
        lat = base_lat,
        lon = base_lon,
        altitude = '15000 ft',
        heading = 220,
        proficiency = 'Regular'
    })
end

spawn_raid('Red', 'N27.00.00', 'E057.00.00')

-- === [missions] 20.2 Recipe: create CAP box and patrol mission from scratch ===
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 1', lat = 'N25.20.00', lon = 'E054.50.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 2', lat = 'N25.20.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 3', lat = 'N24.50.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 4', lat = 'N24.50.00', lon = 'E054.50.00' })

ScenEdit_AddMission('Blue', 'Northern CAP', 'Patrol', {
    type = 'AAW',
    Zone = { 'CAP 1', 'CAP 2', 'CAP 3', 'CAP 4' }
})

ScenEdit_AssignUnitToMission('Eagle #1', 'Northern CAP')
ScenEdit_AssignUnitToMission('Eagle #2', 'Northern CAP')

ScenEdit_SetDoctrine({ side = 'Blue', mission = 'Northern CAP' }, {
    weapon_control_status_air = 0,
    engage_opportunity_targets = 'true'
})

-- === [sim_control] 20.3 Recipe: persist a one time spawn with key store ===
local already_spawned = ScenEdit_GetKeyValue('enemy_raid_spawned')

if already_spawned ~= 'true' then
    ScenEdit_AddUnit({
        type = 'Aircraft',
        unitname = 'Enemy Raid #1',
        side = 'Red',
        dbid = 3500,
        loadoutid = 16934,
        lat = 'N27.00.00',
        lon = 'E057.00.00',
        altitude = '18000 ft'
    })

    ScenEdit_SetKeyValue('enemy_raid_spawned', 'true')
end

-- === [scenario_state] 20.4 Recipe: dynamic weather randomization at scenario start ===
math.randomseed(os.time())

ScenEdit_SetWeather(
    math.random(10, 35),
    math.random(0, 20),
    math.random(0, 10) / 10.0,
    math.random(0, 5)
)

-- === [sim_control] 20.5 Recipe: build a blank scenario then add sides and seed units ===
Tool_BuildBlankScenario('Generated Scenario')

ScenEdit_AddSide({ side = 'Blue' })
ScenEdit_AddSide({ side = 'Red' })

ScenEdit_SetSidePosture('Blue', 'Red', 'H')
ScenEdit_SetSidePosture('Red', 'Blue', 'H')

ScenEdit_AddUnit({
    type = 'Ship',
    unitname = 'Blue Frigate',
    side = 'Blue',
    dbid = 52,
    lat = 'N25.00.00',
    lon = 'E055.00.00'
})

ScenEdit_AddUnit({
    type = 'Ship',
    unitname = 'Red Corvette',
    side = 'Red',
    dbid = 1132,
    lat = 'N25.30.00',
    lon = 'E055.40.00'
})

-- === [ui_messages] 21.1 Find a unit by name and return its GUID ===
function get_unit_guid(side_name, unit_name)
    local unit = ScenEdit_GetUnit({ side = side_name, unitname = unit_name })
    if unit then
        return unit.guid
    end
    return nil
end

-- === [helpers] 21.2 Safe print of CommandLua error state ===
function print_last_commandlua_error()
    print('Function: ' .. tostring(_errfnc_))
    print('Message: ' .. tostring(_errmsg_))
    print('Number: ' .. tostring(_errnum_))
end

-- === [doctrine] 21.3 Require a unit wrapper or raise a descriptive message ===
function require_unit(side_name, unit_name)
    local unit = ScenEdit_GetUnit({ side = side_name, unitname = unit_name })
    if not unit then
        error('Unit not found: ' .. tostring(side_name) .. ' / ' .. tostring(unit_name))
    end
    return unit
end

