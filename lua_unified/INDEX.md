# CMO Lua Unified — folder index

This folder is the canonical local CommandLua library for CMO scenario design
and testing. The bridge and the RAG reach for these items instead of searching
online. Treat it as the single source of truth for CMO Lua work.

## Primary references

| File | What it is |
|---|---|
| `cmo_comprehensive_unified_library_v3.md` | 3,861-line CommandLua master reference: data types, selectors, wrappers, function catalog, detailed function notes, and 194 example/recipe blocks. Sections 11.10/11.11 list simulation-control and Pro-only functions. |
| `cmo_lookup_library_all_v2.lua` | Lua module: all 18,744 records (Aircraft, Facility, Mount, Sensor, Ship, Submarine, Weapon) with `lookup`, `lookup_exact`, `lookup_key`, `get_type`, `normalize`, `count`. |
| `cmo_lookup_library_platforms_v2.lua` | Lua module: platform-focused subset with the same lookup API. |
| `cmo_lookup_library_clean_v2.csv` | Flat lookup table: `Name, Type, Cost, Key` for all 18,744 records. Source for the Python RAG lookup layer. |

## Extracted snippets (`snippets/`)

Auto-generated from the master reference by `_extract_snippets.py`. Grouped by
topic so both a human and the RAG can reach a pattern fast.

| File | Blocks | Notes |
|---|---|---|
| `_sim_control_authoritative.lua` | hand-authored | Canonical play / pause / time-compression / run-window / scenario-lifecycle `AGENT_*` helpers the bridge injects. Guarded with `pcall` and edition fallbacks. |
| `all_recipes.lua` | 194 | Every extracted block, topic-tagged. |
| `sim_control.lua` | 16 | Time/scenario setup blocks from the reference. |
| `units.lua` | 33 | Add/edit units, positions, sides. |
| `missions.lua` | 17 | Strike/patrol/support/ferry, assignment. |
| `events.lua` | 31 | Triggers, conditions, actions, scaffolds. |
| `loadout_cargo.lua` | 12 | Magazines, loadouts, refuel, cargo. |
| `doctrine.lua` | 11 | Side/mission/unit doctrine and WRA. |
| `scenario_state.lua` | 9 | Weather, time, score, title, end. |
| `refpoints_zones.lua` | 8 | Reference points and zones. |
| `world_tools.lua` | 8 | Bearing, range, LOS, elevation, circle. |
| `contacts.lua` | 7 | Contact get/attack patterns. |
| `ui_messages.lua` | 6 | Msg/input boxes, sound, bark. |
| `keystore.lua` | 4 | Persistent key/value patterns. |
| `minefield.lua` | 3 | Minefields and explosions. |
| `helpers.lua` | 1 | GUID lookup / error-print / require helpers. |
| `misc.lua` | 28 | Everything else (add-side, imports, wrapper notes). |
| `recipe_manifest.json` | 194 | Structured records (heading, section, topic, code) consumed by the RAG. |

## Regeneration

If the master reference is updated, re-extract snippets and rebuild the RAG:

```
python lua_unified/_extract_snippets.py
python cmo_rag.py --build
```

## Coverage summary (from the master reference)

Total lookup records: 18,744 — Aircraft 2,578, Facility 2,029, Mount 2,408,
Sensor 5,643, Ship 2,191, Submarine 325, Weapon 3,570.

Known gap (carried from v3 audit): authoritative DBIDs, loadout IDs, and
per-record GUIDs are not yet in the lookup layer. Resolve DBIDs at runtime
with `ScenEdit_QueryDB` / unit wrappers before placing units; store resolved
GUIDs in the keystore.
