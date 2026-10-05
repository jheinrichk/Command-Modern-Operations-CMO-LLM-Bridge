# ============================================================
# CMO + LLM BRIDGE - CALIBRATION UI (Resizable)
# Same capture mechanism as the original (which works well).
# Extended with LLM browser points and simulation controls:
#   play / pause / time-compression / scenario start/reset/reload.
# Writes the SAME bridge_config.json keys the main bridge reads.
# ============================================================

import json
import os
import time
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("ERROR: pyautogui is not installed. Run: pip install pyautogui")
    input("Press Enter to exit...")
    exit()

CONFIG_PATH = Path(__file__).with_name("bridge_config.json")

# Grouped so the window reads clearly. Keys MUST match the main bridge.
CALIBRATION_POINTS = [
    # --- LLM browser tab ---
    ("llm_input", "LLM / browser input field"),
    ("llm_submit", "LLM submit button"),
    ("llm_code_copy", "LLM response code block (copy area)"),
    # --- CMO Lua console ---
    ("cmo_lua_input", "CMO Lua console input field"),
    ("cmo_execute", "CMO Lua Execute / Run button"),
    ("cmo_popup_ok", "CMO popup dialog OK button (after running Lua)"),
    ("cmo_output_area", "CMO Lua output area (for copying results)"),
    # --- CMO simulation controls (NEW) ---
    ("cmo_play", "CMO Play / Resume simulation"),
    ("cmo_pause", "CMO Pause / Stop simulation"),
    ("cmo_time_comp_up", "CMO Time-Compression increase"),
    ("cmo_time_comp_down", "CMO Time-Compression decrease"),
    ("cmo_scenario_start", "CMO Scenario Start (if separate from Play)"),
    ("cmo_scenario_reset", "CMO Scenario Reset / Restart"),
    ("cmo_scenario_reload", "CMO Scenario Reload from file"),
]


LOAD_FAILED = False


def load_config():
    global LOAD_FAILED
    LOAD_FAILED = False
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            # never save over a file that could not be read: it holds CONN's
            # anchors, layouts and settings, not only these coordinates
            LOAD_FAILED = True
    return {"coordinates": {}}


def save_config(config):
    """Write only the legacy coordinates back into the current file, in one
    atomic replace. CONN's anchors, layouts and settings in the same file
    are re-read from disk and kept as they are."""
    if LOAD_FAILED:
        messagebox.showwarning("Calibration", "bridge_config.json could not be read, so "
                               "nothing was saved. Fix the file and reopen this window.")
        return False
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            messagebox.showwarning("Calibration", "bridge_config.json changed and can no "
                                   "longer be read; nothing was saved.")
            return False
    data["coordinates"] = config.get("coordinates", {})
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(CONFIG_PATH))
    return True


class CalibrationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CMO + LLM Bridge - Calibration")
        self.root.geometry("640x780")
        self.root.minsize(540, 620)

        self.config = load_config()
        if "coordinates" not in self.config:
            self.config["coordinates"] = {}

        self.countdown_seconds = tk.IntVar(value=5)
        self.hide_window = tk.BooleanVar(value=True)
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="CMO + LLM Bridge Calibration",
                 font=("Arial", 14, "bold")).pack(pady=8)
        tk.Label(
            self.root,
            text="Click a button, move your mouse to the target, wait for the countdown.\n"
                 "Simulation-control points are optional but enable play / pause / time\n"
                 "compression / reset / reload from inside any bridge cycle.",
            justify="left",
        ).pack(pady=5, padx=10)

        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Label(frame, text="Countdown (seconds):").pack(side="left")
        tk.Entry(frame, textvariable=self.countdown_seconds, width=5).pack(side="left", padx=5)
        tk.Checkbutton(frame, text="Hide window during countdown",
                       variable=self.hide_window).pack(side="left")

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=8, padx=10)

        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas)
        scrollable.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.buttons = {}
        section_headers = {
            "llm_input": "LLM browser",
            "cmo_lua_input": "CMO Lua console",
            "cmo_play": "CMO simulation controls",
        }
        for key, description in CALIBRATION_POINTS:
            if key in section_headers:
                tk.Label(scrollable, text=section_headers[key],
                         font=("Arial", 10, "bold"), fg="#334").pack(
                    anchor="w", pady=(8, 2))
            row = tk.Frame(scrollable)
            row.pack(fill="x", pady=3)
            tk.Button(row, text="Calibrate: {}".format(key), width=26,
                      command=lambda k=key: self.start_countdown_capture(k)).pack(side="left")
            status = tk.Label(row, text="Not set", fg="gray", width=16)
            status.pack(side="left", padx=6)
            tk.Label(row, text=description, fg="#666", anchor="w").pack(side="left")
            self.buttons[key] = status
            if key in self.config.get("coordinates", {}):
                status.config(text="\u2713 Calibrated", fg="green")

        bottom = tk.Frame(self.root)
        bottom.pack(pady=10)
        tk.Button(bottom, text="Save & Close", command=self.save_and_close,
                  width=14).pack(side="left", padx=5)
        tk.Button(bottom, text="Reset All", command=self.reset_all,
                  width=12).pack(side="left", padx=5)

        self.status = tk.Label(self.root, text="Ready", relief="sunken", anchor="w")
        self.status.pack(fill="x", side="bottom")

    def start_countdown_capture(self, key):
        seconds = self.countdown_seconds.get()
        if self.hide_window.get():
            self.root.withdraw()
        for i in range(seconds, 0, -1):
            self.status.config(text="Capturing {} in {} seconds... Move mouse now!".format(key, i))
            self.root.update()
            time.sleep(1)
        try:
            x, y = pyautogui.position()
            self.config.setdefault("coordinates", {})[key] = [x, y]
            if key in self.buttons:
                self.buttons[key].config(text="\u2713 Calibrated", fg="green")
            self.status.config(text="Captured {} at ({}, {})".format(key, x, y))
            save_config(self.config)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        if self.hide_window.get():
            self.root.deiconify()
            self.root.lift()

    def reset_all(self):
        if messagebox.askyesno("Reset", "Reset all calibration points?"):
            self.config["coordinates"] = {}
            save_config(self.config)
            for key in self.buttons:
                self.buttons[key].config(text="Not set", fg="gray")

    def save_and_close(self):
        save_config(self.config)
        messagebox.showinfo("Saved", "Calibration saved!")
        self.root.destroy()


def main():
    try:
        root = tk.Tk()
        CalibrationUI(root)
        root.mainloop()
    except Exception as e:
        print("ERROR:", e)
        input("Press Enter to close...")


if __name__ == "__main__":
    main()
