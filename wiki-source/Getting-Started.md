# Getting Started

[[Home]] · [[CONN Interface|CONN-Interface]] · [[Troubleshooting]]

## Prerequisites

CMO LLM Bridge runs its GUI automation **on Windows**, alongside Command: Modern Operations, its Lua Script Console and a selected LLM chat window. Python must include Tkinter. The requirements file specifies the Python packages needed by the bridge.

```powershell
git clone https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge.git
cd Command-Modern-Operations-CMO-LLM-Bridge
python -m pip install -r requirements.txt
python conn.py
```

There is no provider-key configuration step: the bridge's normal chat integration is calibrated GUI interaction, not an LLM API connector.

## 1. Identify the four windows

Open (1) CMO, (2) CMO Lua Script Console, (3) your LLM chat in a supported browser and (4) CONN itself.

In CONN's **Layout** area, refresh the window list and make sure `llm`, `cmo`, `cmo_lua` and `conn` resolve to the intended windows. If the LLM window is not found, adjust the configured browser/chat title matching and use the separate *LLM tab must contain* setting as an additional safeguard.

## 2. Save the working layout

Keep **DRY RUN** switched on. Position CMO, the console and browser so controls are not hidden. Use **Layout → Capture current** to save a named desktop profile. Select it (the active choice has an asterisk). Later, **Apply Layout** restores the arrangement; a Mission-tab option can apply it when a run starts.

A layout positions windows. **Calibration** identifies a particular button or field *inside* each window. Both are needed.

## 3. Calibrate the six mandatory anchors

On the Calibration tab choose an anchor, press **Capture point**, hold the pointer on the real target for the countdown and save. Use a visible LLM code-block response when calibrating its Copy button.

| Anchor | Target |
| --- | --- |
| `llm_input` | LLM chat input field |
| `llm_submit` | LLM Send button |
| `llm_code_copy` | Copy button of the Lua response code block |
| `cmo_lua_input` | CMO Lua console input editor |
| `cmo_execute` | Execute/Run button in the Lua console |
| `cmo_output_area` | CMO console output/results pane |

Anchors are saved relative to a tracked window. Pixel offsets are used near window edges, while fractional coordinates track inner areas. Recalibrate when zoom, display scaling or the actual internal layout changes.

Use **Show overlay** to inspect anchor positions. In Dry Run, **Test click** logs the target without clicking; in live mode it can actually press Execute or Send.

## 4. Review settings and knowledge

- Check the chat Copy method and attachment route. The default Ctrl+U attachment shortcut is **not universal** across chat interfaces.
- Check output wait limits, reply polling, maximum iterations and run stop conditions.
- Run `python cmo_rag.py --build` when you need to rebuild local retrieval indexes.
- Use database extraction against the CMO installation for authoritative DBID/loadout mappings; name-only lookup references are insufficient for unit creation.
- Choose an opening stage. **AUDIT** is useful for examining an already loaded scenario, whereas **DESIGN** is for generating a scenario.

## 5. Run Preflight and rehearse

Visit **Preflight → Run checks**. Check dependencies, window identification, anchors, writable folders, RAG index and (when relevant) IKE paths. Resolve blocking findings before going live.

Start with Dry Run, which rehearses the cycle without injecting Lua, clicking real targets or pasting into CMO. Once calibration is correct, turn Dry Run off and confirm the color change to the blue/dark live palette.

## 6. Begin a bounded task

Select **Scenario Development**, enter a concrete request, and click **Start**. CONN will drive the exchange and display steps in the monitor. A good first live task is a **read-only audit of an open disposable scenario**, not the modification of an important master.

Use **Pause** and **Step** to inspect intermediate operations. **Abort** or `Ctrl+Alt+X` stops further actions.

## 7. Review the saved session

Each run creates a `SESSIONS` directory containing an event log, transcript, deployed Lua files, successive diffs and a summary report. Review the console's actual output, any failures and the generated scripts before reusing changes in a production scenario.

## Next pages

[[Scenario Development Workflow|Scenario-Development-Workflow]] · [[Knowledge Pack and RAG|Knowledge-Pack-and-RAG]] · [[Automation and Safety|Automation-and-Safety]]

Authoritative installation detail: [docs/SETUP.md](https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/blob/main/docs/SETUP.md).
