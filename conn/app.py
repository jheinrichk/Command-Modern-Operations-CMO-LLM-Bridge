"""
conn.app  -  CONN, the control surface for the CMO LLM Bridge.

Tabs
    Mission      scenario prompt, run controls, IKE finalization
    Play         mode settings, sides, turn rules, commander profiles
    Monitor      the process monitor (also available undocked as a strip)
    Calibration  window-relative anchors, live, with an on-screen overlay
    Layout       arrangement profiles, capture and apply, strip reservation
    Preflight    go / no-go checks with per-row fixes
    Settings     folders, timing, safety
"""

import os
import re
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import theme
from .anchors import AnchorResolver, anchors_to_absolute, migrate_absolute
from .config import Config, num
from .engine import Aborted, Engine, Halted
from .hotkeys import GlobalHotkey
from .layouts import LayoutManager, rect_to_frac
from .monitor import MonitorPanel, stamp
from .overlay import AnchorOverlay, capture_point
from .preflight import run_preflight, summarize
from .winmgr import IS_WINDOWS, Rect, WindowManager
from .tooltips import tip, set_palette as tip_palette

MODES = [
    ("design", "Scenario Development"),
    ("normal", "Normal Play (monitor only)"),
    ("player_vs_llm", "Player vs LLM"),
    ("llm_vs_llm", "LLM vs LLM"),
    ("pbem_h2h", "Head to Head PBEM"),
]
MODE_LABELS = {k: v for k, v in MODES}
DRY_ON_TEXT = "DRY RUN  no clicks or keys"
DRY_OFF_TEXT = "DRY RUN off  live input"
LABEL_MODES = {v: k for k, v in MODES}


class ConnApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = Config()
        self.title("CONN  -  CMO LLM Bridge")
        # provisional; replaced by _fit_to_content() once the tabs exist so
        # every tab is fully visible at launch on any screen or DPI
        self.geometry("1180x820")
        self.minsize(900, 600)

        self.bus = queue.Queue()
        # the window watcher, the hotkey thread and the engine run off the Tk
        # thread; they log through the queue, never by touching widgets
        self.wm_ = WindowManager(self.cfg, log=self._tlog)
        self.resolver = AnchorResolver(self.cfg, self.wm_)
        self.layouts = LayoutManager(self.cfg, self.wm_, log=self.log)
        self.engine = Engine(self.cfg, self.wm_, self.resolver, self.bus)
        self.overlay = AnchorOverlay(self, self.cfg, self.wm_, self.resolver)

        self.dry_run = tk.BooleanVar(value=bool(self.cfg.get("ui.dry_run_default", True)))
        # reopen in the mode used last time
        self.mode_var = tk.StringVar(value=MODE_LABELS.get(
            str(self.cfg.get("play.mode", "design")), MODE_LABELS["design"]))
        self.engine.state["mode"] = self.current_mode()   # the monitor header shows it
        self.apply_layout_on_start = tk.BooleanVar(value=True)
        self.state = dict(self.engine.state)
        self.state["paused"] = False
        self.pal = theme.palette(self.dry_run.get())
        self.panels = []
        self.strip = None
        self._windows_dirty = threading.Event()
        self._ike_result = None
        self._ike_busy = False
        self._rebuild_busy = False
        self._was_running = None
        self._save_warned = False

        self._build()
        self.engine.set_dry_run(self.dry_run.get())
        theme.apply_theme(self, self.pal)
        tip_palette(self, self.pal)
        # fonts and theme metrics settle after the first full update; fit once
        # more then so the launch size is right on every screen and DPI
        self.after_idle(self._fit_to_content)
        self.after_idle(self._refresh_clock_method_label)
        self._apply_dry_run_visuals()

        self.wm_.refresh()
        mode = self.wm_.start_watch(self._on_windows_changed,
                                    int(self.cfg.get("ui.watch_rate_ms", 250)))
        self.log("window tracking: {} ({}, dpi {})".format(
            mode, "windows" if IS_WINDOWS else "no-op off Windows", self.wm_.dpi_mode))

        self.hotkey = GlobalHotkey(self.cfg.get("safety.abort_hotkey", "ctrl+alt+x"),
                                   self._hotkey_abort, log=self._tlog)
        self.hotkey.start()
        self.bind("<Escape>", lambda _e: self.abort())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._pump_id = self.after(120, self._pump)
        self.refresh_calibration()
        self.refresh_layouts()
        self.run_preflight()
        self._sync_run_buttons(force=True)
        for m in getattr(self.cfg, "migrated", []) or []:
            self.log("config migrated: " + m)
        self.cfg.migrated = []          # shown once, not again at every Start
        if self.cfg.load_error:
            msg = ("bridge_config.json could not be read, so CONN started with built-in "
                   "defaults and will NOT save over it (your calibration is safe on "
                   "disk).\n\n{}\n\nFix the file or restore bridge_config.backup.json, "
                   "then restart CONN.".format(self.cfg.load_error))
            self.log("CONFIG NOT LOADED: " + self.cfg.load_error)
            if not os.environ.get("CONN_NO_DIALOGS"):
                self.after(300, lambda: messagebox.showwarning("CONN settings", msg))

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def _build(self):
        self._build_header()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._tab_mission()
        self._tab_play()
        self._tab_monitor()
        self._tab_calibration()
        self._tab_layout()
        self._tab_preflight()
        self._tab_settings()
        self.status = ttk.Label(self, text="ready", style="Muted.TLabel", anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0, 6))
        self._fit_to_content()

    def _fit_to_content(self):
        """Size the window so the largest non-scrolling tab is fully visible,
        capped to the screen, and centre it. The window stays resizable."""
        try:
            self.update_idletasks()
            need_w, need_h = 0, 0
            for t in self.nb.tabs():
                w = self.nametowidget(t)
                if getattr(w, "_conn_scrolls", False):
                    continue          # a scrolling tab never dictates height
                need_w = max(need_w, w.winfo_reqwidth())
                need_h = max(need_h, w.winfo_reqheight())
            chrome_w = 40
            chrome_h = 150            # header, tab strip, status bar, padding
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w = min(int(sw * 0.94), max(1180, need_w + chrome_w))
            h = min(int(sh * 0.92), max(820, need_h + chrome_h))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 3)
            self.geometry("{}x{}+{}+{}".format(w, h, x, y))
            self.minsize(min(900, w), min(600, h))
            # On a small screen the Monitor tab can still be taller than the
            # window. Its log box is the only elastic part, so shorten it
            # until the tab fits rather than let the bottom controls clip.
            avail = h - chrome_h - 16      # margin for font metrics that settle late
            for p in self.panels:
                if not p.winfo_exists():
                    continue
                tab = p.master
                # elastic boxes, shrunk in this order, never below their floor
                boxes = [(p.log, 4), (getattr(p, "out_box", None), 2),
                         (getattr(p, "lua_box", None), 2), (getattr(p, "rag", None), 2)]
                for _ in range(24):
                    tab.update_idletasks()
                    if tab.winfo_reqheight() <= avail:
                        break
                    shrunk = False
                    for box, floor in boxes:
                        if box is None:
                            continue
                        lines = int(box.cget("height"))
                        if lines > floor:
                            box.configure(height=lines - 1)
                            shrunk = True
                            break
                    if not shrunk:
                        break
        except tk.TclError:
            pass

    def _build_header(self):
        bar = ttk.Frame(self, style="TFrame")
        bar.pack(fill="x", padx=8, pady=8)

        # right side first so the run controls always keep their width
        tip(ttk.Button(bar, text="Abort", width=7, style="Danger.TButton",
                       command=self.abort),
            "Stop the run immediately. Nothing more is clicked or typed. The global "
            "abort hotkey in Settings does the same from any window.").pack(side="right", padx=2)
        self.btn_step = tip(ttk.Button(bar, text="Step", width=6, command=self.step),
                            "Release the current wait. Used when CONN is waiting for you: "
                            "a human turn, an IKE hand-off, loading an incoming save.")
        self.btn_step.pack(side="right", padx=2)
        self.btn_pause = tip(ttk.Button(bar, text="Pause", width=8, command=self.toggle_pause),
                             "Hold the run between steps without ending it. Press again to resume.")
        self.btn_pause.pack(side="right", padx=2)
        self.btn_start = tip(ttk.Button(bar, text="Start", width=8, style="Accent.TButton",
                                        command=self.start),
                             "Begin a run in the selected mode using the mission text. "
                             "Calibration must be complete for the windows the mode needs.")
        self.btn_start.pack(side="right", padx=(10, 6))
        tip(ttk.Button(bar, text="Apply Layout", width=13,
                       command=lambda: self.apply_layout()),
            "Move and size every tracked window to the profile selected on the Layout "
            "tab. Windows that are not open are reported as missing.").pack(side="right", padx=2)

        ttk.Label(bar, text="CONN", style="Head.TLabel",
                  font=("Segoe UI", 16, "bold")).pack(side="left", padx=(2, 12))
        ttk.Label(bar, text="Mode").pack(side="left")
        cb = ttk.Combobox(bar, textvariable=self.mode_var, width=24, state="readonly",
                          values=[label for _k, label in MODES])
        tip(cb, "Scenario Development: build and playtest through the Lua console.\n"
                "Normal Play: CONN only watches; it never injects.\n"
                "Player vs LLM: you hold one side, a commander agent holds the other.\n"
                "LLM vs LLM: two commander agents alternate under an arbiter.\n"
                "Head to Head PBEM: turns arrive and leave as IKE save files.")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda _e: self.on_mode_change())

        self.dry_chk = tip(ttk.Checkbutton(
            bar, text=DRY_ON_TEXT, variable=self.dry_run, style="Dry.TCheckbutton",
            command=self.on_dry_run_toggle),
            "Dry run logs every click and keystroke CONN would make without sending "
            "any of them. Turn it off for a live run.")
        self.dry_chk.pack(side="left", padx=12)

    # -- Mission --------------------------------------------------------
    def _tab_mission(self):
        f = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(f, text="Mission")

        top = ttk.Labelframe(f, text="Scenario request")
        top.pack(fill="both", expand=True, padx=10, pady=8)
        self.prompt = tip(tk.Text(top, height=10, wrap="word", font=("Consolas", 10)),
                          "The request sent to LLM each cycle, after the retrieved CMO "
                          "context. For a playtest, describe the side, the clicks planned "
                          "and what to verify.")
        self.prompt.pack(fill="both", expand=True, padx=8, pady=8)
        # the request typed last time comes back; it used to reset on launch
        self.prompt.insert("1.0", str(self.cfg.get("ui.last_prompt", "") or
                                      "Design a balanced Strait of Hormuz surface action "
                                      "scenario: Blue escort group against Red missile boat "
                                      "swarm, one decisive engagement, two hour window."))
        row = ttk.Frame(top, style="TFrame")
        row.pack(fill="x", padx=8, pady=(0, 8))
        tip(ttk.Checkbutton(row, text="Apply the layout profile when the run starts",
                            variable=self.apply_layout_on_start),
            "Arrange the windows to the active Layout profile before the first "
            "cycle, so the calibrated anchors line up.").pack(side="left")
        self.var_aalog_cycle = tk.BooleanVar(value=bool(self.cfg.get("bridge.attach_aalog_each_cycle", False)))
        tip(ttk.Checkbutton(row, text="AALog every cycle",
                            variable=self.var_aalog_cycle,
                            command=lambda: self.cfg.set("bridge.attach_aalog_each_cycle",
                                                         bool(self.var_aalog_cycle.get()))),
            "Attach an excerpt of CMO's after-action log to every design cycle. Off, the "
            "model gets it only when it asks with BRIDGE_ATTACH: AALOG. It can also ask for "
            "MAPSHOT, EXCEPTIONLOG and LUAHISTORY.").pack(side="left", padx=(18, 0))
        ttk.Label(row, text="Opening stage").pack(side="left", padx=(18, 4))
        stages = ["DESIGN (build new)", "AUDIT (review loaded scenario)",
                  "PLAYTEST (play the loaded scenario)"]
        last = str(self.cfg.get("ui.last_stage", "") or "")
        self.start_stage = tk.StringVar(value=next((v for v in stages if v.startswith(last)),
                                                   stages[0]) if last else stages[0])
        tip(ttk.Combobox(row, textvariable=self.start_stage, width=34, state="readonly",
                         values=stages),
            "DESIGN builds a new scenario from the request.\n"
            "AUDIT inspects the loaded scenario first, then evaluates it.\n"
            "PLAYTEST plays the loaded scenario as the side you name; it never builds.").pack(side="left")

        ike = ttk.Labelframe(f, text="IKE PBEM finalization (one way: the master is snapshotted first)")
        ike.pack(fill="both", expand=True, padx=10, pady=8)
        r1 = ttk.Frame(ike, style="TFrame")
        r1.pack(fill="x", padx=8, pady=6)
        ttk.Label(r1, text="Master .scen").pack(side="left")
        self.master_scen = tk.StringVar(value="")
        tip(ttk.Entry(r1, textvariable=self.master_scen),
            "The master .scen to convert. It is snapshotted to Snapshots as "
            "name_vNN_preIKE.scen before anything runs; conversion is one way.").pack(side="left", fill="x",
                                                          expand=True, padx=6)
        tip(ttk.Button(r1, text="Browse", command=self.browse_master),
            "Pick the master scenario file.").pack(side="left")
        r2 = ttk.Frame(ike, style="TFrame")
        r2.pack(fill="x", padx=8, pady=(0, 6))
        tip(ttk.Button(r2, text="Finalize for PBEM", style="Accent.TButton",
                       command=self.finalize_ike),
            "Snapshot the master, inject the IKE conversion Lua, then answer IKE's "
            "questions in CMO. Answer No to 'prevent Editor mode' if the LLM will "
            "play a side: the Lua console CONN uses is part of the editor.").pack(side="left")
        tip(ttk.Button(r2, text="Verify converted file",
                       command=self.verify_ike),
            "Check that the saved file carries IKE's turn data and that the "
            "playable sides match the Play tab.").pack(side="left", padx=6)
        self.ike_steps = tip(tk.Text(ike, height=8, wrap="word", font=("Consolas", 9)),
                             "Progress of the last IKE finalization, step by step.")
        rb = ttk.Labelframe(f, text="Scenario rebuild (one click)")
        rb.pack(fill="x", padx=10, pady=(0, 8))
        r3 = ttk.Frame(rb, style="TFrame")
        r3.pack(fill="x", padx=8, pady=6)
        ttk.Label(r3, text="Master .lua").pack(side="left")
        self.master_lua = tk.StringVar(value=str(self.cfg.get("build.master_lua", "")))
        tip(ttk.Entry(r3, textvariable=self.master_lua),
            "A Lua file CMO runs in place (ScenEdit_RunScript with the full path). For Hormuz "
            "this is HORMUZ_2026_MASTER.lua: it rebuilds, embeds the pictures, applies the "
            "realism settings and computer-only sides, and saves the .scen.").pack(side="left", fill="x", expand=True, padx=6)
        tip(ttk.Button(r3, text="Browse", command=self.browse_master_lua),
            "Pick the master .lua file.").pack(side="left")
        tip(ttk.Button(r3, text="Rebuild in CMO", style="Accent.TButton", command=self.rebuild_in_cmo),
            "Inject one line into the Lua console that runs the master file. Watch the console "
            "for created=154 failed=0 and the SAVED line. Takes about a minute.").pack(side="left", padx=6)
        self.ike_steps.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.ike_steps.configure(state="disabled")

    # -- Play -----------------------------------------------------------
    def _tab_play(self):
        f = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(f, text="Play")
        self.play_vars = {}

        g = ttk.Labelframe(f, text="Sides and turn rules")
        g.pack(fill="x", padx=10, pady=8)
        fields = [
            ("play.my_side", "My side"),
            ("play.opponent_side", "Opponent side"),
            ("play.turn_length_minutes", "Turn length (min)"),
            ("play.order_deadline_minutes", "Order deadline (min)"),
            ("play.turn_cap", "Turn cap"),
            ("play.order_budget_per_turn", "Order budget per turn"),
        ]
        help_for = {
            "play.my_side": "The side you play, spelled exactly as the scenario names it.",
            "play.opponent_side": "The side the LLM commander plays, spelled exactly as the "
                                  "scenario names it. In LLM vs LLM both sides get an agent.",
            "play.turn_length_minutes": "Simulated minutes per turn. For an IKE scenario, "
                                        "match the turn length chosen at conversion.",
            "play.order_deadline_minutes": "How long CONN waits for you to give orders on "
                                           "your turn before reminding you to press Step.",
            "play.turn_cap": "The run stops after this many turns unless the scenario ends first.",
            "play.order_budget_per_turn": "Maximum discrete orders the LLM may issue in one turn.",
        }
        for i, (key, label) in enumerate(fields):
            ttk.Label(g, text=label).grid(row=i // 3, column=(i % 3) * 2,
                                          sticky="e", padx=6, pady=4)
            v = tk.StringVar(value=str(self.cfg.get(key, "")))
            self.play_vars[key] = v
            tip(ttk.Entry(g, textvariable=v, width=16), help_for.get(key, "")).grid(
                row=i // 3, column=(i % 3) * 2 + 1, sticky="w", padx=6, pady=4)

        t = ttk.Frame(g, style="TFrame")
        t.grid(row=3, column=0, columnspan=6, sticky="w", padx=6, pady=4)
        self.var_arbiter = tk.BooleanVar(value=bool(self.cfg.get("play.arbiter_enabled", True)))
        self.var_sidelock = tk.BooleanVar(value=bool(self.cfg.get("play.side_lock", True)))
        self.var_editorlock = tk.BooleanVar(
            value=bool(self.cfg.get("safety.editor_lock_in_play_modes", True)))
        tip(ttk.Checkbutton(t, text="Arbiter checks orders", variable=self.var_arbiter),
            "Review every LLM order script before injection: refuses editor calls, "
            "unbalanced Lua and orders over budget.").pack(side="left", padx=6)
        tip(ttk.Checkbutton(t, text="Side lock", variable=self.var_sidelock),
            "Refuse any LLM order that names a side other than the one on the clock. "
            "Keep this on: IKE treats side switching as corruption.").pack(side="left", padx=6)
        tip(ttk.Checkbutton(t, text="Editor lock in play modes",
                            variable=self.var_editorlock),
            "Block editor functions (add or delete units and sides, set time, set score) "
            "in every play mode. ScenEdit_SetTime trips IKE's anti-cheat.").pack(side="left", padx=6)

        # play-mode switches the engine honours but the UI never exposed
        t2 = ttk.Frame(g, style="TFrame")
        t2.grid(row=4, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 4))
        self.var_ike_hotseat = tk.BooleanVar(value=bool(self.cfg.get("play.ike_hotseat", False)))
        self.var_rag_play = tk.BooleanVar(value=bool(self.cfg.get("play.rag_enabled", True)))
        self.var_rag_learn = tk.BooleanVar(value=bool(self.cfg.get("play.rag_learn_in_play", False)))
        self.var_aalog_turn = tk.BooleanVar(value=bool(self.cfg.get("play.attach_aalog_each_turn", True)))
        self.var_mapshot_turn = tk.BooleanVar(value=bool(self.cfg.get("play.attach_mapshot_each_turn", False)))
        tip(ttk.Checkbutton(t2, text="IKE hotseat: run the LLM's turn after its orders",
                            variable=self.var_ike_hotseat),
            "After the LLM's orders are injected, CONN presses play and waits the turn "
            "length at your manual compression. IKE stops the clock at the turn boundary "
            "and raises the hand-off notice; CONN then waits for Step.").pack(side="left", padx=6)
        tip(ttk.Checkbutton(t2, text="RAG context for the LLM commander",
                            variable=self.var_rag_play),
            "Give the commander retrieved doctrine, mission and posture knowledge with "
            "its orders prompt. Retrieval happens during the order phase, while the clock "
            "is stopped. Your own turns never touch the RAG.").pack(side="left", padx=6)
        t4 = ttk.Frame(g, style="TFrame")
        t4.grid(row=6, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 4))
        tip(ttk.Checkbutton(t4, text="Give the LLM the after-action log each turn",
                            variable=self.var_aalog_turn),
            "Append the lines CMO wrote to AALog.txt since this side's last turn to the "
            "commander's SITREP, with a digest of kills, hits, launches and contacts. "
            "Each side has its own marker, so it sees only the interval it was away.").pack(side="left", padx=6)
        tip(ttk.Checkbutton(t4, text="Attach a map screenshot each turn",
                            variable=self.var_mapshot_turn),
            "Capture the CMO map before the commander's orders and upload it with the "
            "prompt. A minimized or small map window is restored and resized without "
            "taking focus, captured, then put back exactly as it was.").pack(side="left", padx=6)
        t3 = ttk.Frame(g, style="TFrame")
        t3.grid(row=5, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 6))
        ttk.Label(t3, text="CMO clock right now:").pack(side="left")
        self.var_clock_running = tk.BooleanVar(value=False)
        tip(ttk.Radiobutton(t3, text="paused", value=False, variable=self.var_clock_running,
                            command=self._clock_state_changed),
            "Tell CONN the clock is stopped. The play control is one toggle button, so "
            "CONN must know the true state or its next press does the opposite of what "
            "it intends. Set this after starting or stopping the clock by hand.").pack(side="left", padx=6)
        tip(ttk.Radiobutton(t3, text="running", value=True, variable=self.var_clock_running,
                            command=self._clock_state_changed),
            "Tell CONN the clock is running. Use this if you pressed play yourself "
            "and CONN did not.").pack(side="left", padx=6)
        self.lbl_clock_method = ttk.Label(t3, text="", style="Muted.TLabel")
        self.lbl_clock_method.pack(side="left", padx=12)
        tip(self.lbl_clock_method,
            "How CONN drives the clock: the calibrated click on the play/pause button "
            "first, then the Space key if the click cannot be made. Change under "
            "cmo_controls in bridge_config.json.")
        tip(ttk.Checkbutton(t2, text="Learn from LLM turns",
                            variable=self.var_rag_learn),
            "Harvest RAG_NOTE lines from the LLM's orders into the lesson store. Off by "
            "default: in LLM vs LLM a note can describe the other side's positions. When "
            "on, each lesson is tagged with its side and only that side can retrieve it.").pack(side="left", padx=6)

        self.agent_text = {}
        for side_key, title in (("blue", "Blue commander"), ("red", "Red commander")):
            lf = ttk.Labelframe(f, text=title)
            lf.pack(fill="both", expand=True, padx=10, pady=6)
            boxes = {}
            for i, (fk, lab) in enumerate((("objectives", "Objectives"),
                                           ("roe", "Rules of engagement"),
                                           ("persona", "Persona"))):
                ttk.Label(lf, text=lab).grid(row=i, column=0, sticky="ne", padx=6, pady=3)
                txt = tip(tk.Text(lf, height=2, wrap="word", font=("Consolas", 9)),
                          {"objectives": "What this commander is trying to achieve. Goes into "
                                         "every orders prompt for the side.",
                           "roe": "Rules of engagement the commander must respect, in plain "
                                  "words. The arbiter does not enforce these; the prompt does.",
                           "persona": "How the commander thinks: cautious, aggressive, "
                                      "doctrine-bound. One or two sentences."}[fk])
                txt.grid(row=i, column=1, sticky="ew", padx=6, pady=3)
                txt.insert("1.0", str(self.cfg.get("play.agents.{}.{}".format(side_key, fk), "")))
                boxes[fk] = txt
            lf.grid_columnconfigure(1, weight=1)
            self.agent_text[side_key] = boxes

        tip(ttk.Button(f, text="Save play settings", command=self.save_play),
            "Write the sides, turn rules, switches and commander profiles to "
            "bridge_config.json. Applies to the next run.").pack(
            anchor="e", padx=12, pady=(0, 10))

    # -- Monitor --------------------------------------------------------
    def _tab_monitor(self):
        f = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(f, text="Monitor")
        bar = ttk.Frame(f, style="TFrame")
        bar.pack(fill="x", padx=10, pady=(8, 0))
        tip(ttk.Button(bar, text="Undock strip", command=self.toggle_strip),
            "Open the monitor as a narrow always-on-top strip at the screen edge, "
            "so it stays visible beside CMO. Press again to dock it back.").pack(side="left")
        tip(ttk.Button(bar, text="Export session", command=self.export_session),
            "Write the current session's transcript, scripts, events and report "
            "to the Sessions folder.").pack(side="left", padx=6)
        p = MonitorPanel(f, self)
        p.pack(fill="both", expand=True, padx=6, pady=6)
        self.panels.append(p)

    # -- Calibration ----------------------------------------------------
    def _tab_calibration(self):
        f = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(f, text="Calibration")
        info = ("Anchors are stored inside a window, not on the screen. Move or resize a "
                "window and the targets follow it, so calibration survives rearranging.")
        ttk.Label(f, text=info, style="Muted.TLabel", wraplength=1050).pack(
            anchor="w", padx=12, pady=(8, 4))

        cols = ("window", "mode", "offset", "point", "status")
        self.cal_tree = ttk.Treeview(f, columns=cols, show="tree headings", height=16)
        self.cal_tree.heading("#0", text="anchor")
        self.cal_tree.column("#0", width=200, anchor="w")
        for c, w in zip(cols, (110, 60, 140, 140, 110)):
            self.cal_tree.heading(c, text=c)
            self.cal_tree.column(c, width=w, anchor="w")
        tip(self.cal_tree,
            "One row per anchor. window: which tracked window it lives in. mode: frac "
            "(fraction of the window) or px (pixels from a corner). status: usable "
            "means the window was found and the point resolves. Select a row, then "
            "Capture, Test click, Rebind or Clear.")
        self.cal_tree.pack(fill="both", expand=True, padx=10, pady=4)

        row = ttk.Frame(f, style="TFrame")
        row.pack(fill="x", padx=10, pady=6)
        ttk.Label(row, text="Capture countdown").pack(side="left")
        self.count_var = tk.IntVar(value=5)
        tip(ttk.Spinbox(row, from_=2, to=15, width=4, textvariable=self.count_var),
            "Seconds you get to move the mouse onto the target after pressing "
            "Capture point.").pack(side="left", padx=6)
        tip(ttk.Button(row, text="Capture point", style="Accent.TButton",
                       command=self.capture_anchor),
            "Record the mouse position for the selected anchor after the countdown. "
            "The point is stored relative to the window under the cursor, so it "
            "follows the window when it moves.").pack(side="left", padx=4)
        tip(ttk.Button(row, text="Test click", command=self.test_click),
            "Move the mouse to the selected anchor and click it once, so you can "
            "see it land where it should.").pack(side="left", padx=4)
        tip(ttk.Button(row, text="Rebind window", command=self.rebind_anchor),
            "Attach the selected anchor to a different tracked window without "
            "recapturing its position.").pack(side="left", padx=4)
        tip(ttk.Button(row, text="Clear", command=self.clear_anchor),
            "Remove the stored position for the selected anchor.").pack(side="left", padx=4)

        row2 = ttk.Frame(f, style="TFrame")
        row2.pack(fill="x", padx=10, pady=(0, 10))
        tip(ttk.Button(row2, text="Show overlay", command=self.toggle_overlay),
            "Draw a marker on screen at every resolved anchor so you can check "
            "them all at once. Press again to hide.").pack(side="left", padx=4)
        tip(ttk.Button(row2, text="Import legacy coordinates",
                       command=self.import_legacy),
            "Convert absolute screen coordinates from the old bridge config into "
            "window-relative anchors.").pack(side="left", padx=4)
        tip(ttk.Button(row2, text="Write absolute back (legacy bridge)",
                       command=self.write_absolute),
            "Export the current anchors as absolute screen coordinates for the "
            "old bridge. Only valid for the current window arrangement.").pack(side="left", padx=4)
        tip(ttk.Button(row2, text="Save", command=self.save_config),
            "Write the anchors to bridge_config.json.").pack(side="right", padx=4)

    # -- Layout ---------------------------------------------------------
    def _tab_layout(self):
        f = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(f, text="Layout")
        left = ttk.Frame(f, style="TFrame")
        left.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        ttk.Label(left, text="Profiles", style="Head.TLabel").pack(anchor="w")
        # exportselection=False: selecting text anywhere else in CONN used to
        # clear this selection, and Start then applied the built-in profile
        self.layout_list = tip(tk.Listbox(left, height=12, font=("Consolas", 10),
                                          exportselection=False),
                               "Saved window arrangements. Click one to make it the active "
                               "profile for the current mode (marked *); Start applies it. "
                               "Each stores every tracked window as a fraction of the "
                               "desktop. A name ending in @number is tied to one monitor "
                               "layout.")
        self.layout_list.pack(fill="both", expand=True, pady=4)
        self.layout_list.bind("<<ListboxSelect>>", lambda _e: self._on_layout_pick())
        self._layout_keys = []
        btns = ttk.Frame(left, style="TFrame")
        btns.pack(fill="x")
        tip(ttk.Button(btns, text="Apply", style="Accent.TButton",
                       command=lambda: self.apply_layout()),
            "Restore the selected profile: move and size every tracked window, "
            "including CONN. Windows that are not open are listed as missing; "
            "open them and apply again.").pack(side="left", padx=2)
        tip(ttk.Button(btns, text="Capture current", command=self.capture_layout),
            "Save where every tracked window is right now as a new profile. "
            "Arrange the windows first, then capture.").pack(side="left", padx=2)
        tip(ttk.Button(btns, text="Delete", command=self.delete_layout),
            "Remove the selected profile.").pack(side="left", padx=2)

        right = ttk.Frame(f, style="TFrame")
        right.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        ttk.Label(right, text="Tracked windows", style="Head.TLabel").pack(anchor="w")
        self.win_tree = ttk.Treeview(right, columns=("rect", "title"),
                                     show="tree headings", height=8)
        self.win_tree.heading("#0", text="key")
        self.win_tree.column("#0", width=90)
        self.win_tree.heading("rect", text="rect")
        self.win_tree.column("rect", width=190)
        self.win_tree.heading("title", text="title")
        self.win_tree.column("title", width=260)
        tip(self.win_tree,
            "The windows CONN tracks: llm, cmo, cmo_lua and conn. rect shows where "
            "each was last found; 'not found' means it is not open or its title "
            "changed. Refresh after opening a window.")
        self.win_tree.pack(fill="both", expand=True, pady=4)

        strip = ttk.Labelframe(right, text="Monitor strip")
        strip.pack(fill="x", pady=8)
        self.dock_side = tk.StringVar(value=self.cfg.get("ui.dock_side", "right"))
        self.strip_width = tk.IntVar(value=int(self.cfg.get("ui.strip_width", 320)))
        r = ttk.Frame(strip, style="TFrame")
        r.pack(fill="x", padx=6, pady=6)
        ttk.Label(r, text="Side").pack(side="left")
        tip(ttk.Combobox(r, textvariable=self.dock_side, width=8, state="readonly",
                         values=["right", "left"]),
            "Which screen edge the undocked monitor strip sits on.").pack(side="left", padx=6)
        ttk.Label(r, text="Width").pack(side="left")
        tip(ttk.Spinbox(r, from_=240, to=640, textvariable=self.strip_width,
                        width=6),
            "Width of the monitor strip in pixels.").pack(side="left", padx=6)
        tip(ttk.Button(r, text="Reserve space in profile",
                       command=self.reserve_strip),
            "Shrink every window in the selected profile away from that edge and "
            "put the strip in the freed band, so nothing overlaps.").pack(side="left", padx=6)
        tip(ttk.Button(r, text="Refresh windows", command=self.refresh_windows),
            "Re-scan the desktop for the tracked windows.").pack(side="right")

    # -- Preflight ------------------------------------------------------
    def _tab_preflight(self):
        f = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(f, text="Preflight")
        bar = ttk.Frame(f, style="TFrame")
        bar.pack(fill="x", padx=10, pady=8)
        tip(ttk.Button(bar, text="Run checks", style="Accent.TButton",
                       command=self.run_preflight),
            "Check folders, the knowledge pack, tracked windows, anchors and the "
            "layout profile for the selected mode. Each failing item offers a "
            "fix button where one exists.").pack(side="left")
        self.pf_summary = ttk.Label(bar, text="", style="Muted.TLabel")
        self.pf_summary.pack(side="left", padx=12)
        canvas = tk.Canvas(f, highlightthickness=0, bg=self.pal["bg"])
        sb = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        self.pf_holder = ttk.Frame(canvas, style="TFrame")
        self.pf_holder.bind("<Configure>",
                            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        pf_win = canvas.create_window((0, 0), window=self.pf_holder, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(pf_win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)

        def _pf_wheel(e):
            if e.delta:
                canvas.yview_scroll(int(-e.delta / 120), "units")
            elif e.num in (4, 5):
                canvas.yview_scroll(-1 if e.num == 4 else 1, "units")
        self._pf_wheel = _pf_wheel
        for w in (canvas, self.pf_holder):
            w.bind("<MouseWheel>", _pf_wheel)
            w.bind("<Button-4>", _pf_wheel)
            w.bind("<Button-5>", _pf_wheel)
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6)
        self.pf_canvas = canvas

    # -- Settings -------------------------------------------------------
    def _tab_settings(self):
        outer = ttk.Frame(self.nb, style="TFrame")
        self.nb.add(outer, text="Settings")
        outer._conn_scrolls = True      # never dictates the launch height
        # Settings is the one tab taller than any screen. It scrolls, and the
        # wheel works anywhere over it.
        canvas = tk.Canvas(outer, highlightthickness=0, bg=self.pal["bg"])
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        f = ttk.Frame(canvas, style="TFrame")
        win_id = canvas.create_window((0, 0), window=f, anchor="nw")

        def _on_inner(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas(e):
            canvas.itemconfigure(win_id, width=e.width)

        def _wheel(e):
            if e.delta:
                canvas.yview_scroll(int(-e.delta / 120), "units")
            elif e.num == 4:
                canvas.yview_scroll(-1, "units")
            elif e.num == 5:
                canvas.yview_scroll(1, "units")

        f.bind("<Configure>", _on_inner)
        canvas.bind("<Configure>", _on_canvas)
        for w in (canvas, f):
            w.bind("<MouseWheel>", _wheel)
            w.bind("<Button-4>", _wheel)
            w.bind("<Button-5>", _wheel)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.settings_canvas = canvas
        self._settings_wheel = _wheel
        self.setting_vars = {}
        groups = [
            ("Folders", [("io.in_folder", "IN folder"), ("io.out_folder", "OUT folder"),
                         ("io.sessions_folder", "Sessions"), ("io.snapshots_folder", "Snapshots"),
                         ("ike.scenarios_folder", "Scenarios"),
                         ("ike.save_exchange_folder", "PBEM exchange"),
                         ("ike.ike_conversion_lua_path", "IKE conversion Lua"),
                         ("cmo.logs_folder", "CMO Logs folder (blank = auto-detect)")]),
            ("LLM chat", [("bridge.llm_title_must_contain",
                              "LLM tab must contain (blank = any)")]),
            ("Timing", [("timing.llm_min_wait_seconds", "First look at the reply after (s)"),
                        ("timing.llm_reply_poll_seconds", "Check the reply every (s)"),
                        ("timing.llm_output_wait_seconds", "Longest wait for a reply (s)"),
                        ("timing.llm_max_reprints", "Reprint requests before stopping"),
                        ("bridge.copy_method", "Copy method (button or select_all)"),
                        ("bridge.copy_clipboard_settle_seconds", "Clipboard settle (s)"),
                        ("timing.llm_scroll_page_downs", "Page Downs before copy"),
                        ("timing.llm_scroll_pause_seconds", "Pause per Page Down (s)"),
                        ("timing.cmo_output_wait_seconds", "CMO wait (s)"),
                        ("timing.cmo_output_poll_seconds", "Result pane poll (s)"),
                        ("timing.cmo_output_timeout_seconds", "Result pane timeout (s)"),
                        ("timing.test_window_wall_cap_seconds", "Test wall cap (s)"),
                        ("bridge.max_consecutive_failures", "Stop after N failing cycles"),
                        ("bridge.max_repeat_signature", "Stop after N identical faults"),
                        ("bridge.max_cycles", "Cycle budget"),
                        ("bridge.default_test_seconds", "Test window sim (s)"),
                        ("bridge.default_test_compression", "Test compression"),
                        ("io.paste_max_chars", "Paste limit (chars)"),
                        ("io.attach_method", "Oversize route (ctrl_u, anchors, chunks)"),
                        ("timing.upload_wait_base_seconds", "Upload wait base (s)"),
                        ("timing.file_dialog_wait_seconds", "File dialog wait (s)")]),
            ("Safety", [("safety.abort_hotkey", "Global abort hotkey")]),
        ]
        help_for = {
            "io.in_folder": "Where CONN writes prompt_*.txt for the file-exchange route. "
                            "LLM is pointed here with Ctrl+U.",
            "io.out_folder": "Where finished outputs and reports are written.",
            "io.sessions_folder": "One folder per run: transcript, scripts, events, report.",
            "io.snapshots_folder": "Pre-IKE copies of the master scenario, versioned.",
            "ike.scenarios_folder": "Where converted PBEM scenarios are saved.",
            "ike.save_exchange_folder": "Watched folder for incoming and outgoing PBEM .save files.",
            "ike.ike_conversion_lua_path": "Path to ike_min.lua from musurca's IKE release.",
            "cmo.logs_folder": "Where CMO writes AALog.txt, ExceptionLog_*.txt and "
                               "LuaHistory_*.txt. Leave blank to try the Steam install first, "
                               "then the Matrix Games install. Set it if CMO lives elsewhere.",
            "bridge.llm_title_must_contain": "Part of the LLM chat's title, for example "
                                                "'Hormuz playtest'. CONN checks the tab under "
                                                "the input box before every paste and stops if "
                                                "it does not match, so prompts never land in "
                                                "another chat. Blank = no check.",
            "timing.llm_min_wait_seconds": "CONN waits this long after sending, then starts "
                                              "checking whether the reply is finished.",
            "timing.llm_reply_poll_seconds": "How often CONN re-copies the reply while "
                                                "waiting for it to finish.",
            "timing.llm_output_wait_seconds": "The most CONN waits for one reply. It moves on "
                                                 "as soon as the reply is complete (valid Lua "
                                                 "with the NEXT_RECOMMENDED_STATE line). If "
                                                 "nothing can be copied by then, the run stops.",
            "timing.llm_max_reprints": "How many times CONN asks LLM to reprint a "
                                          "broken code block before it stops the run. An "
                                          "empty copy never triggers a reprint.",
            "bridge.copy_method": "button: click the code block's copy button. "
                                  "select_all: select the page and copy.",
            "bridge.copy_clipboard_settle_seconds": "Pause after copying before reading the "
                                                    "clipboard.",
            "timing.llm_scroll_page_downs": "Page Downs sent to reach the end of a long "
                                               "reply before copying.",
            "timing.llm_scroll_pause_seconds": "Pause between those Page Downs.",
            "timing.cmo_output_wait_seconds": "How long to let a script run in CMO before "
                                              "reading the result pane.",
            "timing.cmo_output_poll_seconds": "How often to re-read the result pane while "
                                              "waiting for the run marker.",
            "timing.cmo_output_timeout_seconds": "Give up waiting for the run marker after this.",
            "timing.test_window_wall_cap_seconds": "Longest real-time wait for one test window. "
                                                   "Long windows are allowed and announced; "
                                                   "they stay abortable.",
            "bridge.max_consecutive_failures": "Stop the run after this many failing cycles "
                                               "in a row.",
            "bridge.max_repeat_signature": "Stop the run when the same fault repeats this "
                                           "many times.",
            "bridge.max_cycles": "Hard limit on cycles per run.",
            "bridge.default_test_seconds": "Simulated seconds for a test window when the "
                                           "model does not say.",
            "bridge.default_test_compression": "Compression for a test window only when "
                                               "CONN owns compression. Ignored while the "
                                               "operator sets it by hand.",
            "io.paste_max_chars": "Prompts longer than this go by file instead of paste.",
            "io.attach_method": "How an oversize prompt reaches LLM: ctrl_u opens the "
                                "upload dialog; anchors clicks the attach button; chunks "
                                "pastes in pieces.",
            "timing.upload_wait_base_seconds": "Base wait for a file upload to register.",
            "timing.file_dialog_wait_seconds": "Wait for the file dialog to open before typing "
                                               "the path.",
            "safety.abort_hotkey": "Global key combination that aborts the run from any "
                                   "window.",
        }
        for title, fields in groups:
            lf = ttk.Labelframe(f, text=title)
            lf.pack(fill="x", padx=10, pady=6)
            for i, (key, label) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=i, column=0, sticky="e", padx=6, pady=3)
                v = tk.StringVar(value=str(self.cfg.get(key, "")))
                self.setting_vars[key] = v
                ent = tip(ttk.Entry(lf, textvariable=v, width=70), help_for.get(key, ""))
                ent.grid(row=i, column=1, sticky="ew", padx=6, pady=3)
                for w in (lf, ent):
                    w.bind("<MouseWheel>", self._settings_wheel)
                if key == "cmo.logs_folder":
                    tip(ttk.Button(lf, text="Browse", width=8,
                                   command=lambda vv=v: self._browse_folder(vv)),
                        "Pick the CMO Logs folder.").grid(row=i, column=2, padx=(0, 4))
                    tip(ttk.Button(lf, text="Find", width=6, command=self._find_cmo_logs),
                        "Auto-detect the folder and show which AALog.txt would be read."
                        ).grid(row=i, column=3, padx=(0, 6))
            lf.grid_columnconfigure(1, weight=1)

        row = ttk.Frame(f, style="TFrame")
        row.pack(fill="x", padx=12, pady=8)
        self.var_syntax = tk.BooleanVar(value=bool(self.cfg.get("safety.lua_syntax_check", True)))
        self.var_guard = tk.BooleanVar(value=bool(self.cfg.get("io.guard_clipboard", True)))
        self.var_confirm = tk.BooleanVar(value=bool(self.cfg.get("safety.confirm_ike_conversion", True)))
        self.var_readonly = tk.BooleanVar(value=bool(self.cfg.get("safety.lock_master_scen_readonly", True)))
        self.var_dry_default = tk.BooleanVar(value=bool(self.cfg.get("ui.dry_run_default", True)))
        self.var_apiguard = tk.BooleanVar(value=bool(self.cfg.get("safety.api_symbol_guard", True)))
        self.var_echo = tk.BooleanVar(value=bool(self.cfg.get("bridge.echo_input_script", False)))
        self.var_markers = tk.BooleanVar(value=bool(self.cfg.get("bridge.use_run_markers", True)))
        self.var_tablock = tk.BooleanVar(value=bool(self.cfg.get("bridge.lock_llm_tab", True)))
        self.var_dlgcheck = tk.BooleanVar(value=bool(self.cfg.get("io.verify_file_dialog", True)))
        switches = (
            ("Check the file dialog opened before attaching", self.var_dlgcheck,
             "After Ctrl+U CONN waits for the Open dialog before pasting the file path. "
             "Without it, a missed shortcut pasted the path into the chat and Enter sent "
             "it to LLM. Untick only if your browser's dialog is never detected."),
            ("Stop if the LLM tab changes during a run", self.var_tablock,
             "After the first good reply CONN remembers the chat's title. If a different "
             "chat is in front before a paste, the run stops instead of pasting there."),
            ("API symbol guard (block CMO names absent from the local index)", self.var_apiguard,
             "Refuse to inject a script that calls a CMO function not in the local "
             "index. Catches invented function names before they burn a cycle."),
            ("Lua console has 'Echo input script on result text' ticked", self.var_echo,
             "Tell CONN the result pane repeats the script, so it skips that part "
             "when reading output."),
            ("Wrap runs in markers and read the pane by completion", self.var_markers,
             "Add start and end markers to every script and read the pane until the "
             "end marker appears, instead of waiting a fixed time."),
            ("Lua syntax check before injection", self.var_syntax,
             "Parse the script locally first. A syntax error is rejected before it "
             "reaches CMO."),
            ("Guard the clipboard", self.var_guard,
             "Refuse to inject clipboard content that does not look like the reply "
             "CONN just requested."),
            ("Confirm before IKE conversion", self.var_confirm,
             "Ask before running the one-way IKE conversion."),
            ("Lock the master .scen read only during conversion", self.var_readonly,
             "Set the master file read-only while IKE runs so it cannot be overwritten."),
            ("Start in dry run", self.var_dry_default,
             "Open CONN with dry run on, so nothing is clicked until you switch it off."),
        )
        for text, var, help_text in switches:
            tip(ttk.Checkbutton(row, text=text, variable=var), help_text).pack(anchor="w")
        rowb = ttk.Frame(f, style="TFrame")
        rowb.pack(fill="x", padx=12, pady=8)
        tip(ttk.Button(rowb, text="Import environment dump into the API guard",
                       command=self.import_env_dump),
            "Paste the output of the environment probe script to add every symbol "
            "your CMO build actually has to the API guard's index.").pack(side="left")
        tip(ttk.Button(rowb, text="Save settings", style="Accent.TButton",
                       command=self.save_settings),
            "Write all settings on this tab to bridge_config.json.").pack(side="right")

    # ------------------------------------------------------------------
    # dry run and theme
    # ------------------------------------------------------------------
    def on_dry_run_toggle(self):
        on = self.dry_run.get()
        if not on and self.engine.state.get("running"):
            if not messagebox.askyesno(
                    "Leave dry run",
                    "Turning dry run off while a run is active will let CONN click and "
                    "type on the live screen. Continue?"):
                self.dry_run.set(True)
                return
        self.engine.set_dry_run(on)
        self._apply_dry_run_visuals()
        self.log("dry run {}".format("ON, no synthetic input" if on else "OFF, live input"))

    def _apply_dry_run_visuals(self):
        self.pal = theme.palette(self.dry_run.get())
        theme.apply_theme(self, self.pal)
        for p in self.panels:
            p.set_palette(self.pal)
        try:
            self.pf_canvas.configure(bg=self.pal["bg"])
        except Exception:
            pass
        if self.strip:
            self.strip.configure(bg=self.pal["bg"])
        self.title("CONN  -  CMO LLM Bridge" +
                   ("   [DRY RUN]" if self.dry_run.get() else ""))
        self.dry_chk.configure(text=DRY_ON_TEXT if self.dry_run.get() else DRY_OFF_TEXT)

    # ------------------------------------------------------------------
    # run control
    # ------------------------------------------------------------------
    def current_mode(self):
        return LABEL_MODES.get(self.mode_var.get(), "design")

    BUILTIN_PROFILES = ("scenario_dev", "play")

    def on_mode_change(self):
        """Switch mode. The layout profile follows the mode only when it is
        a built-in one; a profile you picked (LLM_SCEN_DEV@...) stays, and
        each mode remembers the profile last picked for it. Resetting it to
        scenario_dev here used to move the windows away from the arrangement
        the anchors were calibrated in."""
        mode = self.current_mode()
        self.cfg.set("play.mode", mode)
        if not self.engine.state.get("running"):
            self.engine.state["mode"] = mode
        remembered = self.cfg.get("layouts.active_by_mode.{}".format(mode))
        current = self.layouts.active()
        if remembered and remembered in self.cfg.profiles:
            self.cfg.set("layouts.active", remembered)
        elif current in self.BUILTIN_PROFILES or current not in self.cfg.profiles:
            self.cfg.set("layouts.active", "scenario_dev" if mode == "design" else "play")
        self._save_cfg()
        self.refresh_layouts()
        self.run_preflight()
        self.log("mode: {} (layout profile {})".format(MODE_LABELS[mode], self.layouts.active()))

    def start(self):
        if self.engine.state.get("running"):
            self.log("a run is already going")
            return
        if self._rebuild_busy or self._ike_busy:
            messagebox.showinfo("CONN", "Wait for the rebuild or IKE step to finish first: "
                                        "both use the Lua console.")
            return
        mode = self.current_mode()
        self._remember_mission()
        checks = run_preflight(self.cfg, self.wm_, self.resolver, mode)
        self._refresh_clock_method_label()
        s = summarize(checks)
        if not s["ok"]:
            if not messagebox.askyesno(
                    "Preflight failures",
                    "Blocking checks:\n  - {}\n\nStart anyway?".format(
                        "\n  - ".join(s["blockers"]))):
                self.nb.select(5)
                self.render_preflight(checks)
                return
        if self.apply_layout_on_start.get():
            self.apply_layout()
        params = {"clock_running": bool(self.var_clock_running.get())}
        if mode == "design":
            params["scenario_prompt"] = self.prompt.get("1.0", "end").strip()
            sel = self.start_stage.get()
            params["start_stage"] = ("AUDIT" if sel.startswith("AUDIT")
                                     else "PLAYTEST" if sel.startswith("PLAYTEST")
                                     else "DESIGN")
        self.save_play(quiet=True)
        ok, msg = self.engine.start(mode, params)
        self.log("start: {}".format(msg))
        if not ok and not os.environ.get("CONN_NO_DIALOGS"):
            messagebox.showwarning("CONN did not start", msg)
        self._sync_run_buttons(force=True)

    def _remember_mission(self):
        """Keep the request, stage and mode for the next launch."""
        try:
            self.cfg.set("ui.last_prompt", self.prompt.get("1.0", "end").strip())
            self.cfg.set("ui.last_stage", self.start_stage.get().split(" ")[0])
            self.cfg.set("play.mode", self.current_mode())
        except tk.TclError:
            pass

    def _sync_run_buttons(self, force=False):
        """Start is off while a run is going; Pause and Step only work
        during one."""
        running = bool(self.engine.state.get("running"))
        if not force and running == self._was_running:
            return
        self._was_running = running
        try:
            self.btn_start.state(["disabled"] if running else ["!disabled"])
            self.btn_pause.state(["!disabled"] if running else ["disabled"])
            self.btn_step.state(["!disabled"] if running else ["disabled"])
        except tk.TclError:
            pass

    def toggle_pause(self):
        if not self.engine.state.get("running"):
            return
        paused = not self.state.get("paused", False)
        self.engine.request_pause(paused)
        self.state["paused"] = paused
        self.btn_pause.configure(text="Resume" if paused else "Pause")

    def step(self):
        self.engine.request_step()
        if self.state.get("paused"):
            self.state["paused"] = False
            self.engine.request_pause(False)
            self.btn_pause.configure(text="Pause")

    def abort(self):
        if self.engine.state.get("running"):
            self.engine.abort()
            self.log("abort requested")

    def _hotkey_abort(self):
        """Runs on the hotkey thread: no widget calls here."""
        if self.engine.state.get("running"):
            self.engine.abort()
            self.bus.put({"kind": "log", "text": "abort requested (hotkey)"})

    def _tlog(self, text, level="info"):
        """Log from any thread: queued, then written by the Tk pump."""
        self.bus.put({"kind": "log", "text": str(text), "level": level})

    def _save_cfg(self):
        """Save the config; a refused save (the file could not be read at
        start) is reported once instead of raising inside a Tk callback."""
        try:
            self.cfg.save()
            return True
        except Exception as ex:
            self.log("settings NOT saved: {}".format(ex))
            if not self._save_warned and not os.environ.get("CONN_NO_DIALOGS"):
                self._save_warned = True
                messagebox.showwarning("CONN settings not saved", str(ex))
            return False

    def open_session_folder(self):
        sess = self.engine.session
        folder = Path(str(sess.dir)) if sess else self.cfg.folder("sessions_folder")
        if not folder or not Path(folder).exists():
            messagebox.showinfo("Session", "No session folder yet. Start a run first.")
            return
        try:
            if IS_WINDOWS:
                os.startfile(str(folder))       # noqa: only on Windows
            else:
                self.log("session folder: {}".format(folder))
        except Exception as ex:
            self.log("could not open {}: {}".format(folder, ex))

    # ------------------------------------------------------------------
    # IKE
    # ------------------------------------------------------------------
    def browse_master(self):
        p = filedialog.askopenfilename(
            title="Select the master scenario",
            filetypes=[("CMO scenario", "*.scen"), ("All files", "*.*")])
        if p:
            self.master_scen.set(p)

    def _ike_log(self, text):
        """Tk thread only. Worker threads queue 'ike' events instead."""
        self.ike_steps.configure(state="normal")
        self.ike_steps.insert("end", "{}  {}\n".format(stamp(), text))
        self.ike_steps.see("end")
        self.ike_steps.configure(state="disabled")

    def finalize_ike(self):
        master = self.master_scen.get().strip()
        if not master:
            messagebox.showinfo("IKE", "Select the master .scen first.")
            return
        if self.engine.state.get("running") or self._rebuild_busy or self._ike_busy:
            messagebox.showinfo("IKE", "Stop the run (or wait for the rebuild) first: IKE "
                                       "conversion uses the same Lua console.")
            return
        out = str(Path(master).with_name(Path(master).stem + "_PBEM.scen"))
        if self.cfg.get("safety.confirm_ike_conversion", True):
            if not messagebox.askyesno(
                    "Confirm IKE conversion",
                    "Conversion cannot be undone.\n\n"
                    "Input  : {}\nOutput : {}\n\n"
                    "A pre-IKE snapshot is written first and the master is locked "
                    "read only during the operation.\n\nProceed?".format(master, out)):
                return
        self._ike_log("starting finalization for {}".format(master))

        def work():
            self._ike_busy = True
            try:
                result, err = self.engine.finalize_ike(master, on_step=self._ike_step)
                self._ike_result = result
                if err:
                    self.bus.put({"kind": "ike", "text": "ERROR: {}".format(err)})
                else:
                    self.bus.put({"kind": "ike", "text": "Answer the IKE popups in CMO, then "
                                  "use SAVE AS to write the converted scenario, then press "
                                  "Verify."})
            except (Aborted, Halted, Exception) as ex:
                self.bus.put({"kind": "ike", "text": "stopped: {}".format(ex)})
            finally:
                self._ike_busy = False

        threading.Thread(target=work, name="conn-ike", daemon=True).start()

    def _ike_step(self, step, detail=""):
        self.bus.put({"kind": "ike", "text": "{}: {}".format(step, detail)})

    def verify_ike(self):
        if not self._ike_result:
            messagebox.showinfo("IKE", "Run Finalize first.")
            return
        result, err = self.engine.verify_ike(self._ike_result)
        if err:
            self._ike_log("VERIFY FAILED: {}".format(err))
        else:
            self._ike_log("verified: {} ({} bytes)".format(
                result.get("expected_output"), result.get("verified")))
            self._ike_log("sidecar: {}".format(result.get("sidecar", "n/a")))

    # ------------------------------------------------------------------
    # calibration
    # ------------------------------------------------------------------
    def refresh_calibration(self):
        tree = self.cal_tree
        sel = tree.selection()
        keep = sel[0] if sel else None
        tree.delete(*tree.get_children())
        for name in sorted(self.cfg.anchors.keys()):
            a = self.cfg.anchors.get(name)
            pt = self.resolver.resolve(name)
            if a:
                offset = ("{},{} from {}".format(a.get("dx"), a.get("dy"), a.get("corner"))
                          if a.get("mode") == "px"
                          else "{}, {}".format(a.get("dx"), a.get("dy")))
                vals = (a.get("window", "screen"), a.get("mode", "frac"), offset,
                        "{}, {}".format(*pt) if pt else "-", self.resolver.status(name))
            else:
                vals = ("-", "-", "-", "-", "unset")
            tree.insert("", "end", iid=name, text=name, values=vals)
        if keep and keep in self.cfg.anchors:
            tree.selection_set(keep)
        if self.overlay.visible:
            self.overlay.redraw()

    def selected_anchor(self):
        sel = self.cal_tree.selection()
        return sel[0] if sel else None

    def capture_anchor(self):
        name = self.selected_anchor()
        if not name:
            messagebox.showinfo("Calibration", "Select an anchor row first.")
            return
        was_visible = self.overlay.visible
        if was_visible:
            self.overlay.hide()
        self.log("capturing {}: put the pointer on the target".format(name))
        pt = capture_point(self, self.count_var.get(), hide=True,
                           on_tick=lambda r: self.set_status("capturing {} in {}".format(name, r)))
        if not pt:
            self.set_status("capture unavailable (pyautogui missing)")
            return
        self.wm_.refresh()
        a = self.resolver.set_from_point(name, pt[0], pt[1])
        self._save_cfg()
        self.log("{} -> {} {} ({}, {})".format(name, a["window"], a["mode"],
                                               a["dx"], a["dy"]))
        self.refresh_calibration()
        if was_visible:
            self.overlay.show()

    def test_click(self):
        name = self.selected_anchor()
        if not name:
            return
        pt = self.resolver.resolve(name)
        if not pt:
            messagebox.showinfo("Calibration", "That anchor does not resolve right now.")
            return
        if self.dry_run.get():
            self.log("DRY RUN: would click {} at {},{}".format(name, pt[0], pt[1]))
            return
        if messagebox.askyesno("Test click",
                               "Click {} at {}, {} now?".format(name, pt[0], pt[1])):
            self.engine.act.click(name, name)

    def rebind_anchor(self):
        name = self.selected_anchor()
        if not name:
            return
        keys = [k for k in self.cfg.windows.keys()] + ["screen"]
        win = tk.Toplevel(self)
        win.title("Rebind " + name)
        win.configure(bg=self.pal["bg"])
        var = tk.StringVar(value=keys[0])
        ttk.Label(win, text="Bind {} to window".format(name)).pack(padx=12, pady=8)
        tip(ttk.Combobox(win, textvariable=var, values=keys, state="readonly"),
            "The tracked window this anchor should live in.").pack(padx=12)

        def do():
            self.resolver.rebind(name, var.get())
            self._save_cfg()
            self.refresh_calibration()
            win.destroy()

        tip(ttk.Button(win, text="Rebind", command=do),
            "Move the anchor to that window, keeping its stored offset.").pack(pady=10)

    def clear_anchor(self):
        name = self.selected_anchor()
        if name:
            self.cfg.anchors[name] = None
            self._save_cfg()
            self.refresh_calibration()

    def toggle_overlay(self):
        visible = self.overlay.toggle()
        self.log("overlay {}".format("shown" if visible else "hidden"))

    def import_legacy(self):
        # read the coordinates from disk: the legacy calibration window may
        # have written new ones since CONN loaded the file
        coords = {}
        try:
            import json as _json
            disk = _json.loads(Path(self.cfg.path).read_text(encoding="utf-8-sig"))
            coords = disk.get("coordinates") or {}
        except Exception:
            coords = {}
        coords = coords or self.cfg.data.get("coordinates", {})
        if not coords:
            messagebox.showinfo("Calibration", "No legacy coordinates block found.")
            return
        self.wm_.refresh()
        rects = self.wm_.all_rects()
        if not rects:
            messagebox.showinfo(
                "Calibration",
                "No tracked windows are on screen. Arrange CMO, the Lua console and the "
                "browser as they were when the coordinates were captured, then import.")
            return
        anchors, notes = migrate_absolute(coords, rects, self.wm_.virtual_screen())
        for k, v in anchors.items():
            self.cfg.anchors[k] = v
        self._save_cfg()
        self.refresh_calibration()
        for n in notes:
            self.log("migrate " + n)

    def write_absolute(self):
        n = anchors_to_absolute(self.cfg, self.resolver)
        self._save_cfg()
        self.log("wrote {} absolute coordinates for the legacy bridge".format(n))

    # ------------------------------------------------------------------
    # layouts and windows
    # ------------------------------------------------------------------
    def refresh_layouts(self):
        active = self.layouts.active()
        self.layout_list.delete(0, "end")
        self._layout_keys = []
        for i, name in enumerate(self.layouts.profile_names()):
            prof = self.layouts.get(name) or {}
            self.layout_list.insert("end", "{} {}   [{}]".format(
                "*" if name == active else " ", name, str(prof.get("label", ""))[:40]))
            self._layout_keys.append(name)
            if name == active:
                self.layout_list.selection_clear(0, "end")
                self.layout_list.selection_set(i)
                self.layout_list.see(i)
        self.refresh_windows()

    def selected_profile(self):
        # names are kept in a list; parsing the row text broke on names
        # with spaces ("Scenario Dev 2@12345" became "Scenario")
        sel = self.layout_list.curselection()
        if sel and sel[0] < len(self._layout_keys):
            return self._layout_keys[sel[0]]
        return self.layouts.active()

    def _on_layout_pick(self):
        name = self.selected_profile()
        if not name or name == self.layouts.active():
            return
        self.cfg.set("layouts.active", name)
        self.cfg.set("layouts.active_by_mode.{}".format(self.current_mode()), name)
        self._save_cfg()
        self.log("active layout profile for {}: {}".format(
            MODE_LABELS.get(self.current_mode(), ""), name))
        self.refresh_layouts()

    def apply_layout(self, name=None):
        name = name or self.selected_profile()
        ok, msg = self.layouts.apply(name, conn_setter=self._place_self)
        self.log("layout: " + msg)
        if ok:
            self.cfg.set("layouts.active_by_mode.{}".format(self.current_mode()), name)
        self._save_cfg()
        self.refresh_layouts()
        return ok

    def _place_self(self, rect, topmost=True):
        target = self.strip if self.strip else self
        try:
            target.geometry("{}x{}+{}+{}".format(
                max(300, rect.right - rect.left), max(300, rect.bottom - rect.top),
                rect.left, rect.top))
            target.attributes("-topmost", bool(topmost) and
                              bool(self.cfg.get("ui.monitor_always_on_top", True)))
        except Exception:
            pass

    def capture_layout(self):
        name = tk.simpledialog.askstring("Capture layout", "Profile name",
                                         parent=self) if hasattr(tk, "simpledialog") else None
        if not name:
            from tkinter import simpledialog
            name = simpledialog.askstring("Capture layout", "Profile name", parent=self)
        if not name:
            return
        self.update_idletasks()
        target = self.strip if self.strip else self
        conn_rect = Rect(target.winfo_x(), target.winfo_y(),
                         target.winfo_x() + target.winfo_width(),
                         target.winfo_y() + target.winfo_height())
        key = self.layouts.capture(name, label=name, conn_rect=conn_rect)
        self.log("captured layout {}".format(key))
        self.refresh_layouts()

    def delete_layout(self):
        name = self.selected_profile()
        if name and messagebox.askyesno("Delete", "Delete profile {}?".format(name)):
            self.layouts.delete(name)
            self.refresh_layouts()

    def reserve_strip(self):
        name = self.selected_profile()
        self.cfg.set("ui.dock_side", self.dock_side.get())
        self.cfg.set("ui.strip_width", int(self.strip_width.get()))
        if self.layouts.reserve_strip(name, self.dock_side.get(), int(self.strip_width.get())):
            self.log("reserved a {}px strip on the {} in {}".format(
                self.strip_width.get(), self.dock_side.get(), name))
            self.refresh_layouts()

    def refresh_windows(self):
        self.wm_.refresh()
        self.win_tree.delete(*self.win_tree.get_children())
        for key, spec in self.cfg.windows.items():
            info = self.wm_.info(key)
            r = self.wm_.rect(key)
            self.win_tree.insert("", "end", iid=key, text=key, values=(
                "{},{} {}x{}".format(r.left, r.top, r.right - r.left, r.bottom - r.top)
                if r else "not found",
                (info.title[:50] if info else spec.get("title_regex", ""))))

    def _on_windows_changed(self):
        self._windows_dirty.set()

    # ------------------------------------------------------------------
    # monitor strip
    # ------------------------------------------------------------------
    def toggle_strip(self):
        if self.strip:
            self.strip.destroy()
            self.panels = [p for p in self.panels if p.winfo_exists()]
            self.strip = None
            return
        self.strip = tk.Toplevel(self)
        self.strip.title("CONN monitor")
        self.strip.configure(bg=self.pal["bg"])
        w = int(self.cfg.get("ui.strip_width", 320))
        screen = self.wm_.virtual_screen()
        x = screen.right - w if self.cfg.get("ui.dock_side", "right") == "right" else screen.left
        self.strip.geometry("{}x{}+{}+{}".format(w, screen.bottom - screen.top - 80,
                                                 x, screen.top + 20))
        self.strip.attributes("-topmost", bool(self.cfg.get("ui.monitor_always_on_top", True)))
        p = MonitorPanel(self.strip, self, compact=True)
        p.pack(fill="both", expand=True)
        self.panels.append(p)
        theme.apply_theme(self, self.pal)
        tip_palette(self, self.pal)
        p.set_palette(self.pal)
        self.strip.protocol("WM_DELETE_WINDOW", self.toggle_strip)

    # ------------------------------------------------------------------
    # preflight
    # ------------------------------------------------------------------
    def run_preflight(self):
        checks = run_preflight(self.cfg, self.wm_, self.resolver, self.current_mode())
        self.render_preflight(checks)
        return checks

    def render_preflight(self, checks):
        for child in self.pf_holder.winfo_children():
            child.destroy()
        colors = {"ok": self.pal["ok"], "warn": self.pal["warn"], "fail": self.pal["fail"]}
        self.pf_holder.grid_columnconfigure(0, weight=1)
        for i, c in enumerate(checks):
            row = ttk.Frame(self.pf_holder, style="TFrame")
            row.grid(row=i, column=0, sticky="ew", pady=1)
            dot = tk.Label(row, text="  ", bg=colors[c.state], width=2)
            dot._conn_fixed_color = True      # the theme must not repaint status dots
            dot.pack(side="left", padx=(4, 8))
            ttk.Label(row, text=c.label, width=40).pack(side="left")
            tip(ttk.Label(row, text=c.detail[:110], style="Muted.TLabel"),
                c.detail or c.label).pack(side="left", padx=6)
            for w in (row, dot):
                w.bind("<MouseWheel>", self._pf_wheel)
            if c.fix and c.state != "ok":
                tip(ttk.Button(row, text=c.fix_label, width=8,
                               command=lambda cc=c: self._do_fix(cc)),
                    "Apply the suggested fix for this check: " + (c.detail or c.label)).pack(
                    side="right", padx=6)
        s = summarize(checks)
        self.pf_summary.configure(text="{} checks, {} blocking, {} advisory".format(
            s["total"], s["fail"], s["warn"]))

    def _do_fix(self, check):
        try:
            check.fix()
            self.log("fixed: {}".format(check.label))
        except Exception as ex:
            self.log("fix failed for {}: {}".format(check.label, ex))
        self.run_preflight()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def browse_master_lua(self):
        p = filedialog.askopenfilename(parent=self, title="Master .lua",
                                       filetypes=[("Lua", "*.lua"), ("All", "*.*")])
        if p:
            self.master_lua.set(p)
            self.cfg.set("build.master_lua", p)
            self._save_cfg()

    REBUILD_KEEP = re.compile(r"created=|failed=|built=|SAVED|embedded|DONE|ERROR|[Ee]rror|"
                              r"FAIL|not set|REALISM\|.*\|false|CLOCK")

    def rebuild_in_cmo(self):
        path = self.master_lua.get().strip()
        if not path:
            self.log("rebuild: pick the master .lua first")
            return
        if self.engine.state.get("running"):
            messagebox.showinfo("Rebuild", "Stop the run first: the rebuild uses the same "
                                           "Lua console and would mix into the run's output.")
            return
        if self._rebuild_busy or self._ike_busy:
            self.log("rebuild: already busy, wait for it to finish")
            return
        self.cfg.set("build.master_lua", path)
        self._save_cfg()
        lua = "ScenEdit_RunScript('{}', true)".format(path.replace("\\", "/").replace("'", "\\'"))
        self.log("rebuild: injecting " + lua)
        timeout = int(num(self.cfg.get("timing.rebuild_timeout_seconds", 240), 240))

        def work():
            self._rebuild_busy = True
            try:
                if not self.engine.run_lua_in_cmo(lua, label="rebuild"):
                    self.bus.put({"kind": "log", "text": "rebuild: the script was not injected"})
                    return
                if self.engine.dry_run:
                    return
                out = self.engine.read_cmo_output(timeout=timeout) or ""
                keep = [l.strip() for l in out.splitlines() if self.REBUILD_KEEP.search(l)]
                if not keep:
                    keep = [l.strip() for l in out.splitlines() if l.strip()][-6:]
                for line in keep[:25]:
                    self.bus.put({"kind": "log", "text": "rebuild: " + line[:200]})
                self.bus.put({"kind": "log", "text": "rebuild finished; the full output is "
                              "under Last CMO output on the Monitor tab"})
            except (Aborted, Halted) as ex:
                self.bus.put({"kind": "log", "text": "rebuild stopped: {}".format(ex)})
            except Exception as ex:
                self.bus.put({"kind": "log", "text": "rebuild failed: {}: {}".format(
                    type(ex).__name__, ex)})
            finally:
                self._rebuild_busy = False

        threading.Thread(target=work, name="conn-rebuild", daemon=True).start()

    def _browse_folder(self, var):
        d = filedialog.askdirectory(parent=self, title="Choose folder",
                                    initialdir=var.get() or None)
        if d:
            var.set(d)

    def _find_cmo_logs(self):
        from .cmologs import CmoLogs
        v = self.setting_vars.get("cmo.logs_folder")
        if v is not None:
            self.cfg.set("cmo.logs_folder", v.get().strip())
        logs = CmoLogs(self.cfg)
        self.log("CMO logs: " + logs.describe())
        if logs.folder and v is not None and not v.get().strip():
            v.set(str(logs.folder))
        self.engine.logs = None     # re-detect on next use

    def _clock_state_changed(self):
        """Operator says what the clock is doing; the toggle tracker follows."""
        running = bool(self.var_clock_running.get())
        if not self.engine.set_clock_state(running):
            self.log("clock state noted: {} (applies when the run starts)".format(
                "running" if running else "paused"))

    def _refresh_clock_method_label(self):
        try:
            import cmo_sim_control as sc
            key = "+".join(sc.KEY_PLAY_PAUSE)
            self.lbl_clock_method.configure(text="method: {}   key: {}".format(
                sc.SIM_CONTROL_METHOD, key))
        except Exception:
            self.lbl_clock_method.configure(text="")

    def save_play(self, quiet=False):
        self.cfg.set("play.ike_hotseat", bool(self.var_ike_hotseat.get()))
        self.cfg.set("play.rag_enabled", bool(self.var_rag_play.get()))
        self.cfg.set("play.rag_learn_in_play", bool(self.var_rag_learn.get()))
        self.cfg.set("play.attach_aalog_each_turn", bool(self.var_aalog_turn.get()))
        self.cfg.set("play.attach_mapshot_each_turn", bool(self.var_mapshot_turn.get()))
        for key, var in self.play_vars.items():
            val = var.get().strip()
            if key.endswith(("minutes", "cap", "turn")) or "budget" in key:
                try:
                    f = float(val)
                    val = int(f) if f.is_integer() else f
                except ValueError:
                    pass
            self.cfg.set(key, val)
        self.cfg.set("play.arbiter_enabled", bool(self.var_arbiter.get()))
        self.cfg.set("play.side_lock", bool(self.var_sidelock.get()))
        self.cfg.set("safety.editor_lock_in_play_modes", bool(self.var_editorlock.get()))
        for side_key, boxes in self.agent_text.items():
            for fk, widget in boxes.items():
                self.cfg.set("play.agents.{}.{}".format(side_key, fk),
                             widget.get("1.0", "end").strip())
        self._save_cfg()
        if not quiet:
            self.log("play settings saved")

    def save_settings(self):
        for key, var in self.setting_vars.items():
            val = var.get().strip()
            if key in ("bridge.copy_method", "io.attach_method"):
                val = val.strip().lower()
            elif "pause" in key or "settle" in key or key.endswith("_pause_seconds"):
                try:
                    val = float(val)
                except ValueError:
                    pass
            elif any(k in key for k in ("seconds", "attempts", "chars", "cycles", "reprints",
                                        "compression", "page_downs", "failures",
                                        "signature")):
                # 2 stays 2, 2.5 stays 2.5; "2.5" as text made int() raise mid-run
                try:
                    f = float(val)
                    val = int(f) if f.is_integer() else f
                except ValueError:
                    pass
            self.cfg.set(key, val)
        self.cfg.set("safety.api_symbol_guard", bool(self.var_apiguard.get()))
        self.cfg.set("bridge.echo_input_script", bool(self.var_echo.get()))
        self.cfg.set("bridge.use_run_markers", bool(self.var_markers.get()))
        self.cfg.set("bridge.lock_llm_tab", bool(self.var_tablock.get()))
        self.cfg.set("io.verify_file_dialog", bool(self.var_dlgcheck.get()))
        self.cfg.set("safety.lua_syntax_check", bool(self.var_syntax.get()))
        self.cfg.set("io.guard_clipboard", bool(self.var_guard.get()))
        self.cfg.set("safety.confirm_ike_conversion", bool(self.var_confirm.get()))
        self.cfg.set("safety.lock_master_scen_readonly", bool(self.var_readonly.get()))
        self.cfg.set("ui.dry_run_default", bool(self.var_dry_default.get()))
        self.cfg.ensure_folders()
        if self._save_cfg():
            self.log("settings saved to {}".format(self.cfg.path))
        # a changed abort hotkey used to need a restart
        spec = str(self.cfg.get("safety.abort_hotkey", "ctrl+alt+x"))
        if spec != self.hotkey.spec:
            self.hotkey.stop()
            self.hotkey = GlobalHotkey(spec, self._hotkey_abort, log=self._tlog)
            self.hotkey.start()
        self.run_preflight()

    def import_env_dump(self):
        """Paste a console environment dump; CMO-pattern symbols in it are
        added to the guard's environment file."""
        top = tk.Toplevel(self)
        top.title("Import environment dump")
        top.configure(bg=self.pal["bg"])
        top.geometry("700x460")
        ttk.Label(top, text="Paste the console dump (the GLOBALS listing or any "
                            "text containing the symbol names), then Import.").pack(
            anchor="w", padx=10, pady=8)
        txt = tk.Text(top, wrap="none", font=("Consolas", 9))
        txt.pack(fill="both", expand=True, padx=10)

        def do():
            new_syms = self.engine.guard.learn_from_text(txt.get("1.0", "end"))
            self.log("API guard: {} new symbols imported".format(len(new_syms)))
            top.destroy()

        tip(ttk.Button(top, text="Import", style="Accent.TButton",
                       command=do),
            "Read the pasted probe output and add its symbols to the API guard.").pack(pady=8)

    def save_config(self):
        if self._save_cfg():
            self.log("config saved")

    def export_session(self):
        if not self.engine.session:
            messagebox.showinfo("Session", "Nothing to export yet.")
            return
        text = self.engine.session.export()
        self.log("session exported to {}".format(self.engine.session.dir))
        messagebox.showinfo("Session", text[:1200])

    # ------------------------------------------------------------------
    # event pump
    # ------------------------------------------------------------------
    def log(self, text, level="info"):
        line = "{}  {}".format(stamp(), text)
        for p in self.panels:
            if p.winfo_exists():
                p.append_log(line)
        self.set_status(text)

    def set_status(self, text):
        try:
            self.status.configure(text=text[:160])
            self.update_idletasks()
        except Exception:
            pass

    def _pump(self):
        # one bad event used to stop the pump for good: the monitor froze
        # and no stop box could appear again
        try:
            drained = 0
            while drained < 200:
                try:
                    ev = self.bus.get_nowait()
                except queue.Empty:
                    break
                drained += 1
                try:
                    self._handle(ev)
                except Exception as ex:
                    try:
                        self.status.configure(text="event error: {}".format(ex)[:160])
                    except Exception:
                        pass
            self.state.update(self.engine.state)
            for p in self.panels:
                if p.winfo_exists():
                    p.refresh(self.state)
            self._sync_run_buttons()
            if self._windows_dirty.is_set():
                self._windows_dirty.clear()
                self.refresh_calibration()
                self.refresh_windows()
        except Exception:
            pass
        finally:
            if getattr(self, "_pump_id", None) is not None:
                self._pump_id = self.after(120, self._pump)

    def _handle(self, ev):
        kind = ev.get("kind")
        if kind in ("log", "act", "error", "ike"):
            prefix = {"error": "ERROR ", "act": "", "ike": "IKE ", "log": ""}[kind]
            self.log(prefix + str(ev.get("text", "")))
            if kind == "ike":
                self._ike_log(str(ev.get("text", "")))
        elif kind == "step":
            self.log("step {} of 6: {} [{}]".format(
                ev.get("number"), ev.get("text"), ev.get("anchor")))
        elif kind == "stage":
            self.log("stage {} (cycle {})".format(ev.get("stage"), ev.get("cycle")))
        elif kind == "turn":
            self.log("turn {} {} {}".format(ev.get("turn"), ev.get("phase"),
                                            ev.get("side", "")))
        elif kind == "tick":
            for p in self.panels:
                if p.winfo_exists():
                    p.set_phase(ev.get("label", ""), ev.get("remaining"), ev.get("cap"))
        elif kind == "phase":
            for p in self.panels:
                if p.winfo_exists():
                    p.set_phase(ev.get("label", ""))
        elif kind == "started":
            self.log("run started in {} mode{}".format(
                ev.get("mode"), " (dry run)" if ev.get("dry_run") else ""))
        elif kind == "stopped":
            self.state["paused"] = False
            self.btn_pause.configure(text="Pause")
            self.log("run stopped")
        elif kind == "halted":
            # the run stopped itself because it could not go on safely;
            # say so in a box as well as the log, the operator may be away
            if not os.environ.get("CONN_NO_DIALOGS"):
                try:
                    self.after(50, lambda t=ev.get("text", ""): messagebox.showwarning(
                        "CONN stopped the run", t))
                except Exception:
                    pass
        elif kind == "rag":
            pass
        elif kind == "rag_learn":
            # the bridge learned something from its own run; show it so the
            # operator can see the knowledge base growing, not just a counter
            for s in ev.get("samples", [])[:3]:
                self.log("RAG learned: " + str(s))
        elif kind == "dry_run":
            pass

    def on_close(self):
        try:
            if getattr(self, "_pump_id", None):
                try:
                    self.after_cancel(self._pump_id)
                except Exception:
                    pass
                self._pump_id = None
            self.engine.abort()
            self.hotkey.stop(wait=0.3)
            self.wm_.stop_watch()
            self.overlay.destroy()
            self._remember_mission()
            try:
                self.cfg.save()
            except Exception:
                pass            # a refused save must not keep the window open
        finally:
            self.destroy()


def main():
    app = ConnApp()
    app.mainloop()
