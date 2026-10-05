# CMO Comprehensive Unified Library v3

This v3 file keeps the v2 unified library intact and adds an explicit **gap audit**, **missing data checklist**, and **build roadmap** so the package clearly distinguishes what is already covered from what is still missing.

## What this package already includes

- CommandLua documentation based working reference
- wrappers
- selectors
- tables
- data types
- examples and recipes
- uploaded lookup CSV
- uploaded platform lookup Lua module
- uploaded all records lookup Lua module

## Current lookup coverage summary

Total lookup records: **18744**

### Type counts
- Aircraft: 2578
- Facility: 2029
- Mount: 2408
- Sensor: 5643
- Ship: 2191
- Submarine: 325
- Weapon: 3570

### Confirmed facility template names present in the lookup data
- `Single-Unit Airfield 1x 2001-2600m Runway` with normalized key `single_unit_airfield_1x_2001_2600m_runway`
- `Single-Unit Port` with normalized key `single_unit_port`
- `Structure Forward Operating Base` with normalized key `structure_forward_operating_base`
- `Structure Military Base` with normalized key `structure_military_base`
- `Structure Naval Dock` with normalized key `structure_naval_dock`
- `Structure Oil Refinery` with normalized key `structure_oil_refinery`

---

# Explicit Gap Audit

## A. Present now

These are already in this package:

1. **CommandLua scripting reference**
   - main documentation structure
   - function families
   - wrappers
   - selectors
   - tables
   - data types
   - examples and recipes

2. **Lookup layer**
   - exact name lookup
   - normalized key lookup
   - type grouping
   - CSV for spreadsheet filtering
   - Lua modules for script side lookup

3. **Scenario scripting support**
   - common script patterns
   - naming consistency for facilities and platform classes where present in lookup data

## B. Missing now

These are still missing and are **not** in this package yet:

1. **Authoritative DBIDs**
   - platform DBIDs
   - facility DBIDs
   - ship DBIDs
   - submarine DBIDs
   - aircraft DBIDs
   - weapon DBIDs
   - sensor DBIDs
   - mount DBIDs

2. **Aircraft loadout identity data**
   - loadout IDs
   - loadout role linkage by aircraft record
   - time of day and weather loadout mapping
   - ferry and strike loadout selection cross reference

3. **Runtime scenario identity data**
   - GUIDs for placed units
   - GUIDs for contacts
   - GUIDs for missions
   - GUIDs for reference points
   - GUIDs for zones

4. **Database schema reference**
   - table names from the actual CMO SQLite database
   - column names for units, facilities, loadouts, mounts, sensors, and weapons
   - SQL extraction queries matched to the user's owned database build

5. **Full page by page example harvest**
   - every official example block from every linked page captured line by line
   - every oldsite example merged to the same command entry
   - forum example snippets cataloged and tagged by task

6. **Validated facility placement identity mapping**
   - exact class name to exact DBID mapping for facility templates used in Hormuz scripts
   - land placement versus water placement notes
   - tested placement coordinates for each base template

7. **Version pinning**
   - exact CMO database build number tied to the lookup data
   - exact source database file name and date
   - exact extraction date for all derived lookup files

## C. Important practical limitation

This package is a **working scripting library plus name based lookup layer**.

It is **not yet** a full authoritative database identity library.

That means:
- it is good for script structure and class naming consistency
- it is not yet sufficient for exact DBID driven scenario generation without additional database extraction work

---

# What needs to be added for a truly complete CMO database aware Lua library

## Phase 1
Add from the CMO SQLite database:
- unit tables
- facility tables
- aircraft tables
- ship tables
- submarine tables
- sensor tables
- weapon tables
- mount tables
- loadout tables

## Phase 2
Build enrichment files:
- `cmo_dbid_lookup_platforms.lua`
- `cmo_dbid_lookup_facilities.lua`
- `cmo_dbid_lookup_weapons.lua`
- `cmo_dbid_lookup_sensors.lua`
- `cmo_dbid_lookup_mounts.lua`
- `cmo_loadout_lookup.lua`

## Phase 3
Add exact SQL documentation:
- schema overview
- extraction queries
- join queries
- export queries to CSV
- normalization rules from SQLite to Lua lookup modules

## Phase 4
Add validation sections:
- name to DBID validation
- DBID to class name back check
- scenario placement tests
- loadout lookup tests
- mission creation tests using known valid DBIDs

---

# Recommended next files for v4

1. `cmo_database_schema_reference.md`
2. `cmo_dbid_lookup_platforms.csv`
3. `cmo_dbid_lookup_platforms.lua`
4. `cmo_dbid_lookup_facilities.csv`
5. `cmo_dbid_lookup_facilities.lua`
6. `cmo_loadout_lookup.csv`
7. `cmo_loadout_lookup.lua`
8. `cmo_sql_extraction_queries.sql`

---

# Original v2 library content follows

# CMO Comprehensive Unified Library

This file consolidates the existing CommandLua unified library with the uploaded lookup libraries so the working reference includes both:
- the CommandLua documentation, examples, wrappers, selectors, tables, and data types
- the lookup library records for platform and non platform objects derived from the uploaded CSV and Lua lookup modules

## Included companion files in this package

- `cmo_comprehensive_unified_library_v2.md`
- `cmo_lookup_library_clean_v2.csv`
- `cmo_lookup_library_platforms_v2.lua`
- `cmo_lookup_library_all_v2.lua`

## Lookup library coverage

Total lookup records: **18744**

### Type counts
- Aircraft: 2578
- Facility: 2029
- Mount: 2408
- Sensor: 5643
- Ship: 2191
- Submarine: 325
- Weapon: 3570

## Important limitation

The lookup library provides:
- `Name`
- `Type`
- `Cost`
- normalized `Key`

It does not provide:
- DBID
- loadout ID
- GUID
- sensor ID
- weapon ID
- mount ID

So this package is a strong name/type lookup and scripting support library, but it is not yet a full DBID database.

## Confirmed facility template names present in the lookup library

- `Structure Naval Dock` → key `structure_naval_dock`
- `Single-Unit Airfield 1x 2001-2600m Runway` → key `single_unit_airfield_1x_2001_2600m_runway`
- `Single-Unit Port` → key `single_unit_port`
- `Structure Military Base` → key `structure_military_base`
- `Structure Oil Refinery` → key `structure_oil_refinery`
- `Structure Forward Operating Base` → key `structure_forward_operating_base`

These exact facility names are present in the uploaded lookup library and can be used for template naming consistency in scenario scripts.

## How to use the Lua lookup modules in CMO scripts

### Platform focused lookup
```lua
local db = dofile("cmo_lookup_library_platforms_v2.lua")

local rec = db.lookup_exact("Structure Naval Dock")
if rec then
    print(rec.name, rec.type, rec.cost, rec.key)
end

local ships = db.get_type("Ship")
print(#ships)
```

### All record lookup
```lua
local db = dofile("cmo_lookup_library_all_v2.lua")

local rec = db.lookup("single unit port")
if rec then
    print(rec.name, rec.type, rec.key)
end

local facilities = db.get_type("Facility")
print(#facilities)
```

## Recommended use order for future CMO work

1. Use the comprehensive library markdown for:
   - API behavior
   - wrappers
   - selectors
   - tables
   - data types
   - example scripts
   - recipes

2. Use `cmo_lookup_library_platforms_v2.lua` for:
   - platform name lookup
   - normalized key lookup
   - platform type grouping

3. Use `cmo_lookup_library_all_v2.lua` for:
   - weapons
   - sensors
   - mounts
   - aircraft
   - ships
   - submarines
   - facilities

4. Use `cmo_lookup_library_clean_v2.csv` for:
   - spreadsheet filtering
   - bulk search
   - external tooling
   - future enrichment with DBIDs

---

## Original unified CommandLua library

# CMO CommandLua Unified Master Library

This unified file merges the prior master library and the examples and recipes library into one working reference.

It is intended to be the single default Markdown knowledge file for future CMO Lua scenario work.

## Contents
- Part I: Master library
- Part II: Examples and recipes

---

# Part I: Master Library


# CMO CommandLua Comprehensive Working Library

This file is the revised master working reference for Command: Modern Operations Lua scripting.

It is designed to be the default internal library for future CMO scenario scripting work so that script generation can be based on a consolidated reference instead of trial and error.

## 1. Scope and intent

This library consolidates and reorganizes the documentation and linked support material the user provided, with special emphasis on:

- official current CommandLua documentation
- official legacy CommandLua documentation
- selectors
- wrappers
- tables
- data types
- function catalog
- official examples that appear in the docs
- doc compatible complete runnable example scripts for common scenario building tasks

### Important usage note

This is a **working library** and **scenario scripting reference**, not a verbatim mirror of every linked webpage.

Where the current docs provide explicit examples, those examples are included in full where practical.
Where a current page contains only a placeholder example or no example, the example set here is completed using:
- the legacy oldsite docs
- the overview pages
- the linked data type, selector, wrapper, and table pages
- doc compatible CMO Lua patterns

## 2. Documentation basis and coverage map

### 2.1 Official current CommandLua documentation
- `https://commandlua.github.io/index.html`
- `https://commandlua.github.io/index2.html`
- `https://commandlua.github.io/assets/Functions.html`
- `https://commandlua.github.io/assets/Wrappers.html`
- `https://commandlua.github.io/assets/Selectors.html`
- `https://commandlua.github.io/assets/Tables.html`
- `https://commandlua.github.io/assets/DataTypes.html`

### 2.2 Official legacy CommandLua documentation
- `https://commandlua.github.io/oldsite/index.html`

### 2.3 Linked community and support pages
- Matrix Games Lua Legion forum index
- Matrix Games Command series forum index
- Lua Users Wiki tutorials
- Lua Programming Wikibook
- Lua 5.3 manual
- LDoc documentation
- WarfareSims social pages

### 2.4 What each linked source contributes
- **current CommandLua docs**: authoritative current function, selector, wrapper, table, and data type structure
- **oldsite docs**: many usable examples and older explanatory notes not fully present on current function pages
- **Lua Legion forum**: community discussion, troubleshooting, examples, wrapper dumping tricks, scenario scripting discussions
- **Lua manual / tutorials / wikibook / ldoc**: base Lua language help, not CMO specific API definitions
- **social pages**: community contact paths, not API reference content

## 3. Current official doc build notes

Current main documentation build noted on the official site:
- **B1706** for **CMO v1.08**
- **B1705** for **CPE v2.4.2**

Official news and notes visible in the current docs include:
- future build note for additional anchor types in SE_Add/SetReferencePoint
- doc update note dated 25 July 2025
- added pages for missing function docs such as `ScenEdit_ClearAllMagazines`, `ScenEdit_GetFormation`, `ScenEdit_SetLoadoutAvailable`, `ScenEdit_UpdateRSetting`, `ScenEdit_WeaponAllocation`, `Tool_UIwindow`, `SetScenarioTitle`, and others
- CMO 1.08 notes for mission wrapper additions like `packagelist` and `parentTaskPool`
- CMO 1.07 notes for `Tool_BuildBlankScenario`, mission package/task pool support, and wrapper additions

## 4. How to use this library

When building a script, use this order:

1. identify the scenario task
2. identify the object type being manipulated:
   - side
   - unit
   - mission
   - reference point
   - zone
   - contact
   - doctrine / WRA
   - event / trigger / condition / action
3. identify the selector or wrapper required
4. identify the data types or enum values required
5. use the relevant `ScenEdit_*`, `VP_*`, `Tool_*`, `UI_*`, or wrapper method
6. apply one of the complete examples or recipes in this file
7. test in the console or in event context and check `_errmsg_`, `_errfnc_`, `_errnum_` on failure

## 5. Official overview content consolidated

### 5.1 How to Use These Docs
The official docs state that they were written to be accessible to users of different skill levels. Their stated conventions include:
- examples offered where practical
- color coding and linking
- simple language where possible

### 5.2 Need Help
The docs point users to the **Lua Legion** subforum on the official Matrix forums as the main place to get help from the Command Lua community.

### 5.3 Found Something Wrong
The official docs direct users to official community channels including Discord, Twitter, and Facebook for reporting doc problems or asking for help.

### 5.4 Conventions used in the docs
The docs distinguish:
- in text code
- parameter references
- selector references
- wrapper references
- table references
- data type references
- READ ONLY fields
- PRO ONLY fields

### 5.5 First Steps
The official guidance is:
- if already comfortable with Lua, go to the Functions section
- if comfortable with programming but not Lua, read the external resources first

### 5.6 External Resources
The docs explicitly recommend:
- Lua Users Wiki tutorials
- Lua Programming Wikibook
- Lua 5.3 Reference Manual

### 5.7 Case Sensitivity and Conventions
Official current guidance:
- Lua is case sensitive
- direct wrapper property access should use lowercase generated field names such as `unit.name`
- function keyword/value handling is generally case insensitive in the docs
- some special uppercase fields exist and are documented where relevant

### 5.8 Event Handling
Official model:
- an event consists of one or more triggers
- conditions are optional
- one or more actions can be attached
- trigger, condition, and action objects can be created independently and then linked into events

### 5.9 Global Keywords
The current docs identify the following global values:
- `_scriptfolder_`
- `_scenariofolder_`
- `_outputfolder_`

The event section also exposes:
- `_enumTable_`
- `_errfnc_`
- `_errmsg_`

The docs elsewhere add:
- `_errnum_`

### 5.10 Error Handling
The current docs state that failed Command Lua functions normally return `nil` and expose:
- `_errmsg_`
- `_errfnc_`
- `_errnum_`

The docs also explain:
- console execution may visibly throw errors
- event execution usually does not stop with a visible message
- designers should handle command failures explicitly in scripts
- `Tool_EmulateNoConsole(true)` can be used to emulate event like no console behavior while testing

### 5.11 Date and Time
The current docs note newer date/time handling in progress and show the pattern:
- `"2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"`

This allows an explicit format suffix after `!` so the engine can parse the date string correctly.

## 6. Core CommandLua rules to keep in mind

- Prefer GUIDs over names whenever practical
- When selecting units:
  - use `guid`
  - or use `name` plus `side`
- When selecting contacts:
  - prefer the contact GUID from `ScenEdit_GetContacts(side)`
- Prefer `ScenEdit_Set...` functions to direct wrapper mutation when that function exists
- Use wrapper reads for inspection and object traversal
- Use setters and scenario edit functions for authoritative updates
- When working with event Lua script text in a string, use `\r\n` for new lines
- For scripts intended to run from events, check return values explicitly because errors may not appear interactively

## 7. Data type library

The CMO Lua API extends normal Lua types with CMO specific data types and enumerations.

### 7.1 Altitude
Altitude is height or depth. The docs state it is displayed in meters when accessed, but can be set in meters or feet.

Official examples:
```lua
{altitude = '100 FT'}
--or
{altitude = '100 M'}
--or
{altitude = '100'} -- same as 100 M
```

Short form:
- `alt` can be used where `altitude` is accepted

### 7.2 Arc
Sensor or mount firing or detection arcs. The docs illustrate PMF and other directional codes.

### 7.3 Armor
Representative enum notes:
- `1001 = None`
- `1005 = Armor_Handgun`
- `1010 = Armor_Rifle`
- `1015 = Armor_HMG`
- `1020` to `1035` = RHA variants
- `2001 = Light`
- `2002 = Medium`
- `2003 = Heavy`
- `2004 = Special`

### 7.4 Awareness
- `-1 = Blind`
- `0 = Normal`
- `1 = AutoSideID`
- `2 = AutoSideAndUnitID`
- `3 = Omniscient`

### 7.5 CargoObjectType
- `0 = None`
- `1 = Mount`
- `2 = Vehicle`
- `3 = Facility`
- `4 = CargoContainer`
- `5 = CargoContainerContent`

### 7.6 CargoStorageType
- `0 = StoredInternal`
- `1 = StoredExternal`
- `2 = TowedExternal`

### 7.7 CargoType
Representative notes:
- `0 = NoCargo`
- `1000 = Personnel`
- `2000 = SmallCargo`
- up through `5000 = VLargeCargo`

### 7.8 ContactIdStatus
Identification confidence scale:
- `0 = Unknown`
- up to `4 = PreciseID`

### 7.9 ContactType
Representative categories in the uploaded reference:
- `00 = Air`
- `01 = Missile`
- `02 = Surface`
- `03 = Submarine`
- `05 = Aimpoint`
- `06 = Orbital`
- `07 = Facility_Fixed`
- other codes continue in docs

### 7.10 DateTime
Locale aware date string support exists, but new parsing patterns also allow explicit format suffixes after `!`.

### 7.11 Doctrine / ROE / WCS family
These include many coded values for:
- ambiguous target engagement
- weapon control status
- fuel state
- battery recharge
- allied UNREP behavior
- many other doctrine fields

Representative WCS notes:
- `0 = Free`
- `1 = Tight`
- `2 = Hold`

### 7.12 Fuel
Fuel values are a table keyed by fuel type, with current and max quantities.

Representative type notes from the uploaded reference:
- `1001 = NoFuel`
- `2001 = AviationFuel`
- `3001 = Diesel`
- more types continue through weapon related types

### 7.13 GUID
32 character unique ID string. Read only after creation.

### 7.14 KeyStore
Persistent key value storage using strings.

Practical rule:
- store strings
- use `tostring()` and `tonumber()` as needed for numeric values

### 7.15 LandCover
Representative notes:
- `0 = Water`
- `1` to `16` = forest/grass/terrain classes
- `201` to `208` = urban variants
- `254 = Unclassified`
- `255 = User data`

### 7.16 Latitude / Longitude
Can be passed as:
- decimal degrees
- DMS style strings

Representative examples from uploaded reference:
- `'S 60.20.10'`
- `-60.336`

Short forms:
- `lat`
- `lon`

### 7.17 LoadoutRole / LoadoutTimeOfDay / LoadoutWeather
Used in aircraft loadout logic.

### 7.18 MissionType / MissionSubtype
Mission categories and mission subtypes drive `ScenEdit_AddMission()` behavior and mission wrapper behavior.

### 7.19 Preset
Preset speed, altitude, and depth values.

### 7.20 Proficiency
Representative scale:
- `0 = Novice`
- `1 = Cadet`
- `2 = Regular`
- `3 = Veteran`
- `4 = Ace`

### 7.21 RealismSetting
Scenario realism settings exposed to Lua.

### 7.22 Sensor
Sensor related enums and data.

### 7.23 Stance
Side posture / relationship state.

### 7.24 TargetingMode
Used by `AttackOptions`.

### 7.25 TargetTypeWRA
Weapon release authority target type logic.

### 7.26 TimeStamp
CMO specific time stamp values.

### 7.27 TrueFalse
CMO docs use True/False as a documented type family.

### 7.28 Unit Types
Base unit type notes:
- `1 = Aircraft`
- `2 = Ship`
- `3 = Submarine`
- `4 = Facility`
- `5 = Aimpoint`
- `6 = Weapon`
- `7 = Satellite`
- `8 = Ground unit`

### 7.29 Aircraft category codes
Representative notes:
- `1001 = None`
- `2001 = Fixed Wing`
- `2002 = Fixed Wing Carrier Capable`
- `2003 = Helicopter`
- `2004 = Tiltrotor`
- `2006 = Airship`
- `2007 = Seaplane`
- `2008 = Amphibian`

### 7.30 Facility category data
See facility data type page and database specific values.

### 7.31 Satellite category and subtype examples
Representative notes:
- `1001 = None`
- `2001 = Geo-Stationary`
- `2002 = Something Else`
- `2003 = Unmanned Test Vehicle`

Representative subtype examples:
- `2001 = IMGSAT`
- `2002 = RORSAT`
- `2003 = EORSAT`
- `2004 = SIGINT`
- `2005 = ELINT`
- `2006 = NOSS`
- `2007 = MASINT`
- `2008 = Reusable Test Vehicle`

### 7.32 Ship category data
See ship data type page and DB specific values.

### 7.33 Submarine category and subtype examples
Representative category notes:
- `1001 = None`
- `2001 = Submarine`
- `2002 = Biologics`
- `2003 = False Target`

Representative subtype examples:
- `2001 = AGSS`
- `2002 = APSS`
- `2003 = SS`
- `2004 = SSB`
- `2005 = SSBN`
- `2006 = SSG`
- `2007 = SSGN`
- `2008 = SSK`
- `2009 = SSM`
- `2010 = SSN`
- `2011 = SSP`
- `2012 = SSR`
- `2013 = SSRN`
- `3001 = SDV`
- `4001 = ROV`
- `4002 = UUV`
- `4003 = Unmanned Underwater Glider`
- `9001 = Biologics`
- `9002 = False Target`

### 7.34 Size
CMO size categories.

### 7.35 UI Windows
Used by UI helpers and Tool_UIwindow.

### 7.36 WayPoint
Waypoint type family.

### 7.37 WeaponControl
Weapon control data family.

### 7.38 WeaponDoctrine
Weapon doctrine data family.

### 7.39 WeaponType
Weapon type enum family.

## 8. Selector library

Selectors define how many `ScenEdit_*` functions identify the object to operate on.

### 8.1 AttackOptions
Official selector fields:
- `mode` = TargetingMode
- `mount` = attacker mount DBID
- `weapon` = attacker weapon DBID
- `qty` = number to allocate

### 8.2 ContactSelector
Official selector notes:
- a unit GUID and its contact GUID are different
- contact GUIDs are side perspective specific
- fields:
  - `side`
  - `guid`

Practical rule:
- get the contact GUID from `ScenEdit_GetContacts(side)`

### 8.3 DamageOptions
Representative uploaded reference notes:
- `side`
- `unitname`
- `guid`
- `fires`
- `flood`
- `dp`
- `components`

### 8.4 DoctrineSelector
Representative uploaded reference notes:
- `side`
- `mission`
- `unitname`
- `actual`
- `escort`

### 8.5 DoctrineWRASelector
Representative uploaded reference notes:
- side / mission / unit selector
- `weapon_id`
- either `contact_id` or `target_type`

### 8.6 EventActionUpdate
- `ID`
- `Description`
- `NewName`
- `Mode`
- `Type`

### 8.7 EventConditionUpdate
- `ID`
- `Description`
- `NewName`
- `Mode`
- `Type`

### 8.8 EventSpecialAction
Representative fields:
- `GUID`
- `ActionNameOrID`
- `IsActive`
- `IsRepeatable`
- `NewName`
- `Description`
- `Side`
- `Mode`
- `ScriptText`

### 8.9 EventTCAUpdate / EventTriggerUpdate / EventUpdate
Representative notes:
- `ID`
- `Description`
- `NewName`
- `Mode`
- type specific attributes

`EventUpdate` includes:
- `IsActive`
- `IsRepeatable`
- `IsShown`
- `Probability`

### 8.10 NewMission
Current selector notes:
- `type` = mission sub type
- `destination` = ferry destination
- `zone` = table of reference points for patrol/support/mining/cargo mission types

### 8.11 NewUnit
Official minimum fields:
- `type`
- `unitname`
- `side`
- `dbid`
- `latitude`
- `longitude`
- `base` where applicable
- `loadoutid` for aircraft
- `altitude` for aircraft
- `depth` for submarines
- `orbit` for satellites
- `guid` optional override

Other Unit wrapper fields may also be included.

### 8.12 ReferencePointSelector
Official selection rules:
- `name` and `side`
- or `guid`
- or `area` table
- GUID is preferred and takes precedence

### 8.13 SideOption
Official fields:
- `side`
- `guid`
- `awareness`
- `proficiency`
- `switchto`

### 8.14 TargetFilter
Official order:
- side
- type
- subtype
- unitclass
- specific unit

Official fields:
- `TargetSide`
- `TargetType`
- `targetSubType`
- `SpecificUnitClass`
- `SpecificUnit`

### 8.15 UnitSelector
Official rules:
- use `name` and `side`
- or use `guid`
- if both are provided, GUID wins

Fields:
- `name`
- `side`
- `guid`

### 8.16 UnitUpdate
Official fields include:
- `guid`
- `mode`
- `dbid`
- `sensorid`
- `mountid`
- `weaponid`
- `commsid`
- `magid`
- `file`
- `arc_detect`
- `arc_track`
- `arc_mount`

### 8.17 UnitCargoUpdate
Official fields:
- `guid`
- `mode`
- `cargoList`

### 8.18 VPContactSelector
Used by VP functions for contact selection.

### 8.19 Weapon2Magazine
Used by `ScenEdit_AddWeaponToUnitMagazine()`.

### 8.20 Weapon2Mount
Used for direct mount weapon updates.

## 9. Wrapper library

Wrappers are the runtime objects returned by getters and other Lua functions.

Wrapper index:
- `Cargo`
- `Contact`
- `Doctrine`
- `DoctrineWRA`
- `Event`
- `Group`
- `Loadout`
- `Magazine`
- `Mission`
- `Mount`
- `Operation`
- `ReferencePoint`
- `Scenario`
- `Sensor`
- `Serial`
- `Side`
- `SpecialAction`
- `Unit`
- `Waypoint`
- `Weapon`
- `Zone`

### 9.1 Unit wrapper
The Unit wrapper is the most important object for scenario manipulation.

Current wrapper notes include:
- identity:
  - `guid`
  - `name`
  - `dbid`
  - `classname`
  - `side`
  - `type`
  - `subtype`
  - `category`
- movement and kinematics:
  - `altitude`
  - `desiredAltitude`
  - `desiredSpeed`
  - `desiredHeading`
  - `heading`
  - `speed`
  - `groundSpeed`
  - `course`
  - `pitch`
  - `roll`
- state:
  - `damage`
  - `fuelstate`
  - `unitstate`
  - `weaponstate`
  - `condition`
  - `doctrine`
  - `proficiency`
  - `holdposition`
  - `holdfire`
  - `autodetectable`
  - `outOfComms`
- relationships:
  - `base`
  - `group`
  - `groupLead`
  - `assignedUnits`
  - `AssignedMissionsQueue`
  - `embarkedUnits`
  - `hostFacility`
- combat and signatures:
  - `sensors`
  - `signature`
  - `target`
  - `targetedBy`
  - `firedOn`
- logistics:
  - `cargo`
  - `readytime`
  - `readytime_v`
  - `quickTurnaround`
- special:
  - `SAR_enabled`
  - `sprintDrift`
  - `avoidCavitation`
  - `UseCustomIntermittentEmissionOnly`

Representative methods visible in current/legacy docs include:
- `rangetotarget(contactid)`
- `RTB()`
- `updateorbit({TLE=...})`
- `createUnitCargo(type, dbid [,customname])`
- `deleteUnitCargo(guid)`

### 9.2 Contact wrapper
Representative uploaded reference notes:
- `actualunit`
- `age`
- `altitude`
- `areaofuncertainty`
- `BDA`
- `classificationlevel`
- `detectedBySide`
- `detectionBy`
- `emissions`
- `firedOn`
- `firingAt`
- `fromside`
- `guid`
- `heading`
- `lastDetections`
- `lat`
- `lon`
- `markedAsDecoy`
- `missile_defence`
- `name`
- `observer`
- `posture`
- `potentialmatches`
- `side`
- `speed`
- `targetedBy`
- `type`
- `weather`

Representative methods:
- `DropContact()`
- `inArea()`

### 9.3 Doctrine wrapper
The doctrine wrapper is large. Representative field families mentioned in docs and uploaded text:
- air operations tempo
- automatic evasion
- avoid contact
- engage ambiguous targets
- deploy on attack / damage / fuel conditions
- EMCON behavior
- fuel state logic
- gun strafing
- ignore plotted course when attacking
- jettison ordnance
- torpedo kinematic range
- maintain standoff
- quick turnaround
- recharge rules
- refuel / UNREP allied options
- RTB when winchester
- strike member focus
- target priority

### 9.4 Mission wrapper
Representative notes:
- many mission fields can be updated through `ScenEdit_SetMission()`
- wrapper fields vary by mission type
- current docs note wrapper additions like `packagelist`, `parentTaskPool`, and strike mission focus settings

### 9.5 Side wrapper
Useful for:
- posture logic
- units on side
- contacts on side
- area and filter queries

### 9.6 ReferencePoint wrapper
Useful for:
- position
- visibility
- highlighted / locked attributes
- zone construction

### 9.7 Scenario wrapper
Useful for:
- scenario level information
- time / weather / score integration

### 9.8 Sensor, Weapon, Magazine, Loadout wrappers
Useful for:
- database inspection
- weapon counts
- mount and sensor details
- emission behavior
- loadout state

## 10. Table library

Table index:
- `AAR`
- `Area`
- `Cargo`
- `CargoItem`
- `Component`
- `EMmatch`
- `Emissions`
- `Enablers`
- `Facility`
- `Formation`
- `LastDetections`
- `LatLon`
- `LoadoutInfo`
- `Magazine`
- `MissionCargo`
- `MissionFerry`
- `MissionMine`
- `MissionMineClear`
- `MissionPatrol`
- `MissionStrike`
- `MissionSupport`
- `Mount`
- `ReferencePoint`
- `Sensor`
- `Signature`
- `TargetPriority`
- `WRA`
- `WeaponLoaded`
- `Weather`

### 10.1 Weather table
The current tables page identifies Weather as a dedicated table type.

### 10.2 WeaponLoaded table
Current fields visible on the table page:
- `wpn_guid`
- `wpn_current`
- `wpn_maxcap`
- `wpn_default`
- `wpn_name`
- `wpn_dbid`
- `wpn_type`

### 10.3 Area table
Often a table of named or GUID reference points defining an area.

### 10.4 Signature table
Current profile data for a unit or loadout.

### 10.5 TargetPriority and WRA tables
Used for doctrine and weapon release authority tuning.

## 11. Full function catalog

### 11.1 Events
- `ScenEdit_EventX()`
- `ScenEdit_AddSpecialAction()`
- `ScenEdit_ExecuteEventAction()`
- `ScenEdit_ExecuteSpecialAction()`
- `ScenEdit_GetEvent()`
- `ScenEdit_GetEvents()`
- `ScenEdit_GetSpecialAction()`
- `ScenEdit_SetAction()`
- `ScenEdit_SetCondition()`
- `ScenEdit_SetEvent()`
- `ScenEdit_SetEventAction()`
- `ScenEdit_SetEventCondition()`
- `ScenEdit_SetEventTrigger()`
- `ScenEdit_SetSpecialAction()`
- `ScenEdit_SetTrigger()`
- `ScenEdit_UnitC()`
- `ScenEdit_UnitX()`
- `ScenEdit_UnitY()`

### 11.2 Missions
- `ScenEdit_AddMission()`
- `ScenEdit_AssignUnitAsTarget()`
- `ScenEdit_AssignUnitToMission()`
- `ScenEdit_CreateMissionFlightPlan()`
- `ScenEdit_DeleteMission()`
- `ScenEdit_ExportMission()`
- `ScenEdit_GetMission()`
- `ScenEdit_GetMissions()`
- `ScenEdit_ImportMission()`
- `ScenEdit_SetMission()`
- `ScenEdit_RemoveUnitAsTarget()`

### 11.3 Reference points and zones
- `ScenEdit_AddReferencePoint()`
- `ScenEdit_AddZone()`
- `ScenEdit_DeleteReferencePoint()`
- `ScenEdit_GetReferencePoint()`
- `ScenEdit_GetReferencePoints()`
- `ScenEdit_RemoveZone()`
- `ScenEdit_SetReferencePoint()`
- `ScenEdit_SetZone()`
- `ScenEdit_TransformZone()`

### 11.4 Scenario
- `GetScenarioTitle()`
- `ScenEdit_CurrentLocalTime()`
- `ScenEdit_CurrentTime()`
- `ScenEdit_EndScenario()`
- `ScenEdit_GetScenHasStarted()`
- `ScenEdit_GetWeather()`
- `ScenEdit_GetScore()`
- `ScenEdit_GetTimeOfDay()`
- `ScenEdit_SetStartTime()`
- `ScenEdit_SetScore()`
- `ScenEdit_SetTime()`
- `ScenEdit_SetWeather()`
- `VP_GetContact()`
- `VP_GetScenario()`
- `VP_GetSide()`
- `VP_GetSides()`
- `VP_GetUnit()`

### 11.5 Unit
- `ScenEdit_AddReloadsToUnit()`
- `ScenEdit_AddUnit()`
- `ScenEdit_AddWeaponToUnitMagazine()`
- `ScenEdit_DeleteUnit()`
- `ScenEdit_GetDoctrine()`
- `ScenEdit_GetDoctrineWRA()`
- `ScenEdit_GetFormation()`
- `ScenEdit_GetLoadout()`
- `ScenEdit_GetUnit()`
- `ScenEdit_FillMagsForLoadout()`
- `ScenEdit_KillUnit()`
- `ScenEdit_MergeUnits()`
- `ScenEdit_RefuelUnit()`
- `ScenEdit_SetDoctrine()`
- `ScenEdit_SetDoctrineWRA()`
- `ScenEdit_SetEMCON()`
- `ScenEdit_SetLoadout()`
- `ScenEdit_SetUnit()`
- `ScenEdit_SetUnitDamage()`
- `ScenEdit_SplitUnit()`
- `ScenEdit_TransferCargo()`
- `ScenEdit_UnloadCargo()`
- `ScenEdit_UpdateUnit()`
- `ScenEdit_UpdateUnitCargo()`

### 11.6 Emission configuration
- `ScenEdit_ClearAllSideUnitsEmconConfigs()`
- `ScenEdit_ClearUnitEmconConfigs()`
- `ScenEdit_DuplicateEmconConfigToSide()`
- `ScenEdit_DuplicateEmconConfigToUnit()`
- `ScenEdit_GetUnitIntermittentEmissionConfig()`
- `ScenEdit_SetSideEmconAlertness()`
- `ScenEdit_SetUnitIntermittentEmissionConfig()`
- `ScenEdit_SwitchUnitIntermittentEmission()`

### 11.7 Contacts
- `ScenEdit_AttackContact()`
- `ScenEdit_GetContact()`
- `ScenEdit_GetContacts()`

### 11.8 Miscellaneous and tools
- `Command_SaveScen()`
- `Exporter_SetSetting()`
- `GetBuildNumber()`
- `ScenEdit_ClearKeyValue()`
- `ScenEdit_CreateBarkNotification_Geo()`
- `ScenEdit_CreateBarkNotification_Geo_Bulk()`
- `ScenEdit_CreateBarkNotification_Unit()`
- `ScenEdit_CreateBarkNotification_Unit_Bulk()`
- `ScenEdit_ExportInst()`
- `ScenEdit_GetKeyValue()`
- `ScenEdit_ImportInst()`
- `ScenEdit_InputBox()`
- `ScenEdit_MsgBox()`
- `ScenEdit_PlaySound()`
- `ScenEdit_QueryDB()`
- `ScenEdit_RunScript()`
- `ScenEdit_SelectedUnits()`
- `ScenEdit_SetKeyValue()`
- `ScenEdit_SpecialMessage()`
- `ScenEdit_UpdateRSetting()`
- `ScenEdit_UseAttachment()`
- `ScenEdit_UseAttachmentOnSide()`
- `SetScenarioTitle()`
- `Tool_Bearing()`
- `Tool_BuildBlankScenario()`
- `Tool_DumpEvents()`
- `Tool_EmulateNoConsole()`
- `Tool_LOS()`
- `Tool_LOS_Points()`
- `Tool_Range()`
- `Tool_QueryRCS()`
- `Tool_QuerySoundLevel()`
- `World_GetCircleFromPoint()`
- `World_GetElevation()`
- `World_GetLocation()`
- `World_GetPointFromBearing()`

### 11.9 UI
- `UI_CallAdvancedDialog()`
- `UI_CallAdvancedHTMLDialog()`
- `UI_OpenNewDatabaseWindow()`
- `UI_SelectThisUnit()`
- `UI_SelectUnitsPrompt_FromSides()`
- `UI_SelectUnitsPrompt_OwnSide()`
- `UI_SetCameraView()`
- `Tool_ResetMessageLog()`
- `Tool_UIwindow()`

### 11.10 Others
- `ScenEdit_AddCustomLoss()`
- `ScenEdit_AddExplosion()`
- `ScenEdit_AddMinefield()`
- `ScenEdit_AddSide()`
- `ScenEdit_ClearAllAircraft()`
- `ScenEdit_ClearAllMagazines()`
- `ScenEdit_DeleteMine()`
- `ScenEdit_DeleteMinefield()`
- `ScenEdit_DistributeWeaponAtAirbase()`
- `ScenEdit_GetDateTimeTicks()`
- `ScenEdit_GetMinefield()`
- `ScenEdit_GetSideIsHuman()`
- `ScenEdit_GetSideOptions()`
- `ScenEdit_GetSidePosture()`
- `ScenEdit_HostUnitToParent()`
- `ScenEdit_PlayerSide()`
- `ScenEdit_RemoveSide()`
- `ScenEdit_SetLoadoutAvailable()`
- `ScenEdit_SetSideOptions()`
- `ScenEdit_SetSidePosture()`
- `ScenEdit_SetUnitSide()`
- `ScenEdit_WeaponAllocation()`
- `VP_SetTimeCompression()`

### 11.11 Professional Edition only
- `ScenEdit_ExportDoctrineToXML()`
- `ScenEdit_ExportScenarioToXML()`
- `ScenEdit_GetDBFileHash()`
- `ScenEdit_GetSensorData()`
- `ScenEdit_ImportDoctrineFromXML()`
- `ScenEdit_ImportScenarioFromXML()`
- `ScenEdit_LockSimulationFidelity()`
- `ScenEdit_SetExportOutputRate()`
- `ScenEdit_SetSimulationFidelity()`
- `Tool_SatelliteCoveragePrediction()`
- `VP_PauseSimulation()`
- `VP_RunForTimeAndHalt()`
- `VP_RunSimulation()`
- `VP_RunToTimeAndHalt()`

## 12. Detailed function notes and examples

This section combines current function page details, oldsite examples, and doc compatible examples.

### 12.1 `ScenEdit_AddSide({name=...})`
Purpose:
- add a side

Official oldsite example:
```lua
ScenEdit_AddSide({name='OPFOR'})
```

### 12.2 `ScenEdit_AddUnit(table)`
Current page notes:
- adds a new unit to a side
- calls `ScenEdit_SetUnit()` at the end
- extra fields can be passed through without needing a separate setter call

Minimum core fields from current page:
- `type`
- `unitname`
- `side`
- `dbid`
- `base` or `latitude` and `longitude`
- `altitude` if aircraft
- `loadoutid` if aircraft
- `orbit` if satellite
- optional custom `guid`

Official current examples:
```lua
ScenEdit_AddUnit({type ='Air', unitname ='F-15C Eagle', loadoutid =16934, dbid =3500, side ='NATO', Lat="5.123",Lon="-12.51",alt=5000})
ScenEdit_AddUnit({type ='Ship', unitname ='GOE II Det C', dbid =3127, side ='USN', latitude="5.123",longitude="-12.51",proficiency='Veteran'})
```

Official oldsite example:
```lua
ScenEdit_AddUnit({type ='Aircraft', name ='F-15C Eagle', loadoutid =16934, heading =0, dbid =3500, side ='NATO', Latitude="N46.00.00",Longitude="E25.00.00", altitude="5000 ft",autodetectable="false",holdfire="true",proficiency=4})
```

Generated complete example:
```lua
local red_sub = ScenEdit_AddUnit({
    type = 'Submarine',
    unitname = 'Kilo 01',
    side = 'RED',
    dbid = 402,
    latitude = '25.0000',
    longitude = '122.0000',
    depth = 40,
    proficiency = 'Veteran',
    autodetectable = false
})

if red_sub == nil then
    print('AddUnit failed: ' .. tostring(_errmsg_))
else
    print('Created unit: ' .. red_sub.name .. ' / ' .. red_sub.guid)
end
```

### 12.3 `ScenEdit_SetUnit(table)`
Current page notes:
- sets properties on an existing unit
- supports selection by `side` and `unitname` or by `guid`
- `speed` and `throttle` are mutually exclusive
- many movement, behavior, fuel, course, assignment, and readiness fields are supported

Representative current fields:
- `newname`
- `group`
- `mission`
- `speed`
- `throttle`
- `launch`
- `rtb`
- `refuel`
- `unassign`
- `moveto`
- `altitude`
- `depth`
- `heading`
- `desiredHeading`
- `latitude`
- `longitude`
- `autoDetectable`
- `outOfComms`
- `holdPosition`
- `holdFire`
- `proficiency`
- `manualthrottle`
- `manualspeed`
- `manualaltitude`
- `fuel`
- `base`
- `sprintDrift`
- `avoidcavitation`
- `csar`
- `timetoready_minutes`
- `course`

Official current examples:
```lua
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5})
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5, lon ="N50.20.10"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", newname="USS Barack Obama"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", heading=0, HoldPosition=1, HoldFire=1,Proficiency="Ace", Autodetectable="yes"})
```

Generated complete example:
```lua
local updated = ScenEdit_SetUnit({
    side = 'BLUE',
    unitname = 'USS Test',
    desiredHeading = 270,
    holdPosition = false,
    holdFire = false,
    proficiency = 'Veteran',
    sprintDrift = true
})

if updated == nil then
    print('SetUnit failed: ' .. tostring(_errmsg_))
end
```

### 12.4 `ScenEdit_GetUnit(table)`
Purpose:
- retrieve a Unit wrapper for inspection

Practical pattern:
```lua
local u = ScenEdit_GetUnit({side='BLUE', unitname='USS Test'})
if u then
    print(u.name)
    print(u.guid)
    print(u.speed)
    print(u.heading)
end
```

### 12.5 `ScenEdit_GetContact(table)` and `ScenEdit_GetContacts(side)`
Current page note:
- `ScenEdit_GetContact()` is like `ScenEdit_GetUnit()` but for contacts
- contact names can change
- use `ScenEdit_GetContacts(side)` and then take the GUID you want

Official example:
```lua
local con = ScenEdit_GetContacts('south korea')
```

Generated complete example:
```lua
local contacts = ScenEdit_GetContacts('BLUE')
if contacts then
    for i, con in pairs(contacts) do
        print(i, con.name, con.guid, con.type)
    end
end
```

### 12.6 `ScenEdit_SelectedUnits()`
Official current example:
```lua
local selected = ScenEdit_SelectedUnits()
print(selected.units) -- list of selected units
```

Expanded practical example:
```lua
local selected = ScenEdit_SelectedUnits()

if selected.units then
    for i, u in pairs(selected.units) do
        print('UNIT', i, u.name, u.guid)
    end
end

if selected.contacts then
    for i, c in pairs(selected.contacts) do
        print('CONTACT', i, c.name, c.guid)
    end
end
```

### 12.7 `ScenEdit_QueryDB(objectType, DBID)`
Current page notes:
- object types currently supported: `weapon`, `mount`, `sensor`

Generated example:
```lua
local w = ScenEdit_QueryDB('weapon', 51)
if w then
    print(w.name)
    print(w.dbid)
end
```

### 12.8 `ScenEdit_AddReloadsToUnit()`
Official oldsite example:
```lua
ScenEdit_AddReloadsToUnit({unitname='Mech Inf #1', wpn_dbid=773, number=1, w_max=10})
```

### 12.9 `ScenEdit_AddWeaponToUnitMagazine()`
Official oldsite example:
```lua
ScenEdit_AddWeaponToUnitMagazine({unitname='Ammo', wpn_dbid=773, number=1, w_max=10})
```

### 12.10 `ScenEdit_AddMission(side, missionName, missionType, missionOptions)`
Current page notes:
- adds a mission to a side
- mission name should be unique across the scenario
- mission can then be adjusted through wrapper or `ScenEdit_SetMission()`

Generated complete example: Patrol
```lua
local patrol = ScenEdit_AddMission('BLUE', 'Barrier CAP', 'Patrol', {
    type = 'AAW',
    zone = {'CAP-1', 'CAP-2', 'CAP-3', 'CAP-4'}
})

if patrol == nil then
    print('AddMission failed: ' .. tostring(_errmsg_))
end
```

Generated complete example: Strike
```lua
local strike = ScenEdit_AddMission('BLUE', 'Strike East', 'Strike', {
    type = 'land'
})
```

### 12.11 `ScenEdit_SetMission(side, missionNameOrID, missionOptions)`
Current page notes:
- update only the fields that need changing
- mission object fields are valid update targets

Generated example:
```lua
local mission = ScenEdit_SetMission('BLUE', 'Barrier CAP', {
    isactive = true,
    oneThirdRule = false,
    flightSize = 2
})
```

### 12.12 `ScenEdit_AssignUnitToMission()`
Generated example:
```lua
ScenEdit_AssignUnitToMission('F-16 #1', 'Barrier CAP')
ScenEdit_AssignUnitToMission('F-16 #2', 'Barrier CAP')
```

### 12.13 `ScenEdit_AssignUnitAsTarget()` and `ScenEdit_RemoveUnitAsTarget()`
Generated example:
```lua
ScenEdit_AssignUnitAsTarget('Strike East', 'Enemy Radar Site')
-- later
ScenEdit_RemoveUnitAsTarget('Strike East', 'Enemy Radar Site')
```

### 12.14 `ScenEdit_AddReferencePoint(table)`
Current page notes:
- creates one or more reference points
- can take a single RP or a table of RPs
- at minimum requires side and either lat/lon or area definition

Generated example: single RP
```lua
local rp = ScenEdit_AddReferencePoint({
    side = 'BLUE',
    name = 'CAP-1',
    latitude = '24.9500',
    longitude = '121.9000'
})
```

Generated example: multiple RPs
```lua
ScenEdit_AddReferencePoint({
    side = 'BLUE',
    area = {
        {name='CAP-1', latitude='24.95', longitude='121.90'},
        {name='CAP-2', latitude='25.05', longitude='121.90'},
        {name='CAP-3', latitude='25.05', longitude='122.05'},
        {name='CAP-4', latitude='24.95', longitude='122.05'}
    }
})
```

### 12.15 `ScenEdit_SetReferencePoint(table)`
Current page notes:
- only include the fields you want to update
- bulk update can be done with `area`
- do not include `area` if only updating one RP

Generated example:
```lua
ScenEdit_SetReferencePoint({
    side = 'BLUE',
    name = 'CAP-1',
    highlighted = true,
    locked = false
})
```

Bulk example:
```lua
ScenEdit_SetReferencePoint({
    side = 'BLUE',
    area = {'CAP-1','CAP-2','CAP-3','CAP-4'},
    highlighted = true
})
```

### 12.16 `ScenEdit_AddZone(sideName, zoneType, table)`
Current page notes:
- creates non navigation or exclusion zone
- RPs may be hidden with `hidden=1`

Generated example:
```lua
ScenEdit_AddZone('BLUE', 'Exclusion', {
    description = 'No Entry Box',
    area = {'CAP-1','CAP-2','CAP-3','CAP-4'},
    hidden = 1
})
```

### 12.17 `ScenEdit_SetZone(sideName, zoneType, table)`
Current page notes:
- update only the values that need changing

Generated example:
```lua
ScenEdit_SetZone('BLUE', 'Exclusion', {
    description = 'No Entry Box',
    isactive = true
})
```

### 12.18 `ScenEdit_SetTrigger(table)`
Official overview notes:
- common fields: `Description`, `Mode`, `ID`
- modes: `list`, `add`, `remove`, `update`

TargetFilter notes from official overview:
- `TargetSide`
- `TargetType`
- `TargetSubType`
- `SpecificUnitClass`
- `SpecificUnitID`

Official examples:
```lua
local a = ScenEdit_SetTrigger({
    mode='add',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    targetfilter={SPECIFICUNIT='AOE 421 Sagami'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=true
})
```

```lua
local a = ScenEdit_SetTrigger({
    mode='update',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    rename='Any AOE entering hot zone',
    targetfilter={TargetSubType='5023', TargetType='2', TargetSide='sidea'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=false
})
```

```lua
local a = ScenEdit_SetTrigger({
    mode='remove',
    type='UnitEntersArea',
    name='Any AOE entering hot zone'
})
```

Generated complete example:
```lua
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
```

### 12.19 `ScenEdit_SetCondition(table)`
Official notes:
- common fields: `Description`, `Mode`, `ID`
- types shown in overview:
  - `LuaScript`
  - `ScenHasStarted`
  - `SidePosture`
- multi line script text should use `\r\n`

Official script text note:
```lua
ScriptTest='--comment\r\nif unit ~= nil then\r\n return true\r\n else\r\n return false\r\n end'
```

Official example:
```lua
local a = ScenEdit_SetCondition({
    mode='add',
    type='SidePosture',
    name='sideA hostile to sideB',
    ObserverSideId='sidea',
    TargetSideId='sideb',
    targetposture='hostile'
})
```

Generated LuaScript condition example:
```lua
local cond = ScenEdit_SetCondition({
    mode = 'add',
    type = 'LuaScript',
    name = 'at least one hostile contact exists',
    ScriptText = "local cons = ScenEdit_GetContacts('BLUE')\r\nreturn cons ~= nil and next(cons) ~= nil"
})
```

### 12.20 `ScenEdit_SetAction(table)`
Official notes:
- common fields: `Description`, `Mode`, `ID`
- types shown in overview:
  - `ChangeMissionStatus`
  - `EndScenario`
  - `LuaScript`
  - `Message`
  - `Points`
  - `TeleportInArea`

Official example:
```lua
local a = ScenEdit_SetAction({
    mode='add',
    type='Points',
    name='sideA loses some ..',
    SideId='sidea',
    PointChange=-10
})
```

Generated message example:
```lua
local act = ScenEdit_SetAction({
    mode = 'add',
    type = 'Message',
    name = 'notify blue player',
    SideID = 'BLUE',
    Text = 'Hostile task group detected to the east.'
})
```

Generated Lua action example:
```lua
local act2 = ScenEdit_SetAction({
    mode = 'add',
    type = 'LuaScript',
    name = 'spawn reinforcements',
    ScriptText = "ScenEdit_AddUnit({type='Air', unitname='Reinforcement 1', side='BLUE', dbid=3500, loadoutid=16934, latitude='25.0', longitude='121.8', altitude='5000 ft'})"
})
```

### 12.21 `ScenEdit_SetEvent(eventName, options)`
Official notes:
- use add, remove, update
- use `ScenEdit_SetEventAction/Trigger/Condition` to associate TCA items

Official example:
```lua
local a = ScenEdit_SetEvent('my new event', {mode='add'})
```

Generated example:
```lua
local ev = ScenEdit_SetEvent('Blue detection event', {
    mode = 'add',
    isactive = true,
    isrepeatable = true,
    probability = 100
})
```

### 12.22 `ScenEdit_SetEventTrigger`, `ScenEdit_SetEventCondition`, `ScenEdit_SetEventAction`
Official notes:
- `mode` values: `add`, `remove`, `replace`
- use description or GUID of the TCA

Official examples:
```lua
local a = ScenEdit_SetEventAction('test event', {mode='add', name='test action points'})
local a = ScenEdit_SetEventAction('test event', {mode='replace', name='test action message', replaceby='test action points'})
```

Generated full linking example:
```lua
ScenEdit_SetEvent('Blue detects red surface group', {mode='add'})
ScenEdit_SetEventTrigger('Blue detects red surface group', {mode='add', name='BLUE detects hostile ship'})
ScenEdit_SetEventCondition('Blue detects red surface group', {mode='add', name='sideA hostile to sideB'})
ScenEdit_SetEventAction('Blue detects red surface group', {mode='add', name='notify blue player'})
```

### 12.23 `ScenEdit_SetTime()`
Official oldsite example:
```lua
ScenEdit_SetTime({Date="2.12.2007", Time="22.46.23"})
```

Current date format example:
```lua
local m = ScenEdit_GetMission('sidea', 'test support')
print(m)
m.starttime = "2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"
print(m.starttime)
```

### 12.24 `ScenEdit_AddSpecialAction()` and `ScenEdit_SetSpecialAction()`
Purpose:
- create or modify special actions visible to a side
- multi line ScriptText uses `\r\n`

Generated example:
```lua
local sa = ScenEdit_AddSpecialAction({
    side = 'BLUE',
    name = 'Spawn CAP',
    description = 'Spawn an alert CAP at the player request',
    IsActive = true,
    IsRepeatable = false,
    ScriptText = "ScenEdit_AddUnit({type='Air', unitname='CAP Spawn', side='BLUE', dbid=3500, loadoutid=16934, latitude='25.05', longitude='121.95', altitude='12000 ft'})"
})
```

### 12.25 `ScenEdit_SetKeyValue()`, `ScenEdit_GetKeyValue()`, `ScenEdit_ClearKeyValue()`
Purpose:
- persistent simple key value state storage

Generated example:
```lua
ScenEdit_SetKeyValue('BLUE_CAP_STATE', 'launched')

local v = ScenEdit_GetKeyValue('BLUE_CAP_STATE')
print(v)

ScenEdit_ClearKeyValue('BLUE_CAP_STATE')
```

### 12.26 `ScenEdit_PlaySound()`, `ScenEdit_MsgBox()`, `ScenEdit_InputBox()`, `ScenEdit_SpecialMessage()`
Purpose:
- UI and feedback helpers
- useful for debugging, special actions, and scenario narration

Generated example:
```lua
ScenEdit_MsgBox('This is a test message')
```

### 12.27 `Command_SaveScen()` and `SetScenarioTitle()`
Purpose:
- save scenario
- set or update title

Generated example:
```lua
SetScenarioTitle('Taiwan Strait Escalation')
Command_SaveScen()
```

### 12.28 `Tool_Bearing()`, `Tool_Range()`, `Tool_LOS()`, `World_GetPointFromBearing()`, `World_GetElevation()`
Purpose:
- spatial utility functions for scripting and scenario geometry

Generated range and bearing example:
```lua
local brg = Tool_Bearing({lat='25.0', lon='121.8'}, {lat='25.2', lon='122.1'})
local rng = Tool_Range({lat='25.0', lon='121.8'}, {lat='25.2', lon='122.1'})
print(brg, rng)
```

Generated offset point example:
```lua
local pt = World_GetPointFromBearing('25.0', '121.8', 90, 25)
print(pt.latitude, pt.longitude)
```

### 12.29 `ScenEdit_QueryDB()`
Use case:
- look up weapon, mount, or sensor DB metadata while scripting

Generated example:
```lua
local sensor = ScenEdit_QueryDB('sensor', 1234)
if sensor then
    print(sensor.name)
end
```

### 12.30 `ScenEdit_AttackContact()`
Use case:
- command attack against a selected contact using `AttackOptions`

Generated example:
```lua
local contact = ScenEdit_GetContact({side='BLUE', guid='CONTACT-GUID-HERE'})
if contact then
    ScenEdit_AttackContact('BLUE UNIT GUID HERE', contact.guid, {
        mode = 0,
        weapon = 51,
        qty = 2
    })
end
```

### 12.31 `ScenEdit_SetDoctrine()` and `ScenEdit_SetDoctrineWRA()`
Use case:
- configure behavior and release policies at side, mission, or unit level

Generated example:
```lua
ScenEdit_SetDoctrine({side='BLUE'}, {use_nuclear_weapons='no', weapon_control_status_air='tight'})
ScenEdit_SetDoctrineWRA({side='BLUE', weapon_id=51, target_type='Aircraft'}, {qty_salvo=2})
```

### 12.32 `ScenEdit_SetEMCON()`
Use case:
- set emission control behavior

Generated example:
```lua
ScenEdit_SetEMCON('Unit', 'BLUE', 'E-2D #1', 'Radar=Active')
ScenEdit_SetEMCON('Unit', 'BLUE', 'E-2D #1', 'OECM=Passive')
```

### 12.33 `ScenEdit_UpdateUnit()` and `ScenEdit_UpdateUnitCargo()`
Use case:
- alter sensors, mounts, magazines, cargo, or apply deltas

Generated example:
```lua
ScenEdit_UpdateUnit({
    guid = 'UNIT-GUID',
    mode = 'add_sensor',
    dbid = 1234
})
```

### 12.34 `ScenEdit_SetSidePosture()`
Use case:
- set posture between sides

Generated example:
```lua
ScenEdit_SetSidePosture('BLUE', 'RED', 'H')
```

### 12.35 `ScenEdit_GetSideOptions()` and `ScenEdit_SetSideOptions()`
Use case:
- side awareness, proficiency, switch to side, and other side option logic

Generated example:
```lua
ScenEdit_SetSideOptions({
    side = 'BLUE',
    awareness = 'Normal',
    proficiency = 'Veteran'
})
```

### 12.36 `Tool_BuildBlankScenario()`
Use case:
- create blank scenario in newer versions

Generated example:
```lua
Tool_BuildBlankScenario('Sandbox Build Test')
SetScenarioTitle('Sandbox Build Test')
```

## 13. Official doc examples gathered in one place

This section collects the key official examples harvested from the linked docs.

### 13.1 Altitude examples
```lua
{altitude = '100 FT'}
{altitude = '100 M'}
{altitude = '100'}
```

### 13.2 Add side
```lua
ScenEdit_AddSide({name='OPFOR'})
```

### 13.3 Add unit
```lua
ScenEdit_AddUnit({type ='Aircraft', name ='F-15C Eagle', loadoutid =16934, heading =0, dbid =3500, side ='NATO', Latitude="N46.00.00",Longitude="E25.00.00", altitude="5000 ft",autodetectable="false",holdfire="true",proficiency=4})
ScenEdit_AddUnit({type ='Air', unitname ='F-15C Eagle', loadoutid =16934, dbid =3500, side ='NATO', Lat="5.123",Lon="-12.51",alt=5000})
ScenEdit_AddUnit({type ='Ship', unitname ='GOE II Det C', dbid =3127, side ='USN', latitude="5.123",longitude="-12.51",proficiency='Veteran'})
```

### 13.4 Set unit
```lua
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5})
ScenEdit_SetUnit({side="United States", unitname="USS Test", lat =5, lon ="N50.20.10"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", newname="USS Barack Obama"})
ScenEdit_SetUnit({side="United States", unitname="USS Test", heading=0, HoldPosition=1, HoldFire=1,Proficiency="Ace", Autodetectable="yes"})
```

### 13.5 Add reloads
```lua
ScenEdit_AddReloadsToUnit({unitname='Mech Inf #1', wpn_dbid=773, number=1, w_max=10})
```

### 13.6 Add weapon to magazine
```lua
ScenEdit_AddWeaponToUnitMagazine({unitname='Ammo', wpn_dbid=773, number=1, w_max=10})
```

### 13.7 Set trigger
```lua
local a = ScenEdit_SetTrigger({
    mode='add',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    targetfilter={SPECIFICUNIT='AOE 421 Sagami'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=true
})
```

```lua
local a = ScenEdit_SetTrigger({
    mode='update',
    type='UnitEntersArea',
    name='Sagami exiting hot zone',
    rename='Any AOE entering hot zone',
    targetfilter={TargetSubType = '5023',TargetType = '2',TargetSide='sidea'},
    area={'rp-1126','rp-1127','rp-1128','rp-1129'},
    exitarea=false
})
```

```lua
local a = ScenEdit_SetTrigger({mode='remove',type='UnitEntersArea',name='Any AOE entering hot zone'})
```

### 13.8 Set condition
```lua
local a = ScenEdit_SetCondition({
    mode='add',
    type='SidePosture',
    name='sideA hostile to sideB',
    ObserverSideId='sidea',
    TargetSideId='sideb',
    targetposture='hostile'
})
```

### 13.9 Condition script text formatting
```lua
ScriptTest='--comment\r\nif unit ~= nil then\r\n return true\r\n else\r\n return false\r\n end'
```

### 13.10 Set action
```lua
local a = ScenEdit_SetAction({mode='add', type='Points', name='sideA loses some ..', SideId='sidea', PointChange=-10})
```

### 13.11 Event action linking
```lua
local a = ScenEdit_SetEventAction('test event', {mode='add', name='test action points'})
local a = ScenEdit_SetEventAction('test event', {mode='replace', name='test action message', replaceby='test action points'})
```

### 13.12 Add event
```lua
local a = ScenEdit_SetEvent('my new event', {mode='add'})
```

### 13.13 Set time
```lua
ScenEdit_SetTime({Date="2.12.2007", Time="22.46.23"})
```

### 13.14 Selected units
```lua
local selected = ScenEdit_SelectedUnits()
print(selected.units)
```

### 13.15 Get contacts
```lua
local con = ScenEdit_GetContacts('south korea')
```

### 13.16 Side wrapper area query
Official oldsite example:
```lua
local u = side:unitsInArea({
    Area = {'RP-3137', 'RP-3139', 'RP-3136', 'RP-3138'},
    TargetFilter = {TargetType = 'Ship'}
})
```

### 13.17 Side wrapper filtering
Official oldsite example:
```lua
local u = side:unitsBy('Ship') -- all ships
u = side:unitsBy('Ship', 2002, 3003) -- ships filtered for subtype and class
```

### 13.18 Satellite orbit update
Official oldsite example:
```lua
theSat = ScenEdit_GetUnit({guid='56f830c1-d0e2-430a-985e-0e301cc01eff'})
theTLE = 'Resurs P1\n1 39186U 13030A 17013.12537468 .00000446 00000-0 16942-4 0 9992\n2 39186 97.3847 79.3911 0015157 247.7411 195.8488 15.31966970198820'
theSat:updateorbit({TLE=theTLE})
```

### 13.19 Date/time explicit format
```lua
local m = ScenEdit_GetMission('sidea', 'test support')
print(m)
m.starttime = "2027-06-09 1:30:00!yyyy-MM-dd HH:mm:ss"
print(m.starttime)
```

## 14. Full scenario recipes

These are full, runnable patterns built from the official function structure.

### 14.1 Recipe: build a simple blank scenario and set title
```lua
Tool_BuildBlankScenario('Test Sandbox')
SetScenarioTitle('Test Sandbox')
ScenEdit_SetTime({Date='06/09/2027', Time='01:30:00'})
```

### 14.2 Recipe: create sides and posture
```lua
ScenEdit_AddSide({name='BLUE'})
ScenEdit_AddSide({name='RED'})

ScenEdit_SetSidePosture('BLUE', 'RED', 'H')
ScenEdit_SetSidePosture('RED', 'BLUE', 'H')

ScenEdit_SetSideOptions({
    side = 'BLUE',
    awareness = 'Normal',
    proficiency = 'Veteran'
})

ScenEdit_SetSideOptions({
    side = 'RED',
    awareness = 'Normal',
    proficiency = 'Regular'
})
```

### 14.3 Recipe: create reference points and an area
```lua
ScenEdit_AddReferencePoint({
    side = 'BLUE',
    area = {
        {name='BOX-1', latitude='25.00', longitude='121.80'},
        {name='BOX-2', latitude='25.10', longitude='121.80'},
        {name='BOX-3', latitude='25.10', longitude='121.95'},
        {name='BOX-4', latitude='25.00', longitude='121.95'}
    }
})
```

### 14.4 Recipe: create a patrol mission and assign aircraft
```lua
local cap = ScenEdit_AddMission('BLUE', 'CAP NORTH', 'Patrol', {
    type = 'AAW',
    zone = {'BOX-1', 'BOX-2', 'BOX-3', 'BOX-4'}
})

ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'F-16A #1',
    side = 'BLUE',
    dbid = 3500,
    loadoutid = 16934,
    latitude = '25.02',
    longitude = '121.82',
    altitude = '12000 ft'
})

ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'F-16A #2',
    side = 'BLUE',
    dbid = 3500,
    loadoutid = 16934,
    latitude = '25.03',
    longitude = '121.83',
    altitude = '12000 ft'
})

ScenEdit_AssignUnitToMission('F-16A #1', 'CAP NORTH')
ScenEdit_AssignUnitToMission('F-16A #2', 'CAP NORTH')

ScenEdit_SetMission('BLUE', 'CAP NORTH', {
    isactive = true,
    flightSize = 2,
    oneThirdRule = false
})
```

### 14.5 Recipe: create a strike package with target mission
```lua
local strike = ScenEdit_AddMission('BLUE', 'STRIKE EAST', 'Strike', {
    type = 'land'
})

ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'Strike #1',
    side = 'BLUE',
    dbid = 3500,
    loadoutid = 16934,
    latitude = '24.95',
    longitude = '121.70',
    altitude = '15000 ft'
})

ScenEdit_AssignUnitToMission('Strike #1', 'STRIKE EAST')
ScenEdit_AssignUnitAsTarget('STRIKE EAST', 'Enemy Radar Site')
```

### 14.6 Recipe: create a detection driven event chain
```lua
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
```

### 14.7 Recipe: use KeyStore to avoid duplicate spawning
```lua
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
```

### 14.8 Recipe: event safe error handling skeleton
```lua
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
```

### 14.9 Recipe: query current contacts and attack one
```lua
local cons = ScenEdit_GetContacts('BLUE')
if cons then
    for i, con in pairs(cons) do
        if con.type == 'Ship' or con.type == 2 then
            print('Attacking contact', con.name, con.guid)
            -- replace unit guid and weapon data as needed
            ScenEdit_AttackContact('ATTACKER-UNIT-GUID', con.guid, {
                mode = 0,
                weapon = 51,
                qty = 2
            })
            break
        end
    end
end
```

## 15. Lua language support references

These are not CMO API pages, but they matter when writing valid scripts.

### 15.1 Lua Users Wiki tutorials
Recommended by the official CommandLua docs:
- Types
- Assignment
- Numbers
- Strings
- Tables
- Functions

Use these for:
- Lua variable rules
- table syntax
- loops
- functions
- string handling
- number handling

### 15.2 Lua Programming Wikibook
Use for:
- base syntax
- examples
- language reminders

### 15.3 Lua 5.3 manual
Use for:
- authoritative language behavior
- standard library
- metatables
- strings
- tables
- patterns
- math
- file I/O

### 15.4 LDoc
Use for:
- structured Lua documentation style
- documenting helper libraries if you build your own reusable CMO Lua module sets

## 16. Matrix forum relevance notes

### 16.1 Lua Legion forum
This is the main linked community source for:
- troubleshooting
- wrapper dumping tricks
- beginner examples
- scenario scripting discussions
- answers from experienced users and WarfareSims staff

Relevant topic titles visible from the linked forum index include:
- `Command lua documents`
- `LUA Resources`
- `LUA script console - hint`
- `IntelliSense for CMO via VSCode Sumneko and Emmy`
- `Dump the properties of Lua wrapper`
- `Absolute Beginner's Intro to Lua Part 1: GetWeather and SetWeather`
- `Building scenario from Lua`

### 16.2 General Command series forum
Useful as the broader series discussion area, but the dedicated Lua Legion forum is the main Lua specific source.

## 17. Practical working rules for future CMO scripting

When generating future scripts:
- treat this file as the first reference
- use current official function names and object families
- prefer GUID selection
- use `ScenEdit_Get...` to inspect and `ScenEdit_Set...` to update
- tie selectors, wrappers, and data types together rather than using guessed field names
- for event code, explicitly handle nil returns and errors
- when a current page has no real example, start from the complete examples in this file

## 18. Gaps and caveats

The linked official docs are authoritative, but some current function pages still show placeholder example text or omit deeper examples. This library fills those gaps with:
- legacy official examples
- structure from current selector / wrapper / datatype pages
- complete doc compatible scenario recipes

This makes the file more useful for actual simulation building than the raw site alone.

## 19. Future expansion targets

The next useful expansions would be:
- one page per major function with more edge cases
- doctrine and WRA field by field examples
- mission type specific recipe pages
- contact handling library by sensor and classification state
- cargo and logistics examples
- minefield, custom loss, explosion, and advanced UI examples
- Pro only import/export and fidelity control examples

## 20. Bottom line

This file is now the consolidated working library for:
- CMO specific Lua command discovery
- scenario construction
- event construction
- mission construction
- unit spawning and manipulation
- selector and wrapper lookup
- complete example driven scripting

It is intended to reduce or eliminate avoidable trial and error in future CMO Lua work.


---

# Part II: Examples and Recipes

# CMO CommandLua Examples and Recipes Library

This companion file extends the master library with example focused material.

It is intended for practical scenario creation, editing, debugging, and event scripting in Command: Modern Operations using CommandLua.

The goal is to reduce trial and error by pairing the documented API surface with runnable Lua patterns.

## 1. How to use this file

Use this file when you already know the general task:

- create or modify units
- create or modify missions
- create or modify events, triggers, conditions, and actions
- set doctrine or WRA
- create reference points and zones
- query contacts and units
- work with time, score, weather, and scenario state
- build helper utilities for larger scripts

General approach:

1. identify the scenario task
2. identify the selector or wrapper needed
3. copy the closest example
4. substitute your side names, mission names, GUIDs, DBIDs, or reference points
5. run in the console or event action context
6. if something fails, inspect `_errmsg_`, `_errfnc_`, and `_errnum_`

## 2. Base CMO Lua conventions that matter in scripts

- Lua is case sensitive
- direct wrapper property access normally uses lowercase style such as `unit.name`
- prefer GUIDs over names where precision matters
- prefer `ScenEdit_Set...()` functions over mutating wrappers directly when a setter exists
- events are built from triggers, optional conditions, and actions
- many selectors accept either a name or a GUID, but GUID is safer
- some current doc pages are brief and oldsite pages contain the fuller example patterns

## 3. Error handling pattern

Adapted from the documented error handling material and oldsite examples.

```lua
local mission = ScenEdit_AddMission('USA', 'Marker strike', 'strike', { type = 'land' })

if mission == nil then
    if _errnum_ ~= 0 then
        print('Failed to add mission: ' .. tostring(_errmsg_))
        print('Function: ' .. tostring(_errfnc_))
        print('Error number: ' .. tostring(_errnum_))
    else
        print('Mission creation returned nil without a documented CommandLua error.')
    end
else
    print('Created mission: ' .. mission.name)
end
```

## 4. Common selector patterns

### 4.1 Unit selector

```lua
local selector_by_name = {
    side = 'Blue',
    unitname = 'USS Test'
}

local selector_by_guid = {
    guid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
}
```

### 4.2 Doctrine selector

```lua
local doctrine_side = { side = 'Blue' }
local doctrine_mission = { side = 'Blue', mission = 'BARCAP North' }
local doctrine_unit = { side = 'Blue', unitname = 'Eagle #1' }
```

### 4.3 Contact selector

```lua
local contact_selector = {
    side = 'Blue',
    guid = 'contact-guid-here'
}
```

### 4.4 Reference point selector

```lua
local rp_selector = {
    side = 'Blue',
    name = 'RP 1'
}
```

### 4.5 New unit selector

```lua
local new_aircraft = {
    type = 'Aircraft',
    unitname = 'Eagle #1',
    side = 'Blue',
    dbid = 3500,
    loadoutid = 16934,
    lat = 'N46.00.00',
    lon = 'E25.00.00',
    altitude = '5000 ft',
    heading = 0,
    proficiency = 4
}
```

## 5. Unit creation and editing examples

### 5.1 Add an aircraft at a location

This is the classic documented pattern, normalized into current field naming.

```lua
local u = ScenEdit_AddUnit({
    type = 'Aircraft',
    unitname = 'F 15C Eagle #1',
    side = 'NATO',
    dbid = 3500,
    loadoutid = 16934,
    heading = 0,
    lat = 'N46.00.00',
    lon = 'E25.00.00',
    altitude = '5000 ft',
    autodetectable = 'false',
    holdfire = 'true',
    proficiency = 4
})

print(u.name)
```

### 5.2 Add an aircraft with numeric lat lon shorthand

```lua
local u = ScenEdit_AddUnit({
    type = 'Air',
    unitname = 'F 15C Eagle #2',
    side = 'NATO',
    dbid = 3500,
    loadoutid = 16934,
    lat = 5.123,
    lon = -12.51,
    alt = 5000
})
```

### 5.3 Add a ship

```lua
local ship = ScenEdit_AddUnit({
    type = 'Ship',
    unitname = 'USS Example',
    side = 'Blue',
    dbid = 52,
    lat = 'N24.45.00',
    lon = 'E054.22.00',
    heading = 90,
    proficiency = 'Regular'
})
```

### 5.4 Add a submarine

```lua
local sub = ScenEdit_AddUnit({
    type = 'Submarine',
    unitname = 'SSN Sample',
    side = 'Blue',
    dbid = 2215,
    lat = 'N24.10.00',
    lon = 'E054.00.00',
    depth = 'Periscope',
    heading = 45,
    proficiency = 'Veteran'
})
```

### 5.5 Rename a unit

```lua
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    newname = 'USS Barack Obama'
})
```

### 5.6 Change position only

```lua
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    lat = 5
})
```

### 5.7 Change position with latitude and longitude

```lua
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    lat = 5,
    lon = 'N50.20.10'
})
```

### 5.8 Change heading and tactical flags

```lua
ScenEdit_SetUnit({
    side = 'United States',
    unitname = 'USS Test',
    heading = 0,
    HoldPosition = 1,
    HoldFire = 1,
    Proficiency = 'Ace',
    Autodetectable = 'yes'
})
```

### 5.9 Move a unit to another side

```lua
ScenEdit_SetUnitSide({
    side = 'Old Side',
    name = 'Eagle #1',
    newside = 'New Side'
})
```

### 5.10 Get a unit wrapper safely

```lua
local unit = Tool_EmulateNoConsole(true)
unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
Tool_EmulateNoConsole(false)

if unit then
    print(unit.name)
    print(unit.guid)
    print(unit.latitude)
    print(unit.longitude)
end
```

### 5.11 Update from wrapper values and then commit with setter

```lua
local unit = ScenEdit_GetUnit({ side = 'Blue', unitname = 'USS Example' })
if unit then
    ScenEdit_SetUnit({
        guid = unit.guid,
        heading = 120,
        desiredSpeed = 18
    })
end
```

## 6. Magazine, loadout, refuel, and cargo examples

### 6.1 Add weapons to a magazine

```lua
local added = ScenEdit_AddWeaponToUnitMagazine({
    unitname = 'Ammo',
    wpn_dbid = 773,
    number = 1,
    w_max = 10
})

print('Added: ' .. tostring(added))
```

### 6.2 Add reloads to a unit

```lua
local ok = ScenEdit_AddReloadsToUnit({
    side = 'Blue',
    unitname = 'Eagle #1'
})

print(ok)
```

### 6.3 Set aircraft loadout

```lua
ScenEdit_SetLoadout({
    side = 'Blue',
    unitname = 'Eagle #1',
    loadoutid = 16934,
    time_to_ready_minutes = 15
})
```

### 6.4 Fill magazines for a chosen loadout pattern

```lua
ScenEdit_FillMagsForLoadout({
    side = 'Blue',
    unitname = 'Eagle #1'
})
```

### 6.5 Refuel a unit

```lua
ScenEdit_RefuelUnit({
    side = 'Blue',
    unitname = 'USS Example'
})
```

### 6.6 Transfer cargo between units

```lua
ScenEdit_TransferCargo({
    side = 'Blue',
    from = 'Transport #1',
    to = 'Airbase Alpha',
    cargo_guid = 'cargo-guid-here'
})
```

### 6.7 Unload cargo

```lua
ScenEdit_UnloadCargo({
    side = 'Blue',
    unitname = 'Transport #1',
    cargo_guid = 'cargo-guid-here'
})
```

## 7. Mission creation examples

### 7.1 Add a simple strike mission

This is the core documented example pattern.

```lua
local mission = ScenEdit_AddMission('USA', 'Marker strike', 'strike', {
    type = 'land'
})

if mission then
    print(mission.name)
end
```

### 7.2 Add a patrol mission

```lua
local mission = ScenEdit_AddMission('Blue', 'BARCAP North', 'Patrol', {
    type = 'AAW',
    Zone = { 'RP CAP 1', 'RP CAP 2', 'RP CAP 3', 'RP CAP 4' }
})
```

### 7.3 Add a support mission

```lua
local mission = ScenEdit_AddMission('Blue', 'Tanker Track', 'Support', {
    zone = { 'TK 1', 'TK 2', 'TK 3', 'TK 4' }
})
```

### 7.4 Add a ferry mission

```lua
local mission = ScenEdit_AddMission('Blue', 'Ferry to Cyprus', 'Ferry', {
    destination = 'Akrotiri'
})
```

### 7.5 Add a package or task pool category mission

```lua
local package = ScenEdit_AddMission('Blue', 'Package Alpha', 'Strike', {
    category = 1,
    type = 'land'
})

local taskpool = ScenEdit_AddMission('Blue', 'Task Pool Alpha', 'Strike', {
    category = 2,
    type = 'land'
})
```

### 7.6 Assign units to a mission

```lua
ScenEdit_AssignUnitToMission('Eagle #1', 'BARCAP North')
ScenEdit_AssignUnitToMission('Eagle #2', 'BARCAP North')
```

### 7.7 Assign a unit as a mission target

```lua
ScenEdit_AssignUnitAsTarget({
    side = 'Blue',
    mission = 'Marker strike',
    target = 'Enemy Radar Site'
})
```

### 7.8 Remove a unit as a mission target

```lua
ScenEdit_RemoveUnitAsTarget({
    side = 'Blue',
    mission = 'Marker strike',
    target = 'Enemy Radar Site'
})
```

### 7.9 Create a mission flight plan

```lua
ScenEdit_CreateMissionFlightPlan({
    side = 'Blue',
    mission = 'Marker strike',
    plan = 'Ingress Alpha'
})
```

### 7.10 Get a mission wrapper and modify it later

```lua
local mission = ScenEdit_GetMission('Blue', 'BARCAP North')
if mission then
    print(mission.name)
end
```

### 7.11 Update a mission

```lua
ScenEdit_SetMission('Blue', 'BARCAP North', {
    flightSize = 2,
    flightSizeCheck = false,
    oneThirdRule = false
})
```

### 7.12 Delete a mission

```lua
ScenEdit_DeleteMission('Blue', 'Old Mission')
```

## 8. Doctrine and WRA examples

### 8.1 Set side level doctrine

Adapted from documented examples.

```lua
ScenEdit_SetDoctrine({
    side = 'Soviet Union'
}, {
    kinematic_range_for_torpedoes = 'AutomaticAndManualFire',
    use_nuclear_weapons = 'yes'
})
```

### 8.2 Set mission level doctrine

```lua
ScenEdit_SetDoctrine({
    side = 'Soviet Union',
    mission = 'ASW PATROL'
}, {
    kinematic_range_for_torpedoes = 'AutomaticAndManualFire',
    use_nuclear_weapons = 'yes'
})
```

### 8.3 Set unit level doctrine

```lua
ScenEdit_SetDoctrine({
    side = 'Soviet Union',
    unitname = 'Bear #2'
}, {
    use_nuclear_weapons = 'yes'
})
```

### 8.4 Reset doctrine to inherit

```lua
ScenEdit_SetDoctrine({
    side = 'Blue',
    mission = 'BARCAP North'
}, {})
```

### 8.5 Read doctrine first, then update selectively

```lua
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
```

### 8.6 Set WRA for a weapon and target type

```lua
ScenEdit_SetDoctrineWRA({
    side = 'Blue',
    mission = 'BARCAP North',
    weapon_id = 51,
    target_type = 2001
}, {
    qty_salvo = 2,
    firing_range = 'max'
})
```

## 9. Reference point and zone examples

### 9.1 Add a single reference point

```lua
local rp = ScenEdit_AddReferencePoint({
    side = 'Blue',
    name = 'RP 1',
    lat = 'N25.00.00',
    lon = 'E055.00.00'
})
```

### 9.2 Add four reference points for a patrol box

```lua
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 1', lat = 'N25.10.00', lon = 'E055.00.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 2', lat = 'N25.10.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 3', lat = 'N24.50.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'RP CAP 4', lat = 'N24.50.00', lon = 'E055.00.00' })
```

### 9.3 Add a no nav zone

```lua
local zone = ScenEdit_AddZone('Blue', 'NoNav', {
    description = 'Civilian Exclusion',
    area = { 'RP CAP 1', 'RP CAP 2', 'RP CAP 3', 'RP CAP 4' },
    hidden = 1
})
```

### 9.4 Set zone attributes

```lua
ScenEdit_SetZone({
    side = 'Blue',
    description = 'Civilian Exclusion',
    isactive = true
})
```

### 9.5 Transform a zone

```lua
ScenEdit_TransformZone({
    side = 'Blue',
    description = 'Civilian Exclusion',
    scale = 1.2
})
```

### 9.6 Update a reference point

```lua
ScenEdit_SetReferencePoint({
    side = 'Blue',
    name = 'RP 1',
    lat = 'N25.05.00',
    lon = 'E055.05.00'
})
```

## 10. Contact handling examples

### 10.1 Get a known contact

```lua
local contact = ScenEdit_GetContact({
    side = 'Blue',
    guid = 'contact-guid-here'
})

if contact then
    print(contact.name)
    print(contact.posture)
end
```

### 10.2 Get all contacts for a side

```lua
local contacts = ScenEdit_GetContacts('Blue')
for i, c in ipairs(contacts) do
    print(i, c.name, c.guid)
end
```

### 10.3 Attack a contact

```lua
ScenEdit_AttackContact('Blue', 'Eagle #1', {
    mode = 0,
    contactguid = 'contact-guid-here'
})
```

### 10.4 Attack with explicit mount and weapon choice

```lua
ScenEdit_AttackContact('Blue', 'Eagle #1', {
    mode = 1,
    contactguid = 'contact-guid-here',
    mount = 12345,
    weapon = 678,
    qty = 2
})
```

## 11. Weather, time, score, and scenario examples

### 11.1 Set weather with random values

This is the classic documented weather example.

```lua
ScenEdit_SetWeather(
    math.random(0, 25),
    math.random(0, 50),
    math.random(0, 10) / 10.0,
    math.random(0, 9)
)
```

### 11.2 Get current weather

```lua
local wx = ScenEdit_GetWeather()
print(wx.temperature)
print(wx.rainfall)
print(wx.undercloud)
print(wx.seastate)
```

### 11.3 Set scenario time using date and time table

```lua
ScenEdit_SetTime({
    Date = '2.12.2007',
    Time = '22.46.23'
})
```

### 11.4 Set scenario title

```lua
SetScenarioTitle('Operation Sample Dawn')
```

### 11.5 Read current title

```lua
print(GetScenarioTitle())
```

### 11.6 Set score for a side

```lua
ScenEdit_SetScore('Blue', 250, 'Awarded for successful convoy protection')
```

### 11.7 End the scenario

```lua
ScenEdit_EndScenario()
```

## 12. Event, trigger, condition, and action examples

### 12.1 Add an event

```lua
ScenEdit_SetEvent('Spawn Enemy Raid', {
    IsActive = true,
    IsShown = true,
    IsRepeatable = false
})
```

### 12.2 Add a trigger to an event

This is the documented basic pattern.

```lua
ScenEdit_SetEventTrigger('MyEvent', {
    mode = 'add',
    description = 'MyNewTrigger'
})
```

### 12.3 Replace a condition on an event

This follows the documented example.

```lua
ScenEdit_SetEventCondition('MyEvent', {
    mode = 'replace',
    description = 'MyCondition'
})
```

### 12.4 Add an action to an event

```lua
ScenEdit_SetEventAction('MyEvent', {
    mode = 'add',
    description = 'SpawnRaidAction'
})
```

### 12.5 Execute an event action manually

```lua
ScenEdit_ExecuteEventAction('Spawn Enemy Raid', 'SpawnRaidAction')
```

### 12.6 Full event scaffold with trigger, condition, and action placeholders

```lua
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
```

### 12.7 Add a special action

```lua
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
```

### 12.8 Execute a special action

```lua
ScenEdit_ExecuteSpecialAction('Blue', 'Request Reinforcements')
```

## 13. Side level examples

### 13.1 Add a side

```lua
ScenEdit_AddSide({
    side = 'Neutral Shipping'
})
```

### 13.2 Remove a side

```lua
ScenEdit_RemoveSide('Neutral Shipping')
```

### 13.3 Set side posture

```lua
ScenEdit_SetSidePosture('Blue', 'Red', 'H')
ScenEdit_SetSidePosture('Red', 'Blue', 'H')
```

### 13.4 Get side posture

```lua
local p = ScenEdit_GetSidePosture('Blue', 'Red')
print(p)
```

### 13.5 Set side options

```lua
ScenEdit_SetSideOptions({
    side = 'Blue',
    awareness = 1,
    proficiency = 3
})
```

## 14. Minefield and explosion examples

### 14.1 Add a minefield

Adapted from the documented example.

```lua
local mf = ScenEdit_AddMinefield({
    side = 'Blue',
    dbid = 2345,
    number = 100,
    delay = 60000,
    area = { 'rp-1', 'rp-2', 'rp-3', 'rp-4' }
})
```

### 14.2 Delete a minefield

```lua
ScenEdit_DeleteMinefield({
    side = 'Blue',
    guid = 'minefield-guid-here'
})
```

### 14.3 Add an explosion

```lua
ScenEdit_AddExplosion({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    altitude = 0,
    dbid = 2100
})
```

## 15. Key store examples

### 15.1 Save a persistent key value

```lua
ScenEdit_SetKeyValue('raid_spawned', 'true')
```

### 15.2 Read a persistent key value

```lua
local value = ScenEdit_GetKeyValue('raid_spawned')
print(value)
```

### 15.3 Clear a persistent key value

```lua
ScenEdit_ClearKeyValue('raid_spawned')
```

### 15.4 Store a counter safely

```lua
local current = tonumber(ScenEdit_GetKeyValue('cap_cycles') or '0')
current = current + 1
ScenEdit_SetKeyValue('cap_cycles', tostring(current))
```

## 16. UI and message examples

### 16.1 Popup message box

```lua
ScenEdit_MsgBox('Enemy raid detected')
```

### 16.2 Input box

```lua
local answer = ScenEdit_InputBox('Enter reinforcement callsign', 'Reserve #3')
print(answer)
```

### 16.3 Special message to a side

```lua
ScenEdit_SpecialMessage('Blue', 'Enemy raid detected from the north east')
```

### 16.4 Play a sound

```lua
ScenEdit_PlaySound('alarm.wav')
```

### 16.5 Bark notification on a unit

```lua
ScenEdit_CreateBarkNotification_Unit({
    side = 'Blue',
    unitname = 'Eagle #1',
    text = 'Bandits detected'
})
```

## 17. Import and export examples

### 17.1 Import scenario from XML string

This follows the documented page closely.

```lua
local ok = ScenEdit_ImportScenarioFromXML({
    XML = '<Scenario>...a big XML string...</Scenario>'
})

print(ok)
```

### 17.2 Import scenario from XML file

The XML and filename parameters are mutually exclusive.

```lua
local ok = ScenEdit_ImportScenarioFromXML({
    filename = 'scenario_fragment.xml'
})

print(ok)
```

### 17.3 Export scenario to XML

```lua
local xml = ScenEdit_ExportScenarioToXML()
print(xml)
```

### 17.4 Export doctrine to XML

```lua
local doctrine_xml = ScenEdit_ExportDoctrineToXML({
    side = 'Blue'
})
print(doctrine_xml)
```

## 18. World and tool function examples

### 18.1 Bearing between two points

```lua
local brg = Tool_Bearing('N25.00.00', 'E055.00.00', 'N25.30.00', 'E055.20.00')
print(brg)
```

### 18.2 Range between two points

```lua
local rng = Tool_Range('N25.00.00', 'E055.00.00', 'N25.30.00', 'E055.20.00')
print(rng)
```

### 18.3 LOS between two points

```lua
local los = Tool_LOS_Points({
    observerlatitude = 'N25.00.00',
    observerlongitude = 'E055.00.00',
    targetlatitude = 'N25.30.00',
    targetlongitude = 'E055.20.00'
})
print(los)
```

### 18.4 Get point from bearing and range

```lua
local p = World_GetPointFromBearing({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    bearing = 45,
    distance = 50
})

print(p.latitude, p.longitude)
```

### 18.5 Get a circle from point

```lua
local circle = World_GetCircleFromPoint({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00',
    radius = 25,
    points = 12
})
```

### 18.6 Get elevation

```lua
local elev = World_GetElevation({
    latitude = 'N25.00.00',
    longitude = 'E055.00.00'
})
print(elev)
```

## 19. Wrapper oriented examples

### 19.1 Unit wrapper inspection

```lua
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
```

### 19.2 Contact wrapper inspection

```lua
local contact = ScenEdit_GetContact({ side = 'Blue', guid = 'contact-guid-here' })
if contact then
    print(contact.name)
    print(contact.type)
    print(contact.posture)
    print(contact.latitude)
    print(contact.longitude)
end
```

### 19.3 Mission wrapper inspection

```lua
local mission = ScenEdit_GetMission('Blue', 'BARCAP North')
if mission then
    print(mission.name)
    print(mission.type)
    print(mission.category)
end
```

### 19.4 Scenario wrapper inspection

```lua
local scen = VP_GetScenario()
print(scen.Title)
```

## 20. Scenario recipes

### 20.1 Recipe: spawn a raid package when an event fires

```lua
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
```

### 20.2 Recipe: create CAP box and patrol mission from scratch

```lua
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 1', lat = 'N25.20.00', lon = 'E054.50.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 2', lat = 'N25.20.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 3', lat = 'N24.50.00', lon = 'E055.20.00' })
ScenEdit_AddReferencePoint({ side = 'Blue', name = 'CAP 4', lat = 'N24.50.00', lon = 'E054.50.00' })

ScenEdit_AddMission('Blue', 'Northern CAP', 'Patrol', {
    type = 'AAW',
    Zone = { 'CAP 1', 'CAP 2', 'CAP 3', 'CAP 4' }
})

ScenEdit_AssignUnitToMission('Eagle #1', 'Northern CAP')
ScenEdit_AssignUnitToMission('Eagle #2', 'Northern CAP')

ScenEdit_SetDoctrine({ side = 'Blue', mission = 'Northern CAP' }, {
    weapon_control_status_air = 0,
    engage_opportunity_targets = 'true'
})
```

### 20.3 Recipe: persist a one time spawn with key store

```lua
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
```

### 20.4 Recipe: dynamic weather randomization at scenario start

```lua
math.randomseed(os.time())

ScenEdit_SetWeather(
    math.random(10, 35),
    math.random(0, 20),
    math.random(0, 10) / 10.0,
    math.random(0, 5)
)
```

### 20.5 Recipe: build a blank scenario then add sides and seed units

```lua
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
```

## 21. Helper utilities

### 21.1 Find a unit by name and return its GUID

```lua
function get_unit_guid(side_name, unit_name)
    local unit = ScenEdit_GetUnit({ side = side_name, unitname = unit_name })
    if unit then
        return unit.guid
    end
    return nil
end
```

### 21.2 Safe print of CommandLua error state

```lua
function print_last_commandlua_error()
    print('Function: ' .. tostring(_errfnc_))
    print('Message: ' .. tostring(_errmsg_))
    print('Number: ' .. tostring(_errnum_))
end
```

### 21.3 Require a unit wrapper or raise a descriptive message

```lua
function require_unit(side_name, unit_name)
    local unit = ScenEdit_GetUnit({ side = side_name, unitname = unit_name })
    if not unit then
        error('Unit not found: ' .. tostring(side_name) .. ' / ' .. tostring(unit_name))
    end
    return unit
end
```

## 22. Practical notes on examples in the official docs

- some current function pages give parameters but little or no example code
- some current event related pages include only a minimal add or replace sample
- many of the older oldsite pages still preserve short but very useful example calls
- therefore this file keeps the official patterns where they exist and extends them into fuller scenario oriented recipes

## 23. Suggested workflow for future scenario generation

For future CMO Lua scripting work, use this order:

1. `cmo_commandlua_master_library.md` for structure, catalog, selectors, wrappers, tables, and data types
2. this examples file for ready patterns and script scaffolds
3. only then go to live documentation if a build specific edge case or newly added function needs confirmation

## 24. Future expansion targets

The next useful expansion would be:

- a function by function example appendix for every major `ScenEdit_*` page
- doctrine and WRA value matrix examples
- event XML examples for common trigger and action types
- cargo and facility breakup buildup examples
- package and task pool mission patterns
- Pro only batch automation examples

