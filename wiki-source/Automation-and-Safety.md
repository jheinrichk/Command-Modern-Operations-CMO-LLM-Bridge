# Automation and Safety

[[Home]] · [[Getting Started|Getting-Started]] · [[Troubleshooting]]

CONN drives a live simulator through desktop controls. A wrong click or a bad Lua payload can change the scenario, so the control philosophy is: **never advance production faster than the work can be understood, coordinated and verified**.

## Dry Run is the first barrier

When enabled, Dry Run changes CONN to amber, prevents synthesized clicks/typing/pasting and prevents Lua injection. It uses stub feedback to rehearse the sequence. Transition to live operation requires an explicit confirmation and changes the appearance of the interface.

## Preflight before Start

Preflight checks the host and dependencies, target windows, six core anchors, writable paths, optional retrieval assets, and IKE setup when relevant. It also detects an anchor covered by CONN's own always-on-top window. Unset `cmo_scenario_start`, `cmo_scenario_reset` and `cmo_scenario_reload` anchors are reported rather than silently guessed.

## Validation of each generated step

1. Read the code block from the intended chat window and reject stale/empty/wrong copies.
2. Apply a syntax/balance check to catch obviously truncated Lua.
3. Screen CMO API symbol names against the local symbol index.
4. Enforce mode-specific editor and side locks.
5. Confirm the actual console target is visible and appropriate.
6. Execute, read only the matching marked output and return errors to the model.

The checker is deliberately conservative: syntax validity and a known API name do not establish that the *behavior* is safe or correct.

## Side and editor locks

Play-mode scripts are checked for prohibited scenario-editor operations and attempts to command a non-active side. Read-only inspection remains possible. An arbiter enforces these checks and the turn's order budget. Rejected actions return a reason rather than being silently omitted.

## Clipboard, browser and window guards

- Clipboard contents are saved and restored across transactions.
- A chat-title guard catches a different tab or unrelated browser window.
- Oversize text is sent through a configured attachment flow or chunked rather than blindly pasted.
- The browser code-block Copy control is preferred over whole-page select-all.
- Window-relative anchors reduce errors after moving or resizing windows.
- CONN refuses clicks under its own window and detects minimized/hidden targets.

## Stop and recovery logic

A failed Lua step normally triggers **FIX_ERRORS**. A run has limits for repetitive failures, non-progress, invalid replies, maximum cycle count and elapsed waits. The operator can **Abort** or use `Ctrl+Alt+X`.

Successful completion is judged from actual printed terminal state or the engine's DONE state, not a model's optimistic commentary.

## Data and scenario protection

- Work on a copied scenario during construction and testing.
- Preserve a known-good master and review script diffs.
- Do not infer unit IDs or loadouts from names alone.
- Use IKE finalization only on a copy; the conversion is not reversible.
- Review transcripts and logs after each meaningful stage.
- Never treat the chat model's ability to propose Lua as proof it ran successfully.

Complete details: [docs/CONN.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/CONN.md).
