# Scenario Development Workflow

[[Home]] · [[CONN Interface|CONN-Interface]] · [[Knowledge Pack and RAG|Knowledge-Pack-and-RAG]]

## Purpose

The bridge is designed for **closed-loop scenario authoring**, with the human responsible for the intent, historical/fictional premise, mission design and acceptance criteria. The LLM provides Lua implementation and iterative diagnosis. CONN transfers instructions to CMO and returns actual console/simulation results.

```text
PROMPT → [AUDIT or DESIGN] → DEPLOY → TEST → EVALUATE
                                              │
                           satisfactory → REPORT → DONE
                                              │
                           changes needed → REFINE → RETEST ─┘
```

The current CONN engine also uses a **FIX_ERRORS** repair path rather than letting a failed Lua step silently terminate the whole task.

## A strong scenario request

Specify the theater and date, database version, playable sides, initial units and mission objectives, air/naval/land/space event timelines, desired player choices, scoring, end conditions and acceptable test criteria. For an existing scenario, choose AUDIT and explain what should be preserved.

Example:

> Audit the loaded scenario first. Confirm the playable sides and key-value state. Add a three-stage diplomatic decision sequence with explicit cancellation paths. Test each outcome and print a concise state report. Do not change unrelated units or missions.

## Stage behavior

**AUDIT** runs the bundled `CMO_BRIDGE_INSPECT.lua` as an opening read rather than asking the model to generate its own initial scenario inspection. This helps avoid accidental rebuilding of an existing scenario.

**DESIGN** derives a first build script from the user request and local retrieval context.

**DEPLOY** checks the script and executes it through CMO. It records what ran and what was printed.

**TEST** advances the clock for a bounded interval, with a directive such as `BRIDGE_CONTROL: COMPRESS=15; RUNFOR=300` where supported, and captures simulation output.

**EVALUATE** looks at observed state: missions, triggers, losses, scoring, time progression, failures and unexpected side effects.

**REFINE / RETEST** applies targeted changes and repeats comparable checks. Preserve known-good state, make small, observable changes and avoid exhaustive collectors when a narrower query can prove a result.

**REPORT** summarizes what was built, what was actually tested, outstanding limitations and session files.

## Simulation directives

A response can include a `BRIDGE_CONTROL:` line with operations `PLAY`, `PAUSE`, `START`, `RESET`, `RELOAD`, `COMPRESS=n` or `RUNFOR=seconds`. Exact available functions depend on the CMO edition. Some `VP_*` simulation-control calls are Professional Edition functions; CONN uses calibrated UI controls where these are absent.

## Reliable Lua exchange

CONN surrounds each script with unique output markers and extracts the matching response. It filters stale console text; the actual console output determines whether a script progressed. An error without a subsequent state print moves to repair. Only a `BRIDGE_DONE` or `BRIDGE_HALT` actually printed from the console should decide completion or halt.

A model-generated script that *contains* the string `BRIDGE_DONE` but never executes it is not a valid proof of success.

## Working standards

- Check source truth in CMO before changing units, events or missions.
- Use existing scenario GUIDs when updating existing objects.
- Resolve exact DBIDs and loadout relationships from local extracted database tables.
- Keep changes limited to the requested scope.
- Test event branches, negative outcomes and cancellation paths, not just the happy path.
- Look for performance regressions from per-second/per-minute Lua event scans.
- Keep an unmodified scenario master; export finished versions separately.
- Treat final scripts and report as inspectable deliverables, not as proof of accuracy without simulation evidence.

## Output files

Under each `SESSIONS` run directory:

```text
events.jsonl
transcript.md
scripts/
diff.md
report.md
```

See [docs/WORKFLOW.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/WORKFLOW.md) and the more recent [docs/CONN.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/CONN.md), which supplies the current error-handling and stop contract.
