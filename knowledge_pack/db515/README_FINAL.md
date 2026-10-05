# CMO DB3K 515 Validated Lookup Library

Source database: `DB3K_515.db3`

This package is the validated result of the Stage-1 through Stage-4 extraction work.

## Confirmed relationship chain

`DataAircraft.ID`
→ `DataAircraftLoadouts.ID`

`DataAircraftLoadouts.ComponentID`
→ `DataLoadout.ID`

`DataLoadoutWeapons.ID`
→ `DataLoadout.ID`

`DataLoadoutWeapons.ComponentID`
→ `DataWeaponRecord.ID`

`DataWeaponRecord.ComponentID`
→ `DataWeapon.ID`

Weapon quantities use `DataWeaponRecord.DefaultLoad` and `MaxLoad`.
`DataLoadoutWeapons.ComponentNumber` is retained as a component/slot ordinal, not treated as quantity.

## Main files

- `cmo_aircraft_lookup.csv` — aircraft DBID catalog
- `cmo_platform_lookup_corrected.csv` / `.lua` — corrected platform catalog
- `cmo_aircraft_loadouts.csv` — authoritative aircraft DBID → loadout DBID relationships
- `cmo_aircraft_loadouts.lua` — full nested Lua lookup
- `cmo_aircraft_loadout_weapons.csv` — raw component-level weapon records
- `cmo_aircraft_loadout_weapon_totals.csv` — corrected weapon quantities
- `cmo_target_aircraft_loadouts.csv` / `.lua` — compact lookup for the nine aircraft used in the current work
- `cmo_target_aircraft_loadout_weapon_totals.csv` — corrected target weapon quantities
- `cmo_target_aircraft_loadout_report.md` — readable target-aircraft report
- `cmo_target_aircraft_variant_audit.csv` — database country/service identity for each target DBID
- `cmo_stage4_summary.md` — extraction counts and notes

## Important target DBID audit

These DBIDs identify specific database variants:

- 4935 — F-35C Lightning II — United States / Marine Corps
- 4293 — E-2D Advanced Hawkeye — United States / Navy
- 5193 — MH-60R Seahawk — South Korea / Navy
- 3326 — F-35A Lightning II — Norway / Air Force
- 5286 — MQ-9A Reaper UAV — France / Air Force
- 3853 — E-3G Sentry — United States / Air Force
- 5456 — F-15E Strike Eagle — United States / Air Force
- 1308 — F-4E Phantom II — Iran / Air Force
- 5022 — Mohajer-6 UAV — Iran / IRGC Navy

CMO can place a database platform on a scenario side that differs from the platform's database operator, so the side name alone does not make a DBID a U.S. variant.

## Recommended use

For manual research, search the CSV files by aircraft DBID, loadout DBID, weapon DBID, or name.

For CMO Bridge / local automation, use `cmo_aircraft_loadouts.lua` as the authoritative nested aircraft → loadout → weapon lookup.

For the current nine-aircraft work, use `cmo_target_aircraft_loadouts.lua` and the target report rather than loading the full database-sized table.

Re-run the scanner only when the CMO database revision changes or when a different DB3K `.db3` file is being used.
