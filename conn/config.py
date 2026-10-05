"""
conn.config  -  single config file shared with the legacy bridge.

Reads and writes bridge_config.json in the package root. The legacy keys
(timing, bridge, coordinates, hotkeys, pbem) are preserved untouched so the
old command-line bridge keeps working. CONN adds:

    windows   window match rules (title / class / exe)
    anchors   window-relative click targets (replaces absolute coordinates)
    layouts   named window-arrangement profiles, keyed by display topology
    ui        UI preferences (dock side, strip width, dry-run default)
    io        IN / OUT folders and the large-paste threshold
    play      play-mode settings (modes, sides, turn engine, agents)
    safety    editor lock, abort hotkey, confirmation rules
"""

import copy
import json
import os
import re
import shutil
import time
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
# CONN_CONFIG_PATH points CONN at another config file. The smoke tests use
# it so they can never write into the real bridge_config.json again.
CONFIG_PATH = Path(os.environ.get("CONN_CONFIG_PATH") or (PKG_ROOT / "bridge_config.json"))

# ------------------------------------------------------------------
# Anchors prefilled from the calibrated 3840 x 2160 arrangement in the
# reference screenshot. mode "frac" = fraction of window width/height.
# mode "px"   = pixel offset from the named corner (tl, tr, bl, br),
#               which survives resizing for toolbar and edge controls.
# ------------------------------------------------------------------
DEFAULT_ANCHORS = {
    "llm_input":        {"window": "llm",  "mode": "frac", "dx": 0.6577, "dy": 0.7936},
    "llm_submit":       {"window": "llm",  "mode": "px", "corner": "br", "dx": 114, "dy": 149},
    "llm_code_copy":    {"window": "llm",  "mode": "px", "corner": "tr", "dx": 105, "dy": 339},
    "cmo_lua_input":       {"window": "cmo_lua", "mode": "frac", "dx": 0.1471, "dy": 0.6305},
    "cmo_execute":         {"window": "cmo_lua", "mode": "px", "corner": "tr", "dx": 210, "dy": 398},
    "cmo_output_area":     {"window": "cmo_lua", "mode": "frac", "dx": 0.1328, "dy": 0.1909},
    "cmo_popup_ok":        {"window": "cmo",     "mode": "frac", "dx": 0.2225, "dy": 0.5290},
    "cmo_play":            {"window": "cmo",     "mode": "px", "corner": "tl", "dx": 246, "dy": 127},
    "cmo_pause":           {"window": "cmo",     "mode": "px", "corner": "tl", "dx": 252, "dy": 136},
    "cmo_time_comp_up":    {"window": "cmo",     "mode": "px", "corner": "tl", "dx": 121, "dy": 645},
    "cmo_time_comp_down":  {"window": "cmo",     "mode": "px", "corner": "tl", "dx": 78,  "dy": 645},
    # Attach sequence for oversized prompts, used only when
    # io.attach_method is "anchors". The default ctrl_u route needs none of
    # these. Calibrate them for a browser LLM without a Ctrl+U shortcut:
    # the attach (+) control, the menu entry that opens the file dialog,
    # the dialog's filename field and its Open button.
    "llm_attach_button":   None,
    "llm_attach_menu":     None,
    "file_dialog_filename": None,
    "file_dialog_open":    None,
    # Never calibrated in the source config. Left unset on purpose so
    # preflight reports them instead of clicking a wrong place.
    "cmo_scenario_start":  None,
    "cmo_scenario_reset":  None,
    "cmo_scenario_reload": None,
}

# Fractions of the virtual desktop, taken from the reference screenshot.
SCENARIO_DEV_LAYOUT = {
    "llm":  {"rect": [0.000, 0.005, 0.385, 0.495], "z": 3},
    "cmo_lua": {"rect": [0.000, 0.490, 0.474, 0.972], "z": 2},
    "cmo":     {"rect": [0.474, 0.003, 1.000, 0.962], "z": 1},
    "conn":    {"rect": [0.382, 0.147, 0.622, 0.486], "z": 4, "topmost": True},
}

PLAY_LAYOUT = {
    "cmo":     {"rect": [0.000, 0.000, 0.840, 1.000], "z": 1},
    "conn":    {"rect": [0.840, 0.000, 1.000, 1.000], "z": 4, "topmost": True},
    "cmo_lua": {"rect": [0.050, 0.560, 0.560, 0.980], "z": 2},
    "llm":  {"rect": [0.300, 0.020, 0.830, 0.560], "z": 3},
}

DEFAULTS = {
    # merged into the existing legacy "bridge" block, nothing there is replaced
    "bridge": {
        # a failed script is a repair cycle, not an ending
        "stop_on_fix_errors": False,
        "max_consecutive_failures": 8,
        "max_repeat_signature": 3,
        "copy_method": "button",
        "copy_clipboard_settle_seconds": 3.0,
        # the console's "Echo input script on result text" box. Off means the
        # pane holds output only, which is what the run markers assume.
        "echo_input_script": False,
        "use_run_markers": True,
        # the LLM tab guard: blank = no title check; the lock stops a run
        # when a different chat comes to the front mid-run
        "llm_title_must_contain": "",
        "lock_llm_tab": True,
    },
    # merged into the existing legacy "timing" block, nothing there is replaced
    "timing": {
        "llm_scroll_page_downs": 2,
        "llm_scroll_pause_seconds": 0.4,
        "cmo_output_poll_seconds": 2.0,
        "cmo_output_timeout_seconds": 90,
        "file_dialog_wait_seconds": 1.5,
        "upload_wait_base_seconds": 5,
        "upload_wait_per_100kb_seconds": 2,
        # reply handling: first look, poll interval, longest wait, and how
        # many reprints of a broken block before the run stops
        "llm_min_wait_seconds": 15,
        "llm_reply_poll_seconds": 8,
        "llm_output_wait_seconds": 300,
        "llm_max_reprints": 2,
    },
    "windows": {
        "llm": {
            "label": "LLM browser tab",
            "title_regex": r"LLM",
            "class_regex": None,
            "exe_regex": r"(msedge|chrome|firefox)\.exe",
        },
        "cmo": {
            "label": "Command: Modern Operations",
            "title_regex": r"Command:? Modern Operations",
            "class_regex": None,
            "exe_regex": None,
        },
        "cmo_lua": {
            "label": "CMO Lua Console",
            "title_regex": r"Lua( Script)? Console",
            "class_regex": None,
            "exe_regex": None,
        },
        "conn": {
            "label": "CONN (this application)",
            "title_regex": r"^CONN",
            "class_regex": None,
            "exe_regex": None,
        },
    },
    "anchors": DEFAULT_ANCHORS,
    "layouts": {
        "active": "scenario_dev",
        "profiles": {
            "scenario_dev": {
                "label": "Scenario Development (reference screenshot)",
                "topology": "any",
                "windows": SCENARIO_DEV_LAYOUT,
            },
            "play": {
                "label": "Play / Turn Mode",
                "topology": "any",
                "windows": PLAY_LAYOUT,
            },
        },
    },
    "ui": {
        "dock_side": "right",
        "strip_width": 320,
        "reserve_strip_space": True,
        "dry_run_default": True,
        "monitor_always_on_top": True,
        "log_tail_lines": 400,
        "watch_rate_ms": 250,
        "use_winevent_hook": True,
    },
    "io": {
        "in_folder": "C:\\Users\\USER\\Desktop\\CMO_LLM_Bridge"
                     "\\CMO_LLM_Bridge\\LUA Output txt bc too big",
        "out_folder": "C:\\CMOBridge\\OUT",
        "sessions_folder": "C:\\CMOBridge\\SESSIONS",
        "snapshots_folder": "C:\\CMOBridge\\SNAPSHOTS",
        # 1500: everything larger is written to a payload txt in the
        # payload folder and attached to the conversation instead of pasted.
        # Large pastes get converted to attachment chips by the LLM web
        # client and those chips have been arriving empty; file attachments
        # arrive intact.
        "paste_max_chars": 1500,
        # payload folder cleanup (bridge-written prompt_*.txt only)
        "payload_keep_recent": 40,
        "payload_max_age_hours": 72,
        "payload_max_files": 400,
        "guard_clipboard": True,
        # oversized prompts: ctrl_u attaches through the browser shortcut,
        # anchors uses the calibrated attach sequence, chunks falls back to
        # sequential pastes into the same input, off truncates nothing and
        # always chunk-pastes
        "attach_method": "ctrl_u",
        "attach_hotkey": ["ctrl", "u"],
    },
    "play": {
        "mode": "design",
        "modes": ["design", "normal", "player_vs_llm", "llm_vs_llm", "pbem_h2h"],
        "my_side": "Blue",
        "opponent_side": "Red",
        "turn_length_minutes": 30,
        "order_deadline_minutes": 20,
        "turn_cap": 40,
        "order_budget_per_turn": 12,
        "arbiter_enabled": True,
        "side_lock": True,
        "watch_poll_seconds": 3,
        "agents": {
            "blue": {
                "label": "Blue Commander",
                "objectives": "Achieve the scenario victory conditions at least cost.",
                "roe": "Engage only declared hostiles. No strikes on neutral territory.",
                "persona": "Methodical task force commander. Concentrates force, protects the high value units.",
            },
            "red": {
                "label": "Red Commander",
                "objectives": "Deny the opposing force its objectives and inflict attrition.",
                "roe": "Engage on detection inside the declared exclusion zone.",
                "persona": "Aggressive asymmetric commander. Prefers saturation and deception.",
            },
        },
    },
    "safety": {
        "api_symbol_guard": True,
        "api_extra_symbols": [],
        "api_soft_symbols": [],
        "api_learn_from_dumps": True,
        "neutralize_console_suppression": True,
        "editor_lock_in_play_modes": True,
        "blocked_in_play": [
            "Tool_BuildBlankScenario", "ScenEdit_AddUnit", "ScenEdit_DeleteUnit",
            "ScenEdit_AddSide", "ScenEdit_RemoveSide", "ScenEdit_SetScore",
            "ScenEdit_SetSideOptions", "ScenEdit_UpdateUnit", "ScenEdit_SetTime",
            "ScenEdit_ImportInst", "Tool_EmulateNoNav",
        ],
        "abort_hotkey": "ctrl+alt+x",
        "confirm_ike_conversion": True,
        "lock_master_scen_readonly": True,
        "lua_syntax_check": True,
    },
    "ike": {
        "ike_conversion_lua_path": "C:\\CMOBridge\\IKE\\ike_convert.lua",
        "ike_release": "https://github.com/musurca/IKE/releases",
        "scenarios_folder": "C:\\CMOBridge\\SCENARIOS",
        "save_exchange_folder": "C:\\CMOBridge\\PBEM",
        "snapshot_suffix": "_preIKE",
    },
}


# Sections whose string values that look like numbers are turned into numbers
# on load. Older Settings saves stored "2.0" and "1.5" as text, and a later
# int("2.5") raised mid-run. Anchors, layouts and window rules are never
# touched here.
_NUMERIC_SECTIONS = ("timing", "bridge", "play", "io", "cmo", "popup", "mapshot", "ui")
_NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _coerce_numbers(node):
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if isinstance(v, str) and _NUM_RE.match(v.strip()):
                f = float(v)
                node[k] = int(f) if f.is_integer() and "." not in v else f
            elif isinstance(v, dict) and k != "agents":
                _coerce_numbers(v)
    return node


def num(value, default=0.0):
    """A config value as a number, whatever form it was stored in."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _merge(dst, src):
    for k, v in src.items():
        if k not in dst:
            dst[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
    return dst


class Config:
    """Thin wrapper over bridge_config.json with dotted-path access."""

    def __init__(self, path=None):
        self.path = Path(path) if path else CONFIG_PATH
        self.data = {}
        self.load_error = ""        # set when the file exists but cannot be read
        self._backed_up = False
        self._mtime = None
        self.load()

    def _disk_mtime(self):
        try:
            return self.path.stat().st_mtime
        except Exception:
            return None

    def load(self):
        self.load_error = ""
        self._mtime = self._disk_mtime()
        if self.path.exists():
            try:
                # utf-8-sig: a file saved by Notepad or PowerShell can start
                # with a byte-order mark, which plain utf-8 json refuses
                self.data = json.loads(self.path.read_text(encoding="utf-8-sig"))
                if not isinstance(self.data, dict):
                    raise ValueError("top level is not an object")
            except Exception as ex:
                # Never fall back to defaults silently: the next save would
                # overwrite the calibration and layouts with the built-in
                # ones. Keep a copy, remember the error, refuse to save.
                self.load_error = "{}: {}".format(type(ex).__name__, ex)
                try:
                    bad = self.path.with_name("{}.bad-{}{}".format(
                        self.path.stem, time.strftime("%Y%m%d_%H%M%S"), self.path.suffix))
                    shutil.copy2(str(self.path), str(bad))
                    self.load_error += " (copy kept as {})".format(bad.name)
                except Exception:
                    pass
                self.data = {}
        else:
            self.data = {}
        for sec in _NUMERIC_SECTIONS:
            if isinstance(self.data.get(sec), dict):
                _coerce_numbers(self.data[sec])
        _merge(self.data, DEFAULTS)
        self._migrate()
        return self.data

    def _migrate(self):
        """Force-correct stale values from older config files.

        A json written by an earlier package version can carry
        paste_max_chars 52000 and the old CMOBridge IN payload folder.
        Under the current LLM web client, pastes that large become
        attachment chips that arrive empty, so the file route must engage
        at 1500. Values are corrected in memory AND written back so the
        settings panel shows the truth. Explicit user choices below the
        cap are respected.
        """
        changed = []
        try:
            limit = int(num(self.get("io.paste_max_chars", 1500), 1500))
        except Exception:
            limit = 52000
        if limit > 1500:
            self.set("io.paste_max_chars", 1500)
            changed.append("io.paste_max_chars {} -> 1500".format(limit))
        legacy_in = "C:\\CMOBridge\\IN"
        cur_in = str(self.get("io.in_folder", "") or "")
        if cur_in.rstrip("\\") == legacy_in.rstrip("\\"):
            new_in = ("C:\\Users\\USER\\Desktop\\CMO_LLM_Bridge"
                      "\\CMO_LLM_Bridge\\LUA Output txt bc too big")
            self.set("io.in_folder", new_in)
            changed.append("io.in_folder -> LUA Output txt bc too big")
        # The 2026-09-07 package shipped with values the smoke tests had
        # written into the real config: every LLM/CMO wait at 0, a cycle
        # budget of 2 and a turn cap of 1. With a zero reply wait CONN tried
        # to copy one second after sending and looped on reprint requests.
        # A zero reply wait is that fingerprint; restore working values.
        try:
            zero_wait = float(self.get("timing.llm_output_wait_seconds", 300)) <= 0
        except (TypeError, ValueError):
            zero_wait = True
        if zero_wait:
            for key, val in (("timing.llm_output_wait_seconds", 300),
                             ("timing.llm_reprint_wait_seconds", 60),
                             ("timing.llm_copy_retry_wait_seconds", 40),
                             ("timing.cmo_output_wait_seconds", 20),
                             ("timing.sim_settle_seconds", 1.0)):
                try:
                    cur = float(self.get(key, 0) or 0)
                except (TypeError, ValueError):
                    cur = 0
                if cur <= 0:
                    self.set(key, val)
                    changed.append("{} 0 -> {}".format(key, val))
            if num(self.get("bridge.max_cycles", 500), 500) <= 2:
                self.set("bridge.max_cycles", 500)
                changed.append("bridge.max_cycles -> 500")
            if num(self.get("play.turn_cap", 40), 40) <= 1:
                self.set("play.turn_cap", 40)
                changed.append("play.turn_cap -> 40")
        for key, val in (("payload_keep_recent", 40),
                         ("payload_max_age_hours", 72),
                         ("payload_max_files", 400)):
            if self.get("io." + key) is None:
                self.set("io." + key, val)
        if changed:
            self.migrated = list(changed)
            try:
                self.save()
            except Exception:
                pass
        else:
            self.migrated = []

    def save(self):
        if self.load_error:
            # the file on disk could not be read; writing now would replace
            # the operator's calibration with defaults
            raise IOError("bridge_config.json was not saved: it could not be read at "
                          "start ({}). Fix or restore the file, then restart CONN."
                          .format(self.load_error))
        if not self._backed_up and self.path.exists():
            # one copy of the file as it was before this session's first save
            try:
                shutil.copy2(str(self.path), str(self.path.with_name(
                    self.path.stem + ".backup" + self.path.suffix)))
            except Exception:
                pass
            self._backed_up = True
        # The legacy calibration window writes "coordinates" into the same file.
        # If the file changed since CONN read it, keep the coordinates on disk
        # rather than putting CONN's older copy back.
        if self._mtime is not None and self._disk_mtime() not in (None, self._mtime):
            try:
                disk = json.loads(self.path.read_text(encoding="utf-8-sig"))
                if isinstance(disk.get("coordinates"), dict):
                    self.data["coordinates"] = disk["coordinates"]
            except Exception:
                pass
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        last = None
        for _ in range(5):
            try:
                os.replace(str(tmp), str(self.path))
                self._mtime = self._disk_mtime()
                return
            except PermissionError as ex:
                # sync clients and antivirus hold files open for a moment
                last = ex
                time.sleep(0.2)
        raise last

    # dotted access -------------------------------------------------
    def get(self, dotted, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted, value):
        parts = dotted.split(".")
        node = self.data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    # convenience ---------------------------------------------------
    @property
    def anchors(self):
        return self.data.setdefault("anchors", {})

    @property
    def windows(self):
        return self.data.setdefault("windows", {})

    @property
    def profiles(self):
        return self.data.setdefault("layouts", {}).setdefault("profiles", {})

    def folder(self, key):
        p = self.get("io." + key) or self.get("ike." + key)
        return Path(p) if p else None

    def ensure_folders(self):
        made = []
        for key in ("in_folder", "out_folder", "sessions_folder", "snapshots_folder"):
            p = self.folder(key)
            if p:
                try:
                    p.mkdir(parents=True, exist_ok=True)
                    made.append(str(p))
                except Exception:
                    pass
        return made
