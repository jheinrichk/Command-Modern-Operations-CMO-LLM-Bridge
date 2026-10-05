-- CMO CommandLua recipes: topic 'missions'

-- --- 12.12 `ScenEdit_AssignUnitToMission()` ---
ScenEdit_AssignUnitToMission('F-16 #1', 'Barrier CAP')
ScenEdit_AssignUnitToMission('F-16 #2', 'Barrier CAP')

-- --- 14.4 Recipe: create a patrol mission and assign aircraft ---
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

-- --- 14.5 Recipe: create a strike package with target mission ---
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

-- --- 7.2 Add a patrol mission ---
local mission = ScenEdit_AddMission('Blue', 'BARCAP North', 'Patrol', {
    type = 'AAW',
    Zone = { 'RP CAP 1', 'RP CAP 2', 'RP CAP 3', 'RP CAP 4' }
})

-- --- 7.3 Add a support mission ---
local mission = ScenEdit_AddMission('Blue', 'Tanker Track', 'Support', {
    zone = { 'TK 1', 'TK 2', 'TK 3', 'TK 4' }
})

-- --- 7.4 Add a ferry mission ---
local mission = ScenEdit_AddMission('Blue', 'Ferry to Cyprus', 'Ferry', {
    destination = 'Akrotiri'
})

-- --- 7.5 Add a package or task pool category mission ---
local package = ScenEdit_AddMission('Blue', 'Package Alpha', 'Strike', {
    category = 1,
    type = 'land'
})

local taskpool = ScenEdit_AddMission('Blue', 'Task Pool Alpha', 'Strike', {
    category = 2,
    type = 'land'
})

-- --- 7.6 Assign units to a mission ---
ScenEdit_AssignUnitToMission('Eagle #1', 'BARCAP North')
ScenEdit_AssignUnitToMission('Eagle #2', 'BARCAP North')

-- --- 7.7 Assign a unit as a mission target ---
ScenEdit_AssignUnitAsTarget({
    side = 'Blue',
    mission = 'Marker strike',
    target = 'Enemy Radar Site'
})

-- --- 7.8 Remove a unit as a mission target ---
ScenEdit_RemoveUnitAsTarget({
    side = 'Blue',
    mission = 'Marker strike',
    target = 'Enemy Radar Site'
})

-- --- 7.9 Create a mission flight plan ---
ScenEdit_CreateMissionFlightPlan({
    side = 'Blue',
    mission = 'Marker strike',
    plan = 'Ingress Alpha'
})

-- --- 7.10 Get a mission wrapper and modify it later ---
local mission = ScenEdit_GetMission('Blue', 'BARCAP North')
if mission then
    print(mission.name)
end

-- --- 7.11 Update a mission ---
ScenEdit_SetMission('Blue', 'BARCAP North', {
    flightSize = 2,
    flightSizeCheck = false,
    oneThirdRule = false
})

-- --- 7.12 Delete a mission ---
ScenEdit_DeleteMission('Blue', 'Old Mission')

-- --- 8.2 Set mission level doctrine ---
ScenEdit_SetDoctrine({
    side = 'Soviet Union',
    mission = 'ASW PATROL'
}, {
    kinematic_range_for_torpedoes = 'AutomaticAndManualFire',
    use_nuclear_weapons = 'yes'
})

-- --- 19.3 Mission wrapper inspection ---
local mission = ScenEdit_GetMission('Blue', 'BARCAP North')
if mission then
    print(mission.name)
    print(mission.type)
    print(mission.category)
end

-- --- 20.2 Recipe: create CAP box and patrol mission from scratch ---
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

