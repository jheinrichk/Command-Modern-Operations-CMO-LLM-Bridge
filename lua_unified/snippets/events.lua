-- CMO CommandLua recipes: topic 'events'

-- --- 12.18 `ScenEdit_SetTrigger(table)` ---
local a = ScenEdit_SetTrigger({
    mode='add',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    targetfilter={SPECIFICUNIT='AOE 421 Sagami'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=true
})

-- --- 12.18 `ScenEdit_SetTrigger(table)` ---
local a = ScenEdit_SetTrigger({
    mode='update',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    rename='Any AOE entering hot zone',
    targetfilter={TargetSubType='5023', TargetType='2', TargetSide='sidea'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=false
})

-- --- 12.18 `ScenEdit_SetTrigger(table)` ---
local a = ScenEdit_SetTrigger({
    mode='remove',
    type='UnitEntersArea',
    name='Any AOE entering hot zone'
})

-- --- 12.18 `ScenEdit_SetTrigger(table)` ---
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

-- --- 12.19 `ScenEdit_SetCondition(table)` ---
ScriptTest='--comment\r\nif unit ~= nil then\r\n return true\r\n else\r\n return false\r\n end'

-- --- 12.19 `ScenEdit_SetCondition(table)` ---
local a = ScenEdit_SetCondition({
    mode='add',
    type='SidePosture',
    name='sideA hostile to sideB',
    ObserverSideId='sidea',
    TargetSideId='sideb',
    targetposture='hostile'
})

-- --- 12.19 `ScenEdit_SetCondition(table)` ---
local cond = ScenEdit_SetCondition({
    mode = 'add',
    type = 'LuaScript',
    name = 'at least one hostile contact exists',
    ScriptText = "local cons = ScenEdit_GetContacts('BLUE')\r\nreturn cons ~= nil and next(cons) ~= nil"
})

-- --- 12.20 `ScenEdit_SetAction(table)` ---
local a = ScenEdit_SetAction({
    mode='add',
    type='Points',
    name='sideA loses some ..',
    SideId='sidea',
    PointChange=-10
})

-- --- 12.20 `ScenEdit_SetAction(table)` ---
local act = ScenEdit_SetAction({
    mode = 'add',
    type = 'Message',
    name = 'notify blue player',
    SideID = 'BLUE',
    Text = 'Hostile task group detected to the east.'
})

-- --- 12.20 `ScenEdit_SetAction(table)` ---
local act2 = ScenEdit_SetAction({
    mode = 'add',
    type = 'LuaScript',
    name = 'spawn reinforcements',
    ScriptText = "ScenEdit_AddUnit({type='Air', unitname='Reinforcement 1', side='BLUE', dbid=3500, loadoutid=16934, latitude='25.0', longitude='121.8', altitude='5000 ft'})"
})

-- --- 12.21 `ScenEdit_SetEvent(eventName, options)` ---
local a = ScenEdit_SetEvent('my new event', {mode='add'})

-- --- 12.21 `ScenEdit_SetEvent(eventName, options)` ---
local ev = ScenEdit_SetEvent('Blue detection event', {
    mode = 'add',
    isactive = true,
    isrepeatable = true,
    probability = 100
})

-- --- 12.22 `ScenEdit_SetEventTrigger`, `ScenEdit_SetEventCondition`, `ScenEdit_SetEventAction` ---
local a = ScenEdit_SetEventAction('test event', {mode='add', name='test action points'})
local a = ScenEdit_SetEventAction('test event', {mode='replace', name='test action message', replaceby='test action points'})

-- --- 12.22 `ScenEdit_SetEventTrigger`, `ScenEdit_SetEventCondition`, `ScenEdit_SetEventAction` ---
ScenEdit_SetEvent('Blue detects red surface group', {mode='add'})
ScenEdit_SetEventTrigger('Blue detects red surface group', {mode='add', name='BLUE detects hostile ship'})
ScenEdit_SetEventCondition('Blue detects red surface group', {mode='add', name='sideA hostile to sideB'})
ScenEdit_SetEventAction('Blue detects red surface group', {mode='add', name='notify blue player'})

-- --- 12.24 `ScenEdit_AddSpecialAction()` and `ScenEdit_SetSpecialAction()` ---
local sa = ScenEdit_AddSpecialAction({
    side = 'BLUE',
    name = 'Spawn CAP',
    description = 'Spawn an alert CAP at the player request',
    IsActive = true,
    IsRepeatable = false,
    ScriptText = "ScenEdit_AddUnit({type='Air', unitname='CAP Spawn', side='BLUE', dbid=3500, loadoutid=16934, latitude='25.05', longitude='121.95', altitude='12000 ft'})"
})

-- --- 13.7 Set trigger ---
local a = ScenEdit_SetTrigger({
    mode='add',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    targetfilter={SPECIFICUNIT='AOE 421 Sagami'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=true
})

-- --- 13.7 Set trigger ---
local a = ScenEdit_SetTrigger({
    mode='update',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    rename='Any AOE entering hot zone',
    targetfilter={TargetSubType = '5023',TargetType = '2',TargetSide='sidea'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=false
})

-- --- 13.7 Set trigger ---
local a = ScenEdit_SetTrigger({mode='remove',type='UnitEntersArea',name='Any AOE entering hot zone'})

-- --- 13.8 Set condition ---
local a = ScenEdit_SetCondition({
    mode='add',
    type='SidePosture',
    name='sideA hostile to sideB',
    ObserverSideId='sidea',
    TargetSideId='sideb',
    targetposture='hostile'
})

-- --- 13.9 Condition script text formatting ---
ScriptTest='--comment\r\nif unit ~= nil then\r\n return true\r\n else\r\n return false\r\n end'

-- --- 13.10 Set action ---
local a = ScenEdit_SetAction({mode='add', type='Points', name='sideA loses some ..', SideId='sidea', PointChange=-10})

-- --- 13.11 Event action linking ---
local a = ScenEdit_SetEventAction('test event', {mode='add', name='test action points'})
local a = ScenEdit_SetEventAction('test event', {mode='replace', name='test action message', replaceby='test action points'})

-- --- 13.12 Add event ---
local a = ScenEdit_SetEvent('my new event', {mode='add'})

-- --- 12.1 Add an event ---
ScenEdit_SetEvent('Spawn Enemy Raid', {
    IsActive = true,
    IsShown = true,
    IsRepeatable = false
})

-- --- 12.2 Add a trigger to an event ---
ScenEdit_SetEventTrigger('MyEvent', {
    mode = 'add',
    description = 'MyNewTrigger'
})

-- --- 12.3 Replace a condition on an event ---
ScenEdit_SetEventCondition('MyEvent', {
    mode = 'replace',
    description = 'MyCondition'
})

-- --- 12.4 Add an action to an event ---
ScenEdit_SetEventAction('MyEvent', {
    mode = 'add',
    description = 'SpawnRaidAction'
})

-- --- 12.5 Execute an event action manually ---
ScenEdit_ExecuteEventAction('Spawn Enemy Raid', 'SpawnRaidAction')

-- --- 12.6 Full event scaffold with trigger, condition, and action placeholders ---
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

-- --- 12.7 Add a special action ---
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

-- --- 12.8 Execute a special action ---
ScenEdit_ExecuteSpecialAction('Blue', 'Request Reinforcements')

