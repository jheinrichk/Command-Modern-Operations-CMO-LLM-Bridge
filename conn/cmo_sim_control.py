"""
cmo_sim_control.py  —  Simulation control for the LLM bridge
===============================================================
REVISION: toggle-aware keystroke control

WHY THIS WAS REWRITTEN
----------------------
The previous version could never start the simulation on a Standard
Edition install. The bug:

    def _lua_call(self, snippet):
        if self.ensure_lua():
            self.p["run_lua"](snippet)
            return True          # True because the Lua RAN

    def play(self):
        if not self._lua_call("AGENT_SimPlay()"):
            self._click("cmo_play", ...)     # unreachable

AGENT_SimPlay() calls VP_RunSimulation, which is Professional Edition
only. On Standard it prints "SIMCTL_MISSING:VP_RunSimulation" and does
nothing, but _lua_call still returned True, so the fallback never fired.
The clock therefore never advanced (observed: tick delta 0 for a whole
session).

WHAT CHANGED
------------
1. PLAY / PAUSE are driven by the CALIBRATED CLICK by default, with the
   Space keystroke as the alternative (cmo_controls.method selects). Both
   act on the same toggle button, which is
   what actually works on this build.
2. Ctrl+Enter is a TOGGLE, so running state is tracked. Without this a
   directive line like "START; COMPRESS=15; RUNFOR=600" toggles twice and
   leaves the sim paused.
3. TIME COMPRESSION still uses Lua VP_SetTimeCompression, confirmed
   working on this build.
4. _lua_call is only used for operations where Lua is trusted, so the
   fallbacks stay reachable.
5. Window focus is self-contained (ctypes), so keystrokes land in the CMO
   main window rather than the Lua console or the browser.

COMPATIBILITY
-------------
Drop-in replacement. Same class name, constructor signature, public
methods and parse_control_directives(). The bridge main script needs NO
changes. Optional primitives ("key", "focus_cmo") are used when supplied,
otherwise this module uses its own pyautogui + ctypes implementation.

OPERATOR NOTE
-------------
Compression-change notification triggers are disabled in the sim, so the
scenario keeps running at the set compression regardless of message-log
entries.
"""

import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIMCTL_LUA = HERE / "lua_unified" / "snippets" / "_sim_control_authoritative.lua"
CONFIG_PATH = HERE / "bridge_config.json"

try:
    import pyautogui
except Exception:  # keeps the module importable for offline tests
    pyautogui = None


# ------------------------------------------------------------------
# Config (read directly so the bridge main script needs no changes)
# ------------------------------------------------------------------
def _load_config():
    try:
        with open(str(CONFIG_PATH), "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


_CFG = _load_config()
_CTRL = _CFG.get("cmo_controls", {}) or {}
_WINDOWS = _CFG.get("windows", {}) or {}

# Keystroke map. Overridable via a "cmo_controls" block in bridge_config.json.
KEY_PLAY_PAUSE = tuple(_CTRL.get("play_pause", ["space"]))
KEY_COMP_UP = _CTRL.get("time_comp_up", "add")
KEY_COMP_DOWN = _CTRL.get("time_comp_down", "subtract")
KEY_COMP_NORMAL = _CTRL.get("time_comp_normal", "enter")
KEY_SAVE = tuple(_CTRL.get("save", ["ctrl", "s"]))
SIM_CONTROL_METHOD = str(_CTRL.get("method", "click")).lower()
# The order each method tries. Every method has a fallback, so a missing
# anchor or an unconfirmed focus never leaves the clock untouched silently.
#   click     : the calibrated coordinate first, then the keystroke
#   keystroke : the keystroke first, then the calibrated coordinate
#   lua       : Professional Edition only; then click, then keystroke
METHOD_ORDER = {
    "click": ("click", "keystroke"),
    "coords": ("click", "keystroke"),
    "keystroke": ("keystroke", "click"),
    "lua": ("lua", "click", "keystroke"),
}
FOCUS_BEFORE_KEYS = bool(_CTRL.get("focus_cmo_before_keys", True))
KEY_SETTLE_SECONDS = float(_CTRL.get("key_settle_seconds", 0.35))

_CMO_TITLE_REGEX = "Command:? Modern Operations"
try:
    _cmo_win = _WINDOWS.get("cmo", {}) or {}
    if _cmo_win.get("title_regex"):
        _CMO_TITLE_REGEX = _cmo_win.get("title_regex")
except Exception:
    pass


# ------------------------------------------------------------------
# Self-contained CMO window focus (ctypes; no dependency on conn/)
# ------------------------------------------------------------------
try:
    import ctypes
    import ctypes.wintypes

    _user32 = ctypes.windll.user32
    _EnumWindows = _user32.EnumWindows
    _EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                          ctypes.c_void_p)
    _IsWindowVisible = _user32.IsWindowVisible
    _GetWindowTextW = _user32.GetWindowTextW
    _GetWindowTextLengthW = _user32.GetWindowTextLengthW
    _SetForegroundWindow = _user32.SetForegroundWindow
    _GetForegroundWindow = _user32.GetForegroundWindow
    _GetWindowRect = _user32.GetWindowRect
    _ShowWindow = _user32.ShowWindow
    _SW_RESTORE = 9
    _HAS_CTYPES = True
except Exception:
    _HAS_CTYPES = False


def _window_title(hwnd):
    try:
        n = _GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        _GetWindowTextW(hwnd, buf, n + 1)
        return buf.value
    except Exception:
        return ""


def find_cmo_window():
    """Return the hwnd of the CMO main window, or None.

    Deliberately EXCLUDES the Lua console: its title contains 'Lua', and
    sending Ctrl+Enter there would do nothing useful.
    """
    if not _HAS_CTYPES:
        return None
    found = []
    try:
        rx = re.compile(_CMO_TITLE_REGEX, re.IGNORECASE)
    except Exception:
        rx = re.compile("Command", re.IGNORECASE)

    def cb(hwnd, lparam):
        try:
            if _IsWindowVisible(hwnd):
                title = _window_title(hwnd)
                if title and rx.search(title) and "lua" not in title.lower():
                    found.append(hwnd)
        except Exception:
            pass
        return True

    try:
        _EnumWindows(_EnumWindowsProc(cb), 0)
    except Exception:
        return None
    return found[0] if found else None


def _foreground_is(hwnd):
    try:
        return _GetForegroundWindow() == hwnd
    except Exception:
        return False


def _window_rect(hwnd):
    try:
        r = ctypes.wintypes.RECT()
        if _GetWindowRect(hwnd, ctypes.byref(r)):
            return r.left, r.top, r.right, r.bottom
    except Exception:
        pass
    return None


def focus_cmo_window():
    """Bring the CMO main window to the foreground so keystrokes land there.

    VERIFIED, not assumed: SetForegroundWindow is silently denied to
    background processes, so the result is checked with
    GetForegroundWindow. On denial the title bar is clicked instead,
    because a real mouse click always grants focus. Returns True only
    when CMO is confirmed foreground.
    """
    hwnd = find_cmo_window()
    if hwnd is None:
        return False
    try:
        _ShowWindow(hwnd, _SW_RESTORE)
        _SetForegroundWindow(hwnd)
        time.sleep(0.3)
        if _foreground_is(hwnd):
            return True
        # denied: click the title bar to take focus the honest way
        rect = _window_rect(hwnd)
        if rect and pyautogui is not None:
            left, top, right, _bottom = rect
            x = left + max(120, int((right - left) * 0.35))
            y = top + 10
            try:
                pyautogui.click(x, y)
            except Exception:
                return False
            time.sleep(0.3)
            return _foreground_is(hwnd)
        return False
    except Exception:
        return False


def load_simctl_lua():
    if SIMCTL_LUA.exists():
        return SIMCTL_LUA.read_text(encoding="utf-8", errors="replace")
    return ""


class SimController:
    """
    primitives: dict with callables the bridge provides:
        run_lua(code)      -> injects code into CMO console and executes
        click(name, label) -> clicks a calibrated coordinate by name
        has_coord(name)    -> bool
        log(msg)
        sleep(seconds)
      optional:
        key(*keys)         -> press a hotkey chord
        focus_cmo()        -> focus the CMO window

    prefer_lua: use the Lua path for operations where Lua is TRUSTED.
                Play/pause are keystroke-driven regardless, because the
                VP_ run/pause globals are Professional Edition only.
    """

    # CMO steps through these discrete compression values on +/-.
    COMP_LADDER = [1, 2, 5, 15, 30, 60, 300, 600, 1800, 3600]

    def __init__(self, primitives, prefer_lua=True):
        self.p = primitives
        self.prefer_lua = prefer_lua
        self._lua_loaded = False
        # Toggle-state tracking. Ctrl+Enter is a toggle, so the controller
        # must know whether the sim is already running. The bridge starts
        # with the scenario paused.
        self._running = False
        self._comp_now = 1

    # ---------------- low-level helpers ----------------
    def _log(self, msg):
        try:
            self.p["log"](msg)
        except Exception:
            print(msg)

    def _sleep(self, seconds):
        try:
            self.p["sleep"](seconds)
        except Exception:
            time.sleep(seconds)

    def _focus_cmo(self):
        """Focus the CMO main window before sending keystrokes."""
        fn = self.p.get("focus_cmo")
        if fn:
            try:
                fn()
                return True
            except Exception:
                pass
        return focus_cmo_window()

    def _key(self, *keys):
        """Send a hotkey chord to the focused window."""
        fn = self.p.get("key")
        if fn:
            try:
                fn(*keys)
                return True
            except Exception:
                pass
        if pyautogui is None:
            self._log("pyautogui unavailable; cannot send keystroke {}".format(keys))
            return False
        try:
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                # Explicit chord with gaps. pyautogui.hotkey can decay under
                # focus churn so that only the final key registers; in the
                # CMO main window a bare Enter means compression 1:1, which
                # is exactly the observed failure. Held modifiers with real
                # gaps make the chord land whole.
                mods, last = keys[:-1], keys[-1]
                for m in mods:
                    pyautogui.keyDown(m)
                    time.sleep(0.08)
                pyautogui.press(last)
                time.sleep(0.08)
                for m in reversed(mods):
                    pyautogui.keyUp(m)
                    time.sleep(0.05)
            return True
        except Exception as ex:
            self._log("Keystroke {} failed: {}".format(keys, ex))
            # never leave a modifier latched after a failure
            try:
                for m in keys[:-1]:
                    pyautogui.keyUp(m)
            except Exception:
                pass
            return False

    def _send_toggle(self, reason):
        """Focus CMO, VERIFY it, then send the play/pause toggle.

        A keystroke into the wrong window is worse than no keystroke:
        a decayed chord in the CMO main window sets compression to 1:1
        and elsewhere it does something unrelated. So the chord is only
        sent when CMO is confirmed foreground. Returns False otherwise
        and the caller falls back to the calibrated coordinate click,
        which self-focuses by nature.
        """
        if FOCUS_BEFORE_KEYS:
            if not self._focus_cmo():
                self._log("Focus on the CMO window could not be confirmed; "
                          "withholding the {} keystroke.".format(reason))
                return False
        ok = self._key(*KEY_PLAY_PAUSE)
        self._sleep(KEY_SETTLE_SECONDS)
        return ok

    # -- ensure AGENT_* helpers exist in the console once per session --
    def ensure_lua(self):
        if self._lua_loaded:
            return True
        code = load_simctl_lua()
        if not code:
            return False
        self.p["run_lua"](code)
        self._lua_loaded = True
        self._log("Sim-control Lua helpers injected (AGENT_*).")
        return True

    def _lua_call(self, snippet):
        """Run a Lua snippet. Only use this for operations known to work on
        this build; play/pause must NOT rely on it."""
        if not self.prefer_lua:
            return False
        if self.ensure_lua():
            self.p["run_lua"](snippet)
            return True
        return False

    def _click(self, name, label):
        """Click a calibrated anchor. Honours the primitive's result: an
        anchor that is set but cannot be clicked right now (window gone,
        pyautogui fault) is a failure, not a success. Only a failure lets
        the caller fall back to the keystroke."""
        if not self.p["has_coord"](name):
            self._log("No coordinate for {} (skipping UI click).".format(name))
            return False
        try:
            result = self.p["click"](name, label)
        except Exception as ex:
            self._log("Click {} raised {}: {}".format(name, type(ex).__name__, ex))
            return False
        # a primitive that returns nothing is the old contract: assume it clicked
        if result is None:
            return True
        return bool(result)

    # ---------------- public control surface ----------------
    def is_running(self):
        return self._running

    def _toggle(self, anchor, reason, lua_fn):
        """Drive the single play/pause toggle by the configured method,
        falling through the method's order until one route reports
        success. Returns the route that worked, or None."""
        order = METHOD_ORDER.get(SIM_CONTROL_METHOD, METHOD_ORDER["click"])
        for route in order:
            if route == "click":
                if self._click(anchor, "CMO {} (calibrated click)".format(reason)):
                    return "click"
            elif route == "keystroke":
                if self._send_toggle(reason):
                    return "keystroke " + "+".join(KEY_PLAY_PAUSE)
            elif route == "lua":
                if self._lua_call(lua_fn):
                    return "lua"
        return None

    def play(self):
        """Start or resume the clock. No-op if already running: the
        button and the key are both toggles and would otherwise PAUSE."""
        if self._running:
            self._log("Sim already running; play() is a no-op (toggle).")
            return True
        how = self._toggle("cmo_play", "play", "AGENT_SimPlay()")
        if how:
            self._running = True
            self._log("Sim STARTED via {}.".format(how))
            return True
        self._log("Sim could not be started: no route succeeded "
                  "(method {}).".format(SIM_CONTROL_METHOD))
        return False

    def pause(self):
        """Pause the clock. No-op if already paused."""
        if not self._running:
            self._log("Sim already paused; pause() is a no-op (toggle).")
            return True
        how = self._toggle("cmo_pause", "pause", "AGENT_SimPause()")
        if how:
            self._running = False
            self._log("Sim PAUSED via {}.".format(how))
            return True
        self._log("Sim could not be paused: no route succeeded "
                  "(method {}).".format(SIM_CONTROL_METHOD))
        return False

    def set_compression(self, mult):
        """Set time compression.

        FIXED: the previous version called AGENT_SimSetCompression through
        _lua_call and then logged success because the Lua was INJECTED --
        not because it worked. The helper's own probe was broken, so the
        Lua printed SIMCTL_MISSING and did nothing while Python reported
        "set to x15". Compression silently stayed at 1x and every test
        window ran ~15x shorter in sim time than intended.

        This version emits a SELF-CONTAINED direct call that does not
        depend on the AGENT_* helper file at all, and prints a verifiable
        marker to the CMO console.
        """
        try:
            mult = int(mult)
        except Exception:
            mult = 15

        snippet = (
            "if VP_SetTimeCompression ~= nil then "
            "local o = pcall(VP_SetTimeCompression, {m}); "
            "print('BRIDGE_COMPRESSION_SET:' .. tostring(o) .. ':x{m}') "
            "else print('BRIDGE_COMPRESSION_ABSENT:x{m}') end"
        ).format(m=mult)

        try:
            self.p["run_lua"](snippet)
            self._comp_now = mult
            # Honest wording: we sent it, the console reports the result.
            self._log("Compression command sent (x{}). Console prints "
                      "BRIDGE_COMPRESSION_SET:true on success.".format(mult))
            return True
        except Exception as ex:
            self._log("Compression command failed to send: {}".format(ex))

        # keystroke ladder fallback: normalize to 1:1, then step up
        if SIM_CONTROL_METHOD == "keystroke":
            if FOCUS_BEFORE_KEYS:
                self._focus_cmo()
            self._key(KEY_COMP_NORMAL)
            self._sleep(0.15)
            target = self._nearest_ladder(mult)
            steps = self.COMP_LADDER.index(target)
            for _ in range(steps):
                self._key(KEY_COMP_UP)
                self._sleep(0.12)
            self._comp_now = target
            self._log("Time compression stepped to x{} (keystroke).".format(target))
            return True

        self._nudge_compression_ui(mult)
        return True

    def _nearest_ladder(self, mult):
        best = self.COMP_LADDER[0]
        for step in self.COMP_LADDER:
            if step <= mult:
                best = step
            else:
                break
        return best

    def _nudge_compression_ui(self, mult):
        steps = 0
        if mult >= 300:
            steps = 6
        elif mult >= 60:
            steps = 5
        elif mult >= 30:
            steps = 4
        elif mult >= 15:
            steps = 3
        elif mult >= 5:
            steps = 2
        elif mult >= 2:
            steps = 1
        for _ in range(steps):
            if not self._click("cmo_time_comp_up", "CMO Time-Compression +"):
                break
            self._sleep(0.15)

    def run_for(self, seconds, compression=15):
        """Set compression and start the clock. The BRIDGE times the pause
        on the wall clock; this build cannot self-halt because
        VP_RunForTimeAndHalt is Professional Edition only."""
        self.set_compression(compression)
        started = self.play()
        # Scenario-scoped message settings can auto-drop compression to 1x
        # at the first contact after start, and a reloaded save restores
        # those settings. One re-assert after the clock is running pins the
        # requested rate again. The console accepts Lua while running.
        if started:
            self._sleep(1.0)
            self.set_compression(compression)
        return {
            "mode": "keystroke" if SIM_CONTROL_METHOD == "keystroke" else "lua",
            "seconds": seconds,
            "compression": compression,
            "started": bool(started),
        }

    def scenario_start(self):
        """Start the scenario clock from a stopped state."""
        return self.play()

    def scenario_reset(self, rebuild_title=None):
        """Reset. For generated sandboxes, rebuild blank via Lua. For a
        loaded .scen, CommandLua cannot reload from inside the running
        instance, so this uses the calibrated coordinate if present."""
        if rebuild_title and self._lua_call(
                "AGENT_ScenRebuildBlank('{}')".format(rebuild_title.replace("'", " "))):
            self._running = False
            return {"mode": "lua_rebuild", "title": rebuild_title}
        clicked = self._click("cmo_scenario_reset", "CMO Scenario Reset")
        if clicked:
            self._running = False
        return {"mode": "ui_reset", "clicked": clicked}

    def scenario_reload(self):
        """Reload the saved scenario from disk. UI-only."""
        ok = self._click("cmo_scenario_reload", "CMO Scenario Reload")
        if ok:
            self._running = False
        return {"mode": "ui_reload", "clicked": ok}

    def save_scenario(self):
        """Ctrl+S. Useful before a PBEM save exchange or a checkpoint."""
        if FOCUS_BEFORE_KEYS:
            self._focus_cmo()
        ok = self._key(*KEY_SAVE)
        return {"mode": "keystroke_save", "sent": ok}

    def has_started(self):
        """Best-effort query; result is read back from CMO stdout by bridge."""
        self._lua_call("print('SCEN_STARTED: ' .. tostring(AGENT_ScenHasStarted()))")

    def sync_running_state(self, running):
        """Let the bridge correct the tracked toggle state if it drifts."""
        self._running = bool(running)
        self._log("Sim running-state synced to {}.".format(self._running))


# directive parsing: LLM can embed a control line in its output.
# e.g.  BRIDGE_CONTROL: RESET; COMPRESS=15; RUNFOR=300; PAUSE
def parse_control_directives(text):
    """Return an ordered list of (op, arg) from a BRIDGE_CONTROL: line."""
    ops = []
    m = re.search(r"BRIDGE_CONTROL\s*:\s*(.+)", text or "", re.IGNORECASE)
    if not m:
        return ops
    # The contract lists the ops as PLAY|PAUSE|COMPRESS=<n>|..., so models
    # reasonably use "|" as the separator too. Accept ; , and | alike.
    for tok in re.split(r"[;,|]", m.group(1)):
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            k, v = tok.split("=", 1)
            # The line often arrives inside a Lua print, so trailing quotes
            # and parens ride along with the value. Keep only what an op
            # name and an argument can legally contain.
            k = re.sub(r"[^A-Za-z_]", "", k).upper()
            v = re.sub(r"[^0-9A-Za-z._-]", "", v)
            if k:
                ops.append((k, v or None))
        else:
            k = re.sub(r"[^A-Za-z_]", "", tok).upper()
            if k:
                ops.append((k, None))
    return ops
