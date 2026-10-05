-- CMO CommandLua recipes: topic 'minefield'

-- --- 14.1 Add a minefield ---
local mf = ScenEdit_AddMinefield({
    side = 'Blue',
    dbid = 2345,
    number = 100,
    delay = 60000,
    area = { 'rp-1', 'rp-2', 'rp-3', 'rp-4' }
})

-- --- 14.2 Delete a minefield ---
ScenEdit_DeleteMinefield({
    side = 'Blue',
    guid = 'minefield-guid-here'
})

-- --- 14.3 Add an explosion ---
ScenEdit_AddExplosion({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    altitude = 0,
    dbid = 2100
})

