# CONN UPDATE 2026-09-07 — REVIEW AND CHANGELOG

## What I found in the running CONN

I read `cmo_rag.py`, `conn/engine.py`, `conn/app.py`, the config, the API guard,
the knowledge pack and the session archives. Six findings drove the changes.

**1. The RAG had a learning channel that nothing used.** `CmoRag.ingest_feedback`
exists and feedback becomes retrievable, but neither the engine nor the app ever
calls it. Every `rag_*` note I wrote during the playtests went to the *scenario
keystore* via `ScenEdit_SetKeyValue`, which CONN never reads and which
`Tool_BuildBlankScenario` wipes. So the RAG was write-only into a file that got
deleted. This is why I repeated the same mistakes across sessions.

**2. Retrieval was keyed on the task text alone.** A lesson about "the swarm
launched but nothing attacked" only surfaces if the query contains those words,
and those words live in the previous cycle's *output*, not in the mission text.

**3. No always-on rules.** The bridge instruction is fixed; the hard-won rules
had no injection point, so mission-doctrine-overrides-side-doctrine could be in
a file on disk and still never reach a cycle.

**4. `RUNFOR` alone forced compression to x15.** `_apply_directives` fell back to
`bridge.default_test_compression` (15) whenever a directive line had no
`COMPRESS`. That is exactly the "double flame" snap you kept seeing after
setting x5 by hand. Separately, `timing.test_window_wall_cap_seconds` was 300,
so an 8,000-second window at x5 (1,600s wall) was cut off after 300s of wall
time, about 1,500 sim seconds. Windows could never reach the next decision.

**5. No DBID validation.** The 18,744-record lookup has names and costs but no
operator country, service, or hypothetical/deprecated flags, and no
aircraft-to-loadout relation. Nine of nine aircraft in the Hormuz build were the
wrong nation by name; nothing in CONN could have caught it.

**6. No playtest stage.** Every cycle opened with "STAGE DESIGN. Produce the
FIRST build script", which I had to override by hand each time. The default
scenario prompt fallback still reads "Blue escort group against Red missile boat
swarm".

## What changed

### `cmo_rag.py`
- **Lessons corpus.** `knowledge_pack/CMO_LUA_SESSION_RAG.md` is indexed as
  `lesson` documents, one per bullet, so each finding retrieves on its own.
- **Pinned rules.** `knowledge_pack/CMO_PINNED_RULES.txt` (12 rules) is injected
  verbatim into every cycle's context regardless of lexical match.
- **Retrieval order.** Pinned rules, then lessons matching the query, then
  recipes, then reference notes. Lessons outrank the reference because they were
  observed on this build.
- **Auto-harvest.** `harvest_lessons(code, output)` finds `RAG_NOTE:` /
  `LESSON:` lines and any `ScenEdit_SetKeyValue("rag_...", ...)` write in either
  form (direct or `pcall`), flattens Lua string concatenations, and skips pure
  telemetry. `ingest_lesson` / `ingest_many` append to
  `rag_index/lessons.jsonl` with de-duplication and rebuild the index once.
- **v515 catalog.** `build_db515_index` loads the corrected platform lookup
  (type-namespaced, with operator country and service resolved from numeric
  codes) and the aircraft→loadout relation (7,630 aircraft). New methods:
  `platform(type, dbid)`, `find_platform(name, ptype, country)`,
  `loadouts_for(dbid)`, `validate_pairing(dbid, loadout)`.
- **`validate_lua_units(code)`.** Scans unit rows in a build script and returns
  warnings for unknown DBID-for-type, hypothetical, deprecated, wrong-nation on
  the two combatant sides, loadout not valid for the airframe, and unarmed
  loadouts on AI-flown combatant aircraft. Generic/Commercial entries and civil
  traffic are exempt. Non-blocking by design.
- **CLI.** `--lesson`, `--harvest FILE`, `--platform NAME --ptype T`,
  `--validate FILE`. `--build` now builds all three indexes.

### `conn/engine.py`
- `build_prompt` retrieves on the task **plus** the last output tail and the
  current notes, includes lessons, and appends DBID warnings from the previous
  validation.
- Before injection: `rag.validate_lua_units(code)`; warnings are logged and ride
  along in the next prompt. Nothing is blocked.
- After output: `harvest_lessons` → `ingest_many`; a `rag_learn` event shows
  what was learned. Controlled by `bridge.rag_autolearn`.
- `_apply_directives`: `RUNFOR` with no `COMPRESS` **does not touch
  compression**. It clicks play, waits, clicks pause. The wait is sized from
  `bridge.manual_compression` (default 5).
- `test_window(sim_seconds, compression, send_compression=True)`: long windows
  are honored (`timing.honor_long_windows`), announced when they exceed the cap,
  and remain abortable. The cap default is now 3,600s.
- TEST-stage fallback (no directive line at all) honors
  `bridge.operator_owns_compression`.
- New stage `PLAYTEST`: "the scenario is already built; do not build; lead with
  the CLICK line; size RUNFOR to the next decision." Added to `VALID_STAGES`
  and `LINEAR`.
- Bridge instruction gains two lines: the `RAG_NOTE:` convention and the pinned
  rules reminder.

### `conn/app.py`
- Start-stage combobox gains **PLAYTEST (play the loaded scenario)**.
- `rag_learn` events are logged as `RAG learned: ...` so the operator can see
  the knowledge base grow.

### `bridge_config.json`
- Added: `bridge.manual_compression: 5`, `bridge.operator_owns_compression:
  true`, `bridge.rag_lessons: 4`, `bridge.rag_max_chars: 7000`,
  `bridge.rag_autolearn: true`, `timing.honor_long_windows: true`.
- Changed: `timing.test_window_wall_cap_seconds` 300 → 3600.
- `safety.api_soft_symbols` gains `UnitX`, `ScenEdit_AddMinefield`,
  `ScenEdit_QueryDB`, `UI_OpenNewDatabaseWindow`, `ScenEdit_SetTime`,
  `ScenEdit_SetStartTime`.
- **All 18 anchors are byte-identical to your running config.** Calibration is
  untouched.

### `knowledge_pack/`
- New: `CMO_LUA_SESSION_RAG.md`, `CMO_PINNED_RULES.txt`, `db515/` (corrected
  platform lookup, aircraft loadouts, the stage-4 scanner, its README).
- `cmo_known_api_index.json`: `UnitX` added (174 → 175). Every other symbol the
  prompt engine uses was already present.
- `README.md`: session-knowledge section.

## What did NOT change

`cmo_sim_control.py`, `conn/anchors.py`, `conn/clipio.py`, `conn/config.py`,
`conn/luacheck.py`, `conn/apiguard.py`, `conn/preflight.py`, `conn/winmgr.py`,
`conn/hotkeys.py`, `cmo_calibration_ui.py`, `lua_unified/`, the IN folder, and
the file-exchange route from the previous update. Confirmed by byte comparison.

## Verified

- All changed Python parses; `tests_conn_smoke.py` passes.
- Fresh index build: 872 docs, 18,744 lookup records, 18,888 v515 platforms,
  7,630 aircraft with loadouts.
- Stubbed engine run: `RUNFOR=8000` alone issues only play and pause, no
  compression call, and waits 1,602s (was capped at 300). `COMPRESS=15;
  RUNFOR=300` still sets compression.
- Pinned rules appear in every prompt. The query "the swarm did not attack; WCS
  surface Hold" returns *Mission-level doctrine overrides side-level doctrine*
  as the top hit.
- Harvest of a real playtest script ingests its `rag_` note; re-ingest is a
  no-op.
- The validator flags the South Korean P-8A trap, and on the current Hormuz
  build it finds **four** entries: the Pakistani Zulfiquar and Norwegian Vidar
  substitutes I made deliberately, and two I did not know about — **CG-56 San
  Jacinto (2861) and the Virginia SSN (678) are both "Junkyard" operator
  entries**. Worth replacing in the scenario.

## QA/QC pass on the update itself

Reviewing my own Lua-facing code before shipping found five defects, all fixed
and each now covered by a test that runs against the real corpus:

1. **Apostrophes destroyed harvested lessons.** The literal matcher treated `'`
   as a delimiter, so *Iran's batteries shot Iran's own hostage ships* became
   *Iran s own hostage ships*. Double- and single-quoted literals are now
   matched separately.
2. **Telemetry was ingested as knowledge.** A `pass=8 fail=2 iran_air=2` readout
   is state, not a lesson. Rejected when key=value tokens dominate the prose.
3. **`RAG_NOTE` inside a `print(...)` in the code was missed.** If the console
   capture came back empty the lesson was lost. The code form is now harvested
   too, and the same note from code and output de-duplicates to one.
4. **Prompt budget starved DESIGN cycles of recipes.** Pinned rules plus four
   lessons filled 7,000 characters before any code example fit. Lessons are now
   capped at half the remaining budget, the budget is 9,000, and assembly stops
   at part boundaries so a recipe's code fence is never cut in half.
5. **Code fences inverted mid-prompt.** A reference chunk sliced at 1,200
   characters could end inside a fence, and a lesson paragraph that *was* a
   code block got its ```` ```lua ```` line used as a title. Clipping is now
   fence-safe and code-block paragraphs merge into the lesson they illustrate.

Also fixed in the engine: `last_output` now carries the pre-window and post-run
output together, so the next cycle's retrieval sees the whole picture.

Verified after the fixes: twelve query types across playtest and design
wording all return pinned rules, at least one lesson, recipes where relevant,
and balanced fences. A lesson printed in cycle N is retrievable in cycle N+1's
prompt. The PLAYTEST entry submits once and hands off to the loop the same way
DESIGN does. All Python parses; smoke tests pass.

## Install

Unzip over your current `CMO_LLM_Bridge` folder. Your `bridge_config.json`
anchors are identical, so the calibration carries. Delete `rag_index/` if one
exists so the new indexes build on first run (about ten seconds, once).

## Convention for me, from now on

Any durable finding goes out as a single line in the Lua output:

    print("RAG_NOTE: mission doctrine overrides side doctrine; set both")

The bridge ingests it, and it is retrievable in the next cycle and every session
after. Wrong hypotheses get retracted the same way.

## QAQC pass on the delivered artifact (same day)

I unzipped the delivered archive and ran the real `_run_design` loop end to end
with LLM, CMO and the sim stubbed, tracing every step in order. The order of
operations is correct: PLAYTEST submits once with no double DESIGN submit, then
each cycle runs copy → local Lua check → API guard → DBID validation → inject →
wait → read → directives → window → post-run read → lesson harvest → next state,
and DONE ends the run.

**Three defects found and fixed in this pass:**

1. **The bridge itself told the model to emit `COMPRESS`.** The fixed instruction
   header (`e.g. 'BRIDGE_CONTROL: COMPRESS=15; RUNFOR=900'`) and both the TEST and
   RETEST stage texts (`COMPRESS={c}; RUNFOR={s}` with `c` = the default 15)
   instructed it every cycle. My `RUNFOR`-alone fix only helps when the model
   omits `COMPRESS`; here the bridge was asking for it. That is precisely how a
   manual x5 was being overridden. All three now read `RUNFOR={s}` with an
   explicit "do NOT emit COMPRESS" note whenever `bridge.operator_owns_compression`
   is true. Verified: no prompt mentions `COMPRESS` as an instruction and
   `set_compression` is never called across a three-cycle run.
2. **A DONE cycle burned a fallback window.** The TEST-stage fallback ran a test
   window even when the console had just declared DONE. It now checks the
   console state first.
3. **PLAYTEST was not sticky.** If the model omitted a state line, `LINEAR`
   carried it to TEST → EVALUATE → REPORT → DONE and the run stopped. PLAYTEST
   now maps to itself, and every later TEST/EVALUATE task in a playtest run is
   prefixed with the "scenario is built, do not build, lead with the CLICK line"
   reminder.

**Also verified in this pass:** `luacheck` accepts the shipped inspect script,
the sim-control snippet (which carries the `_G[fn] ~= nil` probe fix) and a
sample playtest cycle with `RAG_NOTE:` lines; the print contract detector
passes; the API guard accepts a real playtest script; every symbol the prompt
engine uses is in the index; the editor lock applies only in the four play
modes, not in Scenario Development.

**Outside CONN, worth acting on:** the new validator flags two entries in the
current `HORMUZ_2026_BUILD_ALL.lua` that were never known to be wrong: CG-56
San Jacinto (Ship 2861) and the Virginia SSN (Submarine 678) are both "Junkyard"
operator entries in v515. The Pakistani Zulfiquar and Norwegian Vidar it also
flags are the deliberate substitutes.

## Verification round 2026-09-19

Re-verified every claim about the RAG against the delivered archive, from a
fresh unzip, and corrected what did not hold.

**Confirmed working as described:** all storage files present; first-run
autobuild takes about one second (871 docs, 18,744 lookups, 18,888 v515
platforms, 7,630 aircraft with loadouts) and 0.1s thereafter; the context block
is ordered pinned → lessons → recipes → notes and fits the 7,000-char cap; the
end-to-end loop runs PLAYTEST → TEST → TEST → DONE with play/pause only and no
compression call; no prompt instructs `COMPRESS`; pinned rules are in every
prompt; the validator still flags the four v515 entries; smoke tests pass.

**Three corrections:**

1. The bare `RAG:` harvest prefix matched engine error text ("RAG: retrieve
   failed"). Removed; `RAG_NOTE:` and `LESSON:` remain.
2. The telemetry filter missed `pass= fail= iran_air=` because dynamic values
   were dropped in flattening, leaving `key=` with nothing after it. It now
   counts those, and also rejects anything with fewer than five real words.
3. The lessons corpus carried ten junk chunks: `---` separators, code fences
   and the file's own lead-in. Filtered; 46 clean lessons remain.

**One addition:** `python cmo_rag.py --forget "text"` removes harvested lessons
containing the text, and `--lessons` lists them. This exists because
harvesting an old session archive recovers wrong hypotheses alongside their
retractions (the "release_us sandbox" theory, the "throttle bug"), and a store
holding both can surface either. The archive ships with an empty lessons store;
the curated knowledge is in `CMO_LUA_SESSION_RAG.md`. Harvest old archives
only if you then prune them.

## IKE PBEM hotseat against the LLM (added 2026-09-19)

`conn/turnengine.py`: in `player_vs_llm` mode, when `play.ike_hotseat` is true,
the LLM side's turn now runs after its orders are injected: CONN presses play,
waits the configured turn length on the wall clock at the operator's manual
compression, and does not press pause, because IKE stops the clock itself at
the turn boundary and raises the hand-off notice. It then waits for Step. Off
by default; existing modes are unchanged. Verified with stubs both ways.

## RAG by mode (2026-09-19)

Reviewed every RAG touchpoint against the four play modes.

| mode | retrieve | validate DBIDs | harvest | notes |
|---|---|---|---|---|
| design / PLAYTEST | yes, design profile | yes | yes | unchanged |
| normal | no | no | no | monitor only, never calls LLM |
| pbem_h2h | no | no | no | both sides human |
| player_vs_llm, llm_vs_llm | LLM turn only, commander profile | no | off by default | human turn touches nothing |

**Commander profile.** The LLM's order prompt now retrieves on the actual
SITREP tail and the last intents instead of a fixed string, uses a separate
six-rule pinned set about giving orders (`CMO_PINNED_RULES_COMMANDER.txt`),
keeps only doctrine, posture, mission, unit and process lessons, and drops
sim-control and build recipes. Context is capped at 4,500 characters.

**No interference with the simulation.** All commander RAG work happens in
the order phase, when the clock is already stopped. A human turn and normal
mode never build, read or write the index.

**Learning in play is off by default** (`play.rag_learn_in_play`). In
`llm_vs_llm` a note one commander prints can describe the other's positions.
When enabled, each lesson is tagged `play:<side>` and only that side's
commander can retrieve it; design retrieval sees all of them. Verified: Iran's
commander cannot retrieve a lesson harvested for the United States and vice
versa, a human turn makes zero RAG calls, and the design path is unchanged.

## Interface, sizing, calibration and layout (2026-09-19)

**Hover help.** New `conn/tooltips.py`: one shared, delayed, palette-coloured
tooltip window. Every interactive control in the interface now explains
itself on hover: all buttons, toggles, entries, combo boxes, spin boxes, text
boxes, trees and lists across the header, Mission, Play, Monitor (docked and
undocked strip), Calibration, Layout, Preflight and Settings tabs, plus the
rebind and environment-import dialogs and the preflight fix buttons.
Verified under a virtual display: 105 of 105 controls carry a tip; hovering
Start shows it and leaving hides it.

**Launch size.** The window was opening at 1180x820 while its content
requested 1258 px of height, so tabs were clipped. `_fit_to_content` now
sizes the window to the tallest tab, capped to 92 percent of the screen,
centres it, and re-fits once after idle when font metrics have settled. The
Settings tab, the only one taller than any screen, scrolls with the mouse
wheel. On small screens the Monitor tab's text boxes shrink to their floors
rather than clip. Verified fit with no clipped tab at 1366x768, 1600x900,
1920x1080, 2560x1440 and 3840x2160. The window stays resizable; minimum
900x600.

**Play tab.** Three switches the engine honours were never exposed and are
now on the tab with tooltips: IKE hotseat (run the LLM's turn after its
orders), RAG context for the LLM commander, and Learn from LLM turns. All
three persist through Save play settings.

**Calibration for play mode.** No interface or method changes. Verified the
logic that decides which window an anchor binds to: the window manager
picks the largest window matching a rule, so IKE's password and hand-off
popups, which carry the CMO title, cannot displace the main window. Two
matching rules were widened, no anchors touched: the console rule now
matches both "Lua Console" and "Lua Script Console", and the LLM rule
accepts Brave and the LLM desktop app alongside Edge, Chrome and Firefox.
The 18 stored anchors are byte-identical to the running config.

**Layout restore.** Verified with a stub window manager against the real
profiles in the config: every window in the play profile lands at its stored
fraction of the desktop, z-order is applied lowest first, CONN is placed
through its own setter, a window that is not open is reported as missing by
name, capture round-trips to the stored rectangle within a pixel, and a
captured profile resolves through its topology-specific key. Every mode's
active profile covers the windows that mode needs; Apply Layout with nothing
selected falls back to the mode's profile.

**Preflight.** Play modes now also check that the active layout profile
covers the mode's windows, that the side names are set to real scenario
sides rather than the Blue and Red placeholders, and, when IKE hotseat is on,
that a turn length is set.

**Regression fixed.** The earlier update called `test_window` with a third
argument. Anything that overrode it with the original two-argument signature
would have silently skipped the window; the smoke suite caught it once it
could run with a display. The two-argument contract is restored, and the
compression-free path falls back to it.

**Test coverage.** With a display available the full smoke suite now runs:
203 checks pass, including the UI, chaos, audit-opening and turn-gate tests
that every earlier run had skipped.

## Start and stop of the clock (2026-09-19)

**What was wrong.** `cmo_controls.method` was `keystroke`, so the bridge
was sending Ctrl+Enter to start and stop the clock and only used the
calibrated click when it could not confirm window focus. The module's own
comment warns that a decayed Ctrl+Enter, landing as a bare Enter, changes
time compression in the CMO window: a likely source of the compression
snapping seen during the playtests. Separately, `_click` ignored the click
primitive's result, so a click that failed still reported the clock as
started and the toggle tracker went out of step. And two copies of
`cmo_sim_control.py` existed, one stale, with the root copy the live one.

**What changed.**
- `cmo_controls.method` is now `click`: the calibrated click on the play/pause
  button is the primary route. `play_pause` is `["space"]`: the Space key is
  the keystroke alternative. Both are toggles on the same button, and the
  two anchors resolve to the same point, which is correct.
- `play()` and `pause()` follow a method order with fallbacks: click, then
  Space with focus confirmed; or Space, then click, for `keystroke`. A
  failed click now counts as a failure and falls through; a keystroke is
  withheld unless CMO is confirmed foreground; if no route succeeds the
  call returns False and says so.
- The stale copy under `conn/` is now identical to the live root file.
- Play tab: a "CMO clock right now: paused / running" control. The play
  control is one toggle, so after starting or stopping the clock by hand,
  set this and CONN's next press does the right thing. Start passes it to
  the run; changing it mid-run resyncs the tracker immediately. A label
  shows the active method and key.

**Verified.** Nine controller cases with stubbed primitives: click primary,
click fails then Space, click fails and no focus sends nothing, anchor unset
goes to Space, keystroke method sends a single Space with no modifiers, the
old chord still works if configured, double play is one press, operator
resync after a manual start yields exactly one pause, and `RUNFOR` through
the engine clicks play and pause without touching compression. Your real
anchors resolve to the same point for play and pause at two window
positions and report "window missing" when CMO is closed. UI control
present with tooltips; 107 of 107 controls carry hover help; 203 smoke
checks pass.

Confirm on your end: that Space toggles the clock in CMO with the map
focused, and that a live click at your `cmo_play` anchor lands on the
play/pause button after a restart of CONN.

## CMO logs and map screenshots for the model (2026-09-19)

**Where the logs come from.** New `conn/cmologs.py`. The folder is
`cmo.logs_folder` in Settings (with Browse and Find buttons); left blank, CONN
tries the Steam install, then the Matrix Games install, then Steam libraries
on other drives. Preflight reports which AALog.txt it will read.

**What the model can ask for, in any mode where it writes Lua.** A line in
its reply or its console output:
- `BRIDGE_ATTACH: AALOG` (optional `tail=N`): a digest of kills, hits,
  launches, contacts and events, then the log tail, capped and written to a
  file that is uploaded with the next prompt.
- `BRIDGE_ATTACH: MAPSHOT`: a PNG of the map window.
- `BRIDGE_ATTACH: EXCEPTIONLOG`, `LUAHISTORY`, `SESSIONLOG`: the newest of
  CMO's exception logs, Lua console histories, or dated session logs. The
  exception log is what to ask for when an injection crashed CMO.
The prompt names each attached file so the model knows what it received.
The same directive printed from Lua and echoed by the console is queued
once. The Mission tab can also attach the AALog to every design cycle.

**Every LLM turn in play.** The commander's SITREP ends with the lines CMO
wrote to AALog.txt since that side's last turn, with a digest. Each side has
its own marker, so a commander sees only the interval it was away and
nothing of the other side's turn is carried in prose. Verified with two
sides alternating: the second Iranian turn received exactly the one line
written since its first. An optional switch attaches a map screenshot each
turn as well.

**The map screenshot.** New `conn/mapshot.py`. If the CMO window is
minimized or smaller than `mapshot.min_width` x `min_height`, it is restored
and resized to `mapshot.rect` without taking focus, given
`mapshot.settle_seconds` to redraw, captured with `PrintWindow` and full
content rendering (which works while other windows cover it), and put back
exactly as it was, minimized state included. If that render comes back
blank the window is raised without focus and the screen region is grabbed
instead. The image is downscaled to `mapshot.max_width` and saved as PNG.
Off Windows it declines cleanly.

**Verified.** Detection order; tail excerpt with digest capped at the
configured size; per-side deltas with persisted markers; the newest
exception and Lua history logs; directive parsing including inside a Lua
`print`; the design loop delivering a requested excerpt with the next prompt
and none after; the turn engine per-side interval; the blank-frame detector
against a real CMO screenshot; the interface controls with tooltips (113 of
113); no clipped tabs; 203 smoke checks.

Confirm on your end: the first live `BRIDGE_ATTACH: MAPSHOT` with the map
minimized, that the window returns to its previous state afterwards, and
that the uploaded PNG appears in the LLM conversation.

## Score, losses and kills, message log, time and order of battle (2026-09-19)

**Status report.** New `conn/status_lua.py` generates one read-only Lua
script (indexed symbols only, every field guarded) that prints: title, tick,
Zulu, local time, elapsed and remaining; the side's score; losses, kills and
expenditures from the side wrapper when this build exposes them; the order
of battle with class, position, course, speed, altitude, fuel, damage,
mission, mounts, weapons and base; contacts with classification, posture,
position, speed and age; and missions with unit and target counts. For a
commander it is scoped to that side; for the designer it covers every side.

**Where it goes.** The commander's SITREP every turn is now this report
followed by the message log since that side's last turn. In design,
`BRIDGE_ATTACH: STATUS` (optional `side=<name>`, underscores for spaces)
injects it and uploads the console output with the next prompt.

**The message log.** CMO's AALog.txt is the message log written to disk;
it was already available on demand and per turn. It now carries, above the
lines, a tally of unit losses (component damage reports excluded), kills
taken from the side's own BDA reports, and score changes with their reasons,
which is what the Scoring Log tab shows.

**Fairness.** The AALog is CMO's global log with a [Side] prefix on each
line. A commander now receives only the lines its own message log would
show: its own side's lines and unprefixed lines. The other side's score
changes and loss reports are withheld; its kills appear through its own BDA
reports, as in the game. The designer sees everything.

**Verified.** The Lua passes the local checker and the API guard; a stub CMO
run prints every section and excludes the other side; the tally on your
real log finds fifteen Iranian and one American unit loss, matching the
scoreboard you pasted, with component reports excluded; per-turn prompts
carry the side's own losses, kills and score change and not the other
side's; the STATUS directive injects a side-scoped script and queues the
output file; 113 of 113 controls carry hover help; 203 smoke checks pass.

Confirm on your end: whether `VP_GetSide(...).losses`, `.kills` and
`.expenditures` are exposed on your build. If they are, the report prints
them; if not, it says so and the message-log tally covers it.

## Scenario message boxes and database lookups (2026-09-20)

**Message boxes.** New `conn/popups.py`. A scenario's `ScenEdit_MsgBox`
stops the clock and blocks the CMO window, including the Lua console. The
bridge now polls for one every second during any wait. The model declares
its answer before the window runs with `BRIDGE_ANSWER: YES` (or NO /
CANCEL; a sequence as `BRIDGE_ANSWER: NO; YES`). When a box appears the
bridge activates it, presses Tab to the wanted button and Enter, as
requested; it then checks the box closed, and if not, clicks the button's
live rectangle read from the box itself, then tries the accelerator letter.
The box's title, text and button labels are read from its child controls.
If a box appears with no answer declared, the wait ends at once (the box
has already stopped the clock), the next prompt carries POPUP PENDING with
the text and buttons, and nothing is injected until an answer is declared,
because the console is blocked. When a box is answered, the scenario resumes
its own clock; the toggle tracker is synced, and an answer given at the
start of a cycle is followed by a pause so the cycle proceeds in a known
state. Config under `popup.*`; `initial_focus_index` is the button that
holds focus when the box opens (0 = Yes on this build).

**Database lookups.** `BRIDGE_LOOKUP: <name>` (optional `type=Aircraft`)
answers in the next prompt with every v515 match: DBID, operator country,
service, year, hypothetical and deprecated flags, and for aircraft the valid
loadout IDs. A name with no exact match returns the nearest entries.

**Verified.** Answer parsing; a box appearing mid-window is answered with
two Tabs and Enter for Cancel and the wait runs to its full length; an
undeclared box ends a ten-second wait immediately and is recorded with its
buttons; the next cycle answers it with one Tab and Enter for No before any
injection, then pauses and syncs; with still no answer the cycle refuses to
inject and re-asks; a lookup for "P-8A Poseidon" returns eight entries
across five nations with loadouts, which is the trap the validator exists
for. 203 smoke checks pass.

Confirm on your end: that Yes holds focus when the box opens (if Tab lands
one button off, set `popup.initial_focus_index`), and that the box's window
title is "Incoming message" on your build.

## One-click scenario rebuild (2026-09-20)

Mission tab, "Scenario rebuild (one click)": a master .lua path and a
Rebuild in CMO button. The button injects one line,
`ScenEdit_RunScript('<path>', true)`, and CMO runs the file in place. For
Hormuz the master builds the scenario, embeds the pictures, applies the
realism settings and the computer-only sides through `ScenEdit_UpdateRSetting`
and `ScenEdit_SetSideOptions`, and saves the .scen with `Command_SaveScen`.
Verified: the injected line is exact and the smoke suite passes.
