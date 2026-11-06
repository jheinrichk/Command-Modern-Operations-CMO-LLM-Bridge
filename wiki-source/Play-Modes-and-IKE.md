# Play Modes and IKE

[[Home]] · [[CONN Interface|CONN-Interface]] · [[Automation and Safety|Automation-and-Safety]]

## Modes

CONN documents Scenario Development plus four ways to use a loaded scenario:

| Mode | Operator model |
| --- | --- |
| Normal Play | Human plays normally while CONN observes |
| Player vs LLM | Human and model command opposite sides |
| LLM vs LLM | Two model commanders exchange turns |
| Head to Head PBEM | Human players exchange save files in a turn framework |

The latter three modes depend on **IKE**, an independent third-party PBEM/hotseat framework, and require additional installation/configuration. See [musurca/IKE](https://github.com/musurca/IKE).

## Turn state machine

```text
AWAIT_TURN → SITREP → ORDERS → ARBITER → INJECT → END_TURN → HANDOFF
```

On a model turn, a read-only SITREP gives the agent current CMO state. The agent proposes bounded orders subject to its commander profile, objectives, ROE and order budget. The arbiter checks side and editor restrictions before injection.

Human turns stop at a gate until the player explicitly advances. Mode selection alone does not authorize CONN to act as an unsupervised human player.

## Safe IKE conversion sequence

The CONN documentation specifies this order:

1. Snapshot the master into `SNAPSHOTS`.
2. Keep the master protected from edits.
3. Convert **a working copy**, never the original.
4. Run IKE's separately installed conversion Lua and answer its dialog.
5. Save As and Verify the converted file.
6. Record the source, snapshot, sides, turn length and hash in an `.ike.json` sidecar.

Conversion is one-way. The Verify step is intended to ensure the result is nonempty and distinct from the preconversion working copy.

## PBEM handoff

After conversion, each commander loads the appropriate turn, reviews the situation, makes the allowed moves and ends the turn. The exchanged `.save` file carries the game to the opponent. Some scenarios include author-scripted decisions in addition to ordinary CMO orders; IKE and the scenario must both support the chosen workflow.

CONN's PBEM code scaffolds this workflow, but a supported, fully calibrated IKE setup must be tested before relying on automated end-to-end play. The author-provided scenarios may offer their own PBEM options and instructions independently of CONN.

## What is not included

- The IKE software itself.
- Multiplayer services or accounts.
- A universal direct CMO API or direct chatbot-provider API.
- A guarantee that every existing scenario supports safe commander automation without adaptation.

Source: [docs/CONN.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/CONN.md) and [musurca/IKE](https://github.com/musurca/IKE).
