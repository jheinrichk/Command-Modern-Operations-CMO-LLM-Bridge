-- CMO CommandLua recipes: topic 'world_tools'

-- --- 12.28 `Tool_Bearing()`, `Tool_Range()`, `Tool_LOS()`, `World_GetPointFromBearing()`, `World_GetElevation()` ---
local brg = Tool_Bearing({lat='25.0', lon='121.8'}, {lat='25.2', lon='122.1'})
local rng = Tool_Range({lat='25.0', lon='121.8'}, {lat='25.2', lon='122.1'})
print(brg, rng)

-- --- 12.28 `Tool_Bearing()`, `Tool_Range()`, `Tool_LOS()`, `World_GetPointFromBearing()`, `World_GetElevation()` ---
local pt = World_GetPointFromBearing('25.0', '121.8', 90, 25)
print(pt.latitude, pt.longitude)

-- --- 18.1 Bearing between two points ---
local brg = Tool_Bearing('N25.00.00', 'E055.00.00', 'N25.30.00', 'E055.20.00')
print(brg)

-- --- 18.2 Range between two points ---
local rng = Tool_Range('N25.00.00', 'E055.00.00', 'N25.30.00', 'E055.20.00')
print(rng)

-- --- 18.3 LOS between two points ---
local los = Tool_LOS_Points({
    observerlatitude = 'N25.00.00',
    observerlongitude = 'E055.00.00',
    targetlatitude = 'N25.30.00',
    targetlongitude = 'E055.20.00'
})
print(los)

-- --- 18.4 Get point from bearing and range ---
local p = World_GetPointFromBearing({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    bearing = 45,
    distance = 50
})

print(p.latitude, p.longitude)

-- --- 18.5 Get a circle from point ---
local circle = World_GetCircleFromPoint({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    radius = 25,
    points = 12
})

-- --- 18.6 Get elevation ---
local elev = World_GetElevation({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00'
})
print(elev)

