"""
conn.monitor  -  the process monitor that replaces the bridge console window.

The same widget is used twice: once as a tab in the main window and once in
the narrow undocked strip, both fed from the engine event queue.
"""

import time
import tkinter as tk
from .tooltips import tip
from tkinter import ttk

STAGES = ["AUDIT", "DESIGN", "PLAYTEST", "DEPLOY", "TEST", "EVALUATE", "REFINE", "RETEST",
          "FIX_ERRORS", "REPORT", "DONE"]
CHIP_TEXT = {"FIX_ERRORS": "FIX"}
TURN_PHASES = ["AWAIT_TURN", "SITREP", "ORDERS", "ARBITER", "INJECT", "END_TURN"]


class MonitorPanel(ttk.Frame):
    def __init__(self, master, app, compact=False):
        super().__init__(master, style="TFrame")
        self.app = app
        self.compact = compact
        self.pal = app.pal
        self.chips = {}
        self._log_lines = []
        self._shown = {}            # widget -> text last written, to skip rewrites
        self._log_limit = int(getattr(app, "cfg", None).get("ui.log_tail_lines", 800)
                              if getattr(app, "cfg", None) else 800) or 800
        self._build()

    # -- construction ----------------------------------------------
    def _build(self):
        pal = self.pal
        head = ttk.Frame(self, style="TFrame")
        head.pack(fill="x", padx=6, pady=(6, 2))
        self.lbl_mode = ttk.Label(head, text="IDLE", style="Head.TLabel")
        self.lbl_mode.pack(side="left")
        self.lbl_dry = ttk.Label(head, text="", style="Banner.TLabel")
        self.lbl_dry.pack(side="right")

        chipbar = ttk.Frame(self, style="TFrame")
        chipbar.pack(fill="x", padx=6, pady=2)
        for i, s in enumerate(STAGES):
            txt = CHIP_TEXT.get(s, s)
            lab = tk.Label(chipbar, text=txt[:4] if self.compact else txt,
                           font=("Consolas", 8, "bold"), padx=4, pady=2,
                           bg=pal["chip_off"], fg=pal["muted"])
            lab.grid(row=0, column=i, padx=1, sticky="ew")
            chipbar.grid_columnconfigure(i, weight=1)
            self.chips[s] = lab

        counters = ttk.Frame(self, style="TFrame")
        counters.pack(fill="x", padx=6, pady=2)
        self.lbl_counts = ttk.Label(counters, text="cycle 0   errors 0   retries 0",
                                    style="Muted.TLabel", font=("Consolas", 9))
        self.lbl_counts.pack(side="left")

        ph = ttk.Frame(self, style="TFrame")
        ph.pack(fill="x", padx=6, pady=(4, 2))
        self.lbl_phase = ttk.Label(ph, text="idle", font=("Consolas", 9))
        self.lbl_phase.pack(anchor="w")
        self.bar = ttk.Progressbar(ph, mode="determinate", maximum=100,
                                   style="Horizontal.TProgressbar")
        self.bar.pack(fill="x", pady=2)

        self.lua_box, self.lua_frame = self._text_block("Last Lua sent", 4,
                                                        lambda: self._expand("Last Lua sent",
                                                                             self.app.state.get("last_lua", "")))
        self.out_box, self.out_frame = self._text_block("Last CMO output", 5,
                                                        lambda: self._expand("Last CMO output",
                                                                             self.app.state.get("last_output", "")))

        ragf = ttk.Frame(self, style="TFrame")
        ragf.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Label(ragf, text="RAG hits", style="Muted.TLabel").pack(anchor="w")
        self.rag = tip(tk.Listbox(ragf, height=3, font=("Consolas", 8),
                                  bg=self.pal["entry"], fg=self.pal["fg"],
                                  highlightthickness=0, borderwidth=0),
                       "Titles of the pinned rules, lessons, recipes and notes retrieved "
                       "for the last prompt. Shows what the model was grounded on.")
        self.rag.pack(fill="x")

        ctrl = ttk.Frame(self, style="TFrame")
        ctrl.pack(fill="x", padx=6, pady=6)
        self.btn_pause = tip(ttk.Button(ctrl, text="Pause", width=8,
                                        command=self.app.toggle_pause),
                             "Hold the run between steps. Press again to resume.")
        self.btn_pause.pack(side="left", padx=2)
        tip(ttk.Button(ctrl, text="Step", width=6, command=self.app.step),
            "Release the current wait: your turn is given, the save is loaded, "
            "the IKE hand-off is done.").pack(side="left", padx=2)
        tip(ttk.Button(ctrl, text="Abort", width=7, style="Danger.TButton",
                       command=self.app.abort),
            "Stop the run now. Nothing more is clicked or typed.").pack(side="left", padx=2)
        if hasattr(self.app, "open_session_folder"):
            tip(ttk.Button(ctrl, text="Session folder", command=self.app.open_session_folder),
                "Open this run's folder: transcript, every script sent, the events log "
                "and the report.").pack(side="right", padx=2)
        tip(ttk.Button(ctrl, text="Copy log", command=self._copy_log),
            "Copy the whole log (all lines kept, not only the filtered ones) to the "
            "clipboard.").pack(side="right", padx=2)

        logf = ttk.Frame(self, style="TFrame")
        logf.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        fl = ttk.Frame(logf, style="TFrame")
        fl.pack(fill="x")
        ttk.Label(fl, text="Log", style="Muted.TLabel").pack(side="left")
        self.filter_var = tk.StringVar()
        e = tip(ttk.Entry(fl, textvariable=self.filter_var, width=14),
                "Show only log lines containing this text.")
        e.pack(side="right")
        self.filter_var.trace_add("write", lambda *_: self._render_log())
        body = ttk.Frame(logf, style="TFrame")
        body.pack(fill="both", expand=True)
        self.log = tip(tk.Text(body, height=6 if self.compact else 10, wrap="none",
                               font=("Consolas", 8), bg=self.pal["entry"],
                               fg=self.pal["fg"], insertbackground=self.pal["fg"],
                               highlightthickness=0, borderwidth=0),
                       "Everything CONN did and saw this run, newest at the bottom. "
                       "Scroll up to read; it stops following new lines until you "
                       "scroll back to the bottom.")
        sb = ttk.Scrollbar(body, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self.log.configure(state="disabled")

    def _text_block(self, title, height, expand_cb):
        f = ttk.Frame(self, style="TFrame")
        f.pack(fill="x", padx=6, pady=(4, 0))
        bar = ttk.Frame(f, style="TFrame")
        bar.pack(fill="x")
        ttk.Label(bar, text=title, style="Muted.TLabel").pack(side="left")
        tip(ttk.Button(bar, text="expand", width=8, command=expand_cb),
            "Open the full text in its own window.").pack(side="right")
        t = tip(tk.Text(f, height=height, wrap="none", font=("Consolas", 8),
                        bg=self.pal["entry"], fg=self.pal["fg"],
                        highlightthickness=0, borderwidth=0),
                {"Last Lua sent": "The script most recently injected into the CMO console.",
                 "Last CMO output": "What the CMO result pane returned for that script."}.get(
                    title, title))
        t.pack(fill="x")
        t.configure(state="disabled")
        return t, f

    def _expand(self, title, text):
        top = tk.Toplevel(self)
        top.title(title)
        top.geometry("900x600")
        top.configure(bg=self.pal["bg"])
        txt = tk.Text(top, wrap="none", font=("Consolas", 10),
                      bg=self.pal["entry"], fg=self.pal["fg"],
                      insertbackground=self.pal["fg"])
        sb = ttk.Scrollbar(top, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", text or "(empty)")

    # -- updates ----------------------------------------------------
    def set_palette(self, pal):
        self.pal = pal
        for s, lab in self.chips.items():
            lab.configure(bg=pal["chip_off"], fg=pal["muted"])
        for t in (self.lua_box, self.out_box, self.log):
            t.configure(bg=pal["entry"], fg=pal["fg"])
        self.rag.configure(bg=pal["entry"], fg=pal["fg"])

    def refresh(self, state):
        pal = self.pal
        mode = state.get("mode", "idle")
        self.lbl_mode.configure(text="{}  {}".format(
            mode.upper(), "RUNNING" if state.get("running") else "IDLE"))
        self.lbl_dry.configure(text=" DRY RUN " if state.get("dry_run") else "")
        stage = (state.get("stage") or "").upper()
        for s, lab in self.chips.items():
            if s == stage:
                lab.configure(bg=pal["accent"], fg=pal["bg"])
            else:
                lab.configure(bg=pal["chip_off"], fg=pal["muted"])
        counts = "cycle {}   errors {}   retries {}".format(
            state.get("cycle", 0), state.get("errors", 0), state.get("retries", 0))
        if state.get("turn"):
            counts = "turn {} {}   ".format(state.get("turn"), state.get("side", "")) + counts
        self.lbl_counts.configure(text=counts)
        self._set_text(self.lua_box, (state.get("last_lua") or "")[:1200])
        self._set_text(self.out_box, (state.get("last_output") or "")[:1500])
        hits = state.get("rag_hits") or []
        if list(self.rag.get(0, "end")) != list(hits):
            self.rag.delete(0, "end")
            for h in hits:
                self.rag.insert("end", h[:60])
        self.btn_pause.configure(text="Resume" if state.get("paused") else "Pause")

    def set_phase(self, label, remaining=None, cap=None):
        if not label:
            self.lbl_phase.configure(text="idle")
            self.bar["value"] = 0
            return
        if remaining is not None and cap:
            self.lbl_phase.configure(text="{}  {}s / {}s".format(label, remaining, cap))
            self.bar["value"] = max(0, min(100, 100.0 * (cap - remaining) / max(1, cap)))
        else:
            self.lbl_phase.configure(text=label)

    def _set_text(self, widget, text):
        # refresh() runs every 120 ms; rewriting unchanged text reset the
        # scroll position and made the boxes impossible to read
        text = text or ""
        if self._shown.get(widget) == text:
            return
        self._shown[widget] = text
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _at_bottom(self):
        try:
            return self.log.yview()[1] >= 0.999
        except Exception:
            return True

    def append_log(self, line):
        self._log_lines.append(line)
        limit = max(800, int(self._log_limit))
        if len(self._log_lines) > limit:
            self._log_lines = self._log_lines[-limit:]
        f = (self.filter_var.get() or "").lower()
        if f and f not in line.lower():
            return
        follow = self._at_bottom()
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        # keep the widget as bounded as the list; it grew without limit
        extra = int(self.log.index("end-1c").split(".")[0]) - limit - 1
        if extra > 0:
            self.log.delete("1.0", "{}.0".format(extra + 1))
        if follow:
            self.log.see("end")
        self.log.configure(state="disabled")

    def _copy_log(self):
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(self._log_lines))
        except Exception:
            pass

    def _render_log(self):
        f = (self.filter_var.get() or "").lower()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        for line in self._log_lines:
            if not f or f in line.lower():
                self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def stamp():
    return time.strftime("%H:%M:%S")
