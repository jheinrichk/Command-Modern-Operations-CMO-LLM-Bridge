-- CMO CommandLua recipes: topic 'sim_control'

-- --- 12.23 `ScenEdit_SetTime()` ---
ScenEdit_SetTime({Date="2.12.2007", Time="22.46.23"})

-- --- 12.23 `ScenEdit_SetTime()` ---
local m = ScenEdit_GetMission('sidea', 'test support')
print(m)
m.starttime = "2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"
print(m.starttime)

-- --- 12.36 `Tool_BuildBlankScenario()` ---
Tool_BuildBlankScenario('Sandbox Build Test')
SetScenarioTitle('Sandbox Build Test')

-- --- 13.13 Set time ---
ScenEdit_SetTime({Date="2.12.2007", Time="22.46.23"})

-- --- 13.19 Date/time explicit format ---
local m = ScenEdit_GetMission('sidea', 'test support')
print(m)
m.starttime = "2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"
print(m.starttime)

-- --- 14.1 Recipe: build a simple blank scenario and set title ---
Tool_BuildBlankScenario('Test Sandbox')
SetScenarioTitle('Test Sandbox')
ScenEdit_SetTime({Date='06/09/2027', Time='01:30:00'})

-- --- 7.1 Add a simple strike mission ---
local mission = ScenEdit_AddMission('USA', 'Marker strike', 'strike', {
    type = 'land'
})

if mission then
    print(mission.name)
end

-- --- 11.1 Set weather with random values ---
ScenEdit_SetWeather(
    math.random(0, 25),
    math.random(0, 50),
    math.random(0, 10) / 10.0,
    math.random(0, 9)
)

-- --- 11.2 Get current weather ---
local wx = ScenEdit_GetWeather()
print(wx.temperature)
print(wx.rainfall)
print(wx.undercloud)
print(wx.seastate)

-- --- 11.3 Set scenario time using date and time table ---
ScenEdit_SetTime({
    Date = '2.12.2007',
    Time = '22.46.23'
})

-- --- 11.4 Set scenario title ---
SetScenarioTitle('Operation Sample Dawn')

-- --- 11.5 Read current title ---
print(GetScenarioTitle())

-- --- 11.6 Set score for a side ---
ScenEdit_SetScore('Blue', 250, 'Awarded for successful convoy protection')

-- --- 11.7 End the scenario ---
ScenEdit_EndScenario()

-- --- 20.3 Recipe: persist a one time spawn with key store ---
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

-- --- 20.5 Recipe: build a blank scenario then add sides and seed units ---
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

