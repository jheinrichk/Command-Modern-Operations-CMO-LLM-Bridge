-- CMO CommandLua recipes: topic 'refpoints_zones'

-- --- 14.3 Recipe: create reference points and an area ---
ScenEdit_AddReferencePoint({
    side = 'BLUE',
    area = {
        {name='BOX-1', latitude='25.00', longitude='121.80'},
        {name='BOX-2', latitude='25.10', longitude='121.80'},
        {name='BOX-3', latitude='25.10', longitude='121.95'},
        {name='BOX-4', latitude='25.00', longitude='121.95'}
    }
})

-- --- 4.4 Reference point selector ---
local rp_selector = {
    side = 'Blue',
    name = 'RP 1'
}

-- --- 9.1 Add a single reference point ---
local rp = ScenEdit_AddReferencePoint({
    side = 'Blue',
    name = 'RP 1',
    lat = 'N25.00.00',
    lon = 'E055.00.00'
})

-- --- 9.2 Add four reference points for a patrol box ---
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 1', lat = 'N25.10.00', lon = 'E055.00.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 2', lat = 'N25.10.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 3', lat = 'N24.50.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 4', lat = 'N24.50.00', lon = 'E055.00.00' })

-- --- 9.3 Add a no nav zone ---
local zone = ScenEdit_AddZone('Blue', 'NoNav', {
    description = 'Civilian Exclusion',
    area = { 'RP CAP 1', 'RP CAP 2', 'RP CAP 3', 'RP CAP 4' },
    hidden = 1
})

-- --- 9.4 Set zone attributes ---
ScenEdit_SetZone({
    side = 'Blue',
    description = 'Civilian Exclusion',
    isactive = true
})

-- --- 9.5 Transform a zone ---
ScenEdit_TransformZone({
    side = 'Blue',
    description = 'Civilian Exclusion',
    scale = 1.2
})

-- --- 9.6 Update a reference point ---
ScenEdit_SetReferencePoint({
    side = 'Blue',
    name = 'RP 1',
    lat = 'N25.05.00',
    lon = 'E055.05.00'
})

