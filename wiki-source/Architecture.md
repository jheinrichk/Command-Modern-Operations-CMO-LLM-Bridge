# Architecture and Repository Map

[[Home]] · [[Knowledge Pack and RAG|Knowledge-Pack-and-RAG]] · [[Automation and Safety|Automation-and-Safety]]

## Main runtime

CONN couples a Tkinter desktop UI to a control engine that uses calibrated GUI actions to exchange instructions and terminal output between an LLM chat and Command: Modern Operations.

```text
LLM chat UI
    ↕ copy / submit anchors
CONN window manager + clipboard / attachment router
    ↕ guarded execution
CMO Lua Script Console
    ↕ actual Lua output and sim state
CONN engine → monitor + session log → RAG / LLM prompt
```

## Files and modules

| Path | Responsibility |
| --- | --- |
| `conn.py` | Main application launch entry point |
| `conn_ui.py` | Alternate launcher |
| `conn/app.py` | Main Tkinter control panel |
| `conn/engine.py` | Automation cycle and stages |
| `conn/turnengine.py` | Human/model turn state machine |
| `conn/agents.py` | Commander profiles and prompts |
| `conn/winmgr.py` | Window identification and tracking |
| `conn/anchors.py` | Calibration and window-relative coordinates |
| `conn/layouts.py` | Stored screen layouts |
| `conn/preflight.py` | Dependency and calibration checks |
| `conn/monitor.py` | Live status and session monitor |
| `conn/luacheck.py` / `conn/apiguard.py` | Lua and CMO API checks |
| `conn/clipio.py` | Clipboard and attachment handling |
| `conn/ike.py` | IKE snapshot/convert/verify workflow |
| `conn/session.py` | Artifacts, log, transcript, diffs |
| `cmo_rag.py` | Local information retrieval |
| `cmo_sim_control.py` | Lua and UI based simulation control |
| `knowledge_pack/` | Protocol, verified symbols, DBID data and session lessons |
| `lua_unified/` | Main Lua reference and extracted snippets |
| `tests_conn_smoke.py` | Headless test suite |

The older command-line route remains available as `cmo_lua_llm_bridge_main.py` and reads the same configuration family.

## Important directories

**`docs/`** contains the authoritative CONN operation, first-time setup and design-loop documentation.

**`data/`** contains supporting database packages, including a packaged DB515 lookup archive. Database identities must match the particular installation and CMO database version.

**`SESSIONS/`** is generated during execution and contains run-specific traces; user-specific session records should not be committed indiscriminately.

## Working with the project

Review and test changes to generated Lua before moving to a production scenario. A scenario's installed DB and simulation edition affect what is callable and what IDs are valid. Changes to calibration should preserve local settings rather than replacing a user's saved coordinates.

## Further reading

- [README.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/README.md)
- [docs/CONN.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/CONN.md)
- [docs/SETUP.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/SETUP.md)
- [knowledge_pack/README.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/knowledge_pack/README.md)
