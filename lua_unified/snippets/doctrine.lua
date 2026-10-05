-- CMO CommandLua recipes: topic 'doctrine'

-- --- 12.31 `ScenEdit_SetDoctrine()` and `ScenEdit_SetDoctrineWRA()` ---
ScenEdit_SetDoctrine({side='BLUE'}, {use_nuclear_weapons='no', weapon_control_status_air='tight'})
ScenEdit_SetDoctrineWRA({side='BLUE', weapon_id=51, target_type='Aircraft'}, {qty_salvo=2})

-- --- 4.2 Doctrine selector ---
local doctrine_side = { side = 'Blue' }
local doctrine_mission = { side = 'Blue', mission = 'BARCAP North' }
local doctrine_unit = { side = 'Blue', unitname = 'Eagle #1' }

-- --- 8.3 Set unit level doctrine ---
ScenEdit_SetDoctrine({
    side = 'Soviet Union',
    unitname = 'Bear #2'
}, {
    use_nuclear_weapons = 'yes'
})

-- --- 8.4 Reset doctrine to inherit ---
ScenEdit_SetDoctrine({
    side = 'Blue',
    mission = 'BARCAP North'
}, {})

-- --- 8.5 Read doctrine first, then update selectively ---
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

-- --- 8.6 Set WRA for a weapon and target type ---
ScenEdit_SetDoctrineWRA({
    side = 'Blue',
    mission = 'BARCAP North',
    weapon_id = 51,
    target_type = 2001
}, {
    qty_salvo = 2,
    firing_range = 'max'
})

-- --- 17.4 Export doctrine to XML ---
local doctrine_xml = ScenEdit_ExportDoctrineToXML({
    side = 'Blue'
})
print(doctrine_xml)

-- --- 19.1 Unit wrapper inspection ---
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

-- --- 19.2 Contact wrapper inspection ---
local contact = ScenEdit_GetContact({ side = 'Blue', guid = 'contact-guid-here' })
if contact then
    print(contact.name)
    print(contact.type)
    print(contact.posture)
    print(contact.latitude)
    print(contact.longitude)
end

-- --- 19.4 Scenario wrapper inspection ---
local scen = VP_GetScenario()
print(scen.Title)

-- --- 21.3 Require a unit wrapper or raise a descriptive message ---
function require_unit(side_name, unit_name)
    local unit = ScenEdit_GetUnit({ side = side_name, unitname = unit_name })
    if not unit then
        error('Unit not found: ' .. tostring(side_name) .. ' / ' .. tostring(unit_name))
    end
    return unit
end

