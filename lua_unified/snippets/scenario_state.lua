-- CMO CommandLua recipes: topic 'scenario_state'

-- --- 12.27 `Command_SaveScen()` and `SetScenarioTitle()` ---
SetScenarioTitle('Taiwan Strait Escalation')
Command_SaveScen()

-- --- 14.6 Recipe: create a detection driven event chain ---
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

-- --- 14.7 Recipe: use KeyStore to avoid duplicate spawning ---
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

-- --- 14.8 Recipe: event safe error handling skeleton ---
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

-- --- 17.1 Import scenario from XML string ---
local ok = ScenEdit_ImportScenarioFromXML({
    XML = '<Scenario>...a big XML string...</Scenario>'
})

print(ok)

-- --- 17.2 Import scenario from XML file ---
local ok = ScenEdit_ImportScenarioFromXML({
    filename = 'scenario_fragment.xml'
})

print(ok)

-- --- 17.3 Export scenario to XML ---
local xml = ScenEdit_ExportScenarioToXML()
print(xml)

-- --- 20.1 Recipe: spawn a raid package when an event fires ---
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

-- --- 20.4 Recipe: dynamic weather randomization at scenario start ---
math.randomseed(os.time())

ScenEdit_SetWeather(
    math.random(10, 35),
    math.random(0, 20),
    math.random(0, 10) / 10.0,
    math.random(0, 5)
)

