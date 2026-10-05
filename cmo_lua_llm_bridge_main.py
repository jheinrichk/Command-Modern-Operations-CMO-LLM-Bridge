# ============================================================
# CMO LUA + LLM BRIDGE  (revised from the Grok bridge)
# ------------------------------------------------------------
# LLM is the analyst / designer / gatekeeper / reviewer.
# The bridge drives a LLM browser tab + the CMO Lua console,
# grounds every prompt with the LOCAL CMO unified library (RAG),
# and runs a full scenario-design loop:
#     DESIGN -> DEPLOY -> TEST -> EVALUATE -> REFINE -> RETEST -> REPORT
# with play / pause / time-compression / reset / reload control
# available in ANY cycle.  Once a scenario is finalized, the bridge can
# convert it for head-to-head play with IKE (musurca's third-party PBEM/
# hotseat framework for CMO), then play turns to win by exchanging .save
# files with an opponent.
# ============================================================

import json
import re
import sys
import time
from pathlib import Path

import pyautogui
import pyperclip

from cmo_rag import CmoRag
from cmo_sim_control import SimController, parse_control_directives

CONFIG_PATH = Path(__file__).with_name("bridge_config.json")

# ------------------------------------------------------------
# Prompt contract sent to LLM (the browser tab)
# ------------------------------------------------------------
CMO_LUA_BRIDGE_INSTRUCTION = (
    "MODE:CMO_LUA_LLM_BRIDGE\n"
    "ROLE:YOU_ARE_DESIGNER_ANALYST_GATEKEEPER_AND_REVIEWER_FOR_A_CMO_SCENARIO\n"
    "GROUNDING:USE_ONLY_THE_RETRIEVED_CMO_CONTEXT_BELOW;DO_NOT_SEARCH_ONLINE;DO_NOT_INVENT_FUNCTIONS\n"
    "RETURN:FIRST_EXECUTABLE_LUA_CODE_BLOCK_ONLY\n"
    "SCRIPT:CMO_LUA_COMPATIBLE;USE_LOCAL_VARIABLES;PCALL_FOR_CRITICAL_OPS\n"
    "REQ:PRINT_RESULTS_ERRORS_AND_A_LINE_'NEXT_RECOMMENDED_STATE:<STATE>'\n"
    "STATES:DESIGN|DEPLOY|TEST|EVALUATE|REFINE|RETEST|REPORT|DONE|FIX_ERRORS\n"
    "REQ:COPY_FINAL_OUTPUT_TO_WINDOWS_CLIPBOARD\n"
    "SAFETY:USER_EXPLICITLY_ALLOWED_TO_RUN_LUA_IN_THIS_SCENARIO\n"
    "GATEKEEPER_CHECKLIST:R23_API_CORRECTNESS;TRANSACTION_AND_PCALL_DISCIPLINE;"
    "QUERY_BEFORE_MODIFY;PREFER_GUIDS_FOR_MISSIONS_AND_REFPOINTS;"
    "STORE_GUIDS_IN_KEYSTORE;DRY_RUN_WHEN_UNSURE;SCOPE_BANNER_AT_TOP;PRINT_CONTRACT_AT_END\n"
    "OPTIONAL:YOU_MAY_EMIT_ONE_LINE_'BRIDGE_CONTROL:<OPS>'_TO_DRIVE_THE_SIM\n"
    "  OPS_ARE:PLAY|PAUSE|COMPRESS=<n>|RUNFOR=<seconds>|RESET|RELOAD|START\n"
    "OUTPUT:CODE_FIRST;NO_PROSE_BEFORE_CODE\n"
    "LOOP:CONTINUE_THROUGH_CYCLES_UNTIL_REPORT_OR_DONE_OR_MAX_CYCLES_OR_FIX_ERRORS_OR_USER_STOP\n"
    "CMO_RULE:WHEN_GENERATING_LUA_USE_THE_RETRIEVED_CONTEXT_FOR_CORRECT_FUNCTIONS_WRAPPERS_ENUMS_AND_BEST_PRACTICES\n"
    "CMO_RULE:FOR_PLATFORMS_USE_EXACT_NAMES_FROM_THE_LOOKUP_LAYER;RESOLVE_DBIDS_BEFORE_PLACING_UNITS\n"
    "FORMAT_HARD_REQUIREMENT:THE_FIRST_CHARACTER_OF_THE_RESPONSE_MUST_BE_THE_FIRST_BACKTICK_OF_A_FENCED_LUA_CODE_BLOCK\n"
    "FORMAT_HARD_REQUIREMENT:START_EXACTLY_WITH_TRIPLE_BACKTICK_LUA_AND_END_EXACTLY_WITH_TRIPLE_BACKTICK\n"
    "FORMAT_HARD_REQUIREMENT:DO_NOT_OUTPUT_ANY_TEXT_BEFORE_OR_AFTER_THE_CODE_BLOCK"
)

# ------------------------------------------------------------
# Default config (llm_* browser coords + CMO sim controls)
# ------------------------------------------------------------
DEFAULT_CONFIG = {
    "timing": {
        "llm_output_wait_seconds": 60,
        "llm_copy_retry_wait_seconds": 40,
        "llm_copy_retry_attempts": 4,
        "llm_reprint_wait_seconds": 60,
        "cmo_output_wait_seconds": 5,
        "cmo_popup_wait_seconds": 1.5,
        "sim_settle_seconds": 1.0,
        "test_window_wall_cap_seconds": 45,
        "startup_delay_seconds": 3,
        "pause_between_actions": 0.25,
        "pause_after_copy_seconds": 1.0,
        "pause_after_paste_seconds": 1.0,
    },
    "bridge": {
        "max_cycles": 500,
        "stop_on_fix_errors": True,
        "stop_on_report": True,
        "stop_on_done": True,
        "max_invalid_code_attempts": 3,
        "prefer_lua_sim_control": True,
        "default_test_compression": 15,
        "default_test_seconds": 300,
        "rag_recipes": 5,
        "rag_docs": 3,
        "pbem_enabled": False,
    },
    "coordinates": {
        "llm_input": [347, 847],
        "llm_submit": [954, 906],
        "llm_code_copy": [796, 329],
        "cmo_lua_input": [1500, 949],
        "cmo_execute": [2022, 585],
        "cmo_popup_ok": [600, 400],
        "cmo_output_area": [1500, 949],
        # --- simulation controls (calibrate these) ---
        "cmo_play": [500, 300],
        "cmo_pause": [560, 300],
        "cmo_time_comp_up": [1943, 651],
        "cmo_time_comp_down": [1900, 651],
        "cmo_scenario_start": [500, 300],
        "cmo_scenario_reset": [620, 300],
        "cmo_scenario_reload": [680, 300],
    },
    "hotkeys": {
        "copy": ["ctrl", "c"],
        "paste": ["ctrl", "v"],
        "select_all": ["ctrl", "a"],
        "llm_submit": ["enter"],
    },
    "pbem": {
        "framework": "IKE",
        "ike_conversion_lua_path": "C:\\CMOBridge\\IKE\\ike_convert.lua",
        "ike_release": "https://github.com/musurca/IKE/releases",
        "my_side": "Blue",
        "opponent_side": "Red",
        "save_exchange_folder": "C:\\CMOBridge\\PBEM",
        "order_mode": "continuous",
        "turn_length_minutes": 30,
        "setup_phase": True,
        "auto_answer_conversion_popups": False,
        "play_to_win": True,
    },
}


def merge_defaults(config, defaults):
    for key, value in defaults.items():
        if key not in config:
            config[key] = value
        elif isinstance(value, dict) and isinstance(config.get(key), dict):
            merge_defaults(config[key], value)
    return config


def load_config():
    if not CONFIG_PATH.exists():
        with open(str(CONFIG_PATH), "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with open(str(CONFIG_PATH), "r") as f:
        config = json.load(f)
    return merge_defaults(config, json.loads(json.dumps(DEFAULT_CONFIG)))


CONFIG = load_config()
TIMING = CONFIG.get("timing", {})
BRIDGE = CONFIG.get("bridge", {})
COORDS = CONFIG.get("coordinates", {})
HOTKEYS = CONFIG.get("hotkeys", {})
PBEM = CONFIG.get("pbem", {})

LLM_OUTPUT_WAIT = int(TIMING.get("llm_output_wait_seconds", 60))
LLM_COPY_RETRY_WAIT = int(TIMING.get("llm_copy_retry_wait_seconds", 40))
LLM_COPY_RETRY_ATTEMPTS = int(TIMING.get("llm_copy_retry_attempts", 4))
LLM_REPRINT_WAIT = int(TIMING.get("llm_reprint_wait_seconds", 60))
CMO_OUTPUT_WAIT = int(TIMING.get("cmo_output_wait_seconds", 5))
CMO_POPUP_WAIT = float(TIMING.get("cmo_popup_wait_seconds", 1.5))
SIM_SETTLE = float(TIMING.get("sim_settle_seconds", 1.0))
TEST_WALL_CAP = int(TIMING.get("test_window_wall_cap_seconds", 45))
STARTUP_DELAY = int(TIMING.get("startup_delay_seconds", 3))
PAUSE_BETWEEN = float(TIMING.get("pause_between_actions", 0.25))
PAUSE_AFTER_COPY = float(TIMING.get("pause_after_copy_seconds", 1.0))
PAUSE_AFTER_PASTE = float(TIMING.get("pause_after_paste_seconds", 1.0))
# LLM's fenced code block and its copy button only fully render after the
# chat pane is focused and paged down. These keys already existed in
# bridge_config.json but were never read by the script.
LLM_SCROLL_PAGE_DOWNS = int(TIMING.get("llm_scroll_page_downs", 2))
LLM_SCROLL_PAUSE = float(TIMING.get("llm_scroll_pause_seconds", 0.4))
# Short spacing between fast copy retries. The long LLM_COPY_RETRY_WAIT is
# only spent between full rounds, when LLM may still be generating.
COPY_QUICK_RETRIES = int(TIMING.get("copy_quick_retries", 3))
COPY_QUICK_RETRY_WAIT = float(TIMING.get("copy_quick_retry_seconds", 2.0))

MAX_CYCLES = int(BRIDGE.get("max_cycles", 500))
STOP_ON_FIX_ERRORS = bool(BRIDGE.get("stop_on_fix_errors", True))
STOP_ON_REPORT = bool(BRIDGE.get("stop_on_report", True))
STOP_ON_DONE = bool(BRIDGE.get("stop_on_done", True))
MAX_INVALID = int(BRIDGE.get("max_invalid_code_attempts", 3))
PREFER_LUA_SIM = bool(BRIDGE.get("prefer_lua_sim_control", True))
DEF_COMPRESSION = int(BRIDGE.get("default_test_compression", 15))
DEF_TEST_SECONDS = int(BRIDGE.get("default_test_seconds", 300))
RAG_RECIPES = int(BRIDGE.get("rag_recipes", 5))
RAG_DOCS = int(BRIDGE.get("rag_docs", 3))

VERBOSE = True
RAG = CmoRag()  # local unified-library retrieval; no network


# ------------------------------------------------------------
# Low-level UI primitives (kept close to the working original)
# ------------------------------------------------------------
def hotkey_value(name, fallback):
    v = HOTKEYS.get(name)
    return tuple(v) if v else fallback


COPY_HOTKEY = hotkey_value("copy", ("ctrl", "c"))
PASTE_HOTKEY = hotkey_value("paste", ("ctrl", "v"))
SELECT_ALL_HOTKEY = hotkey_value("select_all", ("ctrl", "a"))
LLM_SUBMIT_HOTKEY = hotkey_value("llm_submit", ("enter",))


def log(msg):
    if VERBOSE:
        print(msg)


def pause(seconds=None):
    time.sleep(seconds if seconds is not None else PAUSE_BETWEEN)


def countdown(seconds, label):
    log("{}: waiting {} seconds...".format(label, seconds))
    for r in range(seconds, 0, -1):
        if r % 10 == 0 or r <= 3:
            log("  {} seconds remaining".format(r))
        time.sleep(1)
    log("{}: wait complete.".format(label))


def coord(name):
    v = COORDS.get(name)
    if not v or len(v) != 2:
        raise RuntimeError("Missing coordinate: {}".format(name))
    return int(v[0]), int(v[1])


def has_coord(name):
    v = COORDS.get(name)
    return v is not None and len(v) == 2


def click_at_name(name, label=None):
    x, y = coord(name)
    if label:
        log("Clicking: {} at {}, {}".format(label, x, y))
    try:
        pyautogui.moveTo(x, y, duration=0.08)
    except Exception:
        pass
    pyautogui.click(x, y)
    pause()


def hotkey(keys, label=None):
    if label:
        log("Hotkey: {}".format(label))
    try:
        pyautogui.hotkey(*keys)
    except Exception:
        pass
    pause()


def paste_text(text, label="text"):
    try:
        pyperclip.copy(text)
        pause(0.08)
        hotkey(PASTE_HOTKEY, "paste " + label)
    except Exception as ex:
        log("Paste failed: {}".format(ex))


# --- LLM browser side ---
def click_llm_input_and_clear():
    if has_coord("llm_input"):
        click_at_name("llm_input", "LLM input")
        pause(0.15)
        hotkey(SELECT_ALL_HOTKEY, "select all")
        pyautogui.press("delete")
        pause(0.1)


def submit_to_llm():
    if has_coord("llm_submit"):
        click_at_name("llm_submit", "LLM submit")
    else:
        hotkey(LLM_SUBMIT_HOTKEY, "submit")


def click_llm_code_copy():
    if has_coord("llm_code_copy"):
        click_at_name("llm_code_copy", "LLM code area")


def reveal_llm_code_button():
    """LLM's fenced code block and its copy button only fully render once
    the chat pane is focused and paged down. Click into the pane, then tap
    PgDn, so the copy button is on-screen before it is clicked."""
    if has_coord("llm_input"):
        click_at_name("llm_input", "focus LLM chat pane")
        pause(0.15)
    for _ in range(max(0, LLM_SCROLL_PAGE_DOWNS)):
        try:
            pyautogui.press("pagedown")
        except Exception:
            pass
        pause(LLM_SCROLL_PAUSE)


_CLIP_SENTINEL = "__CMO_BRIDGE_CLIPBOARD_EMPTY__"


def _strip_fences(raw):
    code = (raw or "").strip()
    if code.startswith("```"):
        code = re.sub(r"^```(?:lua)?\s*", "", code, flags=re.IGNORECASE)
        code = re.sub(r"```$", "", code).strip()
    return code


def _looks_like_lua(text):
    """Guard against accepting prose, a stale block, or an empty copy."""
    if not text or not text.strip():
        return False
    t = text.strip()
    if t.startswith("```"):
        return True
    signals = ("ScenEdit_", "VP_", "local ", "print(", "function", "pcall(")
    return sum(1 for s in signals if s in t) >= 2


def copy_llm_code_with_retry(prev_raw=None):
    """Copy the newest Lua block from LLM.

    The previous version accepted ANY non-empty clipboard as success. After
    cycle 1 the clipboard still holds the previous cycle's code, so a copy
    click that missed the newest block silently returned the OLD script and
    the bridge re-ran it. This version rejects stale and empty copies.

      * Fast path: if the clipboard already holds fresh Lua (e.g. the
        operator clicked copy manually), use it with no click and no wait.
      * Sentinel: the clipboard is poisoned before each attempt, so a click
        that copies nothing is detected instead of passing stale text on.
      * Staleness: content identical to prev_raw is rejected.
      * Shape: content must look like Lua.
      * Quick retries are seconds apart; the long LLM_COPY_RETRY_WAIT is
        only spent between rounds, when LLM may still be generating.
    """
    # ---- fast path: clipboard already holds a fresh block ----
    try:
        pre = pyperclip.paste()
    except Exception:
        pre = ""
    if (pre and pre != _CLIP_SENTINEL and _looks_like_lua(pre)
            and (prev_raw is None or pre.strip() != (prev_raw or "").strip())):
        log("Clipboard already holds fresh Lua ({} chars) - using it.".format(len(pre)))
        return _strip_fences(pre), pre

    for attempt in range(LLM_COPY_RETRY_ATTEMPTS):
        for q in range(max(1, COPY_QUICK_RETRIES)):
            try:
                # poison the clipboard so "nothing copied" is detectable
                try:
                    pyperclip.copy(_CLIP_SENTINEL)
                except Exception:
                    pass

                reveal_llm_code_button()
                click_llm_code_copy()
                pause(PAUSE_AFTER_COPY)
                hotkey(COPY_HOTKEY, "copy from LLM")
                pause(0.7)
                raw = pyperclip.paste()

                if not raw or raw == _CLIP_SENTINEL:
                    log("Copy produced nothing new (quick retry {}/{}).".format(
                        q + 1, COPY_QUICK_RETRIES))
                    pause(COPY_QUICK_RETRY_WAIT)
                    continue

                if prev_raw is not None and raw.strip() == (prev_raw or "").strip():
                    log("Clipboard still holds the PREVIOUS cycle's code "
                        "(quick retry {}/{}).".format(q + 1, COPY_QUICK_RETRIES))
                    pause(COPY_QUICK_RETRY_WAIT)
                    continue

                if not _looks_like_lua(raw):
                    log("Clipboard content is not a Lua block yet "
                        "(quick retry {}/{}).".format(q + 1, COPY_QUICK_RETRIES))
                    pause(COPY_QUICK_RETRY_WAIT)
                    continue

                log("Copied {} characters from LLM".format(len(raw)))
                return _strip_fences(raw), raw

            except Exception as ex:
                log("Copy attempt {}.{} error: {}".format(attempt + 1, q + 1, ex))
                pause(COPY_QUICK_RETRY_WAIT)

        if attempt < LLM_COPY_RETRY_ATTEMPTS - 1:
            countdown(LLM_COPY_RETRY_WAIT,
                      "Waiting for LLM to finish generating")
    return "", ""


# --- CMO Lua console side ---
def click_cmo_lua_input_and_clear():
    if has_coord("cmo_lua_input"):
        click_at_name("cmo_lua_input", "CMO Lua input")
        pause(0.15)
        hotkey(SELECT_ALL_HOTKEY, "select all")
        pyautogui.press("delete")
        pause(0.1)


def click_cmo_execute():
    if has_coord("cmo_execute"):
        click_at_name("cmo_execute", "CMO Execute button")


def handle_cmo_popup_ok():
    if has_coord("cmo_popup_ok"):
        log("Checking for CMO popup dialog...")
        pause(CMO_POPUP_WAIT)
        try:
            click_at_name("cmo_popup_ok", "CMO Popup OK button")
            pause(0.5)
        except Exception:
            log("No CMO popup detected or click failed")


def copy_cmo_output():
    if has_coord("cmo_output_area"):
        click_at_name("cmo_output_area", "CMO output area")
    elif has_coord("cmo_lua_input"):
        click_at_name("cmo_lua_input", "CMO output area (fallback)")
    pause(0.3)
    hotkey(SELECT_ALL_HOTKEY, "select all CMO output")
    pause(0.2)
    hotkey(COPY_HOTKEY, "copy CMO output")
    pause(0.5)
    try:
        return pyperclip.paste()
    except Exception:
        return "[Failed to copy CMO output]"


def run_lua_in_cmo(code):
    """Inject and execute Lua in the CMO console. Used for scenario code AND
    for injecting the AGENT_* sim-control helpers."""
    click_cmo_lua_input_and_clear()
    paste_text(code, "lua to CMO")
    pause(PAUSE_AFTER_PASTE)
    click_cmo_execute()
    handle_cmo_popup_ok()


# ------------------------------------------------------------
# Sim controller wiring
# ------------------------------------------------------------
SIM = SimController(
    primitives={
        "run_lua": run_lua_in_cmo,
        "click": click_at_name,
        "has_coord": has_coord,
        "log": log,
        "sleep": pause,
    },
    prefer_lua=PREFER_LUA_SIM,
)


def apply_control_directives(llm_raw):
    """Honor an optional 'BRIDGE_CONTROL: ...' line from LLM's output."""
    ops = parse_control_directives(llm_raw)
    if not ops:
        return
    log("Applying BRIDGE_CONTROL directives: {}".format(ops))
    for op, arg in ops:
        if op == "PLAY" or op == "START":
            SIM.scenario_start() if op == "START" else SIM.play()
        elif op == "PAUSE":
            SIM.pause()
        elif op == "COMPRESS" and arg:
            SIM.set_compression(arg)
        elif op == "RUNFOR" and arg:
            _timed_test_window(int(arg), DEF_COMPRESSION)
        elif op == "RESET":
            SIM.scenario_reset()
        elif op == "RELOAD":
            SIM.scenario_reload()
        pause(SIM_SETTLE)


def _timed_test_window(sim_seconds, compression):
    """Advance the sim by ~sim_seconds at compression, then pause. On Std
    edition (no auto-halt) the wall-clock wait is capped for safety."""
    info = SIM.run_for(sim_seconds, compression=compression)
    wall = min(TEST_WALL_CAP, max(3, int(sim_seconds / max(1, compression)) + 2))
    countdown(wall, "Test window (sim ~{}s @ x{})".format(sim_seconds, compression))
    SIM.pause()
    pause(SIM_SETTLE)
    return info


# ------------------------------------------------------------
# Prompt assembly with RAG grounding
# ------------------------------------------------------------
def build_prompt(task_message, retrieve_for=None):
    context = RAG.retrieve_context(
        retrieve_for or task_message, k_recipes=RAG_RECIPES, k_docs=RAG_DOCS
    )
    return (
        CMO_LUA_BRIDGE_INSTRUCTION
        + "\n\n" + context
        + "\n\nCURRENT_CYCLE_AND_TASK:\n" + task_message
    )


def submit_prompt_to_llm(task, retrieve_for=None, label="LLM output wait"):
    click_llm_input_and_clear()
    paste_text(build_prompt(task, retrieve_for), "prompt")
    submit_to_llm()
    countdown(LLM_OUTPUT_WAIT, label)


def extract_next_state(text):
    m = re.search(r"NEXT_RECOMMENDED_STATE[:\s]*([A-Z_]+)", text or "", re.IGNORECASE)
    if m:
        return m.group(1).upper()
    if "FIX_ERRORS" in (text or "").upper():
        return "FIX_ERRORS"
    return "CONTINUE"


# ------------------------------------------------------------
# The design loop state machine
# ------------------------------------------------------------
STAGE_TASKS = {
    "DESIGN": (
        "STAGE DESIGN. Produce the FIRST build script for this scenario. "
        "Build a blank scenario if none is loaded (Tool_BuildBlankScenario), add sides "
        "with postures, seed the core order of battle using EXACT platform names resolved "
        "from the lookup layer, add reference points/zones and the primary missions. "
        "End with the print contract and NEXT_RECOMMENDED_STATE: DEPLOY."
    ),
    "DEPLOY": (
        "STAGE DEPLOY. The previous script ran; review the CMO output below. If the build "
        "is clean, emit a short verification script (counts of sides/units/missions, key GUIDs "
        "stored to keystore) and NEXT_RECOMMENDED_STATE: TEST. If errors, fix them and "
        "NEXT_RECOMMENDED_STATE: DEPLOY."
    ),
    "TEST": (
        "STAGE TEST. Emit any pre-run instrumentation (score baseline, event hooks, expected "
        "outcomes to keystore). You MAY add 'BRIDGE_CONTROL: COMPRESS={c}; RUNFOR={s}' to advance "
        "a test window. End NEXT_RECOMMENDED_STATE: EVALUATE."
    ),
    "EVALUATE": (
        "STAGE EVALUATE. Read the post-run CMO output below. Judge whether the scenario behaved "
        "as intended (balance, triggers fired, losses, score deltas). If acceptable "
        "NEXT_RECOMMENDED_STATE: REPORT, else describe the fix intent in a comment header and "
        "NEXT_RECOMMENDED_STATE: REFINE."
    ),
    "REFINE": (
        "STAGE REFINE. Emit a targeted patch script (adjust forces, doctrine, WRA, timing, zones) "
        "addressing the evaluation. Query-before-modify; prefer GUIDs. "
        "You MAY add 'BRIDGE_CONTROL: RESET' if a clean re-run is needed. NEXT_RECOMMENDED_STATE: RETEST."
    ),
    "RETEST": (
        "STAGE RETEST. Re-run the test window ('BRIDGE_CONTROL: COMPRESS={c}; RUNFOR={s}') and "
        "print the same metrics as TEST for comparison. NEXT_RECOMMENDED_STATE: EVALUATE."
    ),
    "REPORT": (
        "STAGE REPORT. Emit a final Lua block that prints a structured evaluation report: scenario "
        "title, sides, force counts, test outcomes across iterations, balance verdict, and readiness "
        "for IKE PBEM conversion (two human-playable sides, balanced, decisive). "
        "NEXT_RECOMMENDED_STATE: DONE."
    ),
}


def stage_task(stage):
    t = STAGE_TASKS.get(stage, STAGE_TASKS["DESIGN"])
    return t.format(c=DEF_COMPRESSION, s=DEF_TEST_SECONDS)


def cycle_deploy_and_capture(lua_code):
    """Run LLM's Lua in CMO, run the automatic test window if this stage
    calls for it, and return the CMO output text."""
    run_lua_in_cmo(lua_code)
    countdown(CMO_OUTPUT_WAIT, "CMO execution wait")
    return copy_cmo_output()


def main_loop(user_scenario_prompt):
    stage = "DESIGN"
    invalid = 0

    log("\n########## SCENARIO DESIGN SESSION ##########")
    log("User scenario request:\n" + user_scenario_prompt + "\n")

    # First cycle: seed DESIGN with the user's scenario intent, grounded by RAG.
    first_task = (
        stage_task("DESIGN")
        + "\n\nUSER_SCENARIO_REQUEST:\n" + user_scenario_prompt
    )
    submit_prompt_to_llm(first_task, retrieve_for=user_scenario_prompt)

    prev_raw = None
    for cycle in range(1, MAX_CYCLES + 1):
        log("\n========== CYCLE {}  [STAGE {}] ==========".format(cycle, stage))

        lua_code, llm_raw = copy_llm_code_with_retry(prev_raw=prev_raw)

        if not lua_code.strip():
            click_llm_input_and_clear()
            paste_text(
                CMO_LUA_BRIDGE_INSTRUCTION
                + "\n\nCURRENT_CYCLE_AND_TASK:\nReprint the last Lua code block only.",
                "reprint request",
            )
            submit_to_llm()
            countdown(LLM_REPRINT_WAIT, "LLM reprint wait")
            # A reprint is EXPECTED to return the same code, so the staleness
            # check is relaxed for this one call.
            lua_code, llm_raw = copy_llm_code_with_retry(prev_raw=None)

        if not lua_code.strip():
            invalid += 1
            if invalid >= MAX_INVALID:
                log("Too many empty copies. Stopping.")
                break
            continue
        invalid = 0
        prev_raw = llm_raw  # next cycle rejects an identical copy

        # Honor any sim-control directive LLM embedded (e.g. RESET before deploy)
        apply_control_directives(llm_raw)

        # Deploy LLM's Lua into CMO and capture the console output
        cmo_output = cycle_deploy_and_capture(lua_code)
        if not cmo_output.strip():
            cmo_output = "[No output copied from CMO]"

        # Stages that own an automatic test window advance the sim here
        if stage in ("TEST", "RETEST"):
            _timed_test_window(DEF_TEST_SECONDS, DEF_COMPRESSION)
            post = copy_cmo_output()
            if post.strip():
                cmo_output = cmo_output + "\n\n[POST-RUN OUTPUT]\n" + post

        # Decide next stage: LLM's recommendation wins, else linear advance
        recommended = extract_next_state(llm_raw) or extract_next_state(cmo_output)
        stage = decide_next_stage(stage, recommended, cmo_output)
        log("Recommended: {}  ->  next stage: {}".format(recommended, stage))

        if STOP_ON_FIX_ERRORS and stage == "FIX_ERRORS":
            log("FIX_ERRORS reached. Stopping for human review.")
            break
        if STOP_ON_REPORT and stage == "REPORT_DONE":
            log("Report delivered. Scenario design session complete.")
            break
        if STOP_ON_DONE and stage == "DONE":
            log("DONE reached. Scenario ready" +
                (" for IKE PBEM conversion." if BRIDGE.get("pbem_enabled") else "."))
            if BRIDGE.get("pbem_enabled"):
                pbem_handoff(cmo_output)
            break

        # Feed CMO output back to LLM with the next stage's task
        next_task = (
            stage_task(stage if stage in STAGE_TASKS else "EVALUATE")
            + "\n\nCYCLE: {}\nPREVIOUS_STAGE_OUTPUT (CMO console):\n{}".format(cycle, cmo_output)
        )
        submit_prompt_to_llm(next_task, retrieve_for=next_task)

    log("\nBridge stopped.")


def decide_next_stage(current, recommended, cmo_output):
    """LLM's NEXT_RECOMMENDED_STATE drives transitions; fall back to a
    sane linear order. REPORT completes into a terminal REPORT_DONE."""
    valid = {"DESIGN", "DEPLOY", "TEST", "EVALUATE", "REFINE", "RETEST",
             "REPORT", "DONE", "FIX_ERRORS"}
    if "ERROR" in (cmo_output or "").upper() and recommended not in valid:
        return "DEPLOY"  # let LLM fix in-place
    if recommended in valid:
        if current == "REPORT" and recommended in ("REPORT", "DONE"):
            return "DONE"
        return recommended
    linear = {"DESIGN": "DEPLOY", "DEPLOY": "TEST", "TEST": "EVALUATE",
              "EVALUATE": "REPORT", "REFINE": "RETEST", "RETEST": "EVALUATE",
              "REPORT": "DONE"}
    return linear.get(current, "EVALUATE")


# ------------------------------------------------------------
# IKE PBEM handoff  (musurca/IKE — third-party PBEM/hotseat framework)
# ------------------------------------------------------------
# IKE converts a finished scenario into a WEGO turn-based multiplayer game
# by INJECTING its Lua into an event action. You paste the IKE conversion
# block into the CMO Lua Script Console, click RUN, and answer its pop-up
# questions (sides, turn order, turn length, optional Setup Phase, per-player
# passwords). Play then proceeds by exchanging .save files: on your turn you
# give orders, end the turn (IKE auto-stops the clock and summarizes losses/
# messages), save, and send the file to your opponent.
#
# IKE is not bundled here (it is musurca's project). Download the Scenario
# Author Pack from pbem.ike_release and point pbem.ike_conversion_lua_path at
# the conversion Lua block.
def pbem_convert_with_ike():
    """Inject the IKE conversion Lua into the CMO console to make the finalized
    scenario PBEM-ready. IKE then drives pop-up questions; unless you have
    pre-answered them, a human completes the conversion dialog once."""
    path = PBEM.get("ike_conversion_lua_path", "")
    p = Path(path) if path else None
    if not p or not p.exists():
        log("IKE conversion Lua not found at '{}'.".format(path))
        log("Download the Scenario Author Pack from {} and set "
            "pbem.ike_conversion_lua_path.".format(PBEM.get("ike_release", "")))
        return False
    log("Injecting IKE conversion Lua from {} ...".format(path))
    run_lua_in_cmo(p.read_text(encoding="utf-8", errors="replace"))
    countdown(CMO_OUTPUT_WAIT, "IKE conversion wait")
    if not PBEM.get("auto_answer_conversion_popups", False):
        log("IKE is asking its conversion questions via pop-ups (sides, turn "
            "order, turn length, Setup Phase, passwords). Answer them in CMO, "
            "then save the PBEM-ready scenario.")
    return True


def pbem_handoff(final_output):
    log("\n########## IKE PBEM HANDOFF (play to win) ##########")
    log("Finalized scenario ready. Converting for turn-based H2H with IKE "
        "({} vs {}), order mode: {}.".format(
            PBEM.get("my_side", "Blue"), PBEM.get("opponent_side", "Red"),
            PBEM.get("order_mode", "continuous")))
    pbem_convert_with_ike()
    log("PBEM play loop (scaffold — enable pbem_enabled and calibrate the "
        "save/load and IKE end-turn UI points):")
    # Turn loop outline (not auto-run):
    #   1. Load the IKE-converted PBEM scenario; enter your password at your turn.
    #   2. (Setup Phase, if enabled) set loadouts, missions, EMCON before start.
    #   3. Read the situation with VP_/ScenEdit_ getters + RAG doctrine, then
    #      give orders (missions, WRA, EMCON, movement) that maximize own score
    #      and deny the opponent. In Limited-Order mode, plan phases in advance.
    #   4. End the turn: IKE auto-stops the clock, summarizes losses/messages,
    #      and prompts to save. Save the .save file to save_exchange_folder.
    #   5. Send the .save to the opponent; on their return file, load it,
    #      evaluate deltas from IKE's turn summary, adapt, and repeat to win.
    return True


def get_initial_prompt():
    if len(sys.argv) > 1 and sys.argv[1] == "--prompt-file":
        return Path(sys.argv[2]).read_text(encoding="utf-8").strip()
    print("Describe the scenario to design. Type END on its own line when finished.")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip() or (
        "Design a balanced Strait of Hormuz surface-action scenario: Blue escort group "
        "vs Red missile-boat swarm, single decisive engagement, ~2 hour window."
    )


def main():
    print("CMO Lua + LLM Bridge  (design -> deploy -> test -> refine -> retest -> evaluate -> report)")
    print("Local RAG loaded: {} lookup records, doc index ready.".format(
        RAG.lk["count"] if RAG.lk else 0))
    print("Starting in {} seconds...".format(STARTUP_DELAY))
    time.sleep(STARTUP_DELAY)
    try:
        prompt = get_initial_prompt()
        main_loop(prompt)
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
