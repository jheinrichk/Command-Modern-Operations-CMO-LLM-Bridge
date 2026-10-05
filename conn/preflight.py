"""
conn.preflight  -  go / no-go checks before any mode starts.

Each check returns a Check with an optional fix() callable that the UI wires
to a Fix button on that row.
"""

import os
import sys
from pathlib import Path

from .winmgr import IS_WINDOWS, point_is_own_window


class Check:
    def __init__(self, key, label, ok, detail="", fix=None, fix_label="Fix", warn=False):
        self.key = key
        self.label = label
        self.ok = ok
        self.detail = detail
        self.fix = fix
        self.fix_label = fix_label
        self.warn = warn

    @property
    def state(self):
        if self.ok:
            return "ok"
        return "warn" if self.warn else "fail"


def run_preflight(cfg, wm, resolver, mode="design"):
    checks = []
    wm.refresh()

    # platform and dependencies
    checks.append(Check(
        "platform", "Windows host", IS_WINDOWS,
        "Detected {}".format(sys.platform),
        warn=False))
    try:
        import pyautogui  # noqa: F401
        pa = True
    except Exception as ex:
        pa = False
    checks.append(Check("pyautogui", "pyautogui installed", pa,
                        "pip install pyautogui" if not pa else "ready"))
    try:
        import pyperclip  # noqa: F401
        pc = True
    except Exception:
        pc = False
    checks.append(Check("pyperclip", "pyperclip installed", pc,
                        "pip install pyperclip" if not pc else "ready"))

    # windows present
    for key, spec in cfg.windows.items():
        if key == "conn":
            continue
        info = wm.info(key)
        need = key in ("cmo", "cmo_lua") or (key == "llm" and mode != "normal")
        checks.append(Check(
            "win_" + key,
            "{} window".format(spec.get("label", key)),
            info is not None,
            (info.title[:60] if info else "not found, match rule: {}".format(
                spec.get("title_regex"))),
            warn=not need))

    # anchors
    unset, missing = [], []
    for name in cfg.anchors.keys():
        st = resolver.status(name)
        if st == "unset":
            unset.append(name)
        elif st != "ok":
            missing.append(name)
    core = ["llm_input", "llm_code_copy", "cmo_lua_input", "cmo_execute",
            "cmo_output_area", "cmo_play", "cmo_pause"]
    if mode == "normal":
        # monitor-only: nothing is clicked in LLM or the console
        core = ["cmo_play", "cmo_pause"]
    core_bad = [n for n in core if resolver.status(n) != "ok"]
    checks.append(Check(
        "anchors_core", "Core click anchors resolve", not core_bad,
        "unresolved: " + ", ".join(core_bad) if core_bad else "all core anchors ok"))

    # CONN stays on top. An anchor under its window would click CONN itself.
    covered = []
    for name in cfg.anchors.keys():
        pt = resolver.resolve(name) if resolver.status(name) == "ok" else None
        if pt and point_is_own_window(pt[0], pt[1]):
            covered.append(name)
    checks.append(Check(
        "anchors_covered", "No anchor under CONN's own window", not covered,
        ("covered by CONN: " + ", ".join(covered) + ". CONN skips these clicks; move "
         "CONN or apply the layout") if covered else "no anchor is covered",
        warn=True))
    checks.append(Check(
        "anchors_optional", "Optional anchors", not unset,
        "unset: " + ", ".join(unset) if unset else "all set", warn=True))

    # folders
    for key, label in (("in_folder", "IN folder"), ("out_folder", "OUT folder"),
                       ("sessions_folder", "Sessions folder"),
                       ("snapshots_folder", "Snapshots folder")):
        p = cfg.folder(key)
        ok = bool(p and p.exists() and os.access(str(p), os.W_OK))

        def _mk(pp=p):
            def fix():
                Path(pp).mkdir(parents=True, exist_ok=True)
            return fix

        checks.append(Check("folder_" + key, label, ok,
                            str(p) if p else "not configured",
                            fix=_mk() if p else None, fix_label="Create", warn=True))

    # IKE for modes that need it
    if mode in ("pbem_h2h", "player_vs_llm", "llm_vs_llm"):
        ike = cfg.get("ike.ike_conversion_lua_path", "")
        p = Path(ike) if ike else None
        checks.append(Check(
            "ike_lua", "IKE conversion Lua", bool(p and p.exists()),
            str(p) if p else "set ike.ike_conversion_lua_path",
            warn=(mode != "pbem_h2h")))
        ex = cfg.folder("save_exchange_folder")
        # an empty setting used to become Path("") == "." and pass
        ok = bool(ex and str(ex).strip() not in ("", ".") and Path(ex).exists())

        def fix_ex(pp=ex):
            Path(pp).mkdir(parents=True, exist_ok=True)

        checks.append(Check("pbem_folder", "PBEM save exchange folder", ok,
                            str(ex) if ex else "not configured",
                            fix=fix_ex if ex else None, fix_label="Create", warn=True))

    # CMO logs: where the AALog comes from
    try:
        from .cmologs import CmoLogs
        logs = CmoLogs(cfg)
        checks.append(Check("cmo_logs", "CMO Logs folder (AALog.txt)", logs.available(),
                            logs.describe(), warn=True))
    except Exception as ex:
        checks.append(Check("cmo_logs", "CMO Logs folder (AALog.txt)", False,
                            "probe failed: {}".format(ex), warn=True))

    # play modes: the layout profile, the side names and the hotseat pairing
    if mode in ("player_vs_llm", "llm_vs_llm", "pbem_h2h", "normal"):
        prof_name = cfg.get("layouts.active", "play")
        prof = cfg.profiles.get(prof_name) or cfg.profiles.get("play")
        need = {"cmo", "cmo_lua", "conn"}
        if mode in ("player_vs_llm", "llm_vs_llm"):
            need.add("llm")
        have = set((prof or {}).get("windows", {}).keys())
        lacking = sorted(need - have)
        checks.append(Check(
            "layout_profile", "Layout profile covers this mode's windows",
            prof is not None and not lacking,
            ("profile {} lacks {}".format(prof_name, ", ".join(lacking)) if lacking
             else "profile {} has {}".format(prof_name, ", ".join(sorted(have))))
            if prof else "no profile named {}".format(prof_name),
            warn=True))
        my, op = cfg.get("play.my_side", ""), cfg.get("play.opponent_side", "")
        placeholder = {"", "Blue", "Red"}
        checks.append(Check(
            "play_sides", "Side names set to the scenario's sides",
            my not in placeholder and op not in placeholder and my != op,
            "my_side={!r} opponent_side={!r}; use the exact side names from the "
            "scenario".format(my, op), warn=True))
        if mode in ("player_vs_llm", "llm_vs_llm") and cfg.get("play.ike_hotseat", False):
            tl = int(cfg.get("play.turn_length_minutes", 0) or 0)
            checks.append(Check(
                "ike_hotseat", "IKE hotseat turn length set",
                tl > 0,
                "turn_length_minutes={} must match the IKE turn length; CONN waits "
                "that long after the LLM's orders".format(tl), warn=True))

    # the six cycle anchors, named as steps so a miss is obvious
    from .engine import CYCLE_STEPS
    missing = [(n, a) for n, a, _d in CYCLE_STEPS if resolver.status(a) != "ok"]
    checks.append(Check(
        "cycle_anchors", "Cycle anchors (steps 1-6)", not missing,
        ("not usable: " + ", ".join("step {} {}".format(n, a) for n, a in missing))
        if missing else "all six resolve",
        warn=(mode == "normal")))

    # attach route for oversized prompts
    method = str(cfg.get("io.attach_method", "ctrl_u")).lower()
    if method == "anchors":
        need = ["llm_attach_button", "llm_attach_menu"]
        bad = [n for n in need if resolver.status(n) != "ok"]
        checks.append(Check(
            "attach_anchors", "Attach sequence anchors", not bad,
            ("calibrate: " + ", ".join(bad)) if bad else "attach sequence ready",
            warn=True))
    else:
        checks.append(Check(
            "attach_route", "Oversized prompt route",
            True, "method: {} (no calibration needed)".format(method), warn=True))

    # rag index
    idx = Path(__file__).resolve().parent.parent / "rag_index" / "lookup_index.json"
    checks.append(Check("rag", "Local RAG index", idx.exists(),
                        str(idx) if idx.exists() else "will build on first use",
                        warn=True))
    return checks


def summarize(checks):
    fails = [c for c in checks if c.state == "fail"]
    warns = [c for c in checks if c.state == "warn"]
    return {"ok": not fails, "fail": len(fails), "warn": len(warns),
            "total": len(checks),
            "blockers": [c.label for c in fails]}
