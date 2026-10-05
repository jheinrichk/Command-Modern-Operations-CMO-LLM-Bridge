-- CMO CommandLua recipes: topic 'loadout_cargo'

-- --- 12.8 `ScenEdit_AddReloadsToUnit()` ---
ScenEdit_AddReloadsToUnit({unitname='Mech Inf #1', wpn_dbid=773, number=1, w_max=10})

-- --- 12.9 `ScenEdit_AddWeaponToUnitMagazine()` ---
ScenEdit_AddWeaponToUnitMagazine({unitname='Ammo', wpn_dbid=773, number=1, w_max=10})

-- --- 12.33 `ScenEdit_UpdateUnit()` and `ScenEdit_UpdateUnitCargo()` ---
ScenEdit_UpdateUnit({
    guid = 'UNIT-GUID',
    mode = 'add_sensor',
    dbid = 1234
})

-- --- 13.5 Add reloads ---
ScenEdit_AddReloadsToUnit({unitname='Mech Inf #1', wpn_dbid=773, number=1, w_max=10})

-- --- 13.6 Add weapon to magazine ---
ScenEdit_AddWeaponToUnitMagazine({unitname='Ammo', wpn_dbid=773, number=1, w_max=10})

-- --- 6.1 Add weapons to a magazine ---
local added = ScenEdit_AddWeaponToUnitMagazine({
    unitname = 'Ammo',
    wpn_dbid = 773,
    number = 1,
    w_max = 10
})

print('Added: ' .. tostring(added))

-- --- 6.2 Add reloads to a unit ---
local ok = ScenEdit_AddReloadsToUnit({
    side = 'Blue',
    unitname = 'Eagle #1'
})

print(ok)

-- --- 6.3 Set aircraft loadout ---
ScenEdit_SetLoadout({
    side = 'Blue',
    unitname = 'Eagle #1',
    loadoutid = 16934,
    time_to_ready_minutes = 15
})

-- --- 6.4 Fill magazines for a chosen loadout pattern ---
ScenEdit_FillMagsForLoadout({
    side = 'Blue',
    unitname = 'Eagle #1'
})

-- --- 6.5 Refuel a unit ---
ScenEdit_RefuelUnit({
    side = 'Blue',
    unitname = 'USS Example'
})

-- --- 6.6 Transfer cargo between units ---
ScenEdit_TransferCargo({
    side = 'Blue',
    from = 'Transport #1',
    to = 'Airbase Alpha',
    cargo_guid = 'cargo-guid-here'
})

-- --- 6.7 Unload cargo ---
ScenEdit_UnloadCargo({
    side = 'Blue',
    unitname = 'Transport #1',
    cargo_guid = 'cargo-guid-here'
})

