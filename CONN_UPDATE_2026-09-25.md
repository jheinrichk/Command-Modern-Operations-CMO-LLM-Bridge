# CONN UPDATE 2026-09-25: the reprint loop

## What happened on the night of 24 to 25 September

The session log (`C:\CMOBridge\SESSIONS\2026-09-25_003344_design`) shows it:

    00:34:02  click step 6 LLM submit
    00:34:03  step 1 of 6: copy the reply
    00:34:08  clipboard did not change after the copy click
    00:34:14  copy rejected (empty clipboard), retry 1 of 4
    00:34:16  paste reprint (3677 chars)

1. **CONN never waited for the reply.** The 2026-09-07 package shipped with
   `timing.llm_output_wait_seconds` set to 0. So were the reprint
   wait, the CMO wait and the sim settle time. The smoke tests set those to 0
   for speed. `ConnApp()` saved them into the real `bridge_config.json`
   and that file went into the zip. The same leak set `bridge.max_cycles` to 2
   and `play.turn_cap` to 1. So CONN copied one second after sending.
2. **An empty copy was treated as a bad code block.** Each one sent a
   "Reprint the corrected Lua code block" prompt, four per cycle. A new cycle
   started after the fourth. That was the loop.
3. **Abort was slow.** With a 0-second wait there was no checkpoint between
   steps, so after Ctrl+Alt+X one more reprint was pasted before it stopped.
4. **Wrong chat.** CONN pastes into whatever LLM tab is in front of the
   calibrated anchors. It had no way to tell one chat from another.
5. **The Play tab clock control did nothing.** `set_clock_state` had landed
   on the Actuator class instead of the Engine, so the "CMO clock right now"
   radio raised an error.

## What changed

**Reply wait (engine.py).** After sending, CONN waits
`timing.llm_min_wait_seconds` (15 s), then copies the reply every
`timing.llm_reply_poll_seconds` (8 s). The reply is finished when the copy
is valid Lua with `NEXT_RECOMMENDED_STATE` (or `BRIDGE_DONE` / `BRIDGE_HALT`)
at its end or when two copies in a row match. The longest wait is
`timing.llm_output_wait_seconds`, now 300 s. A reply is picked up within
about 15 s of finishing. A slow one still gets up to 5 minutes.

**Stops instead of loops.**
- Nothing copied by the end of the wait: the run stops with a message. No
  reprint, because a reprint cannot fix a chat that never answered or a copy
  anchor that lands on nothing.
- The prompt copied instead of the reply: the run stops.
- A broken code block (syntax, no Lua, unknown CMO symbol): at most
  `timing.llm_max_reprints` (2) reprint requests, then the run stops.
- Every stop shows a warning box and a red RUN HALTED line in the log. The
  session is exported.

**Abort.** Every click, key, paste and upload wait checks Abort first, so
Ctrl+Alt+X stops the next input. A stale abort flag never blocks clicks while
no run is going.

**LLM tab guard.** Before every paste CONN reads the title of the window
under the LLM input anchor and logs it ("LLM tab under the input: ...").
- Settings > LLM chat > "LLM tab must contain": when set, a tab whose
  title does not contain the text stops the run before anything is pasted.
- Settings > "Stop if the LLM tab changes during a run" (on): after the
  first good reply the chat title is locked. A different chat in front stops
  the run. "New chat" and bare "LLM" titles never lock.

**Config self-heal (config.py).** On load, a config with
`llm_output_wait_seconds` at 0 is recognised as the leaked test values and
restored: reply wait 300, reprint wait 60, copy retry wait 40, CMO wait 20, sim
settle 1.0, cycle budget 500, turn cap 40. Deliberate settings are left alone.
The log shows "config migrated: ..." once.

**Tests.** The smoke tests now run against a temporary copy of the config
(`CONN_CONFIG_PATH`) and can no longer write to the real one. New tests cover
streaming replies, the empty-copy halt, the two-reprint cap, prompt echo, a
halted design run sending exactly one prompt, the tab guard, abort on every
input and the config heal. All checks pass. `bridge_config.json` and
`knowledge_pack/cmo_environment_symbols.json` hash the same before and after
a full test run.

**Settings tab.** "LLM wait" and "Copy retries" are replaced by "First look
at the reply after (s)", "Check the reply every (s)", "Longest wait for a reply
(s)" and "Reprint requests before stopping".

## Install

This zip has **no bridge_config.json**, so your calibration and layouts stay.
Extract it to `C:\Users\USER\Desktop\CMO_LLM_Bridge`, the same place as
before. Choose "Replace the files in the destination" when Windows asks.
It lands in the inner `CMO_LLM_Bridge` folder that holds `conn_ui.py`. On
first start the log shows the migrated values.
