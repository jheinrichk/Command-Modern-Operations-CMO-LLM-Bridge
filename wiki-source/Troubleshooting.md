# Troubleshooting and FAQ

[[Home]] · [[Getting Started|Getting-Started]] · [[Automation and Safety|Automation-and-Safety]]

## CONN cannot find the chat, CMO or Lua console

Verify that all windows are open and not minimized. Refresh the Layout window list. Adjust the chat title regex to the actual browser/tab title and check the extra *LLM tab must contain* guard. Do not relax window matching indiscriminately: a similarly titled browser page must never be mistaken for CMO.

## Lua gets pasted into the wrong window

This is a calibration or window-identification failure. Turn Dry Run on, inspect the overlay, confirm `cmo_lua_input` and `cmo_execute` bind to `cmo_lua` and rerun Preflight. Move CONN away from any target it obscures.

## The LLM response never gets copied

Ensure the last Lua response has a visible code block with a working Copy button. Recalibrate `llm_code_copy` after browser zoom or UI layout changes. The preferred path copies the code block, not the whole browser page. Check the configured scroll and retry behavior.

## Output contains earlier scripts or a misleading DONE message

The current engine isolates transactions with unique begin/end markers. A terminal directive counts only when **printed by CMO**. Read the current session transcript for the actual returned block. Older bridges may suffer from stale result-pane reads; update to current source.

## The script fails or the API name is not recognized

Use the error text, check the local symbol index and verify whether the function exists in your CMO edition. Avoid guessing `ScenEdit_*` names. If the database ID or aircraft loadout is suspect, regenerate the lookup against the matching installed CMO database.

## A script freezes near the end of each simulated minute

Review every per-second/per-minute event and watchdog. Re-reading whole unit/contact collections on every tick can be expensive. Reduce repeated collectors, cache stable identifiers where safe and test script performance in a disposable scenario. The author's [Hormuz forum thread](https://forums.matrixgames.com/viewtopic.php?t=418898) documents a real iteration of this problem.

## File attachments do not arrive in the chat

The default Ctrl+U attachment route varies between browsers. Configure the actual supported attach method and calibrate attach controls if needed. The bridge can chunk-paste large prompts as a fallback; a raw local path in chat is not an attachment.

## Play mode stops after one turn or repeats forever

Review turn completion criteria, session state, order budget, stale-copy checks, model output wait, and cycle limit. Use the current code and [September 26 update notes](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/CONN_UPDATE_2026-09-26.md), which document fixes to old wait, stop and turn behavior.

## Does it connect directly to ChatGPT, Claude or another provider?

No direct provider API integration is documented in this version. CONN operates an existing LLM chat interface using calibrated screen actions and clipboard/attachment workflows.

## Is an internet connection required?

The local RAG and CMO automation use local files. The selected LLM chat interface may require a network connection. CONN itself is not an offline LLM model.

## Is IKE included?

No. Install [musurca/IKE](https://github.com/musurca/IKE) separately for modes requiring its PBEM and conversion features.

## Do I need CONN to play Orbittoblast or the other Workshop releases?

No. The author publishes CMO scenarios separately through Steam Workshop. CONN assists with developing and testing them.

## Where are logs and scripts?

Look for the run's folder under `SESSIONS`. The transcript, `scripts/`, `diff.md`, `events.jsonl` and `report.md` make it possible to inspect what actually happened.

## What should I report when opening an issue?

Include operating system, CMO edition/database, CONN commit/version, mode, whether Dry Run was enabled, exact preflight failure or error text and a **sanitized** portion of the session transcript. Exclude passwords, private paths and unrelated personal data.

Issues: [GitHub Issues](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/issues).
