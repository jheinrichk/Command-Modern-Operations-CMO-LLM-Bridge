# CMO LLM Bridge — scenario design workflow

The bridge turns a plain-language scenario request into a designed, tested,
refined scenario through a single automated loop, then hands the finished
scenario off for head-to-head PBEM play.

## The loop

```
        user scenario prompt
                 |
                 v
   +----------------------------+
   |          DESIGN            |  LLM writes the first build script,
   |  (RAG-grounded build Lua)  |  grounded ONLY by the local unified library.
   +----------------------------+
                 |
                 v
   +----------------------------+
   |          DEPLOY            |  Bridge injects the Lua into the CMO console,
   |  (execute + verify build)  |  handles popups, captures console output.
   +----------------------------+
                 |
                 v
   +----------------------------+
   |           TEST             |  Bridge advances a test window:
   |  play + time-compression   |  BRIDGE_CONTROL: COMPRESS=15; RUNFOR=300
   |  then pause + capture       |  (deterministic Lua path, UI-click fallback).
   +----------------------------+
                 |
                 v
   +----------------------------+
   |         EVALUATE           |  LLM reads post-run output and judges
   |  (metrics, balance, verdict)|  balance, triggers, losses, score deltas.
   +----------------------------+
              /        \
     acceptable        needs work
          |                 |
          v                 v
     +---------+      +----------------------------+
     | REPORT  |      |          REFINE            | targeted patch (forces,
     +---------+      |  (patch + optional RESET)  | doctrine, WRA, timing).
          |          +----------------------------+
          v                 |
        DONE                v
                     +----------------------------+
                     |          RETEST            | re-run the window, print
                     |  (re-run + compare metrics)|  comparable metrics.
                     +----------------------------+
                                 |
                                 v
                            back to EVALUATE
```

Transitions are driven by LLM's `NEXT_RECOMMENDED_STATE:` line each cycle.
If LLM does not name one, the bridge advances in the linear order above.
Any `ERROR` in the CMO output keeps the loop on `DEPLOY` so LLM fixes it in
place. `FIX_ERRORS`, `REPORT`, and `DONE` are stopping states.

## Simulation control in any cycle

LLM can drive the clock from inside its own output by adding one line:

```
BRIDGE_CONTROL: RESET; COMPRESS=15; RUNFOR=300; PAUSE
```

Recognized ops: `PLAY`, `START`, `PAUSE`, `COMPRESS=<n>`, `RUNFOR=<seconds>`,
`RESET`, `RELOAD`.

Two execution paths, chosen automatically:

- **Lua path (preferred):** injects `AGENT_*` helpers and calls
  `VP_RunSimulation`, `VP_PauseSimulation`, `VP_SetTimeCompression`,
  `VP_RunForTimeAndHalt`. Exact windows on Professional Edition.
- **UI-click path (fallback):** clicks calibrated `cmo_play`, `cmo_pause`,
  `cmo_time_comp_up/down`, `cmo_scenario_start/reset/reload`. Works in every
  edition and whenever a `VP_` global is unavailable.

Reset of a **generated** sandbox rebuilds a blank via `Tool_BuildBlankScenario`.
Reset/reload of a **saved** `.scen` is UI-only, because CommandLua cannot reload
a save file from inside the running instance.

## Grounding (no online search)

Every prompt to LLM carries a `RETRIEVED CMO CONTEXT` block assembled by
`cmo_rag.py` from the local unified library: the top recipes and reference
notes for the current task, plus exact platform names from the 18,744-record
lookup layer. The contract tells LLM to use only that context and never to
invent functions or search online.

## IKE PBEM handoff (play to win)

IKE is musurca's third-party PBEM/hotseat framework for CMO
(github.com/musurca/IKE). It converts any finished scenario into a WEGO
turn-based multiplayer game by injecting its Lua into an event action: you
paste the IKE conversion block into the CMO Lua Script Console, click RUN, and
answer its pop-up questions (sides, turn order, turn length — fixed or
Harpoon-style variable, an optional Setup Phase, and per-player passwords).
Play then proceeds by exchanging `.save` files; IKE tracks turn order and
length, auto-stops the clock when a turn ends, and summarizes losses and
messages from the last turn. It supports Continuous and Limited-Order modes.

When the loop reaches `DONE` with `pbem_enabled = true`, the bridge:

1. Injects the IKE conversion Lua from `pbem.ike_conversion_lua_path` to make
   the finalized scenario PBEM-ready. IKE then asks its conversion questions;
   unless pre-answered, a human completes that dialog once and saves.
2. Plays turns to win. Each turn: enter the side password; (Setup Phase, if
   enabled) set loadouts/missions/EMCON; read the situation with
   `VP_`/`ScenEdit_` getters plus RAG doctrine; give orders that maximize own
   score and deny the opponent (in Limited-Order mode, plan phases ahead).
3. End the turn — IKE auto-stops the clock and prints the turn summary — then
   save the `.save` file into `pbem.save_exchange_folder`.
4. Send the `.save` to the opponent; on their returned file, load it, read
   IKE's summary, evaluate deltas, adapt, and repeat.

IKE is not bundled here. Download the Scenario Author Pack from
`pbem.ike_release`, point `pbem.ike_conversion_lua_path` at the conversion Lua,
enable `bridge.pbem_enabled`, and calibrate the save/load and IKE end-turn UI
points before turn-based play. The objective in PBEM mode is to win, not merely
to run the scenario.
