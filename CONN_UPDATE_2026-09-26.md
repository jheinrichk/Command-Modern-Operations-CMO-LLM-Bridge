# CONN UPDATE 2026-09-26: review of the UI and the run loop

This build also carries the 2026-09-25 fixes (see CONN_UPDATE_2026-09-25.md).
Your install was still on the 2026-09-07 build: CONN waited 0 seconds for
LLM, looped on reprint requests, stopped after 2 cycles and ended play runs
after 1 turn. Those values are repaired automatically on first start.

Left exactly as they were: the calibration (anchors and layouts in your
bridge_config.json), the play/pause start and stop and time compression
(cmo_sim_control.py and the engine's play, pause, compress and run-for code
are byte-for-byte the same).

## Bugs fixed

**CONN clicked itself after every Lua run.** In your LLM_SCEN_DEV layout the
`cmo_popup_ok` point sits under CONN's always-on-top window, so each injection
pressed whatever CONN control was at that spot. Any click that would land on
CONN's own window is now skipped and logged. Preflight has a new row, "No anchor
under CONN's own window", that lists covered anchors.

**A closed or minimized Lua console.** The script was pasted into whatever had
focus. The copy back was then read as if CMO had run it. A minimized window also
resolved to -32000 and drove the pointer into a corner. Now a minimized window
is restored without taking focus. A step that cannot land stops the run
with a message that says which anchor failed.

**A Lua error in the script.** The END marker never printed, so CONN waited
90 s and then read the whole console pane, old BRIDGE_DONE and state lines
included. That could end a run as "fulfilled". Now CONN stops waiting within a
few seconds and reads only what followed this run's BEGIN marker.

**The post-run read after a test window** returned the pre-run output again.
It now returns only what was printed after the run.

**Stale reply.** If the new reply had not rendered yet, the copy anchor could
land on the previous reply's code block and rerun the last script. A copy
identical to the last accepted reply is now treated as "not there yet". If
that lasts the whole wait, the run stops.

**Reprint requests arrived empty.** They were 3,700 characters, over the paste
limit, so the browser turned them into an empty attachment chip. They are now
under 300 characters.

**Popups.** An open box that was already reported ended every wait at once,
which turned the reply wait into a tight loop. A box closed by hand kept the
run asking for an answer every cycle. The POPUP PENDING notice was dropped when
the RAG was unavailable. Answers from an old cycle could answer a later box.
All four are fixed. BRIDGE_ANSWER now goes inside the Lua block as a comment,
because only the code block is copied back.

**Abort.** Ctrl+Alt+X and pyautogui's corner fail-safe now stop the run at the
next input. The abort flag no longer stays set after a run, where it broke the
next IKE or Rebuild. The hotkey no longer touches the window from its own
thread.

**Settings file safety.** A bridge_config.json that could not be read (a
byte-order mark from Notepad or PowerShell, a typo) made CONN start on defaults
and then save them over your calibration. Now it loads files with a byte-order
mark. An unreadable file is kept as `bridge_config.bad-<time>.json` and
never overwritten. The first save of each session keeps
`bridge_config.backup.json`. Numbers stored as text ("2.0") are read as numbers,
and Settings saves 2.5 as 2.5 instead of text that made the run crash.

**Window matching.** A browser tab titled with "Lua Console" or "Command Modern
Operations" could be taken for CMO's window. Lua would then go into the browser.
Browser and CONN windows now only ever match their own entries.

**Layouts.** Changing the mode reset the active profile to the built-in
`scenario_dev` or `play`, so Start moved your windows away from the arrangement
the anchors were calibrated in. Your chosen profile now stays. Each mode
remembers its own. Two more fixes:
- Selecting text anywhere in CONN cleared the profile selection.
- A profile name with spaces was cut at the first space.

Capture now records the real stacking order. The topology key is now the same
from one launch to the next; before, it changed every time CONN started.

**Play modes.**
- A bare "VICTORY" in a sitrep or intent line ended LLM vs LLM after turn 1.
- One side's map and log attachments went into the other side's prompt.
- The side lock rejected legitimate orders that only read a contact's side.
- Rejected orders were never explained to the commander.
- Normal play logged "MONITOR" every 2 seconds.

**Editor lock** missed `Name{...}` and aliased calls. It no longer blocks the
operator's own Rebuild or IKE conversion.

**IKE.** Verify passed a file that was never converted. It now fails until
the file differs from the copy CONN made. An earlier converted file is kept,
not overwritten.

**Theme repaint** turned the calibration overlay into an opaque full-screen
sheet after a dry-run toggle. It also painted all preflight dots one colour.

**Legacy calibration window** could empty bridge_config.json on a failed load
and overwrote CONN's settings on every save. It now writes only its own
coordinates in one atomic write. CONN keeps them.

## Improvements

- The mission request, opening stage and mode come back on the next launch.
- Start is greyed out during a run. Pause and Step are greyed out when idle.
- Rebuild in CMO reads the console when the build finishes and logs the key
  lines (created=, failed=, SAVED, errors). It refuses to run during a run, and
  Start waits for it.
- Monitor tab:
  - The Lua and output boxes no longer jump back to the top every 120 ms.
  - The log has a scrollbar and stops following while you scroll up.
  - The log stays bounded.
  - New "Copy log" and "Session folder" buttons.
  - Stage chips for AUDIT, PLAYTEST and FIX.
- Every run that ends for a reason other than success shows a stop box, so it
  is visible when you come back. Internal errors log a traceback and export the
  session.
- Before attaching a file, CONN checks that the Open dialog is up. A missed
  Ctrl+U used to paste the path into the chat and send it. Settings has a
  switch to turn this check off if your browser's dialog is not detected.
- A changed abort hotkey takes effect on Save. A typo such as "crtl" is
  refused instead of registering Alt+X.
- Preflight in Normal mode no longer blocks on LLM anchors.
- An empty PBEM folder setting no longer passes as ".".

## Tests

All smoke tests pass, including five new groups for these fixes. The tests
run on a temporary copy of the config and cannot touch the real one. Your
bridge_config.json was byte-identical before and after the full test run.

## Install

This zip has no bridge_config.json, so your calibration and layouts stay.
Extract it to `C:\Users\USER\Desktop\CMO_LLM_Bridge` and choose "Replace the
files in the destination". On first start the log shows "config migrated"
lines for the repaired waits, cycle budget and turn cap.
