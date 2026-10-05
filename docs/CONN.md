# CONN

The control surface for the CMO LLM Bridge. It replaces the console window
and the separate calibration tool with one application.

```
python conn.py
```

Requires Windows for window control and input, plus `pyautogui` and
`pyperclip`. The UI itself is Tkinter, so there is nothing else to install.

---

## 1. Dry run

The toggle sits in the header and it is the first thing to check. When it is
on:

- no click, key or paste is ever synthesized
- no Lua is injected into the CMO console
- the loop still runs, using stub replies, so the sequence can be rehearsed
- the entire window turns amber and the title shows `[DRY RUN]`

Turning it off during a run asks for confirmation. The colour change is the
point: there is no way to be in live mode and think you are not.

---

## 2. Modes

| Mode | Who acts | Needs IKE |
|---|---|---|
| Scenario Development | LLM designs, deploys, tests, refines, reports | no |
| Normal Play | you play, CONN only monitors and never injects | no |
| Player vs LLM | you hold one side, a commander agent holds the other | yes |
| LLM vs LLM | two commander agents alternate under an arbiter | yes |
| Head to Head PBEM | turns arrive and leave as .save files | yes |

All four play modes share one turn state machine:

```
AWAIT_TURN -> SITREP -> ORDERS -> ARBITER -> INJECT -> END_TURN -> HANDOFF
```

Only the source of the orders changes. Human turns hold at a gate until you
press Step, so nothing advances while you are still giving orders.

Commander profiles live on the Play tab: objectives, rules of engagement,
persona and an order budget per turn. Each LLM turn starts with a read-only
SITREP script so the commander reasons from console output rather than from
assumptions.

---

## 3. Calibration

Anchors are stored inside a window, not on the screen:

```json
"cmo_execute": {"window": "cmo_lua", "mode": "px", "corner": "tr", "dx": 210, "dy": 398}
"cmo_lua_input": {"window": "cmo_lua", "mode": "frac", "dx": 0.1471, "dy": 0.6305}
```

- `frac` scales with the window and suits fields and content areas
- `px` holds a fixed offset from a corner and suits toolbar and edge buttons

Capture picks the mode for you: a point within 160 px of an edge becomes `px`,
anything else becomes `frac`. Move or resize a window and every target follows
it according to the saved offset or fraction. Recheck targets after zoom, display-scaling or internal UI-layout changes.
The Calibration tab updates live because CONN listens for window location
changes through `SetWinEventHook`, with polling as a fallback.

The shipped anchors were converted from the calibrated coordinates in
`bridge_config.json` using the window rectangles in the reference screenshot at
3840 x 2160. `cmo_scenario_start`, `cmo_scenario_reset` and
`cmo_scenario_reload` were never calibrated, so they ship unset and preflight
reports them rather than clicking somewhere wrong.

Buttons on that tab:

- **Capture point** countdown capture, the same mechanism as the old tool
- **Test click** clicks one anchor so you can confirm it lands
- **Rebind window** moves an anchor to a different window, keeping the point
- **Show overlay** a click-through overlay drawing every window outline and
  every anchor crosshair on the live desktop
- **Import legacy coordinates** converts the old absolute block, using the
  windows as currently arranged
- **Write absolute back** resolves anchors to absolute points and writes them
  into `coordinates`, so the original command-line bridge still runs

---

## 4. Layouts

Profiles store each window as fractions of the virtual desktop, so the
reference arrangement reproduces at any resolution. Two ship by default:

- `scenario_dev` the arrangement in the screenshot: browser upper left, Lua
  console lower left, CMO on the right, CONN in the slot where the bridge
  console used to be
- `play` CMO wide with CONN as a strip on the right

Capture current saves what is on screen now, keyed to the display topology, so
a docked setup and a laptop-only setup do not overwrite each other. Reserve
space shrinks every window away from one edge and puts CONN in the band.

Apply Layout also runs automatically at the start of a run when the checkbox on
the Mission tab is set.

Clicking a profile in the list makes it the active one (marked `*`) for the
current mode. Each mode remembers its own. Changing the mode never
replaces a profile you picked with a built-in one.

---

## 4b. The cycle

Every screen action resolves through an anchor, so the calibration file is the
only place a click position is defined. The order matches the marks:

| Step | Anchor | Action |
|---|---|---|
| 1 | llm_code_copy | copy the reply |
| 2 | cmo_lua_input | paste into the Lua console |
| 3 | cmo_execute | run |
| 4 | cmo_output_area | read the result pane |
| 5 | llm_input | paste the output back |
| 6 | llm_submit | submit |

A run refuses to start when any of the six does not resolve, naming each one.
The monitor logs each step as it happens.

Injected code is wrapped in `CONN_BEGIN:<token>` and `CONN_END:<token>` prints.
Step 4 then re-reads the pane until the END marker appears rather than waiting
a fixed number of seconds, and returns only the slice between the two markers,
so an accumulating pane never feeds an old run's output back into the loop.
Timeout and poll interval are on the Settings tab.

If the console's **Echo input script on result text** box is ticked, tick the
matching box on the Settings tab and the echo is stripped from the reading. The
default assumes it is off.

## 4b2. Sim directives

A reply may carry one `BRIDGE_CONTROL:` line to drive the simulation, e.g.
`BRIDGE_CONTROL: COMPRESS=15; RUNFOR=900`. Ops are PLAY, PAUSE, START,
RESET, RELOAD, COMPRESS=n and RUNFOR=seconds. Semicolons, commas and pipes
all separate ops, and the line is recognised inside a Lua print, with quotes
and parens stripped from the values. A malformed op is logged and skipped:
directive handling can never end a run.

## 4c. When a run stops

A run keeps working until one of these is true:

| Ending | Trigger |
|---|---|
| Request fulfilled | `BRIDGE_DONE:<summary>` printed, or the stage reaches DONE |
| Needs you | `BRIDGE_HALT:<what is needed>` printed by the model |
| No progress | N consecutive failing cycles (default 8) |
| Stuck in a loop | the same fault N cycles running (default 3) |
| No usable reply | the copy could not be salvaged after the retry attempts |
| Cycle budget | the backstop, default 500 |
| You | Abort, or ctrl+alt+x |

A failed script is **not** an ending. It becomes a FIX_ERRORS repair cycle:
the error text, or the local rejection reason when the script never reached
CMO, goes back with an instruction to diagnose, change approach and carry on
with the original request. Only a model that genuinely cannot proceed prints
BRIDGE_HALT, and the reason is shown in the log and in the session report.

The failure verdict for a cycle comes from the console alone: an error line
alongside a console-printed forward state is progress with a cosmetic fault
and does not tick the stop counters, while an error with no console state
line means the script died before its final print and routes to FIX_ERRORS
regardless of what the code declared. Sim directives are applied after the
script's output has been read, a RUNFOR uses a preceding COMPRESS argument,
and a directive-run window replaces the TEST stage's default window instead
of stacking on it.

`BRIDGE_HALT` and `BRIDGE_DONE` are read **only from console output**, never
from the reply's code. A generated script legitimately carries the token
inside a guard branch that never executes, and reading it there stops runs
that would have succeeded.

Faults are fingerprinted so the loop can tell repetition from progress. GUIDs,
numbers and quoted names are stripped, so the same fault reported against
different units collapses to one signature and trips the repeat rule, while a
new fault resets the counters. All three limits are on the Settings tab.

## 4d. Failure containment

Every external step in the loop, the copy, the injection, the result read,
the test window, the submit and the opening submit, runs through a guard that
turns an exception into a logged failure. A cycle that raises anywhere else is
caught by the cycle guard, counted as a failure, and fed back to the model as
a BRIDGE_FAULT repair cycle. Clipboard, attach, payload-file and session
writes are individually contained, and the RAG is optional context rather than
a dependency.

The consequence is that only the endings in 4c stop a run. Nothing in the
screen layer, the parser or the disk layer can end one. This is verified by a
chaos test that breaks each step in turn and requires the run to keep cycling
and terminate with a stated reason.

## 5. Process monitor

The narrow panel that replaces the bridge console window. It appears as a tab
and can be undocked as an always-on-top strip.

- state chips for the design loop, current stage highlighted
- cycle, turn, side, error and retry counters
- live phase timer with a bar, so a stall is visible against the wall cap
- last Lua sent and last CMO output, truncated with expand
- RAG hits for the current step
- Pause, Step, Abort
- filtered log tail

The engine runs on a worker thread and only pushes events onto a queue, so a
sixty second wait never freezes the window.

---

## 6. IKE finalization

Conversion cannot be undone, so the sequence is fixed:

1. copy the master to `SNAPSHOTS/name_vNN_preIKE.scen`
2. set the master read-only for the duration
3. create a working copy and convert only that
4. inject the IKE conversion Lua, then answer its popups in CMO
5. save with **Save As**, then press Verify

Verify confirms the file exists and is non-empty, then writes a sidecar
`.ike.json` recording source, snapshot, time, sides, turn length and a hash.
The confirmation dialog names both input and output paths before anything
runs. IKE is musurca's project and is not bundled: point
`ike.ike_conversion_lua_path` at the conversion Lua from the Scenario Author
Pack.

---

## 6b. Knowledge pack

`knowledge_pack/` holds the v4 bridge knowledge set in its entirety, plus the
SQLite DBID extractor under `knowledge_pack/dbid_extractor/`. It is wired in,
not just stored:

- **RAG.** The v4 master reference, the operating prompt and the terminal
  protocol are chunked into the retrieval corpus, and the lookup layer builds
  from the pack's CSV. Rebuild any time with `python cmo_rag.py --build`.
- **API symbol guard.** Every payload, generated or built in, is scanned for
  CMO-looking identifiers (`ScenEdit_*`, `VP_*`, `Tool_*`, `UI_*`, `World_*`,
  `Command_*`, `Exporter_*` and the bare scenario calls) against
  `cmo_known_api_index.json` before injection. Unknown names block the
  injection and the reprint request tells LLM exactly which calls to fix.
  `safety.api_extra_symbols` extends the index for symbols your build exposes
  that the pack predates. `safety.api_soft_symbols` downgrades named symbols
  to a warning.
- **Environment symbols.** `knowledge_pack/cmo_environment_symbols.json`
  carries the symbols confirmed present in your own build, harvested from the
  console environment dump, merged into the guard alongside the pack index.
  The guard also learns automatically whenever a run's output contains a
  globals dump, and Settings has an "Import environment dump" button for
  pasting one in by hand.
- **Console suppression.** Any line calling `Tool_EmulateNoConsole(true)` is
  commented out before injection, including in the pack's own inspect payload.
  That call silences every print until it is switched back off, which returns
  an empty result pane and starves the loop. The matching `(false)` call is
  left alone. Toggle with `safety.neutralize_console_suppression`.
- **State line reading.** The runtime console output decides the next stage,
  with the reply's code only as a fallback, and the LAST declaration wins
  rather than the first. A script that prints the line from an early-exit
  branch no longer sends the loop to that branch's state. A near-empty result
  pane is logged as its own warning instead of being read as a verdict.
- **Copy retry order.** An empty clipboard first gets one local re-scroll and
  re-click, since a moving copy control is the usual cause. Only a copy that
  is present but invalid goes to a chat reprint, and the reprint names the
  rejection reason.
- **Prompt contract.** The cycle prompt now carries the environment facts the
  hard way taught: the API is callable userdata, so `type(x) == "function"`
  probes are wrong, even for `print`; `rawget`, `load`, `require` and `io` may
  be nil; `VP_GetSides` returns Side wrappers, not strings;
  `ScenEdit_GetSides` and `ScenEdit_GetUnits` do not exist; failures print
  `CMO_ERROR|FUNCTION=|NUMBER=|MESSAGE=` from `_errfnc_`, `_errnum_` and
  `_errmsg_`.
- **AUDIT opening stage.** The Mission tab has an opening-stage selector.
  AUDIT injects the pack's known-good `CMO_BRIDGE_INSPECT.lua` directly, with
  no generation involved, then hands the console dump plus your request to the
  EVALUATE stage. Reviewing a loaded scenario no longer starts with a DESIGN
  instruction that wants to build a blank one.
- **DBID discipline.** Unit creation should use DBIDs from the extractor
  output against your own CMO database, per
  `knowledge_pack/dbid_extractor/cmo_sqlite_extraction_guide.md`. The prompt
  contract forbids guessed DBIDs and loadout IDs.

## 7. Safety

- **Lua syntax check** before every injection. Comments, strings and long
  brackets are skipped, then bracket and block balance are checked, which
  catches truncated pastes before they cost a cycle.
- **Editor lock** in play modes. Calls such as `ScenEdit_AddUnit` are refused
  in scripts the model writes during a play run, in any form (`Name(`,
  `Name{`, an alias). Operator tools (Rebuild, IKE) are not affected. The list
  is editable in the config.
- **Side lock** refuses orders that act as the side that is not on the clock
  (`side = 'X'` or `'X'` as a ScenEdit call's first argument). Reading a
  contact's side is allowed. A rejection is passed to that commander next turn.
- **Own-window guard.** CONN stays on top, so a click at an anchor that sits
  under CONN's window would press a CONN control. Those clicks are skipped and
  logged, and Preflight lists any anchor that is covered.
- **Arbiter** runs both checks plus an order budget before any LLM orders are
  injected.
- **Clipboard guard** saves and restores your clipboard around every copy and
  paste.
- **Large payloads** over the configured limit are written to the IN folder and
  a short pointer is pasted instead, since long pastes arrive empty.
- **Copy method.** The default clicks the code block's own Copy control and
  reads the clipboard. Ctrl+A in a browser selects the whole page, so the
  older select-all path returns the prompt and page furniture instead of the
  reply. `bridge.copy_method` accepts `button` or `select_all`.
- **Waiting for the reply.** After sending, CONN waits
  `timing.llm_min_wait_seconds` (15), then copies the reply every
  `timing.llm_reply_poll_seconds` (8). A reply is finished when the copy is
  valid Lua with the `NEXT_RECOMMENDED_STATE` line at its end, or when two
  copies in a row match. An empty clipboard during the wait means the reply is
  not there yet. The longest wait is `timing.llm_output_wait_seconds` (300).
- **Copy validation and stops.** A copy is rejected when it is empty, carries
  the bridge contract header, repeats the prompt just sent, contains no Lua, or
  fails the syntax check. When the wait runs out with nothing copied, or with
  the prompt copied instead of the reply, the run stops with a message: a
  reprint cannot fix a copy anchor or a chat that never answered. A broken
  code block gets at most `timing.llm_max_reprints` (2) reprint requests,
  then the run stops.
- **LLM tab guard.** Before every paste CONN reads the title of the window
  under the LLM input anchor and logs it. `bridge.llm_title_must_contain`
  (Settings > LLM chat) stops the run if that title does not contain the
  text. `bridge.lock_llm_tab` (on by default) remembers the chat title after
  the first good reply and stops the run if a different chat comes to the front.
- **Scroll before copy.** Each copy attempt sends Page Down twice into the
  reply area first, because the code block's copy control is only rendered
  once the reply is scrolled into view. Count and per-press pause are on the
  Settings tab (`timing.llm_scroll_page_downs`,
  `timing.llm_scroll_pause_seconds`); zero disables it.
- **Oversized prompts become attachments.** The size check runs before any
  paste. Over the limit, the prompt is written to the IN folder and attached
  to the conversation: the default `ctrl_u` route focuses the input, sends the
  browser's attach shortcut, pastes the path into the file dialog's filename
  field and presses Enter, then pastes a short handoff note telling the model
  to read the attachment as the cycle's prompt. No new calibration needed. For
  a browser without the shortcut, set `io.attach_method` to `anchors` and
  calibrate `llm_attach_button`, `llm_attach_menu` and optionally
  `file_dialog_filename` and `file_dialog_open` on the Calibration tab. If the
  attach route is unusable the prompt is chunk-pasted instead, several
  sequential pastes into the same input, and nothing is ever handed over as a
  bare file path, which the browser model cannot read. This is also the path
  large scenario-state dumps ride during play, so a big order of battle
  reaches the model whole.
- **Global abort** on `ctrl+alt+x`, registered system wide so it works while
  CMO has focus. Escape works when CONN has focus.

---

## 8. Preflight

Run before any mode starts and available on its own tab: Windows host,
dependencies, each tracked window, core anchors resolving, folders writable,
IKE paths for the modes that need them, RAG index. Missing folders have a
Create button on the row. Blocking failures ask before the run starts.

---

## 9. Sessions

Every run writes a folder under `SESSIONS`:

```
events.jsonl     event stream
transcript.md    prompts, replies and console output in order
scripts/         each deployed Lua block, numbered
diff.md          unified diff between successive deployed scripts
report.md        exported summary
```

---

## 10. Files

```
conn_ui.py            launcher
conn/app.py           the window: tabs, header, event pump
conn/engine.py        actuator plus the design loop, dry run enforced here
conn/turnengine.py    the four play modes on one turn state machine
conn/agents.py        commander profiles and order prompts
conn/winmgr.py        window discovery, geometry, live change hook
conn/anchors.py       window-relative targets and legacy migration
conn/layouts.py       arrangement profiles
conn/overlay.py       click-through calibration overlay
conn/monitor.py       the process monitor panel
conn/preflight.py     go / no-go checks
conn/luacheck.py      syntax check and call blocklist
conn/clipio.py        clipboard guard and large payload routing
conn/ike.py           snapshot, lock, convert, verify, sidecar
conn/session.py       logging, transcript, diff, export
conn/theme.py         live and dry-run palettes
conn/hotkeys.py       global abort hotkey
conn/config.py        one config file, legacy keys preserved
tests_conn_smoke.py   headless smoke tests
```

---

## 11. Confirm on your end

These cannot be executed in the environment where this was written:

- `SetWindowPos` against the CMO window. Some builds run borderless
  fullscreen and ignore position requests. If CMO will not move, run it
  windowed.
- `SetWinEventHook` behaviour under your DPI setup. If live tracking looks
  slow, set `ui.use_winevent_hook` to false to use polling.
- `RegisterHotKey` for `ctrl+alt+x`. Another application may already own it.
- The prefilled anchors. They were derived from the screenshot geometry, so
  test click each one before the first live run.
- The IKE conversion Lua path and its popup sequence.
