# CMO Bridge Knowledge Pack v4

Use this package as the bridge's local knowledge base.

## Start here
1. Load `CMO_BRIDGE_SYSTEM_PROMPT.txt` as the bridge agent instructions.
2. Make `cmo_bridge_master_reference_v4.md` and `cmo_known_api_index.json` searchable by the LLM.
3. Keep the Lua/CSV lookup files available for exact class-name and type lookup.
4. Generate authoritative DBID/loadout modules from the installed CMO SQLite DB with `build_cmo_dbid_lookups.py`.
5. Run `cmo_lua_command_guard.py` against candidate Lua before sending it to CMO.
6. Use `CMO_BRIDGE_INSPECT.lua` for machine-readable scenario inspection.

## Local command index
174 CMO-specific API symbols were extracted from the existing comprehensive library.

## Remaining database limitation
The included name/type lookup files are not authoritative DBID sources. The SQLite extractor is included so the installed CMO database can become the authoritative local ID source.


## Session knowledge (added 2026-09-07)

`CMO_LUA_SESSION_RAG.md` is what the bridge learned by RUNNING scenarios on
CMO v1.09 / DB3000 v515: 46 findings across doctrine, posture, missions,
movement, events, prompts, time, the API surface, database identifiers and
process. Every entry was observed in play; retractions of wrong hypotheses are
recorded too. The RAG indexes it as `lesson` documents, which outrank the
reference in retrieval because they were seen on this build.

`CMO_PINNED_RULES.txt` is the short subset injected into EVERY cycle regardless
of what the task says. Edit it when a new rule earns its place.

`db515/` carries the corrected v515 catalog: type-namespaced DBIDs with operator
country and service, and the aircraft-to-loadout relation. The engine validates
every unit row in a script against it before injection and reports wrong-nation,
hypothetical, deprecated and unpaired-loadout entries as non-blocking warnings.

The bridge learns as it runs. Any `RAG_NOTE: ...` line in a script or its
console output, and any `ScenEdit_SetKeyValue("rag_...", "...")` write, is
harvested into `rag_index/lessons.jsonl` and becomes retrievable in the next
cycle. Duplicates are ignored. From the command line:

    python cmo_rag.py --lesson "text"            add a lesson by hand
    python cmo_rag.py --harvest some_script.lua   harvest from a file
    python cmo_rag.py --platform "P-8A Poseidon" --ptype Aircraft
    python cmo_rag.py --validate HORMUZ_2026_BUILD_ALL.lua
