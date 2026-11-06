# Knowledge Pack and RAG

[[Home]] · [[Scenario Development Workflow|Scenario-Development-Workflow]] · [[Architecture]]

## Why local grounding matters

CommandLua has specialized function names, argument shapes, runtime wrappers, scenario objects and version-dependent behavior. Invented API symbols or DBIDs often produce plausible-looking Lua that fails, or worse, a script that changes the wrong object.

CMO Bridge includes a local, searchable **knowledge pack** to steer the model toward documented calls, tested recipes and actual database identities.

## Repository content

| Component | Purpose |
| --- | --- |
| `knowledge_pack/cmo_bridge_master_reference_v4.md` | Consolidated CommandLua reference |
| `knowledge_pack/CMO_BRIDGE_SYSTEM_PROMPT.txt` | Operating contract for the bridge agent |
| `knowledge_pack/CMO_BRIDGE_TERMINAL_PROTOCOL.md` | Input/output and terminal conventions |
| `knowledge_pack/cmo_known_api_index.json` | API symbol allowlist reference |
| `knowledge_pack/cmo_environment_symbols.json` | Symbols observed in the author's CMO environment |
| `knowledge_pack/CMO_LUA_SESSION_RAG.md` | Session-derived lessons and retractions |
| `knowledge_pack/CMO_PINNED_RULES.txt` | Short rules injected in every cycle |
| `knowledge_pack/CMO_BRIDGE_INSPECT.lua` | Known-good initial audit |
| `knowledge_pack/dbid_extractor/` | Utilities to extract authoritative database IDs |
| `lua_unified/` | Unified recipes, lookups and topic-organized snippets |
| `cmo_rag.py` | Search, index building and learned-note handling |

## Rebuild, search and verify

```powershell
python cmo_rag.py --build
python cmo_rag.py --query "create a strike mission with event triggers"
python cmo_rag.py --lookup "F-15C Eagle"
python cmo_rag.py --lesson "Confirmed Lua behavior observed during a run"
```

The RAG is local; it does not require the LLM to browse the internet during scenario work.

## DBIDs and loadouts

Name/type lookups are **not** proof of the numeric ID needed by a specific database build. The repository includes SQL extraction tools and DB515-oriented lookup material; if a scenario targets a different database, extract and verify IDs from that installation/version. Platform operator, service, version and associated loadout are separate checks.

The CMO API symbol guard rejects unknown CommandLua-looking symbols before injection unless the configuration explicitly extends or softens the rule. This is a protection against hallucinated functions, not a universal proof of semantic correctness.

## Session learning

When scripts or console output contain supported `RAG_NOTE:` lines or designated `rag_` key-value entries, the bridge can harvest those observations into a local lessons file. Duplicates are skipped. Lessons must remain distinguishable from untested guesses, and mistaken findings should be corrected rather than allowed to contaminate retrieval.

## Runtime pitfalls captured by the pack

- Some CMO API functions appear as callable userdata rather than Lua values whose `type` is `function`.
- Standard Lua facilities such as `io`, `require` or `load` may be unavailable in the restricted console.
- Getters return runtime objects; do not assume sides and units are plain strings.
- The environment does **not** expose every intuitive `ScenEdit_*` name; use the verified index.
- Console suppression can hide all print feedback. The guard neutralizes known offending `Tool_EmulateNoConsole(true)` lines.
- Reliable inspection should report confirmed state, not inferred object existence.

More: [knowledge_pack/README.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/knowledge_pack/README.md).
