-- CMO CommandLua recipes: topic 'keystore'

-- --- 15.1 Save a persistent key value ---
ScenEdit_SetKeyValue('raid_spawned', 'true')

-- --- 15.2 Read a persistent key value ---
local value = ScenEdit_GetKeyValue('raid_spawned')
print(value)

-- --- 15.3 Clear a persistent key value ---
ScenEdit_ClearKeyValue('raid_spawned')

-- --- 15.4 Store a counter safely ---
local current = tonumber(ScenEdit_GetKeyValue('cap_cycles') or '0')
current = current + 1
ScenEdit_SetKeyValue('cap_cycles', tostring(current))

