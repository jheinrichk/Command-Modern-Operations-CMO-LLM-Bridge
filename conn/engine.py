"""
conn.engine  -  the run loop that CONN drives.

Everything that touches the screen goes through Actuator, which is the single
place the dry-run switch is enforced: in dry run no click, key or paste is
ever synthesized and the loop is fed stub responses so the sequence can be
rehearsed safely.

The engine runs on a worker thread and communicates only by pushing events
onto a queue, so a sixty second wait never freezes the UI.
"""

import queue
import re
import sys
import threading
import time
from pathlib import Path

from . import luacheck
from .apiguard import ApiGuard
from .agents import build_commanders
from .clipio import Clipboard
from .config import num
from .ike import IkeFinalizer
from .session import Session
from .cmologs import CmoLogs, parse_attach_directives
from . import popups as _popups
from . import mapshot as _mapshot
from . import winmgr as _winmgr

PKG_ROOT = Path(__file__).resolve().parent.parent
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

try:
    import pyautogui
except Exception:
    pyautogui = None

# pyautogui's fail-safe (pointer slammed into a screen corner) is the
# operator's hardware abort. It must stop the run, not be logged as a
# failed click and ignored.
_FAILSAFE = ((pyautogui.FailSafeException,)
             if pyautogui is not None and hasattr(pyautogui, "FailSafeException") else ())

try:
    from cmo_rag import CmoRag
except Exception:
    CmoRag = None

try:
    from cmo_sim_control import SimController, parse_control_directives
except Exception:
    SimController = None

    def parse_control_directives(text):
        return []


# ----------------------------------------------------------------------
# Prompt contract (kept in step with cmo_lua_llm_bridge_main.py)
# ----------------------------------------------------------------------
BRIDGE_INSTRUCTION = (
    "MODE:CMO_LUA_LLM_BRIDGE\n"
    "ROLE:YOU_ARE_DESIGNER_ANALYST_GATEKEEPER_AND_REVIEWER_FOR_A_CMO_SCENARIO\n"
    "GROUNDING:USE_ONLY_THE_RETRIEVED_CMO_CONTEXT_BELOW;DO_NOT_SEARCH_ONLINE;DO_NOT_INVENT_FUNCTIONS\n"
    "API_FACTS:CMO_API_SYMBOLS_ARE_CALLABLE_USERDATA_NOT_LUA_FUNCTIONS;"
    "NEVER_PROBE_WITH_type()=='function';EVEN_print_IS_USERDATA;"
    "rawget_load_require_io_MAY_BE_NIL\n"
    "API_RULES:USE_ONLY_SYMBOLS_IN_THE_LOCAL_INDEX;"
    "VP_GetSides_RETURNS_SIDE_WRAPPER_OBJECTS_NOT_STRINGS;"
    "ScenEdit_GetSides_AND_ScenEdit_GetUnits_DO_NOT_EXIST;"
    "GUIDs_ARE_NOT_DBIDs;NEVER_GUESS_DBIDs_OR_LOADOUT_IDS\n"
    "CONSOLE:NEVER_CALL_Tool_EmulateNoConsole(true);IT_SILENCES_EVERY_print_UNTIL_SWITCHED_OFF\n"
    "STATE_LINE:PRINT_NEXT_RECOMMENDED_STATE_ONCE_AT_THE_END;NOT_IN_EARLY_EXIT_BRANCHES\n"
    "PERSISTENCE:KEEP_WORKING_UNTIL_THE_REQUEST_IS_FULFILLED;A_FAILED_RUN_IS_A_REPAIR_CYCLE_NOT_AN_ENDING;"
    "USE_THE_ERROR_TEXT_AND_THE_RETRIEVED_CONTEXT_TO_FIX_AND_RETRY\n"
    "FINISH:WHEN_THE_REQUEST_IS_FULLY_ANSWERED_PRINT_'BRIDGE_DONE:<one line summary>'_AND_NEXT_RECOMMENDED_STATE:DONE\n"
    "GIVE_UP:ONLY_WHEN_YOU_TRULY_CANNOT_PROCEED_WITHOUT_THE_USER_PRINT_"
    "'BRIDGE_HALT:<what you need from the user and why>'\n"
    "ERRORS:AFTER_A_FAILED_CALL_PRINT_'CMO_ERROR|FUNCTION=<_errfnc_>|NUMBER=<_errnum_>|MESSAGE=<_errmsg_>'\n"
    "LESSONS:FOR_ANY_DURABLE_FINDING_PRINT_'RAG_NOTE: <one sentence>';THE_BRIDGE_INGESTS_IT_FOR_ALL_FUTURE_CYCLES;RETRACT_WRONG_HYPOTHESES_THE_SAME_WAY\n"
    "ATTACH:TO_SEE_CMO'S_AFTER_ACTION_LOG_PRINT_'BRIDGE_ATTACH: AALOG'_(OPTIONAL_tail=<lines>);"
    "FOR_A_MAP_SCREENSHOT_'BRIDGE_ATTACH: MAPSHOT';FOR_THE_LATEST_CRASH_LOG_'BRIDGE_ATTACH: EXCEPTIONLOG';"
    "FOR_THE_LUA_CONSOLE_HISTORY_'BRIDGE_ATTACH: LUAHISTORY';"
    "FOR_TIME,SCORE,LOSSES,KILLS,ORDER_OF_BATTLE,CONTACTS_AND_MISSIONS_'BRIDGE_ATTACH: STATUS'_(OPTIONAL_side=<name,underscores_for_spaces>);"
    "THEY_ARRIVE_WITH_THE_NEXT_PROMPT\n"
    "POPUPS:A_SCENARIO_MsgBox_STOPS_THE_CLOCK_AND_BLOCKS_THE_CONSOLE;DECLARE_THE_ANSWER_BEFORE_THE_WINDOW_RUNS_WITH_"
    "'-- BRIDGE_ANSWER: YES'_AS_A_COMMENT_LINE_INSIDE_THE_LUA_BLOCK_(OR_NO_/_CANCEL;_A_SEQUENCE_AS_'-- BRIDGE_ANSWER: NO; YES');THE_BRIDGE_ACTIVATES_THE_BOX,_TABS_TO_THE_BUTTON_AND_PRESSES_ENTER;"
    "IF_A_BOX_APPEARS_WITH_NO_ANSWER_DECLARED_THE_WINDOW_ENDS_EARLY_AND_THE_NEXT_PROMPT_CARRIES_'POPUP_PENDING'_WITH_ITS_TEXT_AND_BUTTONS\n"
    "DATABASE:TO_LOOK_UP_A_PLATFORM_IN_DB3000_v515_PRINT_'BRIDGE_LOOKUP: <name>'_(OPTIONAL_type=Aircraft|Ship|Submarine|Facility);"
    "THE_NEXT_PROMPT_LISTS_EVERY_MATCH_WITH_DBID,_OPERATOR_COUNTRY,_SERVICE,_YEAR,_HYPOTHETICAL/DEPRECATED_FLAGS_AND_FOR_AIRCRAFT_THE_VALID_LOADOUT_IDS\n"
    "PINNED:THE_PINNED_RULES_IN_THE_RETRIEVED_CONTEXT_APPLY_EVERY_CYCLE;CHECK_MISSION_DOCTRINE_AND_STATE_FLAGS_BEFORE_ASSERTING_A_CAUSE\n"
    "RETURN:FIRST_EXECUTABLE_LUA_CODE_BLOCK_ONLY\n"
    "SCRIPT:CMO_LUA_COMPATIBLE;USE_LOCAL_VARIABLES;PCALL_FOR_CRITICAL_OPS\n"
    "REQ:PRINT_RESULTS_ERRORS_AND_A_LINE_'NEXT_RECOMMENDED_STATE:<STATE>'\n"
    "STATES:AUDIT|DESIGN|DEPLOY|TEST|EVALUATE|REFINE|RETEST|REPORT|DONE|FIX_ERRORS\n"
    "REQ:COPY_FINAL_OUTPUT_TO_WINDOWS_CLIPBOARD\n"
    "SAFETY:USER_EXPLICITLY_ALLOWED_TO_RUN_LUA_IN_THIS_SCENARIO;"
    "NO_os.execute;NO_FILESYSTEM_DELETION;NO_SHELL\n"
    "OPTIONAL:YOU_MAY_EMIT_ONE_LINE_'BRIDGE_CONTROL:<OPS>'_TO_DRIVE_THE_SIM\n"
    "  OPS_ARE:PLAY_OR_PAUSE_OR_COMPRESS=<n>_OR_RUNFOR=<seconds>_OR_RESET_OR_RELOAD_OR_START;"
    "SEPARATE_MULTIPLE_OPS_WITH_SEMICOLONS_e.g._'BRIDGE_CONTROL: RUNFOR=900';"
    "EMIT_COMPRESS=<n>_ONLY_WHEN_THE_TASK_SAYS_THE_BRIDGE_OWNS_COMPRESSION;"
    "OTHERWISE_THE_OPERATOR_HAS_SET_IT_BY_HAND_AND_RUNFOR_ALONE_IS_CORRECT\n"
    "OUTPUT:CODE_FIRST;NO_PROSE_BEFORE_CODE\n"
    "FORMAT_HARD_REQUIREMENT:START_EXACTLY_WITH_TRIPLE_BACKTICK_LUA_AND_END_EXACTLY_WITH_TRIPLE_BACKTICK"
)

STAGE_TASKS = {
    "FIX_ERRORS": ("STAGE FIX_ERRORS. The previous script failed. The failure detail is "
                   "below. Diagnose it against the retrieved context, then emit a "
                   "corrected script that carries on with the original request. Change "
                   "your approach rather than resubmitting the same call. If a call is "
                   "genuinely unavailable in this build, work around it. Only if you "
                   "cannot proceed at all without the user, print BRIDGE_HALT with what "
                   "you need. Otherwise NEXT_RECOMMENDED_STATE: the stage you were on."),
    "AUDIT": ("STAGE AUDIT. The known-good inspection payload has just run and its "
              "console output follows. Answer the user's review request from that "
              "output. When deeper detail is needed, emit a follow-up read-only "
              "script using only indexed symbols. NEXT_RECOMMENDED_STATE: EVALUATE."),
    "DESIGN": ("STAGE DESIGN. Produce the FIRST build script for this scenario. Build a blank "
               "scenario if none is loaded, add sides with postures, seed the core order of "
               "battle using EXACT platform names from the lookup layer, add reference points "
               "and the primary missions. End with NEXT_RECOMMENDED_STATE: DEPLOY."),
    "DEPLOY": ("STAGE DEPLOY. Review the CMO output below. If the build is clean, emit a short "
               "verification script and NEXT_RECOMMENDED_STATE: TEST. If errors, fix them and "
               "NEXT_RECOMMENDED_STATE: DEPLOY."),
    "TEST": ("STAGE TEST. Emit pre-run instrumentation. You MAY add "
             "'BRIDGE_CONTROL: {control}'. End NEXT_RECOMMENDED_STATE: EVALUATE."),
    "PLAYTEST": ("STAGE PLAYTEST. The scenario is ALREADY BUILT and loaded. Do NOT call "
                 "Tool_BuildBlankScenario, ScenEdit_AddSide or ScenEdit_AddUnit. Play it as "
                 "the side named in the request, evaluate what happens, and fix defects in "
                 "the same cycle where the fix is safe and verified by readback. Lead every "
                 "output with the operator CLICK line. Size any BRIDGE_CONTROL RUNFOR to the "
                 "next decision point minus a margin and show the arithmetic. "
                 "NEXT_RECOMMENDED_STATE: TEST, or EVALUATE if the clock should not move."),
    "EVALUATE": ("STAGE EVALUATE. Judge the post-run output for balance, triggers and losses. "
                 "If acceptable NEXT_RECOMMENDED_STATE: REPORT, else NEXT_RECOMMENDED_STATE: REFINE."),
    "REFINE": ("STAGE REFINE. Emit a targeted patch script addressing the evaluation. "
               "Query before modify, prefer GUIDs. NEXT_RECOMMENDED_STATE: RETEST."),
    "RETEST": ("STAGE RETEST. Re-run the test window ('BRIDGE_CONTROL: {control}') "
               "and print the same metrics as TEST. NEXT_RECOMMENDED_STATE: EVALUATE."),
    "REPORT": ("STAGE REPORT. Print a structured evaluation report and readiness for IKE PBEM "
               "conversion. NEXT_RECOMMENDED_STATE: DONE."),
}

# The cycle in the order the anchors are marked. Every screen action in the
# loop resolves through one of these, so the calibration file is the single
# source of truth for where anything is clicked.
CYCLE_STEPS = [
    (1, "llm_code_copy", "copy the reply"),
    (2, "cmo_lua_input", "paste into the Lua console"),
    (3, "cmo_execute", "run"),
    (4, "cmo_output_area", "read the result pane"),
    (5, "llm_input", "paste the output back"),
    (6, "llm_submit", "submit"),
]
CORE_ANCHORS = [a for _n, a, _d in CYCLE_STEPS]

VALID_STAGES = {"AUDIT", "DESIGN", "DEPLOY", "TEST", "EVALUATE", "REFINE",
                "RETEST", "REPORT", "DONE", "FIX_ERRORS", "PLAYTEST"}
LINEAR = {"AUDIT": "EVALUATE", "DESIGN": "DEPLOY", "DEPLOY": "TEST", "TEST": "EVALUATE",
          "EVALUATE": "REPORT", "REFINE": "RETEST", "RETEST": "EVALUATE",
          "REPORT": "DONE", "PLAYTEST": "PLAYTEST"}


class Aborted(BaseException):
    """Operator abort. A BaseException so that the many broad
    'except Exception' guards cannot swallow it and keep a run going."""
    pass


class Halted(BaseException):
    """The run cannot continue safely without the operator. Carries the
    reason shown in the log and in the stop dialog."""
    pass


# Browser window titles carry the tab title plus browser furniture that
# changes on its own ("and 3 more pages", the profile name). Strip that so
# the tab guard compares only the conversation's own title.
_TAB_MORE_RE = re.compile(r"\s+and \d+ more (?:tabs?|pages?)", re.I)
_TAB_BROWSER_RE = re.compile(
    r"\s+[-\u2014]\s+(?:Microsoft\W*Edge|Google Chrome|Mozilla Firefox|Brave|"
    r"Chromium|Opera)\s*$", re.I)
_TAB_PROFILE_RE = re.compile(
    r"\s+[-\u2014]\s+(?:Personal|Work|Guest|Profile \d+|\[?InPrivate\]?)\s*$", re.I)
GENERIC_TAB_RE = re.compile(
    r"^(?:(?:new chat|new conversation|untitled)(?:\s+[-\u2014|]\s+llm)?|llm|llm\.ai)?$",
    re.I)
REPLY_COMPLETE_RE = re.compile(r"NEXT_RECOMMENDED_STATE|BRIDGE_DONE|BRIDGE_HALT")


def normalize_tab_title(title):
    t = (title or "").replace("\u200b", "").strip()
    t = _TAB_MORE_RE.sub("", t)
    for _ in range(2):
        t = _TAB_BROWSER_RE.sub("", t)
        t = _TAB_PROFILE_RE.sub("", t)
    return t.strip()


# ----------------------------------------------------------------------
# Actuator
# ----------------------------------------------------------------------
class Actuator:
    """Every synthetic input in the whole application passes through here."""

    def __init__(self, cfg, resolver, emit, dry_run=False):
        self.cfg = cfg
        self.resolver = resolver
        self.emit = emit
        self.dry_run = dry_run
        self.clip = Clipboard(cfg, log=lambda m: emit("log", text=m), dry_run=dry_run)
        # set by the Engine: returns True once Abort is pressed during a run.
        # Every synthetic input checks it first, so Ctrl+Alt+X stops the
        # very next click or paste instead of the next loop boundary.
        self.abort_check = None

    def _stop_if_aborted(self):
        chk = self.abort_check
        if chk is not None and chk():
            raise Aborted()

    def set_dry_run(self, on):
        self.dry_run = bool(on)
        self.clip.dry_run = bool(on)

    def _pause(self, s=None):
        time.sleep(s if s is not None else float(
            self.cfg.get("timing.pause_between_actions", 0.25)))

    def point(self, anchor):
        return self.resolver.resolve(anchor)

    def click(self, anchor, label=None):
        self._stop_if_aborted()
        pt = self.point(anchor)
        if not pt:
            self.emit("log", text="anchor unresolved: {}".format(anchor), level="warn")
            return False
        if self.dry_run:
            self.emit("act", text="DRY RUN click {} at {},{}".format(
                label or anchor, pt[0], pt[1]))
            return True
        if not pyautogui:
            return False
        if _winmgr.point_is_own_window(pt[0], pt[1]):
            # CONN is always on top. A click here would press whatever CONN
            # widget sits at that spot (a checkbox, a button) instead of the
            # target. Seen with cmo_popup_ok under the LLM_SCEN_DEV layout.
            self.emit("log", text="skipped click {} at {},{}: that point is under CONN's own "
                                  "window. Move CONN or apply the layout.".format(
                                      label or anchor, pt[0], pt[1]), level="warn")
            return False
        try:
            pyautogui.moveTo(pt[0], pt[1], duration=0.08)
            pyautogui.click(pt[0], pt[1])
            self.emit("act", text="click {} at {},{}".format(label or anchor, pt[0], pt[1]))
            self._pause()
            return True
        except _FAILSAFE:
            self.emit("log", text="pyautogui fail-safe: the pointer is in a screen corner. "
                                  "Treating it as Abort.", level="warn")
            raise Aborted()
        except Exception as ex:
            self.emit("log", text="click failed {}: {}".format(anchor, ex), level="warn")
            return False

    def hotkey(self, *keys):
        self._stop_if_aborted()
        if self.dry_run:
            self.emit("act", text="DRY RUN hotkey {}".format("+".join(keys)))
            return True
        if not pyautogui:
            return False
        try:
            pyautogui.hotkey(*keys)
            self._pause()
            return True
        except _FAILSAFE:
            raise Aborted()
        except Exception:
            return False

    def press(self, key):
        self._stop_if_aborted()
        if self.dry_run:
            self.emit("act", text="DRY RUN press {}".format(key))
            return True
        if not pyautogui:
            return False
        try:
            pyautogui.press(key)
            self._pause()
            return True
        except _FAILSAFE:
            raise Aborted()
        except Exception:
            return False

    def paste_text(self, text, label="text"):
        self._stop_if_aborted()
        try:
            return self._paste_text(text, label)
        except Aborted:
            raise
        except Exception as ex:
            self.emit("log", text="paste {} failed ({}): {}".format(
                label, type(ex).__name__, ex), level="warn")
            return False

    def _paste_text(self, text, label="text"):
        self.clip.save()
        try:
            self.clip.write(text)
            self._pause(0.1)
            self.hotkey(*tuple(self.cfg.get("hotkeys.paste", ["ctrl", "v"])))
            self.emit("act", text="paste {} ({} chars)".format(label, len(text or "")))
        finally:
            # restore after the paste has landed
            self._pause(float(self.cfg.get("timing.pause_after_paste_seconds", 1.0)))
            self.clip.restore()
        return True

    def paste_text_chunks(self, text, label="text", chunk=48000):
        """Sequential pastes into the focused field. Each Ctrl+V appends, so
        the field ends up holding the whole text without one giant paste."""
        text = text or ""
        parts = [text[i:i + chunk] for i in range(0, len(text), chunk)] or [""]
        self.clip.save()
        try:
            for i, part in enumerate(parts, 1):
                self.clip.write(part)
                self._pause(0.1)
                self.hotkey(*tuple(self.cfg.get("hotkeys.paste", ["ctrl", "v"])))
                self.emit("act", text="paste {} chunk {}/{} ({} chars)".format(
                    label, i, len(parts), len(part)))
                self._pause(0.5)
        finally:
            self._pause(float(self.cfg.get("timing.pause_after_paste_seconds", 1.0)))
            self.clip.restore()
        return True

    def attach_file(self, path, input_anchor="llm_input"):
        self._stop_if_aborted()
        try:
            return self._attach_file(path, input_anchor)
        except Aborted:
            raise
        except Exception as ex:
            self.emit("log", text="attach failed ({}): {}, falling back".format(
                type(ex).__name__, ex), level="warn")
            return False

    def _attach_file(self, path, input_anchor="llm_input"):
        """Attach a file to the browser conversation.

        ctrl_u: focus the input, send the browser attach shortcut, then the
        Windows open dialog gets the path pasted into its filename field
        (which holds focus by default) and Enter.

        anchors: the calibrated sequence instead: attach control, menu entry,
        filename field, then the path and Enter (or the Open button when it is
        calibrated). Returns False when the route is unusable so the caller
        can fall back to chunked pasting.
        """
        method = str(self.cfg.get("io.attach_method", "ctrl_u")).lower()
        if method in ("off", "chunks"):
            return False
        if self.dry_run:
            self.emit("act", text="DRY RUN attach ({}) {}".format(method, path))
            return True

        if method == "ctrl_u":
            self.click(input_anchor, "attach: focus input")
            self._pause(0.3)
            self.hotkey(*tuple(self.cfg.get("io.attach_hotkey", ["ctrl", "u"])))
        else:
            if not (self.resolver.has("llm_attach_button")
                    and self.resolver.has("llm_attach_menu")):
                self.emit("log", text="attach anchors not calibrated "
                                      "(llm_attach_button, llm_attach_menu)",
                          level="warn")
                return False
            self.click("llm_attach_button", "attach control")
            self._pause(0.5)
            self.click("llm_attach_menu", "attach menu entry")

        self._pause(num(self.cfg.get("timing.file_dialog_wait_seconds", 1.5), 1.5))
        if _winmgr.IS_WINDOWS and self.cfg.get("io.verify_file_dialog", True):
            # Make sure the Open dialog is really up before pasting a path and
            # pressing Enter. If the shortcut missed, the path went into the
            # chat box and Enter sent it to LLM as a message.
            waited = 0.0
            while _winmgr.foreground_class() != "#32770" and waited < 3.0:
                time.sleep(0.25)
                waited += 0.25
            if _winmgr.foreground_class() != "#32770":
                self.emit("log", text="the file dialog did not open; not attaching {}. If "
                                      "your browser's dialog is never detected, untick 'Check "
                                      "the file dialog opened' in Settings."
                          .format(Path(str(path)).name), level="warn")
                self.press("escape")      # closes a dialog that opens late
                return False
        # calibrated dialog anchors are honored on every route: the filename
        # field normally owns focus, but clicking it first costs nothing and
        # saves the run when the dialog opens unfocused
        if self.resolver.has("file_dialog_filename"):
            self.click("file_dialog_filename", "file dialog filename")
            self._pause(0.2)
        # the filename field owns focus in a fresh dialog; paste the path
        self.clip.save()
        try:
            self.clip.write(str(path))
            self._pause(0.15)
            self.hotkey(*tuple(self.cfg.get("hotkeys.paste", ["ctrl", "v"])))
            self._pause(0.3)
        finally:
            self.clip.restore()
        if self.resolver.has("file_dialog_open"):
            self.click("file_dialog_open", "file dialog Open")
        else:
            self.press("enter")
        try:
            size = Path(str(path)).stat().st_size
        except Exception:
            size = 0
        wait = int(self.cfg.get("timing.upload_wait_base_seconds", 5)) +             (size // 102400) * int(self.cfg.get("timing.upload_wait_per_100kb_seconds", 2))
        self.emit("act", text="attached {} ({} bytes), waiting {}s for the upload"
                  .format(path, size, wait))
        end = time.time() + wait
        while time.time() < end:
            self._stop_if_aborted()
            time.sleep(min(0.25, max(0.0, end - time.time())))
        return True

    def scroll_to_reply(self, anchor, times=None, pause=None, label="reply"):
        """Page Down in the browser before copying.

        The code block's copy control is only rendered once the reply is
        scrolled into view, so the copy has to be preceded by a scroll or it
        lands on an empty or partial selection.
        """
        times = int(self.cfg.get("timing.llm_scroll_page_downs", 2)
                    if times is None else times)
        pause = float(self.cfg.get("timing.llm_scroll_pause_seconds", 0.4)
                      if pause is None else pause)
        if times <= 0:
            return False
        if self.dry_run:
            self.emit("act", text="DRY RUN {} x pagedown over {}".format(times, label))
            return True
        # focus the reply area first, otherwise the key goes to whatever had focus
        self.click(anchor, label)
        self._pause(0.15)
        for _ in range(times):
            self.press("pagedown")
            self._pause(pause)
        self.emit("act", text="{} x pagedown over {}".format(times, label))
        return True

    def copy_region(self, anchor, label="region"):
        """Click into an area, select all, copy, return the text.

        Returns "" when the click could not be made or the copy did not
        change the clipboard. Without that check a failed copy returned
        whatever was already on the clipboard, and that was read as the
        console output."""
        if self.dry_run:
            self.emit("act", text="DRY RUN copy from {}".format(label))
            return "[DRY RUN: no text copied from {}]".format(label)
        if not self.click(anchor, label):
            return ""
        self._pause(0.3)
        self.hotkey(*tuple(self.cfg.get("hotkeys.select_all", ["ctrl", "a"])))
        self._pause(0.2)
        prior = self.clip.read()
        sentinel = "CONN_COPY_SENTINEL_{}".format(int(time.time() * 1000))
        self.clip.write(sentinel)
        try:
            self.hotkey(*tuple(self.cfg.get("hotkeys.copy", ["ctrl", "c"])))
            self._pause(0.5)
            text = self.clip.read()
        finally:
            if prior is not None and self.cfg.get("io.guard_clipboard", True):
                self.clip.write(prior)
        if not text or text == sentinel:
            return ""
        return text

    def copy_button(self, anchor, label="code block"):
        """Click the code block's own Copy control and read what it puts on
        the clipboard.

        This is the correct path in a browser. Ctrl+A there selects the whole
        page, so a select-all copy returns the prompt plus the page furniture
        rather than the reply.
        """
        if self.dry_run:
            self.emit("act", text="DRY RUN copy button on {}".format(label))
            return "[DRY RUN: no text copied from {}]".format(label)
        settle = float(self.cfg.get("bridge.copy_clipboard_settle_seconds", 3.0))
        prior = self.clip.read()
        sentinel = "CONN_COPY_SENTINEL_{}".format(int(time.time() * 1000))
        self.clip.write(sentinel)
        self._pause(0.15)
        self.click(anchor, label)
        deadline = time.time() + settle
        text = ""
        while time.time() < deadline:
            self._stop_if_aborted()
            cur = self.clip.read()
            if cur and cur != sentinel:
                text = cur
                break
            time.sleep(0.15)
        if not text:
            self.emit("log", text="clipboard did not change after the copy click",
                      level="warn")
        if prior is not None and prior != sentinel:
            self.clip.write(prior)
        return text or ""

    def clear_field(self, anchor, label="field"):
        """Focus a field and empty it. Returns False when the field could
        not be clicked, so nothing is typed into whatever has focus."""
        if not self.click(anchor, label):
            return False
        self._pause(0.15)
        self.hotkey(*tuple(self.cfg.get("hotkeys.select_all", ["ctrl", "a"])))
        self.press("delete")
        return True


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------
class Engine:
    def __init__(self, cfg, wm, resolver, bus=None):
        self.cfg = cfg
        self.wm = wm
        self.resolver = resolver
        self.bus = bus or queue.Queue()
        self.dry_run = bool(cfg.get("ui.dry_run_default", True))
        self.act = Actuator(cfg, resolver, self.emit, self.dry_run)
        self.rag = None
        self.guard = ApiGuard(cfg)
        self.sim = None
        self.session = None
        self.logs = None            # CmoLogs, created on first use
        self._pending_attach = []   # (path, caption) to send with the next prompt
        self._pending_by_side = {}  # side -> [(path, caption)] for that commander only
        self._last_reply_raw = ""   # the last reply accepted, to spot a stale copy
        self._popup_seen = None     # hwnd of the box already reported as pending
        self._answers = []          # declared answers for scenario message boxes
        self._popup_hold = False    # a box ended the last window early
        self.thread = None
        self._last_prompt = ""
        self._last_token = ""
        self._abort = threading.Event()
        self._pause = threading.Event()
        self._step = threading.Event()
        self.act.abort_check = lambda: self._abort.is_set() and self.state.get("running")
        self._tab_lock = ""         # conversation title locked after the first good reply
        self._tab_seen = ""         # last title logged
        self.state = {
            "running": False, "mode": "design", "stage": "IDLE", "cycle": 0,
            "phase": "", "phase_started": 0.0, "phase_cap": 0,
            "last_lua": "", "last_output": "", "rag_hits": [],
            "errors": 0, "retries": 0, "turn": 0, "side": "",
            "dry_run": self.dry_run, "notes": "",
        }
        self._init_sim()

    # -- plumbing ---------------------------------------------------
    def emit(self, kind, **fields):
        rec = dict(kind=kind, ts=time.time(), **fields)
        try:
            self.bus.put_nowait(rec)
        except Exception:
            pass
        if self.session and kind in ("stage", "act", "error", "lua", "output",
                                     "turn", "ike", "log"):
            self.session.event(kind, **fields)

    def set_dry_run(self, on):
        self.dry_run = bool(on)
        self.act.set_dry_run(on)
        self.state["dry_run"] = self.dry_run
        self.emit("dry_run", value=self.dry_run)

    def set_clock_state(self, running):
        """Tell the toggle tracker what the clock is doing right now. Use
        after starting or stopping the clock by hand mid-run."""
        if self.sim is not None:
            self.sim.sync_running_state(bool(running))
            self.emit("log", text="clock state set to {} by the operator".format(
                "RUNNING" if running else "paused"))
            return True
        return False

    def _init_sim(self):
        if SimController is None:
            return
        self.sim = SimController(
            primitives={
                "run_lua": self.run_lua_in_cmo,
                "click": lambda name, label=None: self.act.click(name, label),
                "has_coord": lambda name: self.resolver.has(name),
                "log": lambda m: self.emit("log", text=m),
                "sleep": lambda s=0.25: time.sleep(s),
            },
            prefer_lua=bool(self.cfg.get("bridge.prefer_lua_sim_control", True)),
        )

    def _ensure_logs(self):
        if self.logs is None:
            try:
                state_dir = self.cfg.folder("sessions_folder") or Path(".")
                self.logs = CmoLogs(self.cfg, state_dir=state_dir,
                                    log=lambda m: self.emit("log", text=m))
                self.emit("log", text="CMO logs: " + self.logs.describe())
            except Exception as ex:
                self.emit("log", text="CMO logs unavailable: {}".format(ex), level="warn")
        return self.logs

    def _attach_dir(self):
        if self.session and getattr(self.session, "dir", None):
            return Path(self.session.dir) / "attachments"
        return (self.cfg.folder("out_folder") or Path(".")) / "attachments"

    def prepare_attachments(self, requests, turn_marker=None, side=None):
        """Turn BRIDGE_ATTACH requests into files queued for the next prompt.
        requests: list of (kind, opts). Returns the number queued.

        side: queue for that commander's next prompt only. In LLM vs LLM the
        shared queue handed one side's map and log to the other side."""
        made = 0
        for kind, opts in requests or []:
            path, caption = None, ""
            try:
                if kind == "AALOG":
                    logs = self._ensure_logs()
                    if logs and logs.available():
                        lines = int(opts.get("tail", self.cfg.get("cmo.aalog_tail_lines", 400)))
                        mc = int(self.cfg.get("cmo.aalog_max_chars", 24000))
                        if turn_marker:
                            path = logs.write_excerpt(self._attach_dir(), "aalog", mode="delta",
                                                      marker=turn_marker, max_chars=mc,
                                                      for_side=side)
                        else:
                            path = logs.write_excerpt(self._attach_dir(), "aalog", mode="tail",
                                                      lines=lines, max_chars=mc, for_side=side)
                        caption = "CMO after-action log excerpt"
                    else:
                        self.emit("log", text="AALOG requested but not found; set cmo.logs_folder",
                                  level="warn")
                elif kind == "EXCEPTIONLOG":
                    logs = self._ensure_logs()
                    path = logs.copy_latest("ExceptionLog_", self._attach_dir(), "exceptionlog") if logs else None
                    caption = "latest CMO exception log"
                elif kind == "LUAHISTORY":
                    logs = self._ensure_logs()
                    path = logs.copy_latest("LuaHistory_", self._attach_dir(), "luahistory") if logs else None
                    caption = "latest CMO Lua console history"
                elif kind == "SESSIONLOG":
                    logs = self._ensure_logs()
                    path = logs.copy_latest("20", self._attach_dir(), "sessionlog") if logs else None
                    caption = "latest dated CMO session log"
                elif kind == "STATUS":
                    # inject the status report and capture its console output
                    from .status_lua import status_lua
                    side = opts.get("side")
                    if side:
                        side = side.replace("_", " ")
                    code = status_lua(side, max_units=int(self.cfg.get("cmo.status_max_units", 120)),
                                      max_contacts=int(self.cfg.get("cmo.status_max_contacts", 60)))
                    if self.run_lua_in_cmo(code, label="status"):
                        self._wait(int(self.cfg.get("timing.cmo_output_wait_seconds", 5)), "status read")
                        out = self.read_cmo_output() or ""
                        d = self._attach_dir()
                        d.mkdir(parents=True, exist_ok=True)
                        path = d / "status_{}.txt".format(time.strftime("%Y%m%d_%H%M%S"))
                        path.write_text(out, encoding="utf-8")
                        caption = "scenario status report ({})".format(side or "all sides")
                elif kind == "MAPSHOT":
                    if self.dry_run:
                        self.emit("act", text="DRY RUN map capture")
                    else:
                        out = self._attach_dir() / "map_{}.png".format(time.strftime("%Y%m%d_%H%M%S"))
                        path = _mapshot.capture_map(self.wm, self.cfg, out,
                                                    log=lambda m: self.emit("log", text=m))
                        caption = "screenshot of the CMO map"
                else:
                    self.emit("log", text="unknown BRIDGE_ATTACH kind {}".format(kind), level="warn")
            except Exception as ex:
                self.emit("log", text="attachment {} failed: {}".format(kind, ex), level="warn")
            if path:
                if side:
                    self._pending_by_side.setdefault(side, []).append((Path(path), caption))
                else:
                    self._pending_attach.append((Path(path), caption))
                made += 1
                self.emit("log", text="queued attachment: {} ({})".format(Path(path).name, caption))
        return made

    def _ensure_rag(self):
        if self.rag is None and CmoRag is not None:
            try:
                self.rag = CmoRag()
                self.emit("log", text="RAG ready: {} lookup records".format(
                    self.rag.lk["count"] if getattr(self.rag, "lk", None) else 0))
            except Exception as ex:
                self.emit("log", text="RAG unavailable: {}".format(ex), level="warn")
        return self.rag

    # -- control ----------------------------------------------------
    def verify_anchors(self):
        """Every step in the cycle needs its anchor. Returns (ok, missing)."""
        missing = []
        for n, name, desc in CYCLE_STEPS:
            if not self.resolver.has(name):
                missing.append("step {} {} ({}): {}".format(
                    n, name, desc, self.resolver.status(name)))
        return (not missing), missing

    def step_click(self, number):
        """Click the anchor for a numbered cycle step."""
        for n, name, desc in CYCLE_STEPS:
            if n == number:
                self.emit("step", number=n, anchor=name, text=desc)
                return self.act.click(name, "step {} {}".format(n, desc))
        return False

    def start(self, mode, params=None):
        if self.state["running"]:
            return False, "already running"
        ok, missing = self.verify_anchors()
        if not ok and not self.dry_run:
            for m in missing:
                self.emit("error", text="anchor not usable: " + m)
            return False, "calibration incomplete: {} anchor(s)".format(len(missing))
        self._abort.clear()
        self._pause.clear()
        self._step.clear()
        self._tab_lock = ""
        self._tab_seen = ""
        self._pending_attach = []
        self._pending_by_side = {}
        self._answers = []
        self._popup_hold = False
        self._popup_seen = None
        self._last_reply_raw = ""
        self.state["popup_pending"] = None
        self.session = Session(self.cfg, mode=mode, log=lambda m: self.emit("log", text=m))
        self.state.update({"running": True, "mode": mode, "cycle": 0,
                           "errors": 0, "retries": 0, "turn": 0})
        # The play/pause control is one toggle. CONN assumes the clock is
        # PAUSED when a run starts; if you started it by hand, use the
        # clock-state control on the Play tab before pressing Start.
        if self.sim is not None:
            try:
                self.sim.sync_running_state(bool(params.get("clock_running", False)))
                self.emit("log", text="clock state at start: {}".format(
                    "RUNNING (as you set)" if params.get("clock_running") else "paused (assumed)"))
            except Exception:
                pass
        target = {"design": self._run_design}.get(mode, self._run_play)
        self.thread = threading.Thread(target=self._guard, args=(target, params or {}),
                                       name="conn-engine", daemon=True)
        self.thread.start()
        self.emit("started", mode=mode, dry_run=self.dry_run)
        self.emit("log", text="payload route: limit {} chars, method {}, folder {}".format(
            self.cfg.get("io.paste_max_chars", 1500),
            self.cfg.get("io.attach_method", "ctrl_u"),
            self.cfg.get("io.in_folder", "?")))
        migrated = getattr(self.cfg, "migrated", []) or []
        for m in migrated:
            self.emit("log", text="config migrated: " + m)
        return True, "started"

    def _guard(self, target, params):
        try:
            target(params)
        except Aborted:
            self.emit("log", text="Aborted by user.", level="warn")
            self._export_session_quietly()
        except Halted as h:
            self.state["notes"] = str(h)
            self.emit("error", text="RUN HALTED: {}".format(h))
            self.emit("halted", text=str(h))
            if self.session:
                try:
                    self.emit("log", text=self.session.export())
                except Exception:
                    pass
        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            self.emit("error", text="engine error: {}: {}".format(type(ex).__name__, ex))
            self.emit("log", text="traceback:\n" + tb[-3000:])
            self.emit("halted", text="CONN stopped on an internal error: {}: {}. The "
                                     "traceback is in the log and the session folder."
                      .format(type(ex).__name__, ex))
            self._export_session_quietly()
        finally:
            # a leftover abort flag made the next IKE or rebuild step raise
            self._abort.clear()
            self._pause.clear()
            self.state["running"] = False
            self.state["stage"] = "IDLE"
            self.state["phase"] = ""
            if self.session:
                self.emit("log", text="Session folder: {}".format(self.session.dir))
            self.emit("stopped")

    def _export_session_quietly(self):
        if self.session:
            try:
                self.emit("log", text=self.session.export())
            except Exception:
                pass

    def request_pause(self, on=True):
        if on:
            self._pause.set()
        else:
            self._pause.clear()
        self.emit("paused", value=on)

    def request_step(self):
        self._step.set()

    def abort(self):
        self._abort.set()
        self._pause.clear()
        self._step.set()
        self.emit("abort_requested")

    def _checkpoint(self):
        if self._abort.is_set():
            raise Aborted()
        while self._pause.is_set() and not self._abort.is_set():
            if self._step.is_set():
                self._step.clear()
                break
            time.sleep(0.1)
        if self._abort.is_set():
            raise Aborted()

    def await_step(self, label, cap=None):
        """Hold until the user presses Step. Used for the human half of a turn
        and for the moment an incoming PBEM save has to be loaded by hand."""
        self.state["phase"] = label
        self.state["phase_started"] = time.time()
        self._step.clear()
        self.request_pause(True)
        self.emit("phase", label=label, cap=int(cap or 0))
        start = time.time()
        while not self._step.is_set():
            if self._abort.is_set():
                self.request_pause(False)
                raise Aborted()
            if cap:
                self.emit("tick", label=label,
                          remaining=max(0, int(cap - (time.time() - start))),
                          cap=int(cap))
            time.sleep(0.4)
        self._step.clear()
        self.request_pause(False)
        self.state["phase"] = ""
        self.emit("phase", label="", cap=0)

    def _wait(self, seconds, label):
        """Interruptible wait that keeps the phase timer live in the UI."""
        self._checkpoint()
        seconds = int(max(0, seconds))
        self.state["phase"] = label
        self.state["phase_started"] = time.time()
        self.state["phase_cap"] = seconds
        self.emit("phase", label=label, cap=seconds)
        end = time.time() + seconds
        next_poll = 0.0
        poll_every = float(self.cfg.get("popup.poll_seconds", 1.0))
        while time.time() < end:
            self._checkpoint()
            remain = int(end - time.time())
            self.emit("tick", label=label, remaining=remain, cap=seconds)
            if self.cfg.get("popup.auto_answer", True) and time.time() >= next_poll:
                next_poll = time.time() + poll_every
                if self._service_popup():
                    break
            time.sleep(min(1.0, max(0.05, end - time.time())))
        self.state["phase"] = ""
        self.emit("phase", label="", cap=0)

    # -- scenario message boxes --------------------------------------
    def _popup_primitives(self):
        def key(name):
            if self.dry_run:
                self.emit("act", text="DRY RUN key {}".format(name))
                return
            self.act.press(name)

        def click(x, y):
            if self.dry_run:
                self.emit("act", text="DRY RUN click {},{}".format(x, y))
                return
            import pyautogui
            pyautogui.click(x, y)
        return key, click

    def _service_popup(self):
        """Look for an open box. Answer it from the declared queue, or
        record it as pending. Returns True when an unanswered box is open
        (the caller should stop waiting: the box already stops the clock)."""
        try:
            hwnd = _popups.find_popup(self.cfg.get("popup.title_regex", r"^Incoming message$"))
        except Exception:
            return False
        if not hwnd:
            return False
        if hwnd == self._popup_seen and self.state.get("popup_pending") and not self._answers:
            # already reported; ending every wait again would turn the reply
            # wait and each poll into a tight loop while the box stays open
            return False
        info = _popups.read_popup(hwnd) or {}
        if self._answers:
            choice = self._answers.pop(0)
            key, click = self._popup_primitives()
            how = _popups.answer_popup(hwnd, choice, cfg=self.cfg,
                                       log=lambda m: self.emit("log", text=m),
                                       key=key, click=click)
            if how:
                self.state["popup_pending"] = None
                if self.sim is not None and not self._popup_hold:
                    try:
                        self.sim.sync_running_state(True)
                    except Exception:
                        pass
                return False
            self.emit("log", text="could not answer the box; leaving it for the operator",
                      level="warn")
        self.state["popup_pending"] = {"title": info.get("title", ""),
                                       "text": info.get("text", ""),
                                       "buttons": info.get("buttons", [])}
        self._popup_seen = hwnd
        self._popup_hold = True
        self.emit("log", text="POPUP PENDING with no declared answer: {} [{}]".format(
            (info.get("text") or "")[:120], "/".join(info.get("buttons", []))), level="warn")
        return True

    def _answer_pending_popup(self):
        """Before an injection, when a box ended the last window: answer it
        if an answer is declared, then pause the clock the box released."""
        if not self.state.get("popup_pending"):
            return True
        hwnd = _popups.find_popup(self.cfg.get("popup.title_regex", r"^Incoming message$"))
        if not hwnd:
            # answered or closed by hand since it was reported
            self.state["popup_pending"] = None
            self._popup_hold = False
            self._popup_seen = None
            return True
        if not self._answers:
            return False
        key, click = self._popup_primitives()
        how = _popups.answer_popup(hwnd, self._answers.pop(0), cfg=self.cfg,
                                   log=lambda m: self.emit("log", text=m), key=key, click=click)
        if not how:
            return False
        self.state["popup_pending"] = None
        self._popup_hold = False
        self._popup_seen = None
        if self.sim is not None:
            try:
                time.sleep(num(self.cfg.get("popup.settle_seconds", 0.3), 0.3) + 0.5)
                self.sim.sync_running_state(True)
                self.sim.pause()
            except Exception:
                pass
        return True

    # -- CMO / LLM primitives ------------------------------------
    def run_lua_in_cmo(self, code, label="lua"):
        blocked = []
        # the lock is for scripts written by the model during a play run;
        # operator tools (IKE conversion, Rebuild) run outside a run and must
        # not be refused because the header shows a play mode
        if self.cfg.get("safety.editor_lock_in_play_modes", True) and \
                self.state.get("running") and \
                self.state["mode"] in ("normal", "player_vs_llm", "llm_vs_llm", "pbem_h2h"):
            blocked = luacheck.scan_blocklist(code, self.cfg.get("safety.blocked_in_play", []))
        if blocked:
            self.emit("error", text="editor lock blocked: {}".format(", ".join(blocked)))
            return False
        if self.cfg.get("safety.lua_syntax_check", True):
            ok, problems, stats = luacheck.check(code)
            if not ok:
                self.emit("error", text="Lua check failed: {}".format("; ".join(problems)))
                return False
            self.emit("log", text="Lua check ok ({lines} lines, {functions} functions)".format(**stats))
        if self.cfg.get("safety.api_symbol_guard", True):
            ok, why, warns = self.guard.check(code)
            for w in warns:
                self.emit("log", text="API guard: {} is Professional Edition only, "
                                      "expect a guarded fallback".format(w), level="warn")
            if not ok:
                self.emit("error", text="API guard blocked injection: " + why)
                return False
        if self.cfg.get("safety.neutralize_console_suppression", True):
            code, n = neutralize_console_suppression(code)
            if n:
                self.emit("log", text="disabled {} Tool_EmulateNoConsole(true) call(s): "
                                      "they silence the result pane".format(n),
                          level="warn")
        self.state["last_lua"] = code
        self.emit("lua", text=code[:4000], stage=self.state["stage"])
        if self.session:
            # play-mode scripts all ran under stage IDLE; name them by purpose
            tag = self.state.get("stage", "LUA") if label in ("lua", "", None) else label
            self.session.add_script(tag, code)

        # Wrap the payload in markers so the result pane can be read by
        # completion rather than by a fixed timer. With "Echo input script on
        # result text" switched off in the console, these prints are the only
        # reliable boundary between one run and the next.
        token = "{:x}".format(int(time.time() * 1000) & 0xFFFFFFFF)
        self._last_token = token
        if self.cfg.get("bridge.use_run_markers", True):
            payload = ("print('CONN_BEGIN:{t}')\n{c}\nprint('CONN_END:{t}')"
                       .format(t=token, c=code))
        else:
            payload = code

        if self.dry_run:
            self.emit("act", text="DRY RUN: would inject {} chars into the CMO console".format(
                len(payload)))
            return True

        # step 2: paste into the console, step 3: run
        # Every step must land. A console that was closed or minimized used
        # to get the script pasted into whatever had focus, and the copy back
        # then read that text as if CMO had run it.
        self._restore_window("cmo_lua")
        self.emit("step", number=2, anchor="cmo_lua_input", text="paste into the Lua console")
        if not self._must(self.act.clear_field("cmo_lua_input", "step 2 Lua console input"),
                           "The CMO Lua console input (cmo_lua_input) could not be clicked. The "
                          "console is closed, minimized behind something, or not found. Open "
                         "the Lua console, check Calibration, then press Start."):
            return False
        if not self._must(self.act.paste_text(payload, "lua"),
                          "Pasting the script into the CMO Lua console failed. Check the "
                          "clipboard is not locked by another program, then press Start."):
            return False
        self.emit("step", number=3, anchor="cmo_execute", text="run")
        if not self._must(self.act.click("cmo_execute", "step 3 RUN"),
                          "The CMO Lua console Run button (cmo_execute) could not be clicked. "
                          "Check the console is open and not covered, then press Start."):
            return False
        time.sleep(num(self.cfg.get("timing.cmo_popup_wait_seconds", 1.5), 1.5))
        if self.resolver.has("cmo_popup_ok"):
            self.act.click("cmo_popup_ok", "CMO popup OK")
        return True

    def _must(self, ok, message):
        """A step that has to land. Live, a miss stops the run with the
        message. In dry run nothing is clicked anyway, so the miss is only
        reported and the rehearsal goes on."""
        if ok:
            return True
        if self.dry_run:
            self.emit("log", text="DRY RUN: a live run would stop here: " + message,
                      level="warn")
            return True
        raise Halted(message)

    def _restore_window(self, key):
        """A minimized target window does not resolve. Restore it without
        focus so its anchors work again."""
        if self.dry_run:
            return False
        try:
            return bool(self.wm.restore_if_minimized(key))
        except Exception:
            return False

    def read_cmo_output(self, wait_for_marker=True, after_end=False, timeout=None):
        """Step 4: read the result pane.

        When markers are in use the pane is re-read until the END marker for
        the run just injected appears, then only the slice between the two
        markers is returned. That removes the guesswork a fixed wait needs,
        and it works whether or not the console echoes the input script.

        A Lua error stops the script before its END print. When BEGIN is in
        the pane and two reads in a row match without END, the run is over:
        what follows BEGIN is returned (the error text) instead of waiting
        out the timeout and then returning the whole pane, stale lines from
        earlier runs included.

        after_end=True returns only what was printed after the last run's
        END marker: the post-run read after a test window.
        """
        use_markers = bool(self.cfg.get("bridge.use_run_markers", True)) and \
            wait_for_marker and self._last_token and not self.dry_run
        self.emit("step", number=4, anchor="cmo_output_area", text="read the result pane")
        self._restore_window("cmo_lua")

        text = ""
        if use_markers and after_end:
            text = self.act.copy_region("cmo_output_area", "CMO output")
            text = text_after_end_marker(text, self._last_token)
        elif use_markers:
            timeout = int(num(timeout if timeout is not None else
                              self.cfg.get("timing.cmo_output_timeout_seconds", 90), 90))
            poll = num(self.cfg.get("timing.cmo_output_poll_seconds", 2.0), 2.0)
            begin_mark = "CONN_BEGIN:" + self._last_token
            end_mark = "CONN_END:" + self._last_token
            deadline = time.time() + timeout
            self.state["phase"] = "Waiting for the run to finish"
            prev, stalled = None, 0
            while time.time() < deadline:
                self._checkpoint()
                text = self.act.copy_region("cmo_output_area", "CMO output")
                if end_mark in (text or ""):
                    break
                if begin_mark in (text or ""):
                    stalled = stalled + 1 if text == prev else 0
                    if stalled >= 2:
                        self.emit("log", text="run printed BEGIN but never END: the script "
                                              "stopped early, most likely on a Lua error",
                                  level="warn")
                        break
                prev = text
                self.emit("tick", label="Waiting for the run to finish",
                          remaining=int(deadline - time.time()), cap=timeout)
                time.sleep(poll)
            else:
                self.emit("log", text="run marker never appeared, reading the pane as is",
                          level="warn")
            self.state["phase"] = ""
            self.emit("phase", label="", cap=0)
            text = slice_between_markers(text, self._last_token)
            if self.cfg.get("bridge.echo_input_script", False):
                text = drop_echoed_script(text, self.state.get("last_lua", ""))
        else:
            text = self.act.copy_region("cmo_output_area", "CMO output")

        if after_end:
            # nothing new is a normal answer here, not a failure
            return (text or "").strip()
        if not (text or "").strip():
            text = "[no output captured]"
        if self.cfg.get("safety.api_learn_from_dumps", True) and \
                ("--- GLOBALS ---" in text or "GLOBAL_COUNT:" in text):
            # only dump lines; an error line such as "attempt to call a nil
            # value (global 'ScenEdit_GetUnits')" names a symbol that does NOT
            # exist and must never be learned as one that does
            clean = "\n".join(l for l in text.splitlines()
                              if not re.search(r"nil|error|attempt|not found|unknown",
                                               l, re.I))
            new_syms = self.guard.learn_from_text(clean)
            if new_syms:
                self.emit("log", text="API guard learned {} symbols from the "
                                      "environment dump".format(len(new_syms)))
        self.state["last_output"] = text
        self.emit("output", text=text[:6000])
        if self.session:
            self.session.add_transcript("CMO console", text)
        return text

    ATTACH_POINTER = (
        "ATTACHED_PROMPT_HANDOFF\n"
        "The full prompt for this cycle is in the attached file {name}. Read the "
        "attachment as this cycle's prompt and answer under its output contract: "
        "first executable Lua code block only, ending with the state line.")

    def submit_to_llm(self, prompt, wait_label="LLM output", side=None):
        limit = int(self.cfg.get("io.paste_max_chars", 52000))
        self._guard_llm_tab("before pasting the prompt")
        self._restore_window("llm")
        self.emit("step", number=5, anchor="llm_input", text="paste the output back")
        self._must(self.act.clear_field("llm_input", "step 5 LLM input"),
                   "The LLM input box (llm_input) could not be clicked. The browser "
                   "window is closed, minimized or covered. Bring the LLM chat to the "
                   "front, check Calibration, then press Start.")
        # queued attachments (AALog excerpts, map screenshots, crash logs)
        # go up first, each named in the prompt so the model knows what it has
        sent = []
        queued = list(self._pending_attach)
        if side:
            queued += self._pending_by_side.pop(side, [])
        for path, caption in queued:
            try:
                if self.act.attach_file(path, "llm_input"):
                    sent.append("{} = {}".format(path.name, caption))
                else:
                    self.emit("log", text="could not attach {}".format(path.name), level="warn")
            except Exception as ex:
                self.emit("log", text="attach {} failed: {}".format(path.name, ex), level="warn")
        self._pending_attach = []
        if sent:
            prompt = ("ATTACHED_FILES (read them; they are this cycle's evidence):\n- "
                      + "\n- ".join(sent) + "\n\n" + prompt)
        if len(prompt or "") > limit:
            self.emit("log", text="prompt is {} chars, over the {} paste limit"
                      .format(len(prompt), limit))
            ok, path = self._safe("payload file", self.act.clip.write_payload_file,
                                  prompt, "prompt")
            path = path if ok else None
            attached = bool(path) and self.act.attach_file(path, "llm_input")
            if attached:
                pointer = self.ATTACH_POINTER.format(name=Path(str(path)).name)
                self.act.click("llm_input", "step 5 LLM input")
                self.act.paste_text(pointer, "attach pointer")
            else:
                self.emit("log", text="attach unavailable, chunk-pasting the "
                                      "prompt instead", level="warn")
                margin = min(2000, max(1, limit // 4))
                self.act.paste_text_chunks(prompt, "prompt",
                                           chunk=max(1, limit - margin))
        else:
            self.act.paste_text(prompt, "prompt")
        self.emit("step", number=6, anchor="llm_submit", text="submit")
        if self.resolver.has("llm_submit"):
            self.act.click("llm_submit", "step 6 LLM submit")
        else:
            self.act.hotkey(*tuple(self.cfg.get("hotkeys.llm_submit", ["enter"])))
        self._last_prompt = prompt
        if self.session:
            self.session.add_transcript("Prompt to LLM", prompt)
        # A short first wait only. copy_llm_code then polls the reply and
        # moves on as soon as it is complete, up to llm_output_wait_seconds.
        self._wait(self._reply_min_wait(), wait_label)

    # -- reply timing and the LLM tab guard -----------------------
    def _reply_cap(self):
        """Longest wait for one reply. Never shorter than the first wait."""
        try:
            return max(0, int(float(self.cfg.get("timing.llm_output_wait_seconds", 300))))
        except (TypeError, ValueError):
            return 300

    def _reply_min_wait(self):
        try:
            m = int(float(self.cfg.get("timing.llm_min_wait_seconds", 15)))
        except (TypeError, ValueError):
            m = 15
        return max(0, min(m, self._reply_cap()))

    def _reply_poll(self):
        try:
            return max(0, int(float(self.cfg.get("timing.llm_reply_poll_seconds", 8))))
        except (TypeError, ValueError):
            return 8

    def _llm_tab_title(self):
        """Title of the window under the LLM input anchor: the window a
        paste would actually land in."""
        try:
            pt = self.resolver.resolve("llm_input")
        except Exception:
            pt = None
        if not pt:
            return ""
        try:
            return _winmgr.window_title_at(pt[0], pt[1]) or ""
        except Exception:
            return ""

    def _guard_llm_tab(self, when):
        """Refuse to paste into the wrong conversation.

        bridge.llm_title_must_contain: when set, the tab under the input
        anchor must contain it. bridge.lock_llm_tab: after the first good
        reply the conversation title is remembered, and a different title
        later stops the run.
        """
        if self.dry_run:
            return True
        title = normalize_tab_title(self._llm_tab_title())
        if not title:
            return True            # cannot read it on this platform; do not block
        if title != self._tab_seen:
            self.emit("log", text="LLM tab under the input: '{}'".format(title))
            self._tab_seen = title
        must = str(self.cfg.get("bridge.llm_title_must_contain", "") or "").strip()
        if must and must.lower() not in title.lower():
            raise Halted(
                "Stopped {}: the LLM tab in front is '{}', which does not contain "
                "'{}'. Bring the right chat to the front (or change 'LLM tab must "
                "contain' in Settings) and press Start again.".format(when, title, must))
        lock = self._tab_lock
        if (lock and self.cfg.get("bridge.lock_llm_tab", True)
                and title != lock and not GENERIC_TAB_RE.match(title)):
            raise Halted(
                "Stopped {}: the LLM tab changed from '{}' to '{}'. Nothing was "
                "pasted, so no prompt went into the wrong chat. Bring '{}' back to the "
                "front and press Start, or untick 'Stop if the LLM tab changes' in "
                "Settings.".format(when, lock, title, lock))
        return True

    def _lock_llm_tab(self):
        if self.dry_run or self._tab_lock or not self.cfg.get("bridge.lock_llm_tab", True):
            return
        title = normalize_tab_title(self._llm_tab_title())
        if title and not GENERIC_TAB_RE.match(title):
            self._tab_lock = title
            self.emit("log", text="LLM tab locked to '{}' for this run".format(title))

    def copy_llm_code(self):
        """Wait for the reply to finish, then get its Lua back.

        The reply is polled: copy, check, wait, copy again. A copy counts as
        finished when it is valid Lua and either carries the state line
        (NEXT_RECOMMENDED_STATE, BRIDGE_DONE or BRIDGE_HALT) or matches the
        previous copy exactly. An empty clipboard while polling only means
        the reply is not there yet; it never triggers a reprint.

        When the wait runs out:
          - nothing was ever copied: the run HALTS. A reprint cannot fix a
            copy anchor that lands on nothing, or a chat that never answered.
          - the copy is the prompt, not the reply: the run HALTS for the
            same reason.
          - the copy is there but broken (syntax, no Lua, unknown symbol):
            a reprint is requested, at most timing.llm_max_reprints times
            (default 2). After that the run HALTS with the last reason.
        """
        if self.dry_run:
            self._checkpoint()
            stub = ("-- DRY RUN stub reply\nprint('CONN dry run')\n"
                    "print('NEXT_RECOMMENDED_STATE: {}')\n".format(
                        LINEAR.get(self.state["stage"], "EVALUATE")))
            self.emit("log", text="DRY RUN: substituting a stub LLM reply")
            return stub, stub

        method = str(self.cfg.get("bridge.copy_method", "button")).lower()
        max_reprints = max(0, int(self.cfg.get("timing.llm_max_reprints", 2)))
        reprints = 0

        def one_copy():
            self.emit("step", number=1, anchor="llm_code_copy", text="copy the reply")
            self.act.scroll_to_reply("llm_code_copy", label="LLM reply")
            if method == "button":
                return self.act.copy_button("llm_code_copy", "LLM reply")
            return self.act.copy_region("llm_code_copy", "LLM reply")

        while True:
            cap = self._reply_cap()
            poll = self._reply_poll()
            deadline = time.time() + cap
            prev_raw, last_raw, last_why, last_code = None, "", "empty clipboard", ""
            polls, last_note = 0, ""
            while True:
                self._checkpoint()
                raw = one_copy() or ""
                polls += 1
                code, why = self._validate_copy(raw)
                if code and self._last_reply_raw and raw == self._last_reply_raw:
                    # the anchor is still on the previous reply's code block:
                    # the new one has not rendered yet (or the prompt never
                    # went). Injecting it would rerun the last script.
                    code, why = "", "same as the previous reply (the new one is not there yet)"
                # the state line is printed once at the END, so it only counts
                # as "finished" when it sits in the tail of the code
                if code and (REPLY_COMPLETE_RE.search(code[-800:]) or raw == prev_raw):
                    self.emit("log", text="copied {} chars from LLM ({} chars of Lua)"
                              .format(len(raw), len(code)))
                    if self.session:
                        self.session.add_transcript("LLM reply", raw[:8000])
                    self._lock_llm_tab()
                    self._last_reply_raw = raw
                    return code, raw
                if raw.strip():
                    last_raw, last_why = raw, why
                    if code:
                        last_code = code
                prev_raw = raw if raw.strip() else prev_raw
                if time.time() >= deadline:
                    break
                remain = int(max(0, deadline - time.time()))
                self.state["phase"] = "Waiting for LLM's reply"
                note = why if raw.strip() else "nothing to copy yet"
                if polls == 1 or polls % 4 == 0 or note != last_note:
                    self.emit("log", text="reply not complete yet ({}); checking every {}s, "
                              "{}s left".format(note, poll, remain))
                last_note = note
                self._wait(min(poll, remain), "Waiting for LLM's reply")

            # the wait ran out
            if last_code:
                # valid Lua that never showed the state line or settled:
                # take it rather than burn a reprint on a working script
                self.emit("log", text="reply never showed the state line; using the "
                                      "last valid copy ({} chars of Lua)".format(len(last_code)),
                          level="warn")
                if self.session:
                    self.session.add_transcript("LLM reply", last_raw[:8000])
                self._lock_llm_tab()
                self._last_reply_raw = last_raw
                return last_code, last_raw
            self.state["retries"] += 1
            if not last_raw.strip():
                self.state["notes"] = "no reply could be copied"
                raise Halted(
                    "Nothing could be copied from LLM's reply after {}s ({} tries). "
                    "Either the reply never arrived or the copy anchor "
                    "(llm_code_copy) is not on the code block's Copy button. Check "
                    "that the right LLM chat is in front and answered, re-mark the "
                    "anchor if needed, then press Start.".format(cap, polls))
            if "previous reply" in last_why:
                self.state["notes"] = "last copy rejected: " + last_why
                raise Halted(
                    "After {}s the copy still returns LLM's previous reply. Either LLM "
                    "did not answer the last prompt or the reply has no code block at the "
                    "copy anchor. Check the LLM chat, then press Start.".format(cap))
            if "prompt" in last_why:
                self.state["notes"] = "last copy rejected: " + last_why
                raise Halted(
                    "The copy picked up the prompt instead of LLM's reply ({}). The "
                    "reply has no code block where the copy anchor points, or LLM did "
                    "not answer. Check the LLM chat, then press Start.".format(last_why))
            self.state["notes"] = "last copy rejected: " + last_why
            if reprints >= max_reprints:
                raise Halted(
                    "LLM's reply was rejected {} time(s) in a row: {}. Stopped instead "
                    "of asking for more reprints. Check the LLM chat, then press "
                    "Start.".format(reprints + 1, last_why))
            reprints += 1
            self.emit("log", text="copy rejected ({}), reprint {} of {}".format(
                last_why, reprints, max_reprints), level="warn")
            self._request_reprint(last_why)

    def _validate_copy(self, raw):
        """Return (code, reason). code is empty when the copy is unusable."""
        if not raw or not raw.strip():
            return "", "empty clipboard"
        head = raw[:4000].upper()
        if "MODE:CMO_LUA_LLM_BRIDGE" in head or "CURRENT_CYCLE_AND_TASK" in head:
            return "", "copied the prompt, not the reply"
        if self._last_prompt:
            a = "".join(raw.split())[:400]
            b = "".join(self._last_prompt.split())[:400]
            if a and a == b:
                return "", "copy matches the prompt just sent"
        code = extract_lua_block(raw)
        if not code.strip():
            return "", "no Lua found in the copy"
        # prose passes a bracket-balance check trivially, so require it to
        # actually look like Lua before anything is injected
        if "(" not in code or not re.search(
                r"\b(local|function|print|pcall|return|for|while|if|"
                r"ScenEdit_\w+|VP_\w+|Tool_\w+|AGENT_\w+)\b", code):
            return "", "copy does not look like Lua"
        ok, problems, _stats = luacheck.check(code)
        if not ok:
            return "", "syntax: " + "; ".join(problems[:2])
        if self.cfg.get("safety.api_symbol_guard", True):
            gok, why, _warns = self.guard.check(code)
            if not gok:
                return "", why
        return code, ""

    def _request_reprint(self, why=""):
        detail = ""
        if why and "unknown CMO symbols" in why:
            detail = (" It was rejected locally: {}. Correct those calls using only "
                      "symbols from the retrieved context.".format(why))
        self._guard_llm_tab("before pasting a reprint request")
        self._must(self.act.clear_field("llm_input", "LLM input"),
                   "The LLM input box (llm_input) could not be clicked for a reprint "
                   "request. Bring the LLM chat to the front, then press Start.")
        # Kept short on purpose. The full instruction block made this 3,700
        # characters, over the paste limit, and the browser turned it into an
        # attachment chip that arrived empty. The contract is already in the
        # chat; CURRENT_CYCLE_AND_TASK stays so an echo is still recognised.
        why_short = (why or "")[:300]
        text = ("CURRENT_CYCLE_AND_TASK:\nThe previous code block did not transfer cleanly"
                "{}.{} Reprint the corrected Lua code block, complete and unabridged, as one "
                "fenced lua block and nothing else. Keep the print of "
                "NEXT_RECOMMENDED_STATE as its last line.".format(
                    " ({})".format(why_short) if why_short else "", detail[:600]))
        limit = int(num(self.cfg.get("io.paste_max_chars", 1500), 1500))
        self.act.paste_text(text[:max(200, limit - 20)], "reprint")
        if self.resolver.has("llm_submit"):
            self.act.click("llm_submit", "LLM submit")
        else:
            self.act.hotkey(*tuple(self.cfg.get("hotkeys.llm_submit", ["enter"])))
        self._wait(self._reply_min_wait(), "LLM reprint")

    def build_prompt(self, task, retrieve_for=None):
        ok, rag = self._safe("RAG init", self._ensure_rag)
        rag = rag if ok else None
        context = ""
        if rag:
            try:
                # Retrieve on the task AND on what just happened. A lesson
                # about "the swarm did not attack" only surfaces if the
                # query mentions the symptom, and the symptom lives in the
                # last output, not in the task text.
                q = retrieve_for or task
                tail = (self.state.get("last_output") or "")[-1500:]
                notes = self.state.get("notes") or ""
                if tail or notes:
                    q = q + "\n" + notes + "\n" + tail
                context = rag.retrieve_context(
                    q,
                    k_recipes=int(num(self.cfg.get("bridge.rag_recipes", 5), 5)),
                    k_docs=int(num(self.cfg.get("bridge.rag_docs", 3), 3)),
                    k_lessons=int(num(self.cfg.get("bridge.rag_lessons", 4), 4)),
                    max_chars=int(num(self.cfg.get("bridge.rag_max_chars", 7000), 7000)))
                hits = re.findall(r"^#+\s*(.+)$", context or "", re.MULTILINE)[:8]
                self.state["rag_hits"] = hits
                self.emit("rag", hits=hits)
            except Exception as ex:
                self.emit("log", text="RAG retrieve failed: {}".format(ex), level="warn")
        # These ride along whether or not the RAG is available. They used to
        # sit inside the RAG block, so a missing index also dropped the
        # popup notice and the lookup answers the model had asked for.
        warns = self.state.get("dbid_warnings") or []
        if warns:
            context += ("\n\n### DBID VALIDATION (v515 catalog, non-blocking)\n"
                        + "\n".join("- " + w for w in warns[:12]))
        rows = self.state.pop("lookup_results", None)
        if rows:
            context += ("\n\n### DB LOOKUP RESULTS (DB3000 v515)\n"
                        + "\n".join("- " + r for r in rows[:40]))
        pp = self.state.get("popup_pending")
        if pp:
            context += ("\n\n### POPUP PENDING (the clock is stopped and the console is blocked)\n"
                        "TITLE: {}\nTEXT: {}\nBUTTONS: {}\n"
                        "Put the line -- BRIDGE_ANSWER: <button> at the top INSIDE your Lua "
                        "code block. Only the code block is copied back, so an answer "
                        "written outside it is never seen.".format(
                            pp.get("title", ""), pp.get("text", ""),
                            " / ".join(pp.get("buttons", []))))
        return BRIDGE_INSTRUCTION + "\n\n" + context + "\n\nCURRENT_CYCLE_AND_TASK:\n" + task

    # -- sim control ------------------------------------------------
    def _safe(self, label, fn, *args, **kw):
        """Run something that touches the screen, the model or the disk.

        Returns (ok, value). Aborts still propagate; everything else becomes
        a logged failure so one bad step cannot end a run.
        """
        try:
            return True, fn(*args, **kw)
        except (Aborted, Halted):
            raise
        except Exception as ex:
            self.emit("log", text="{} failed ({}): {}".format(
                label, type(ex).__name__, ex), level="warn")
            return False, None

    @staticmethod
    def _safe_format(text, **kw):
        """STAGE_TASKS carry braces only for the test-window numbers. Any
        other brace in the text must not raise."""
        try:
            return text.format(**kw)
        except Exception:
            return text

    @staticmethod
    def _as_int(arg, default):
        """Directives arrive as free text. A malformed number is a warning,
        not a reason to end the run."""
        try:
            return int(str(arg).strip())
        except (TypeError, ValueError):
            return None if default is None else int(default)

    def apply_directives(self, raw):
        try:
            return self._apply_directives(raw)
        except Aborted:
            raise
        except Exception as ex:
            self.emit("log", text="BRIDGE_CONTROL ignored ({}): {}".format(
                type(ex).__name__, ex), level="warn")
            return {"window": False}

    def _apply_directives(self, raw):
        result = {"window": False}
        ops = parse_control_directives(raw)
        if not ops or not self.sim:
            return result
        pending_comp = None
        self.emit("log", text="BRIDGE_CONTROL: {}".format(
            "; ".join("{}{}".format(o, "=" + str(a) if a else "") for o, a in ops)))
        for op, arg in ops:
            self._checkpoint()
            if self.dry_run:
                self.emit("act", text="DRY RUN sim op {} {}".format(op, arg or ""))
                continue
            if op in ("PLAY", "START"):
                self.sim.scenario_start() if op == "START" else self.sim.play()
                result["window"] = True
            elif op == "PAUSE":
                self.sim.pause()
            elif op == "COMPRESS" and arg:
                n = self._as_int(arg, None)
                if n is None:
                    self.emit("log", text="COMPRESS={} is not a number, ignored".format(arg),
                              level="warn")
                else:
                    self.sim.set_compression(n)
                    pending_comp = n
            elif op == "RUNFOR" and arg:
                n = self._as_int(arg, None)
                if n is None:
                    self.emit("log", text="RUNFOR={} is not a number, ignored".format(arg),
                              level="warn")
                else:
                    # A RUNFOR with no COMPRESS in the same directive line
                    # means the operator owns the compression. Do NOT force
                    # the default: that is what kept snapping a manual x5
                    # back to x15. Use the assumed rate only to size the
                    # wall-clock wait.
                    if pending_comp is not None:
                        # the original two-argument contract, unchanged
                        self.test_window(n, pending_comp)
                    else:
                        assumed = int(self.cfg.get("bridge.manual_compression", 5))
                        self.emit("log", text="RUNFOR={} with no COMPRESS: leaving "
                                              "compression as set by the operator "
                                              "(assuming x{} for the wait)".format(n, assumed))
                        self._window_without_compression(n, assumed)
                    result["window"] = True
            elif op == "RESET":
                self.sim.scenario_reset()
            elif op == "RELOAD":
                self.sim.scenario_reload()
            time.sleep(float(self.cfg.get("timing.sim_settle_seconds", 1.0)))
        return result

    def _window_without_compression(self, sim_seconds, assumed):
        """A test window that leaves compression alone. Falls back to the
        two-argument test_window if this instance has been given one."""
        try:
            return self.test_window(sim_seconds, assumed, send_compression=False)
        except TypeError:
            return self.test_window(sim_seconds, assumed)

    def test_window(self, sim_seconds, compression, send_compression=True):
        if self.dry_run:
            self.emit("act", text="DRY RUN test window {}s at x{}".format(sim_seconds, compression))
            return
        if self.sim:
            if send_compression:
                self.sim.run_for(sim_seconds, compression=compression)
            else:
                # operator-owned compression: just start the clock
                self.sim.play()
        wall = max(3, int(sim_seconds / max(1, compression)) + 2)
        cap = int(self.cfg.get("timing.test_window_wall_cap_seconds", 3600))
        if not self.cfg.get("timing.honor_long_windows", True):
            wall = min(cap, wall)
        elif wall > cap:
            # a window longer than the cap is allowed but announced, so a
            # 27-minute wait is never a surprise. The wait is abortable.
            self.emit("log", text="long window: {}s of sim at x{} is {}s of wall time"
                      .format(sim_seconds, compression, wall), level="warn")
        self._wait(wall, "Test window sim {}s at x{}".format(sim_seconds, compression))
        if self.sim:
            self.sim.pause()

    # -- design loop ------------------------------------------------
    def inspect_payload(self):
        """The knowledge pack's known-good read-only inspection script."""
        path = PKG_ROOT / "knowledge_pack" / "CMO_BRIDGE_INSPECT.lua"
        if path.exists():
            code, _n = neutralize_console_suppression(
                path.read_text(encoding="utf-8", errors="replace"))
            return code
        return "print('CMO_DUMP_BEGIN|SIDES=0')\nprint('CMO_DUMP_END|UNITS=0|MISSIONS=0')"

    def _run_design(self, params):
        prompt = params.get("scenario_prompt", "").strip()
        if not prompt:
            prompt = ("Design a balanced Strait of Hormuz surface action scenario: "
                      "Blue escort group against Red missile boat swarm, one decisive "
                      "engagement, two hour window.")
        start = params.get("start_stage", "DESIGN")
        stage = "AUDIT" if start == "AUDIT" else ("PLAYTEST" if start == "PLAYTEST" else "DESIGN")

        self.state["playtest"] = (stage == "PLAYTEST")
        if stage == "PLAYTEST":
            # the scenario exists; open with the playtest framing and let the
            # model's own state line drive from there. No inspect, no build.
            self.state["stage"] = "PLAYTEST"
            self.emit("stage", stage="PLAYTEST", cycle=0)
            task = STAGE_TASKS["PLAYTEST"] + "\n\nUSER_SCENARIO_REQUEST:\n" + prompt
            self._safe("submit", self.submit_to_llm, self.build_prompt(task, prompt))

        if stage == "AUDIT":
            # inspect first with the pack's payload, no generation involved,
            # then hand the output to the EVALUATE stage with the request
            self.state["stage"] = "AUDIT"
            self.emit("stage", stage="AUDIT", cycle=0)
            ok, injected = self._safe("inspect injection", self.run_lua_in_cmo,
                                      self.inspect_payload(), label="inspect")
            if ok and injected:
                self._wait(int(self.cfg.get("timing.cmo_output_wait_seconds", 5)),
                           "inspect execution")
                ok2, out = self._safe("inspect read", self.read_cmo_output)
                out = out if ok2 and out else "[inspection produced no output]"
            else:
                out = "[inspection payload was blocked or failed]"
            task = (STAGE_TASKS["AUDIT"] +
                    "\n\nUSER_REVIEW_REQUEST:\n" + prompt +
                    "\n\nINSPECTION_OUTPUT (CMO console):\n" + out)
            self._safe("opening submit", self.submit_to_llm,
                       self.build_prompt(task, prompt))
            stage = "EVALUATE"
        invalid = 0
        max_cycles = int(self.cfg.get("bridge.max_cycles", 500))
        comp = int(self.cfg.get("bridge.default_test_compression", 15))
        secs = int(self.cfg.get("bridge.default_test_seconds", 300))

        if stage == "DESIGN":
            self.state["stage"] = stage
            self.emit("stage", stage=stage, cycle=0)
            first = STAGE_TASKS["DESIGN"] + "\n\nUSER_SCENARIO_REQUEST:\n" + prompt
            self._safe("opening submit", self.submit_to_llm,
                       self.build_prompt(first, prompt))

        # Stop policy: the run ends when the request is fulfilled, when the
        # model declares it cannot proceed without the user, or when it is
        # demonstrably making no progress. A failed script is a repair cycle.
        max_fail = int(self.cfg.get("bridge.max_consecutive_failures", 8))
        max_repeat = int(self.cfg.get("bridge.max_repeat_signature", 3))
        consecutive, last_sig, repeats = 0, "", 0
        stop_reason = "cycle budget reached ({})".format(max_cycles)
        pending_fault = ""

        for cycle in range(1, max_cycles + 1):
            self._checkpoint()
            self.state["cycle"] = cycle
            self.state["stage"] = stage
            self.emit("stage", stage=stage, cycle=cycle)

            try:
                cont, stop_reason, stage, consecutive, last_sig, repeats, invalid = \
                    self._design_cycle(cycle, stage, secs, comp, max_fail, max_repeat,
                                       consecutive, last_sig, repeats, invalid,
                                       stop_reason)
                if not cont:
                    break
                continue
            except (Aborted, Halted):
                raise
            except Exception as ex:
                # An unexpected fault inside a cycle is a repair cycle, not an
                # ending. The run only stops on the counters below.
                self.state["errors"] += 1
                consecutive += 1
                sig = "ENGINE {}: {}".format(type(ex).__name__, ex)
                repeats = repeats + 1 if sig == last_sig else 0
                last_sig = sig
                self.emit("log", text="cycle {} raised, continuing ({}): {}".format(
                    cycle, type(ex).__name__, ex), level="warn")
                if consecutive >= max_fail:
                    stop_reason = "{} consecutive failing cycles without progress".format(
                        consecutive)
                    break
                if repeats >= max_repeat:
                    stop_reason = "the same engine fault {} cycles running: {}".format(
                        repeats + 1, sig[:160])
                    break
                stage = "FIX_ERRORS"
                task = (STAGE_TASKS["FIX_ERRORS"] +
                        "\n\nCYCLE: {}\nBRIDGE_FAULT (the bridge itself errored while "
                        "handling your last reply):\n{}\nEmit a simpler, self-contained "
                        "script that avoids whatever triggered this."
                        .format(cycle, sig[:400]))
                self._safe("recovery submit", self.submit_to_llm,
                           self.build_prompt(task, task))
                continue

        self.state["notes"] = stop_reason
        self.emit("log", text="run ended: " + stop_reason)
        if not stop_reason.startswith("request fulfilled"):
            # the operator is often away; a stop for any other reason must be
            # visible when they come back, not only as a log line
            self.emit("halted", text="The run ended: " + stop_reason)
        if self.session:
            self._safe("session export", lambda: self.emit(
                "log", text=self.session.export()))
        return

    def _design_cycle(self, cycle, stage, secs, comp, max_fail, max_repeat,
                      consecutive, last_sig, repeats, invalid, stop_reason):
        """One pass of the loop.

        Returns (continue?, stop_reason, stage, consecutive, last_sig,
        repeats, invalid). Every external step goes through _safe.
        """
        def state(cont, reason=None):
            return (cont, reason if reason is not None else stop_reason, stage,
                    consecutive, last_sig, repeats, invalid)

        ok, res = self._safe("copy", self.copy_llm_code)
        code, raw = res if ok and res else ("", "")
        if not (code or "").strip():
            invalid += 1
            self.state["errors"] += 1
            consecutive += 1
            if invalid >= int(self.cfg.get("bridge.max_invalid_code_attempts", 3)):
                return state(False, "no usable reply after {} attempts: {}".format(
                    invalid, self.state.get("notes", "")))
            return state(True)
        invalid = 0

        # Directives are applied after the script has run and its output has
        # been read, so a BRIDGE_CONTROL line in the script cannot advance
        # the sim before the baseline it belongs to is even injected.
        # answers the model declared for scenario message boxes
        # answers declared by this reply apply to the window that follows it;
        # a leftover YES from an earlier cycle must not answer a later box
        self._answers = list(_popups.parse_answer_directives(raw))
        if self.state.get("popup_pending"):
            if not self._answer_pending_popup():
                consecutive += 1
                self.state["notes"] = ("A scenario message box is OPEN and blocks the console. "
                                       "Answer it with -- BRIDGE_ANSWER: YES / NO / CANCEL "
                                       "inside the Lua block.")
                if consecutive >= max_fail:
                    return state(False, "a scenario message box stayed open for {} cycles "
                                        "with no answer".format(consecutive))
                self.emit("log", text="box still pending; asking the model for an answer",
                          level="warn")
                task = ("A scenario message box is OPEN. It stops the clock and blocks the Lua "
                        "console, so no script can run until it is answered. Its title, text "
                        "and buttons are under POPUP PENDING. Reply with one Lua code block "
                        "whose first line is -- BRIDGE_ANSWER: <button>, followed by the script "
                        "to run once the box is closed, ending with the "
                        "NEXT_RECOMMENDED_STATE print.")
                self._safe("submit", self.submit_to_llm, self.build_prompt(task, task))
                return state(True, "waiting for a popup answer")

        # DBID validation against the v515 catalog. Non-blocking: the author
        # decides, but the warnings ride along in the next prompt. This is
        # the check that would have caught nine wrong-nation aircraft.
        self.state["dbid_warnings"] = []
        if self.rag and hasattr(self.rag, "validate_lua_units"):
            ok_v, warns = self._safe("DBID validation", self.rag.validate_lua_units, code)
            if ok_v and warns:
                self.state["dbid_warnings"] = list(warns)
                self.emit("log", text="DBID validation: {} warning(s); first: {}".format(
                    len(warns), warns[0][:160]), level="warn")

        ok, injected = self._safe("injection", self.run_lua_in_cmo, code)
        if not (ok and injected):
            # rejected locally (syntax, API guard, editor lock) or the
            # injection itself faulted. Feed the reason back and repair.
            self.state["errors"] += 1
            consecutive += 1
            fault = self.state.get("notes", "") or "the script was rejected before injection"
            sig = "LOCAL_REJECT " + fault
            repeats = repeats + 1 if sig == last_sig else 0
            last_sig = sig
            if consecutive >= max_fail:
                return state(False, "{} consecutive failures without progress".format(
                    consecutive))
            if repeats >= max_repeat:
                return state(False, "the same rejection {} times running: {}".format(
                    repeats + 1, fault))
            stage = "FIX_ERRORS"
            task = (STAGE_TASKS["FIX_ERRORS"] +
                    "\n\nCYCLE: {}\nREJECTION (the script never reached CMO):\n{}"
                    .format(cycle, fault))
            self._safe("submit", self.submit_to_llm, self.build_prompt(task, task))
            return state(True)

        self._wait(int(self.cfg.get("timing.cmo_output_wait_seconds", 5)), "CMO execution")
        ok, output = self._safe("output read", self.read_cmo_output)
        output = output if ok and output else "[no output captured]"
        body = [l for l in (output or "").splitlines()
                if l.strip() and not l.startswith("NEXT_RECOMMENDED_STATE")
                and "AUDIT_COMPLETE" not in l]
        pending_fault = ""
        if len(body) <= 1:
            pending_fault = ("the result pane came back almost empty ({} line(s)). "
                             "The script may have exited early or printed nothing."
                             .format(len(body)))
            self.emit("log", text=pending_fault, level="warn")

        ran = self.apply_directives(raw)
        window_done = bool(ran and ran.get("window"))
        ending = extract_next_state(output) in ("DONE", "REPORT")
        if stage in ("TEST", "RETEST") and not window_done and not ending:
            if self.cfg.get("bridge.operator_owns_compression", True):
                # the operator set compression by hand; never override it
                self._safe("test window", self._window_without_compression, secs,
                           int(self.cfg.get("bridge.manual_compression", 5)))
            else:
                self._safe("test window", self.test_window, secs, comp)
            window_done = True
        if window_done:
            ok, post = self._safe("post-run read", self.read_cmo_output, after_end=True)
            if ok and post and post.strip():
                output += "\n\n[POST-RUN OUTPUT]\n" + post
        # the next cycle's retrieval should see the whole picture, not only
        # whichever read happened last
        self.state["last_output"] = output

        # The bridge learns from its own runs. Any RAG_NOTE / LESSON line and
        # any rag_* keystore write in the script or its output becomes a
        # retrievable lesson for every later cycle and every later session.
        if self.rag and hasattr(self.rag, "harvest_lessons") and \
                self.cfg.get("bridge.rag_autolearn", True):
            ok_h, pairs = self._safe("lesson harvest", self.rag.harvest_lessons, code, output)
            if ok_h and pairs:
                ok_i, new = self._safe("lesson ingest", self.rag.ingest_many, pairs)
                if ok_i and new:
                    self.emit("log", text="RAG learned {} new lesson(s) this cycle".format(new))
                    self.emit("rag_learn", count=new,
                              samples=[t[:120] for _, t in pairs[:3]])

        # database lookups the model asked for
        lk = re.findall(r"BRIDGE_LOOKUP\s*:\s*([^\n]+)", (raw or "") + "\n" + (output or ""))
        if lk and self.rag and hasattr(self.rag, "find_platform"):
            rows = []
            for q in dict.fromkeys(x.strip().strip("'\")") for x in lk):
                if not q:
                    continue
                m = re.search(r"\btype=([A-Za-z]+)", q)
                ptype = m.group(1) if m else None
                name = re.sub(r"\btype=[A-Za-z]+", "", q).strip().strip("'\"")
                hits = self.rag.find_platform(name, ptype=ptype)
                if not hits:
                    near = self.rag.suggest(name)[:8] if hasattr(self.rag, "suggest") else []
                    rows.append("{}: no exact v515 match; nearest: {}".format(
                        name, "; ".join(str(h.get("name", h)) for h in near) or "none"))
                    continue
                for h in hits[:8]:
                    line = "{} | {}:{} | {} / {} | {}{}{}".format(
                        h["name"], h["type"], h["dbid"], h.get("country", ""), h.get("service", ""),
                        h.get("year", ""), " HYPOTHETICAL" if h.get("hypothetical") else "",
                        " DEPRECATED" if h.get("deprecated") else "")
                    if h["type"] == "Aircraft":
                        lo = self.rag.loadouts_for(h["dbid"])
                        line += " | loadouts: " + ", ".join(
                            "{}={}".format(k, v[:28]) for k, v in list(lo.items())[:12])
                    rows.append(line)
            self.state["lookup_results"] = rows
            self.emit("log", text="DB lookup: {} answered".format(len(lk)))

        # the model may ask for evidence; it arrives with the next prompt
        # the same directive shows up in the reply's Lua and again in the
        # console once printed; one request per kind is enough
        seen, wants = set(), []
        for kind, opts in parse_attach_directives(raw) + parse_attach_directives(output):
            if kind not in seen:
                seen.add(kind)
                wants.append((kind, opts))
        if self.cfg.get("bridge.attach_aalog_each_cycle", False) and "AALOG" not in seen:
            wants.append(("AALOG", {}))
        if wants:
            self.prepare_attachments(wants)

        halt = extract_halt(output)
        if halt:
            self.emit("error", text="BRIDGE_HALT: " + halt)
            return state(False, "the model asked for you: " + halt)

        done_line = extract_done(output)
        recommended, src = state_from_run(output, raw)

        # The failure verdict comes from the CONSOLE alone. A forward state
        # printed by the console alongside an error line is progress with a
        # cosmetic fault (the recurring reference point error would otherwise
        # have ended a healthy run on its third appearance). An error with NO
        # console state line means the script died before its final print,
        # and the code's own state declaration must not paper over that.
        sig = error_signature(output)
        console_state = extract_next_state(output)
        failure_cycle = (console_state == "FIX_ERRORS") or \
            (bool(sig) and not console_state)
        if failure_cycle:
            stage = "FIX_ERRORS"
            self.emit("log", text="console verdict: failure ({}), routing to "
                                  "FIX_ERRORS".format(
                                      console_state or "error with no state line"),
                      level="warn")
        else:
            stage = decide_next_stage(stage, recommended, output)
            self.emit("log", text="recommended {} (from {}) -> next {}".format(
                recommended or "nothing", src, stage))

        if sig and failure_cycle:
            self.state["errors"] += 1
            consecutive += 1
            repeats = repeats + 1 if sig == last_sig else 0
            last_sig = sig
            self.emit("log", text="run reported errors ({} in a row, same fault x{})"
                      .format(consecutive, repeats + 1), level="warn")
        elif sig:
            self.emit("log", text="output carries an error line but the run is "
                                  "progressing, not counted toward stopping",
                      level="warn")
            consecutive, last_sig, repeats = 0, "", 0
        else:
            consecutive, last_sig, repeats = 0, "", 0

        if done_line or stage == "DONE":
            self.state["stage"] = "DONE"
            self.emit("stage", stage="DONE", cycle=cycle)
            return state(False, "request fulfilled" + (": " + done_line if done_line else ""))

        if consecutive >= max_fail:
            return state(False, "{} consecutive failing cycles without progress".format(
                consecutive))
        if repeats >= max_repeat:
            return state(False, "the same fault {} cycles running, no progress: {}".format(
                repeats + 1, sig[:160]))

        if self.cfg.get("bridge.operator_owns_compression", True):
            control = ("RUNFOR={s}  (compression is set BY HAND to x{m}; do NOT emit "
                       "COMPRESS; size RUNFOR to the next decision minus a margin)"
                       .format(s=secs, m=int(self.cfg.get("bridge.manual_compression", 5))))
        else:
            control = "COMPRESS={c}; RUNFOR={s}".format(c=comp, s=secs)
        task = self._safe_format(STAGE_TASKS.get(stage, STAGE_TASKS["EVALUATE"]),
                                 c=comp, s=secs, control=control)
        if self.state.get("playtest"):
            task = ("PLAYTEST RUN IN PROGRESS: the scenario is already built, do not build "
                    "or add units; lead with the operator CLICK line; verify by readback.\n"
                    + task)
        label = "FAILURE_OUTPUT" if failure_cycle else "PREVIOUS_STAGE_OUTPUT"
        task += "\n\nCYCLE: {}\n{} (CMO console):\n{}".format(
            cycle, label, output)
        if pending_fault:
            task += "\n\nBRIDGE_NOTE: " + pending_fault
        if sig:
            task += ("\n\nBRIDGE_NOTE: the run reported errors. Repair them and carry "
                     "on with the original request. Print BRIDGE_HALT only if you "
                     "cannot proceed without the user.")
        self._safe("submit", self.submit_to_llm, self.build_prompt(task, task))
        return state(True)

    # -- play modes -------------------------------------------------
    def _run_play(self, params):
        from .turnengine import TurnEngine
        te = TurnEngine(self, params)
        te.run()

    # -- IKE --------------------------------------------------------
    def finalize_ike(self, master_path, on_step=None):
        fin = IkeFinalizer(self.cfg, self.run_lua_in_cmo,
                           lambda s: self._wait(s, "IKE conversion"),
                           lambda m: self.emit("ike", text=m), dry_run=self.dry_run)
        result, err = fin.finalize(master_path, on_step=on_step)
        if err:
            self.emit("error", text="IKE finalize: {}".format(err))
            return result, err
        return result, None

    def verify_ike(self, result):
        fin = IkeFinalizer(self.cfg, self.run_lua_in_cmo,
                           lambda s: None, lambda m: self.emit("ike", text=m),
                           dry_run=self.dry_run)
        return fin.verify_and_record(result)

    def commanders(self):
        return build_commanders(self.cfg)


def drop_echoed_script(text, code):
    """Remove the console's echo of the script it just ran.

    Only needed when "Echo input script on result text" is left ticked. The
    echo is matched on its first and last lines rather than the whole body,
    since the console reflows long lines.
    """
    if not text or not code:
        return text
    lines = [l for l in code.splitlines() if l.strip()]
    if len(lines) < 2:
        return text
    first, last = lines[0].strip(), lines[-1].strip()
    i = text.find(first)
    if i < 0:
        return text
    j = text.find(last, i + len(first))
    if j < 0:
        return text
    return (text[:i] + text[j + len(last):]).strip()


SUPPRESS_CALL = re.compile(r"Tool_EmulateNoConsole\s*[(,]\s*true\b", re.IGNORECASE)


def neutralize_console_suppression(code):
    """Comment out any line that switches console output off.

    Tool_EmulateNoConsole(true) makes the script behave as if it were not run
    from the console, which silences every print until it is switched back
    off. A payload that opens with it returns an empty result pane, so the
    loop has nothing to read and nothing to reason about. Works line by line
    so both the bare call and the guarded pcall form are caught, and the
    matching (false) call is left alone. Returns (code, count).
    """
    out, hits = [], 0
    for line in (code or "").split("\n"):
        if SUPPRESS_CALL.search(line):
            hits += 1
            indent = line[:len(line) - len(line.lstrip())]
            out.append("{}-- [CONN] disabled, suppresses console output: {}".format(
                indent, line.strip()))
        else:
            out.append(line)
    return "\n".join(out), hits


def slice_between_markers(text, token):
    """Return only what the last run printed.

    BEGIN without END (the script died on an error) returns what followed
    BEGIN, not the whole pane: earlier runs' state lines and BRIDGE_DONE
    must never be read as this run's. Falls back to the whole pane only
    when neither marker is present.
    """
    t = text or ""
    begin, end = "CONN_BEGIN:" + token, "CONN_END:" + token
    i = t.rfind(begin)
    j = t.rfind(end)
    if i >= 0 and j > i:
        return t[i + len(begin):j].strip()
    if i >= 0:
        return t[i + len(begin):].strip()
    if j > 0:
        return t[:j].strip()
    return t.strip()


def text_after_end_marker(text, token):
    """What was printed after the given run's END marker (post-run output)."""
    t = text or ""
    end = "CONN_END:" + token
    j = t.rfind(end)
    if j < 0:
        return ""
    return t[j + len(end):].strip()


def extract_lua_block(text):
    """Pull the Lua out of a copy.

    Handles a clean copy-button result (bare code), a single fenced block, and
    a page-wide select-all copy holding several fenced blocks, in which case
    the last one is the reply.
    """
    t = text or ""
    blocks = re.findall(r"```[ \t]*lua[ \t]*\r?\n(.*?)```", t, re.DOTALL | re.IGNORECASE)
    if not blocks:
        blocks = re.findall(r"```[ \t]*\r?\n(.*?)```", t, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    return luacheck.strip_fences(t)


def extract_next_state(text):
    """Take the LAST declaration, not the first.

    A script can print the line from several branches, so the first match is
    usually an early-exit path that never executed. In console output the last
    line printed is the one that actually ran; in a code block the final line
    is the intended terminal state.
    """
    found = re.findall(r"NEXT_RECOMMENDED_STATE[:\s]*([A-Z_]+)", text or "",
                       re.IGNORECASE)
    if found:
        return found[-1].upper()
    return ""


def state_from_run(output, raw):
    """Runtime output is authority. The reply's code is the fallback."""
    st = extract_next_state(output)
    if st:
        return st, "console"
    st = extract_next_state(raw)
    if st:
        return st, "code"
    if "ERROR" in (output or "").upper():
        return "FIX_ERRORS", "error text"
    return "", "none"


HALT_RE = re.compile(r"BRIDGE_HALT[:\s]*(.+)", re.IGNORECASE)
DONE_RE = re.compile(r"BRIDGE_DONE[:\s]*(.+)", re.IGNORECASE)


def extract_halt(text):
    """Only ever call this on runtime console output.

    A generated script legitimately carries the token inside an early-exit
    guard. Scanning the reply's code for it stops runs that would have
    succeeded, which is exactly what happened on 2026-08-23.
    """
    m = HALT_RE.search(text or "")
    return m.group(1).strip()[:300] if m else ""


def extract_done(text):
    m = DONE_RE.search(text or "")
    return m.group(1).strip()[:300] if m else ""


def error_signature(text):
    """A normalized fingerprint of the failure, for spotting a loop.

    GUIDs, numbers and quoted names are stripped so the same fault reported
    against different objects still collapses to one signature.
    """
    t = (text or "").upper()
    lines = []
    for line in t.splitlines():
        if ("CMO_ERROR" in line or "ATTEMPT TO" in line or "ERROR:" in line
                or "AUDIT_ERR" in line or "SIMCTL_ERR" in line):
            lines.append(line)
    if not lines:
        return ""
    sig = " | ".join(lines[:4])
    sig = re.sub(r"[0-9A-F]{8}-[0-9A-F-]{4,}", "<GUID>", sig)
    sig = re.sub(r"\d+", "<N>", sig)
    sig = re.sub(r"'[^']*'", "<S>", sig)
    return sig[:400]


def decide_next_stage(current, recommended, output):
    if "ERROR" in (output or "").upper() and recommended not in VALID_STAGES:
        return "DEPLOY"
    if recommended in VALID_STAGES:
        if current == "REPORT" and recommended in ("REPORT", "DONE"):
            return "DONE"
        return recommended
    return LINEAR.get(current, "EVALUATE")
