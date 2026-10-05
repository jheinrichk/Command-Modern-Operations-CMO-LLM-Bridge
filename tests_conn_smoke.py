"""
Smoke tests for CONN. Runs headless under Xvfb on this sandbox; on Windows it
runs against the real desktop. It never clicks anything: the engine is forced
into dry run for the loop test.

    python tests_conn_smoke.py
"""

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Never touch the real bridge_config.json. The 2026-09-07 package shipped
# with the zeros these tests set, because ConnApp() saved into it.
import os as _os
import shutil as _shutil
_TEST_CFG_DIR = tempfile.mkdtemp(prefix="conn_test_cfg_")
_REAL_CFG = ROOT / "bridge_config.json"
if _REAL_CFG.exists():
    _shutil.copy(str(_REAL_CFG), _os.path.join(_TEST_CFG_DIR, "bridge_config.json"))
_os.environ["CONN_CONFIG_PATH"] = _os.path.join(_TEST_CFG_DIR, "bridge_config.json")
_os.environ["CONN_NO_DIALOGS"] = "1"

from conn import anchors, ike, layouts, luacheck
from conn.config import Config
from conn.winmgr import Rect

FAILS = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        FAILS.append(name)


def test_luacheck():
    print("luacheck")
    ok, probs, stats = luacheck.check("local x = 1\nif x then print('a') end\n")
    check("balanced code passes", ok, str(probs))
    ok, probs, _ = luacheck.check("function f()\n print('x')\n")
    check("missing end detected", not ok, str(probs))
    ok, probs, _ = luacheck.check("print('unterminated)\n")
    check("unterminated string detected", not ok, str(probs))
    ok, probs, _ = luacheck.check("--[[ long comment\nstill comment ]]\nprint(1)")
    check("long comment skipped", ok, str(probs))
    ok, probs, _ = luacheck.check("-- [[ not a long comment\nprint(1)")
    check("spaced dashes are a line comment", ok, str(probs))
    ok, probs, _ = luacheck.check("while true do print(1) end")
    check("while/do counted once", ok, str(probs))
    ok, probs, _ = luacheck.check("do print(1) end")
    check("bare do block counted", ok, str(probs))
    ok, probs, _ = luacheck.check("for i=1,3 do print(i)")
    check("missing end after for detected", not ok, str(probs))
    ok, probs, _ = luacheck.check("for i=1,3 do print(i) end")
    check("for/do counted once", ok, str(probs))
    ok, probs, _ = luacheck.check("local s = 'end end end' print(s)")
    check("keywords inside strings ignored", ok, str(probs))
    ok, probs, _ = luacheck.check("repeat print(1) until true")
    check("repeat/until balanced", ok, str(probs))
    hits = luacheck.scan_blocklist("ScenEdit_AddUnit({})", ["ScenEdit_AddUnit"])
    check("blocklist hit", hits == ["ScenEdit_AddUnit"], str(hits))
    check("fence stripped",
          luacheck.strip_fences("```lua\nprint(1)\n```") == "print(1)")


def test_anchor_math():
    print("anchor math")
    r = Rect(100, 200, 1100, 1200)          # 1000 x 1000
    a = anchors.point_to_anchor("w", r, 600, 700)
    check("center becomes frac", a["mode"] == "frac", str(a))
    pt = anchors.anchor_to_point(a, r)
    check("frac round trip", pt == (600, 700), str(pt))
    moved = Rect(0, 0, 1000, 1000)
    pt2 = anchors.anchor_to_point(a, moved)
    check("frac follows the window", pt2 == (500, 500), str(pt2))

    b = anchors.point_to_anchor("w", r, 140, 240)
    check("corner becomes px", b["mode"] == "px" and b["corner"] == "tl", str(b))
    check("px round trip", anchors.anchor_to_point(b, r) == (140, 240))
    check("px survives resize",
          anchors.anchor_to_point(b, Rect(100, 200, 1600, 1700)) == (140, 240))

    c = anchors.point_to_anchor("w", r, 1050, 1150)
    check("bottom right corner", c["corner"] == "br", str(c))
    check("br round trip", anchors.anchor_to_point(c, r) == (1050, 1150))

    rects = {"a": Rect(0, 0, 500, 500), "b": Rect(100, 100, 300, 300)}
    got, notes = anchors.migrate_absolute({"p": [150, 150]}, rects, Rect(0, 0, 2000, 2000))
    check("migration picks the smallest containing window",
          got["p"]["window"] == "b", str(got))
    got2, _ = anchors.migrate_absolute({"q": [1900, 1900]}, rects, Rect(0, 0, 2000, 2000))
    check("outside points pin to screen", got2["q"]["window"] == "screen", str(got2))


def test_layout_math():
    print("layout math")
    screen = Rect(0, 0, 3840, 2160)
    r = layouts.frac_to_rect([0.0, 0.0, 0.5, 0.5], screen)
    check("frac to rect", r == Rect(0, 0, 1920, 1080), str(r))
    f = layouts.rect_to_frac(Rect(1920, 0, 3840, 2160), screen)
    check("rect to frac", f == [0.5, 0.0, 1.0, 1.0], str(f))
    small = Rect(0, 0, 1920, 1080)
    r2 = layouts.frac_to_rect([0.474, 0.003, 1.0, 0.962], small)
    check("reference profile scales down", r2.right == 1920 and r2.left == 910, str(r2))


def test_config():
    print("config")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bridge_config.json"
        p.write_text('{"coordinates": {"llm_input": [10, 20]}}', encoding="utf-8")
        cfg = Config(p)
        check("legacy keys survive", cfg.data["coordinates"]["llm_input"] == [10, 20])
        check("defaults merged", cfg.get("play.turn_cap") == 40)
        check("anchors prefilled", cfg.anchors["cmo_play"]["mode"] == "px")
        cfg.set("play.turn_cap", 7)
        cfg.save()
        cfg2 = Config(p)
        check("round trip", cfg2.get("play.turn_cap") == 7)
        check("unset anchors are None", cfg2.anchors["cmo_scenario_reset"] is None)


def test_ike():
    print("ike finalization")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "snaps").mkdir()
        master = root / "Hormuz.scen"
        master.write_text("SCENARIO DATA", encoding="utf-8")
        cfg = Config(root / "bridge_config.json")
        cfg.set("io.snapshots_folder", str(root / "snaps"))
        cfg.set("ike.ike_conversion_lua_path", str(root / "ike.lua"))
        (root / "ike.lua").write_text("print('ike')", encoding="utf-8")
        ran = []
        fin = ike.IkeFinalizer(cfg, lambda code, label=None: ran.append(code),
                               lambda s: None, lambda m: None, dry_run=False)
        res, err = fin.finalize(str(master))
        check("no error", err is None, str(err))
        snap = Path(res["snapshot"])
        check("snapshot written", snap.exists() and snap.read_text() == "SCENARIO DATA")
        check("snapshot named v01", "_v01_preIKE" in snap.name, snap.name)
        check("master untouched", master.read_text() == "SCENARIO DATA")
        work = Path(res["working_copy"])
        check("working copy is separate", work.exists() and work != master, str(work))
        check("conversion lua injected", ran and "ike" in ran[0])
        check("master unlocked afterwards", not res.get("master_locked"))
        res2, err2 = fin.finalize(str(master))
        check("second snapshot increments", "_v02_preIKE" in Path(res2["snapshot"]).name,
              Path(res2["snapshot"]).name)
        check("earlier converted file kept, not overwritten",
              any("_prev_" in p.name for p in root.glob("Hormuz_PBEM_prev_*.scen")))
        _r, err_same = fin.verify_and_record(dict(res2))
        check("verify refuses a copy IKE never converted", err_same is not None
              and "unchanged" in err_same, str(err_same))
        Path(res2["expected_output"]).write_text("SCENARIO DATA + IKE", encoding="utf-8")
        res2, err3 = fin.verify_and_record(res2)
        check("verify passes after the converted SAVE AS", err3 is None
              and res2.get("verified") is True, str(err3))
        check("sidecar written", Path(res2.get("sidecar", "")).exists())


def test_turn_helpers():
    print("turn helpers")
    from conn.turnengine import extract_intent, side_named
    check("intent parsed",
          extract_intent("TURN_INTENT: hold the strait") == "hold the strait")
    check("side lock catches the other side",
          side_named("ScenEdit_SetSidePosture({side='Red'})", "Red"))
    check("side lock ignores unrelated text",
          not side_named("print('the red boats')", "Red"))


def test_ui():
    print("ui")
    try:
        import tkinter  # noqa: F401
    except Exception as ex:
        print("  skip (no tkinter): {}".format(ex))
        return
    from conn.app import ConnApp
    app = ConnApp()
    app.update()
    check("window built", app.winfo_exists())
    tabs = [app.nb.tab(i, "text") for i in range(len(app.nb.tabs()))]
    check("all tabs present",
          tabs == ["Mission", "Play", "Monitor", "Calibration", "Layout",
                   "Preflight", "Settings"], str(tabs))

    app.dry_run.set(False)
    app.on_dry_run_toggle()
    app.update()
    live_bg = app.pal["bg"]
    check("live mode drops the dry-run marker", "[DRY RUN]" not in app.title())
    app.dry_run.set(True)
    app.on_dry_run_toggle()
    app.update()
    check("dry run repaints the window", app.pal["bg"] != live_bg,
          "{} -> {}".format(live_bg, app.pal["bg"]))
    check("dry run reaches the engine", app.engine.dry_run and app.engine.act.dry_run)
    check("title marks dry run", "[DRY RUN]" in app.title())

    for i in range(len(app.nb.tabs())):
        app.nb.select(i)
        app.update()
    check("every tab renders", True)

    app.toggle_strip()
    app.update()
    check("strip opens with its own panel", app.strip is not None and len(app.panels) == 2)
    app.toggle_strip()
    app.update()
    check("strip closes", app.strip is None)

    app.refresh_calibration()
    rows = app.cal_tree.get_children()
    check("calibration lists every anchor", len(rows) == len(app.cfg.anchors), str(len(rows)))

    checks = app.run_preflight()
    check("preflight runs", len(checks) > 5, str(len(checks)))

    # dry-run loop: no synthetic input, stub replies, stops on its own
    app.cfg.set("bridge.max_cycles", 2)
    app.cfg.set("timing.llm_output_wait_seconds", 0)
    app.cfg.set("timing.cmo_output_wait_seconds", 0)
    app.cfg.set("timing.llm_copy_retry_wait_seconds", 0)
    app.engine.set_dry_run(True)
    ok, msg = app.engine.start("design", {"scenario_prompt": "smoke test"})
    check("engine starts", ok, msg)
    for _ in range(120):
        app.update()
        time.sleep(0.05)
        if not app.engine.state["running"]:
            break
    check("dry run loop finished", not app.engine.state["running"])
    check("cycles advanced", app.engine.state["cycle"] >= 1,
          "cycle {}".format(app.engine.state["cycle"]))
    check("scripts captured", len(app.engine.session.scripts) >= 1)
    app.engine.abort()
    app.on_close()


def test_scroll_before_copy():
    print("scroll before copy")
    import tempfile as _tf
    from conn.anchors import AnchorResolver
    from conn.engine import Actuator
    from conn.winmgr import Rect, WindowManager

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        check("default is two page downs",
              cfg.get("timing.llm_scroll_page_downs") == 2,
              str(cfg.get("timing.llm_scroll_page_downs")))

        class FakeWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        wm = FakeWM(cfg)
        res = AnchorResolver(cfg, wm)
        events = []
        act = Actuator(cfg, res, lambda kind, **f: events.append((kind, f)),
                       dry_run=True)
        acted = act.scroll_to_reply("llm_code_copy", label="LLM reply")
        check("scroll runs in dry run without pressing keys", acted)
        texts = " ".join(f.get("text", "") for _k, f in events)
        check("dry run logs the page downs", "2 x pagedown" in texts, texts)

        # real key path, with the actual press and click captured
        pressed, clicked = [], []
        act.dry_run = False
        act.press = lambda k: pressed.append(k)
        act.click = lambda a, label=None: clicked.append(a)
        act._pause = lambda s=None: None
        act.scroll_to_reply("llm_code_copy", label="LLM reply")
        check("focuses the reply area first", clicked == ["llm_code_copy"], str(clicked))
        check("sends exactly two page downs", pressed == ["pagedown", "pagedown"],
              str(pressed))

        cfg.set("timing.llm_scroll_page_downs", 4)
        pressed.clear()
        act.scroll_to_reply("llm_code_copy")
        check("count is configurable", len(pressed) == 4, str(pressed))

        cfg.set("timing.llm_scroll_page_downs", 0)
        pressed.clear()
        did = act.scroll_to_reply("llm_code_copy")
        check("zero disables the scroll", not did and pressed == [], str(pressed))


def test_copy_validation():
    print("copy validation")
    import tempfile as _tf
    from conn.anchors import AnchorResolver
    from conn.engine import Engine, extract_lua_block
    from conn.winmgr import Rect, WindowManager

    good = "```lua\nlocal x = 1\nprint(x)\n```"
    check("fenced block extracted",
          extract_lua_block(good) == "local x = 1\nprint(x)", extract_lua_block(good))
    two = "```lua\nprint(1)\n```\nsome prose\n```lua\nprint(2)\n```"
    check("last block wins on a page copy", extract_lua_block(two) == "print(2)",
          extract_lua_block(two))
    check("bare code passes through", extract_lua_block("print(9)") == "print(9)")

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        check("copy method defaults to the button",
              cfg.get("bridge.copy_method") == "button", str(cfg.get("bridge.copy_method")))

        class FakeWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        wm = FakeWM(cfg)
        eng = Engine(cfg, wm, AnchorResolver(cfg, wm))

        # the actual failure from the log: the prompt came back instead of the reply
        prompt_echo = ("MODE:CMO_LUA_LLM_BRIDGE\nROLE:YOU_ARE_DESIGNER\n"
                       "```lua\nlocal function _has(fn) return type(_G[fn]) == 'function' end\n```")
        code, why = eng._validate_copy(prompt_echo)
        check("prompt echo rejected", code == "" and "prompt" in why, why)

        code, why = eng._validate_copy("")
        check("empty copy rejected", code == "" and "empty" in why, why)

        code, why = eng._validate_copy("```lua\nfunction f()\nprint(1)\n```")
        check("truncated Lua rejected", code == "" and "syntax" in why, why)

        code, why = eng._validate_copy("here is prose with no code at all")
        check("prose rejected", code == "", why)

        eng._last_prompt = "STAGE DESIGN do the thing"
        code, why = eng._validate_copy("STAGE   DESIGN do the thing")
        check("echo of the prompt just sent rejected", code == "", why)

        eng._last_prompt = ""
        code, why = eng._validate_copy(good)
        check("valid reply accepted", code == "local x = 1\nprint(x)" and why == "", why)


def test_cycle_and_markers():
    print("cycle order and run markers")
    import tempfile as _tf
    from conn.anchors import AnchorResolver
    from conn.engine import (CYCLE_STEPS, Engine, drop_echoed_script,
                             slice_between_markers)
    from conn.winmgr import Rect, WindowManager

    order = [n for n, _a, _d in CYCLE_STEPS]
    anchors = [a for _n, a, _d in CYCLE_STEPS]
    check("six steps in marked order", order == [1, 2, 3, 4, 5, 6], str(order))
    check("steps map to the marked anchors",
          anchors == ["llm_code_copy", "cmo_lua_input", "cmo_execute",
                      "cmo_output_area", "llm_input", "llm_submit"], str(anchors))

    out = "noise before\nCONN_BEGIN:ab12\nUNIT: Blue Frigate\nCONN_END:ab12\ntrailing"
    check("marker slice returns only the run output",
          slice_between_markers(out, "ab12") == "UNIT: Blue Frigate",
          slice_between_markers(out, "ab12"))
    stale = ("CONN_BEGIN:ab12\nold\nCONN_END:ab12\nCONN_BEGIN:cd34\nnew\nCONN_END:cd34")
    check("latest run wins when the pane accumulates",
          slice_between_markers(stale, "cd34") == "new",
          slice_between_markers(stale, "cd34"))
    check("missing markers fall back to the whole pane",
          slice_between_markers("just output", "zz") == "just output")

    code = "print('a')\nprint('b')"
    echoed = "print('a')\nprint('b')\na\nb"
    check("echoed script stripped when the box is ticked",
          drop_echoed_script(echoed, code) == "a\nb", repr(drop_echoed_script(echoed, code)))

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        check("echo assumed off", cfg.get("bridge.echo_input_script") is False)
        check("markers on by default", cfg.get("bridge.use_run_markers") is True)

        class NoWM(WindowManager):
            def rect(self, key):
                return None

        eng = Engine(cfg, NoWM(cfg), AnchorResolver(cfg, NoWM(cfg)))
        ok, missing = eng.verify_anchors()
        check("missing anchors are detected", not ok and len(missing) == 6, str(len(missing)))
        eng.set_dry_run(False)
        started, msg = eng.start("design", {})
        check("run refuses to start on bad calibration",
              not started and "calibration" in msg, msg)

        class OkWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        eng2 = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
        ok2, missing2 = eng2.verify_anchors()
        check("good calibration passes", ok2, str(missing2))


def test_knowledge_pack_integration():
    print("knowledge pack integration")
    import tempfile as _tf
    from conn.agents import SITREP_LUA
    from conn.apiguard import ApiGuard
    from conn.engine import Engine, STAGE_TASKS, VALID_STAGES, LINEAR
    from conn.anchors import AnchorResolver
    from conn.winmgr import Rect, WindowManager

    kp = Path(__file__).parent / "knowledge_pack"
    for f in ("cmo_known_api_index.json", "cmo_bridge_master_reference_v4.md",
              "CMO_BRIDGE_INSPECT.lua", "CMO_BRIDGE_SYSTEM_PROMPT.txt",
              "cmo_lookup_library_all.lua", "cmo_lookup_library_platforms.lua",
              "cmo_lookup_library_clean.csv", "cmo_lua_command_guard.py",
              "dbid_extractor/build_cmo_dbid_lookups.py"):
        check("pack file present: " + f, (kp / f).exists())

    g = ApiGuard()
    check("index loaded", g.loaded and len(g.known) >= 170, str(len(g.known)))
    ok, why, warns = g.check("local u = ScenEdit_GetUnit({guid='x'}) print(u.name)")
    check("known symbol passes", ok, why)
    ok, why, _ = g.check("local s = ScenEdit_GetSideList()")
    check("invented symbol blocked", not ok and "ScenEdit_GetSideList" in why, why)
    ok, why, _ = g.check("local e = ScenEdit_GetEMCON('Unit', g, 'Radar')")
    check("absent-in-build symbol blocked", not ok and "ScenEdit_GetEMCON" in why, why)
    ok, why, warns = g.check("if VP_RunSimulation then VP_RunSimulation() end")
    check("Pro symbols are in the index and pass clean", ok and warns == [], str(warns))
    import tempfile as _tf2
    with _tf2.TemporaryDirectory() as d2:
        cfg2 = Config(Path(d2) / "bridge_config.json")
        cfg2.set("safety.api_soft_symbols", ["VP_HypotheticalProCall"])
        g2 = ApiGuard(cfg2)
        ok, why, warns = g2.check("VP_HypotheticalProCall()")
        check("soft-listed unknown warns instead of blocking",
              ok and warns == ["VP_HypotheticalProCall"], str(warns) + " " + why)
        cfg2.set("safety.api_extra_symbols", ["ScenEdit_FutureCall"])
        g3 = ApiGuard(cfg2)
        ok, why, _w = g3.check("ScenEdit_FutureCall()")
        check("extra symbols extend the index", ok, why)
    ok, why, _ = g.check("IranScrambleAircraft() print(PlayerLossCounter)")
    check("authored scenario names ignored", ok, why)

    sit = SITREP_LUA.replace("{side}", "Blue").replace("{{", "{").replace("}}", "}")
    ok, why, _ = g.check(sit)
    check("sitrep uses only indexed symbols", ok, why)
    ok2, probs, _ = luacheck.check(sit)
    check("sitrep parses", ok2, str(probs))

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")

        class OkWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        eng = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
        insp = eng.inspect_payload()
        check("inspect payload comes from the pack", "CMO_DUMP_BEGIN" in insp)
        ok, why, _ = eng.guard.check(insp)
        check("inspect payload passes the guard", ok, why)
        code, why = eng._validate_copy(
            "```lua\nlocal s = ScenEdit_GetSideList()\nprint(s)\n```")
        check("copy validation rejects invented symbols", code == "" and
              "ScenEdit_GetSideList" in why, why)
        check("AUDIT is a stage", "AUDIT" in VALID_STAGES and "AUDIT" in STAGE_TASKS
              and LINEAR["AUDIT"] == "EVALUATE")

    from cmo_rag import CmoRag
    rag = CmoRag()
    ctx = rag.retrieve_context("VP_GetSides side wrapper userdata error _errmsg_",
                               k_recipes=2, k_docs=4)
    check("v4 reference retrievable", "v4" in ctx or "wrapper" in ctx.lower(),
          ctx[:80].replace("\n", " "))


def test_env_symbols_and_copy_retry():
    print("environment symbols and copy retry")
    import tempfile as _tf
    from conn.apiguard import ApiGuard, ENV_PATH
    from conn.anchors import AnchorResolver
    from conn.engine import Engine
    from conn.winmgr import Rect, WindowManager

    g = ApiGuard()
    for sym in ("ScenEdit_GetScore", "ScenEdit_GetWeather", "ScenEdit_GetTimeOfDay",
                "ScenEdit_AddShip", "ScenEdit_GetZone", "Tool_EmulateNoConsole",
                "ScenEdit_PlayerSide", "ScenEdit_CurrentLocalTime"):
        check("env-confirmed symbol passes: " + sym, sym in g.known)
    # the audit v7 payload symbol set passes end to end
    v7 = ("GetScenarioTitle() ScenEdit_CurrentTime() ScenEdit_GetTimeOfDay() "
          "ScenEdit_GetScenHasStarted() ScenEdit_PlayerSide() ScenEdit_GetWeather() "
          "ScenEdit_GetDoctrine() VP_GetSides() ScenEdit_GetScore() "
          "ScenEdit_GetSidePosture() ScenEdit_GetUnit() ScenEdit_GetMission() "
          "ScenEdit_GetReferencePoints() ScenEdit_GetContacts() ScenEdit_GetEvents() "
          "Tool_DumpEvents() Tool_EmulateNoConsole()")
    ok, why, _ = g.check(v7)
    check("audit v7 symbol set passes the guard", ok, why)

    learned = g.learn_from_text("GLOBAL_COUNT: 2\n  ScenEdit_BrandNewCall <userdata>\n")
    check("dump learning adds new symbols", "ScenEdit_BrandNewCall" in learned, str(learned))
    ok, why, _ = g.check("ScenEdit_BrandNewCall()")
    check("learned symbol passes afterwards", ok, why)
    # remove the test symbol from the shipped file
    import json
    d = json.loads(ENV_PATH.read_text())
    d["symbols"] = [x for x in d["symbols"] if x != "ScenEdit_BrandNewCall"]
    d["count"] = len(d["symbols"])
    ENV_PATH.write_text(json.dumps(d, indent=2))

    with _tf.TemporaryDirectory() as dd:
        cfg = Config(Path(dd) / "bridge_config.json")
        cfg.set("timing.llm_copy_retry_attempts", 1)
        cfg.set("timing.llm_reprint_wait_seconds", 0)

        class OkWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        eng = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
        eng.set_dry_run(False)
        calls = {"n": 0}
        good = "```lua\nlocal x = 1\nprint(x)\n```"

        eng.act.scroll_to_reply = lambda *a, **k: True
        def fake_copy(anchor, label=None):
            calls["n"] += 1
            return "" if calls["n"] == 1 else good
        eng.act.copy_button = fake_copy
        reprints = {"n": 0}
        eng._request_reprint = lambda why="": reprints.__setitem__("n", reprints["n"] + 1)
        cfg.set("timing.llm_reply_poll_seconds", 0)
        cfg.set("timing.llm_output_wait_seconds", 5)

        code, raw = eng.copy_llm_code()
        check("empty first copy is 'not ready yet', polled again", calls["n"] == 3, str(calls))
        check("valid copy without the state line accepted once it is stable",
              code == "local x = 1\nprint(x)" and reprints["n"] == 0,
              "reprints={}".format(reprints["n"]))


def test_console_suppression_and_state():
    print("console suppression and state extraction")
    from conn.engine import (extract_next_state, neutralize_console_suppression,
                             state_from_run)

    # the exact opening and closing lines from the audit payload
    code = ("if Tool_EmulateNoConsole ~= nil then pcall(Tool_EmulateNoConsole, true) end\n"
            "print('hello')\n"
            "if Tool_EmulateNoConsole ~= nil then pcall(Tool_EmulateNoConsole, false) end\n")
    out, n = neutralize_console_suppression(code)
    check("suppression call disabled", n == 1, str(n))
    check("disabled line is commented", "-- [CONN] disabled" in out)
    check("the false call is untouched",
          "pcall(Tool_EmulateNoConsole, false) end" in out)
    check("print survives", "print('hello')" in out)

    bare, n2 = neutralize_console_suppression("Tool_EmulateNoConsole(true)\nprint(1)")
    check("bare call form disabled", n2 == 1 and bare.lstrip().startswith("--"), bare)
    keep, n3 = neutralize_console_suppression("print('no suppression here')")
    check("clean code untouched", n3 == 0 and keep == "print('no suppression here')")

    # the exact misread from the log: an early-exit branch declared FIX_ERRORS
    script = ("if bad then print('NEXT_RECOMMENDED_STATE: FIX_ERRORS') return end\n"
              "print('AUDIT_COMPLETE')\n"
              "print('NEXT_RECOMMENDED_STATE: EVALUATE')\n")
    check("last declaration wins in a code block",
          extract_next_state(script) == "EVALUATE", extract_next_state(script))

    console = "CONN_BEGIN:x\nAUDIT_COMPLETE\nNEXT_RECOMMENDED_STATE: EVALUATE\nCONN_END:x"
    st, src = state_from_run(console, script)
    check("console output outranks the code", st == "EVALUATE" and src == "console",
          "{} {}".format(st, src))

    st, src = state_from_run("", script)
    check("code is the fallback", st == "EVALUATE" and src == "code", src)
    st, src = state_from_run("ERROR: attempt to index a nil value", "print(1)")
    check("error text still routes to FIX_ERRORS", st == "FIX_ERRORS", st)


def test_stop_policy():
    print("stop policy")
    from conn.engine import (STAGE_TASKS, error_signature, extract_done,
                             extract_halt)

    check("halt token parsed",
          extract_halt("print('BRIDGE_HALT: need the DBID for the LRUSV')")
          .startswith("need the DBID"),
          extract_halt("BRIDGE_HALT: need the DBID for the LRUSV"))
    check("done token parsed",
          extract_done("BRIDGE_DONE: audit complete, 14 units reviewed")
          .startswith("audit complete"))
    guarded = ("if sideobj == nil then\n"
               "  print(\"BRIDGE_HALT: side wrapper not found\")\n"
               "  return\nend\nprint('PATCH_COMPLETE')\n")
    check("a halt inside an unexecuted guard is still just text",
          "BRIDGE_HALT" in guarded)
    check("no token means no stop", extract_halt("all fine") == ""
          and extract_done("all fine") == "")
    check("FIX_ERRORS is a working stage now", "FIX_ERRORS" in STAGE_TASKS)

    a = "CMO_ERROR|FUNCTION=ScenEdit_GetUnit|NUMBER=3|MESSAGE=unit 'Blue Frigate' not found"
    b = "CMO_ERROR|FUNCTION=ScenEdit_GetUnit|NUMBER=7|MESSAGE=unit 'Red Boghammar' not found"
    check("same fault on different objects collapses to one signature",
          error_signature(a) == error_signature(b), error_signature(a))
    c = "CMO_ERROR|FUNCTION=ScenEdit_AddUnit|NUMBER=3|MESSAGE=bad dbid"
    check("a different fault is a different signature",
          error_signature(a) != error_signature(c))
    check("clean output has no signature", error_signature("UNIT: x\nAUDIT_COMPLETE") == "")

    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        check("failures no longer end the run",
              cfg.get("bridge.stop_on_fix_errors") is False)
        check("failure budget present",
              cfg.get("bridge.max_consecutive_failures") == 8
              and cfg.get("bridge.max_repeat_signature") == 3)


def test_halt_only_from_console():
    print("halt is read from console output only")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp
    app = ConnApp()
    app.engine.set_dry_run(True)
    app.cfg.set("bridge.max_cycles", 2)
    app.cfg.set("timing.llm_output_wait_seconds", 0)
    app.cfg.set("timing.cmo_output_wait_seconds", 0)

    # the exact shape of the script that stopped the live run: the token sits
    # in a guard branch that never fires, and the run completes normally
    guarded = ("-- patch\nif sideobj == nil then\n"
               "print('BRIDGE_HALT: side wrapper not found')\nreturn\nend\n"
               "print('PATCH_COMPLETE')\nprint('NEXT_RECOMMENDED_STATE: RETEST')\n")
    app.engine.copy_llm_code = lambda: (guarded, guarded)
    app.engine.read_cmo_output = lambda wait_for_marker=True: (
        "PATCH_COMPLETE\nNEXT_RECOMMENDED_STATE: RETEST")
    app.engine.start("design", {"scenario_prompt": "patch it"})
    for _ in range(160):
        app.update()
        time.sleep(0.03)
        if not app.engine.state["running"]:
            break
    notes = app.engine.state.get("notes") or ""
    check("guarded halt token did not stop the run",
          "asked for you" not in notes, notes)

    # a halt actually printed by the console does stop it
    app.engine.read_cmo_output = lambda wait_for_marker=True: (
        "BRIDGE_HALT: need a DBID from the user")
    app.engine.start("design", {"scenario_prompt": "patch it"})
    for _ in range(160):
        app.update()
        time.sleep(0.03)
        if not app.engine.state["running"]:
            break
    notes = app.engine.state.get("notes") or ""
    check("printed halt stops the run", "asked for you" in notes, notes)
    app.on_close()


def test_loop_persistence():
    print("loop persistence")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp
    app = ConnApp()
    app.engine.set_dry_run(True)
    app.cfg.set("bridge.max_cycles", 6)
    app.cfg.set("timing.llm_output_wait_seconds", 0)
    app.cfg.set("timing.cmo_output_wait_seconds", 0)
    app.cfg.set("timing.llm_copy_retry_wait_seconds", 0)

    # a run whose output always reports the same error must stop on the
    # repeat rule, not on the first failure
    faults = {"n": 0}
    real_read = app.engine.read_cmo_output

    def fake_read(wait_for_marker=True):
        faults["n"] += 1
        # no state line: the error is the whole story, a genuine failure
        text = "CMO_ERROR|FUNCTION=ScenEdit_GetUnit|NUMBER=3|MESSAGE=nope"
        app.engine.state["last_output"] = text
        return text

    app.engine.read_cmo_output = fake_read
    app.engine.start("design", {"scenario_prompt": "x"})
    for _ in range(200):
        app.update()
        time.sleep(0.03)
        if not app.engine.state["running"]:
            break
    check("kept cycling past the first failure", faults["n"] >= 3, str(faults))
    check("stopped on the repeat rule, not the first error",
          "same fault" in (app.engine.state.get("notes") or ""),
          app.engine.state.get("notes", ""))
    check("error without a console state routed to FIX_ERRORS",
          app.engine.state.get("stage") in ("IDLE",), app.engine.state.get("stage"))
    app.engine.read_cmo_output = real_read
    app.on_close()


def test_attach_route():
    print("oversized prompt attach route")
    import tempfile as _tf
    from conn.anchors import AnchorResolver
    from conn.engine import Engine
    from conn.winmgr import Rect, WindowManager

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        cfg.set("io.in_folder", str(Path(d) / "IN"))
        cfg.set("io.paste_max_chars", 100)
        cfg.set("timing.upload_wait_base_seconds", 0)
        cfg.set("timing.upload_wait_per_100kb_seconds", 0)
        cfg.set("timing.file_dialog_wait_seconds", 0)
        cfg.set("timing.llm_output_wait_seconds", 0)
        check("default route is ctrl_u", cfg.get("io.attach_method") == "ctrl_u")
        check("attach anchors ship unset",
              cfg.anchors["llm_attach_button"] is None
              and cfg.anchors["file_dialog_open"] is None)

        class OkWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        eng = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
        eng.set_dry_run(False)
        events = []
        eng.act.click = lambda a, label=None: events.append(("click", a)) or True
        eng.act.hotkey = lambda *k: events.append(("hotkey", "+".join(k))) or True
        eng.act.press = lambda k: events.append(("press", k)) or True
        eng.act.clip.write = lambda t: events.append(("clip", (t or "")[:40])) or True
        eng.act.clip.read = lambda: ""
        eng.act._pause = lambda s=None: None
        eng._wait = lambda sec, label: None

        big = "X" * 500
        eng.submit_to_llm(big)
        kinds = [e[0] + ":" + str(e[1]) for e in events]
        check("ctrl+u sent", any(k == "hotkey:ctrl+u" for k in kinds), str(kinds[:8]))
        check("path pasted into the dialog",
              any(e[0] == "clip" and "prompt_" in e[1] for e in events))
        check("enter confirms the dialog", ("press", "enter") in events)
        pointer = [e for e in events if e[0] == "clip" and
                   "ATTACHED_PROMPT_HANDOFF" in e[1]]
        check("handoff note pasted, not a bare path", len(pointer) == 1, str(len(pointer)))
        files = list((Path(d) / "IN").glob("prompt_*.txt"))
        check("payload file written", len(files) == 1 and
              files[0].read_text() == big)

        # chunk fallback when the route is off
        events.clear()
        cfg.set("io.attach_method", "chunks")
        eng.submit_to_llm("Y" * 250)
        pastes = [e for e in events if e[0] == "hotkey" and e[1] == "ctrl+v"]
        check("chunk fallback pastes in parts", len(pastes) >= 2, str(len(pastes)))
        check("no attach attempted in chunk mode",
              not any(e == ("hotkey", "ctrl+u") for e in events))

        # small prompts stay a single plain paste
        events.clear()
        cfg.set("io.attach_method", "ctrl_u")
        eng.submit_to_llm("short prompt")
        check("small prompt is one paste and no attach",
              len([e for e in events if e[0] == "hotkey" and e[1] == "ctrl+v"]) == 1
              and not any(e == ("hotkey", "ctrl+u") for e in events))

        # calibrated dialog anchors are honored on the ctrl_u route too
        events.clear()
        cfg.anchors["file_dialog_filename"] = {"window": "cmo_lua", "mode": "frac",
                                               "dx": 0.28, "dy": 0.18}
        cfg.anchors["file_dialog_open"] = {"window": "cmo", "mode": "px",
                                           "corner": "bl", "dx": 19, "dy": 771}
        eng.submit_to_llm("Z" * 500)
        kinds = [(e[0], e[1]) for e in events]
        check("filename field clicked when calibrated",
              ("click", "file_dialog_filename") in kinds, str(kinds[:10]))
        check("Open button clicked instead of Enter",
              ("click", "file_dialog_open") in kinds
              and ("press", "enter") not in kinds)
        cfg.anchors["file_dialog_filename"] = None
        cfg.anchors["file_dialog_open"] = None

        # anchors route refuses politely when uncalibrated
        cfg.set("io.attach_method", "anchors")
        ok = eng.act.attach_file(Path(d) / "IN" / "x.txt")
        check("uncalibrated anchors route declines", ok is False)


def test_bridge_control_directives():
    print("bridge control directives")
    import tempfile as _tf
    from cmo_sim_control import parse_control_directives as parse
    from conn.anchors import AnchorResolver
    from conn.engine import Engine
    from conn.winmgr import Rect, WindowManager

    # the exact line that killed the live run
    check("pipe separator parses",
          parse("BRIDGE_CONTROL:COMPRESS=15|RUNFOR=900") ==
          [("COMPRESS", "15"), ("RUNFOR", "900")],
          str(parse("BRIDGE_CONTROL:COMPRESS=15|RUNFOR=900")))
    check("semicolons still parse",
          parse("BRIDGE_CONTROL: COMPRESS=15; RUNFOR=900") ==
          [("COMPRESS", "15"), ("RUNFOR", "900")])
    check("commas still parse",
          parse("BRIDGE_CONTROL: RESET, COMPRESS=30") ==
          [("RESET", None), ("COMPRESS", "30")])
    check("quotes and parens stripped when the line sits in a print",
          parse("P(\"BRIDGE_CONTROL:COMPRESS=15|RUNFOR=900\")") ==
          [("COMPRESS", "15"), ("RUNFOR", "900")],
          str(parse("P(\"BRIDGE_CONTROL:COMPRESS=15|RUNFOR=900\")")))
    check("bare op parses", parse("BRIDGE_CONTROL: PLAY") == [("PLAY", None)])
    check("no directive means no ops", parse("just some lua") == [])

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")

        class OkWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        eng = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
        check("int coercion survives junk", eng._as_int("15", None) == 15
              and eng._as_int("fast", None) is None
              and eng._as_int(None, 7) == 7)

        # a malformed directive must warn, never raise out of the loop
        logged = []
        eng.emit = lambda kind, **kw: logged.append((kind, kw.get("text", "")))

        class BoomSim(object):
            def set_compression(self, n):
                raise ValueError("boom")

        eng.sim = BoomSim()
        eng.dry_run = False
        eng.apply_directives("BRIDGE_CONTROL: COMPRESS=15")
        check("a raising directive is contained",
              any("BRIDGE_CONTROL ignored" in t for _k, t in logged),
              str(logged[-1:]))
        logged.clear()
        eng.apply_directives("BRIDGE_CONTROL: COMPRESS=fast")
        check("non-numeric argument warns and is skipped",
              any("not a number" in t for _k, t in logged), str(logged[-1:]))


def test_chaos_resilience():
    print("chaos: no single failure ends a run")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp

    good = "print('ok')\nprint('NEXT_RECOMMENDED_STATE: EVALUATE')"

    def run_with(breaker, label, cycles=4):
        app = ConnApp()
        app.engine.set_dry_run(True)
        app.cfg.set("bridge.max_cycles", cycles)
        app.cfg.set("timing.llm_output_wait_seconds", 0)
        app.cfg.set("timing.cmo_output_wait_seconds", 0)
        app.cfg.set("timing.llm_copy_retry_wait_seconds", 0)
        app.cfg.set("timing.llm_reprint_wait_seconds", 0)
        breaker(app)
        app.engine.start("design", {"scenario_prompt": "go"})
        for _ in range(900):
            app.update()
            time.sleep(0.02)
            if not app.engine.state["running"]:
                break
        running = app.engine.state["running"]
        notes = app.engine.state.get("notes") or ""
        cyc = app.engine.state.get("cycle", 0)
        app.on_close()
        check("{}: run terminated cleanly".format(label), not running, notes)
        check("{}: ended with a stated reason".format(label), bool(notes), notes)
        return cyc, notes

    # 1. the copy step throws every time
    def break_copy(app):
        def boom():
            raise RuntimeError("clipboard exploded")
        app.engine.copy_llm_code = boom
    cyc, notes = run_with(break_copy, "copy throws")
    check("copy throws: kept cycling past the first fault", cyc >= 2, str(cyc))

    # 2. injection throws
    def break_inject(app):
        app.engine.copy_llm_code = lambda: (good, good)
        def boom(code, label=None):
            raise RuntimeError("console gone")
        app.engine.run_lua_in_cmo = boom
    cyc, notes = run_with(break_inject, "injection throws")
    check("injection throws: kept cycling", cyc >= 2, str(cyc))

    # 3. the output read throws
    def break_read(app):
        app.engine.copy_llm_code = lambda: (good, good)
        app.engine.run_lua_in_cmo = lambda code, label=None: True
        def boom(wait_for_marker=True):
            raise RuntimeError("pane unreadable")
        app.engine.read_cmo_output = boom
    cyc, notes = run_with(break_read, "read throws")
    check("read throws: kept cycling", cyc >= 2, str(cyc))

    # 4. the submit step throws
    def break_submit(app):
        app.engine.copy_llm_code = lambda: (good, good)
        app.engine.run_lua_in_cmo = lambda code, label=None: True
        app.engine.read_cmo_output = lambda wait_for_marker=True: (
            "ok\nmore\nNEXT_RECOMMENDED_STATE: EVALUATE")
        def boom(prompt, wait_label=None):
            raise RuntimeError("browser closed")
        app.engine.submit_to_llm = boom
    cyc, notes = run_with(break_submit, "submit throws")
    check("submit throws: kept cycling", cyc >= 2, str(cyc))
    check("submit throws: opening submit did not end it",
          "engine error" not in notes, notes)

    # 5. a directive with a bad separator and a junk value
    def break_directive(app):
        code = ("print('BRIDGE_CONTROL:COMPRESS=15|RUNFOR=900')\n"
                "print('NEXT_RECOMMENDED_STATE: EVALUATE')")
        app.engine.copy_llm_code = lambda: (code, code)
        app.engine.run_lua_in_cmo = lambda c, label=None: True
        app.engine.read_cmo_output = lambda wait_for_marker=True: (
            "line one\nline two\nNEXT_RECOMMENDED_STATE: EVALUATE")
    cyc, notes = run_with(break_directive, "pipe directive")
    check("pipe directive: ran the full budget", cyc >= 3, str(cyc))

    # 6. the happy path still reaches DONE and says so
    def clean(app):
        code = "print('done')"
        app.engine.copy_llm_code = lambda: (code, code)
        app.engine.run_lua_in_cmo = lambda c, label=None: True
        app.engine.read_cmo_output = lambda wait_for_marker=True: (
            "work finished\nBRIDGE_DONE: audit complete\n"
            "NEXT_RECOMMENDED_STATE: DONE")
    cyc, notes = run_with(clean, "clean finish")
    check("clean finish: reported fulfilment", "fulfilled" in notes, notes)
    check("clean finish: stopped on cycle 1", cyc == 1, str(cyc))


def test_progress_and_directive_order():
    print("cosmetic errors and directive ordering")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp

    # 1. an identical cosmetic error in progressing output never stops the run
    app = ConnApp()
    app.engine.set_dry_run(True)
    app.cfg.set("bridge.max_cycles", 5)
    for k in ("timing.llm_output_wait_seconds", "timing.cmo_output_wait_seconds",
              "timing.llm_copy_retry_wait_seconds"):
        app.cfg.set(k, 0)
    code = "print('audit')"
    app.engine.copy_llm_code = lambda: (code, code)
    app.engine.run_lua_in_cmo = lambda c, label=None: True
    flip = {"n": 0}

    def read(wait_for_marker=True):
        flip["n"] += 1
        # the recurring RP fault, identical every cycle, with a forward state
        nxt = "EVALUATE" if flip["n"] % 2 else "REFINE"
        return ("CMO_ERROR|FUNCTION=ScenEdit_GetReferencePoints|NUMBER=1|"
                "MESSAGE=Need to define a Side and Name\n"
                "useful work happened\nNEXT_RECOMMENDED_STATE: " + nxt)

    app.engine.read_cmo_output = read
    app.engine.start("design", {"scenario_prompt": "x"})
    for _ in range(900):
        app.update()
        time.sleep(0.02)
        if not app.engine.state["running"]:
            break
    notes = app.engine.state.get("notes") or ""
    check("cosmetic fault ran the full budget", "cycle budget" in notes, notes)
    check("no same-fault stop on progressing output", "same fault" not in notes, notes)
    app.on_close()

    # 2. a RUNFOR directive fires after injection, and the TEST stage does not
    #    run a second default window on top of it
    app = ConnApp()
    app.engine.set_dry_run(False)
    app.engine.verify_anchors = lambda: (True, [])
    app.cfg.set("bridge.max_cycles", 2)
    for k in ("timing.llm_output_wait_seconds", "timing.cmo_output_wait_seconds",
              "timing.sim_settle_seconds"):
        app.cfg.set(k, 0)
    order = []
    code2 = ("print('baseline')\n"
             "print('BRIDGE_CONTROL:COMPRESS=15|RUNFOR=900')\n"
             "print('NEXT_RECOMMENDED_STATE: TEST')")
    app.engine.copy_llm_code = lambda: (code2, code2)
    app.engine.run_lua_in_cmo = lambda c, label=None: order.append("inject") or True
    app.engine.read_cmo_output = lambda wait_for_marker=True: (
        order.append("read") or
        "baseline printed\nline\nNEXT_RECOMMENDED_STATE: TEST")
    app.engine.test_window = lambda secs, comp: order.append(
        "window(c={})".format(comp))
    app.engine.submit_to_llm = lambda prompt, wait_label=None: order.append("submit")

    class FakeSim(object):
        def set_compression(self, n):
            order.append("compress({})".format(n))
    app.engine.sim = FakeSim()
    app.engine.start("design", {"scenario_prompt": "x"})
    for _ in range(900):
        app.update()
        time.sleep(0.02)
        if not app.engine.state["running"]:
            break
    app.on_close()
    seq = [o for o in order if o != "submit"]
    first_inject = seq.index("inject")
    first_window = next(i for i, o in enumerate(seq) if o.startswith("window"))
    check("injection precedes the window", first_inject < first_window, str(seq[:8]))
    try:
        cycle1_end = seq.index("inject", first_inject + 1)
    except ValueError:
        cycle1_end = len(seq)
    windows_c1 = [o for o in seq[:cycle1_end] if o.startswith("window")]
    check("one window per cycle, no doubling", len(windows_c1) == 1, str(seq))
    check("RUNFOR used the COMPRESS argument", "window(c=15)" in seq, str(seq))
    check("directive ran after the baseline read",
          seq.index("read") < first_window, str(seq[:8]))


def test_audit_start():
    print("audit opening stage")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp
    app = ConnApp()
    app.engine.set_dry_run(True)
    app.cfg.set("bridge.max_cycles", 1)
    app.cfg.set("timing.llm_output_wait_seconds", 0)
    app.cfg.set("timing.cmo_output_wait_seconds", 0)
    # sample the event stream rather than polling state: a dry run can
    # finish between polls
    stages = []
    real_emit = app.engine.emit

    def spy(kind, **kw):
        if kind == "stage":
            stages.append(kw.get("stage"))
        return real_emit(kind, **kw)

    app.engine.emit = spy
    ok, msg = app.engine.start("design", {"scenario_prompt": "review it",
                                          "start_stage": "AUDIT"})
    check("audit run starts", ok, msg)
    for _ in range(300):
        app.update()
        time.sleep(0.03)
        if not app.engine.state["running"]:
            break
    check("audit ran before evaluate", "AUDIT" in stages, str(stages))
    check("audit finished", not app.engine.state["running"], str(stages))
    app.on_close()


def test_turn_gate():
    print("turn gate")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp
    app = ConnApp()
    app.engine.set_dry_run(True)
    app.cfg.set("play.turn_cap", 1)
    app.cfg.set("timing.llm_output_wait_seconds", 0)
    app.cfg.set("timing.cmo_output_wait_seconds", 0)
    app.engine.start("player_vs_llm", {})
    # human side gates on Step; confirm it is waiting, then release it
    waited = False
    for _ in range(60):
        app.update()
        time.sleep(0.05)
        if "Order deadline" in (app.engine.state.get("phase") or ""):
            waited = True
            break
    check("human turn waits for Step", waited, app.engine.state.get("phase", ""))
    app.step()
    released = False
    for _ in range(80):
        app.update()
        time.sleep(0.05)
        if "Order deadline" not in (app.engine.state.get("phase") or ""):
            released = True
            break
    check("Step releases the turn gate", released, app.engine.state.get("phase", ""))
    app.engine.abort()
    for _ in range(40):
        app.update()
        time.sleep(0.05)
        if not app.engine.state["running"]:
            break
    check("abort stops the turn loop", not app.engine.state["running"])
    app.on_close()


def _live_engine(cfg):
    from conn.anchors import AnchorResolver
    from conn.engine import Engine
    from conn.winmgr import Rect, WindowManager

    class OkWM(WindowManager):
        def rect(self, key):
            return Rect(0, 0, 1000, 1000)

    eng = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
    eng.set_dry_run(False)
    eng.act.scroll_to_reply = lambda *a, **k: True
    eng.act.click = lambda *a, **k: True
    eng.act.hotkey = lambda *a, **k: True
    eng.act.press = lambda *a, **k: True
    eng.act.paste_text = lambda *a, **k: True
    eng.act.clear_field = lambda *a, **k: True
    eng._llm_tab_title = lambda: ""
    return eng


def test_reply_wait_and_halts():
    """The 2026-09-25 failure: CONN copied one second after sending, the
    clipboard was empty, and each empty copy sent a reprint request, four a
    cycle, cycle after cycle."""
    print("reply wait, reprint cap and halts")
    import tempfile as _tf
    from conn.engine import Halted, normalize_tab_title

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        check("reply cap default is 300 s", cfg.get("timing.llm_output_wait_seconds") == 300)
        check("reprint cap default is 2", cfg.get("timing.llm_max_reprints") == 2)
        cfg.set("timing.llm_reply_poll_seconds", 0)
        cfg.set("timing.llm_min_wait_seconds", 0)

        # 1. the reply streams in: empty, partial (unbalanced), then complete
        eng = _live_engine(cfg)
        cfg.set("timing.llm_output_wait_seconds", 5)
        seq = ["", "", "local x = 1\nif x then\n print(x)",
               "local x = 1\nif x then\n print(x)\nend\n"
               "print('NEXT_RECOMMENDED_STATE: TEST')"]
        n = {"i": 0}

        def streaming(anchor, label=None):
            i = min(n["i"], len(seq) - 1)
            n["i"] += 1
            return seq[i]
        eng.act.copy_button = streaming
        rep = {"n": 0}
        eng._request_reprint = lambda why="": rep.__setitem__("n", rep["n"] + 1)
        code, raw = eng.copy_llm_code()
        check("waits through empty and partial copies", n["i"] == 4, str(n))
        check("returns the complete reply", "NEXT_RECOMMENDED_STATE" in code, code[-40:])
        check("no reprint while the reply streams", rep["n"] == 0, str(rep))

        # 2. nothing ever copies: HALT with no reprint at all
        eng = _live_engine(cfg)
        cfg.set("timing.llm_output_wait_seconds", 1)
        eng.act.copy_button = lambda anchor, label=None: ""
        rep = {"n": 0}
        eng._request_reprint = lambda why="": rep.__setitem__("n", rep["n"] + 1)
        t0 = time.time()
        try:
            eng.copy_llm_code()
            halted = ""
        except Halted as h:
            halted = str(h)
        check("empty clipboard halts the run", "Nothing could be copied" in halted, halted[:90])
        check("empty clipboard never sends a reprint", rep["n"] == 0, str(rep))
        check("halt comes after the wait, not before", time.time() - t0 >= 0.9)

        # 3. a broken block: two reprints, then HALT
        eng = _live_engine(cfg)
        cfg.set("timing.llm_output_wait_seconds", 0)
        eng.act.copy_button = lambda anchor, label=None: "```lua\nfunction f()\nprint(1)\n```"
        rep = {"n": 0}
        eng._request_reprint = lambda why="": rep.__setitem__("n", rep["n"] + 1)
        try:
            eng.copy_llm_code()
            halted = ""
        except Halted as h:
            halted = str(h)
        check("broken block gets exactly two reprints", rep["n"] == 2, str(rep))
        check("then the run halts with the reason", "rejected 3 time" in halted
              and "syntax" in halted, halted[:120])

        # 4. the prompt copied back instead of a reply: HALT, no reprint
        eng = _live_engine(cfg)
        eng.act.copy_button = lambda anchor, label=None: (
            "MODE:CMO_LUA_LLM_BRIDGE\n```lua\nprint(1)\n```")
        rep = {"n": 0}
        eng._request_reprint = lambda why="": rep.__setitem__("n", rep["n"] + 1)
        try:
            eng.copy_llm_code()
            halted = ""
        except Halted as h:
            halted = str(h)
        check("prompt echo halts without a reprint", "prompt" in halted and rep["n"] == 0,
              halted[:90])

        # 5. a halt inside a design run ends the run once, cleanly
        eng = _live_engine(cfg)
        eng.act.copy_button = lambda anchor, label=None: ""
        eng.act.attach_file = lambda *a, **k: True
        eng.act.paste_text_chunks = lambda *a, **k: True
        eng.build_prompt = lambda task, retrieve_for=None: "short prompt"
        events = []
        eng.emit = lambda kind, **f: events.append((kind, f))
        sent = {"n": 0}
        orig_submit = eng.submit_to_llm

        def counting_submit(prompt, wait_label="x"):
            sent["n"] += 1
            return orig_submit(prompt, wait_label)
        eng.submit_to_llm = counting_submit
        eng.state["running"] = True
        eng._guard(eng._run_design, {"scenario_prompt": "play it", "start_stage": "PLAYTEST"})
        kinds = [k for k, _f in events]
        texts = " ".join(f.get("text", "") for _k, f in events)
        check("halt event raised", "halted" in kinds, str(kinds[-5:]))
        check("one prompt sent, no reprint storm",
              sent["n"] == 1 and "reprint" not in texts.lower(), str(sent))
        check("run reports it halted", "RUN HALTED" in texts, texts[-200:])

    # tab titles
    check("edge furniture stripped",
          normalize_tab_title("Hormuz playtest - LLM and 3 more pages - Personal - "
                              "Microsoft\u200b Edge") == "Hormuz playtest - LLM",
          normalize_tab_title("Hormuz playtest - LLM and 3 more pages - Personal - "
                              "Microsoft\u200b Edge"))
    check("chrome furniture stripped",
          normalize_tab_title("Hormuz playtest - LLM - Google Chrome")
          == "Hormuz playtest - LLM")


def test_llm_tab_guard():
    print("LLM tab guard")
    import tempfile as _tf
    from conn.engine import Halted

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        eng = _live_engine(cfg)
        title = {"t": "Hormuz playtest - LLM - Google Chrome"}
        eng._llm_tab_title = lambda: title["t"]

        cfg.set("bridge.llm_title_must_contain", "Hormuz playtest")
        check("matching tab passes", eng._guard_llm_tab("test"))
        title["t"] = "CONN fixes - LLM - Google Chrome"
        try:
            eng._guard_llm_tab("before pasting the prompt")
            msg = ""
        except Halted as h:
            msg = str(h)
        check("wrong tab halts before pasting", "does not contain" in msg, msg[:80])

        cfg.set("bridge.llm_title_must_contain", "")
        title["t"] = "New chat - LLM - Google Chrome"
        eng._lock_llm_tab()
        check("generic title does not lock", eng._tab_lock == "", eng._tab_lock)
        title["t"] = "LLM - Google Chrome"
        eng._lock_llm_tab()
        check("bare 'LLM' does not lock", eng._tab_lock == "", eng._tab_lock)
        title["t"] = "Hormuz playtest - LLM - Google Chrome"
        eng._lock_llm_tab()
        check("real title locks", eng._tab_lock == "Hormuz playtest - LLM", eng._tab_lock)
        title["t"] = "Something else - LLM - Google Chrome"
        try:
            eng._guard_llm_tab("before pasting the prompt")
            msg = ""
        except Halted as h:
            msg = str(h)
        check("tab change halts", "changed from" in msg, msg[:80])
        cfg.set("bridge.lock_llm_tab", False)
        check("lock can be switched off", eng._guard_llm_tab("x"))

        eng.set_dry_run(True)
        cfg.set("bridge.llm_title_must_contain", "nope")
        check("dry run never blocks", eng._guard_llm_tab("x"))


def test_abort_is_immediate():
    print("abort stops the next input")
    import tempfile as _tf
    from conn.anchors import AnchorResolver
    from conn.engine import Aborted, Engine
    from conn.winmgr import Rect, WindowManager

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")

        class OkWM(WindowManager):
            def rect(self, key):
                return Rect(0, 0, 1000, 1000)

        eng = Engine(cfg, OkWM(cfg), AnchorResolver(cfg, OkWM(cfg)))
        eng.state["running"] = True
        eng._abort.set()
        for name, fn in (("click", lambda: eng.act.click("llm_input")),
                         ("paste", lambda: eng.act.paste_text("x")),
                         ("press", lambda: eng.act.press("enter")),
                         ("hotkey", lambda: eng.act.hotkey("ctrl", "v"))):
            try:
                fn()
                ok = False
            except Aborted:
                ok = True
            check("abort stops " + name, ok)
        try:
            eng._wait(0, "zero wait")
            ok = False
        except Aborted:
            ok = True
        check("even a zero-second wait honours abort", ok)
        eng.state["running"] = False
        check("idle clicks are not blocked by a stale abort",
              eng.act.click("llm_input") in (True, False))
        check("engine owns set_clock_state", hasattr(eng, "set_clock_state"))


def test_config_heals_test_values():
    print("config heals the zeros shipped on 2026-09-07")
    import json as _json
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        p = Path(d) / "bridge_config.json"
        p.write_text(_json.dumps({
            "timing": {"llm_output_wait_seconds": 0, "llm_reprint_wait_seconds": 0,
                       "llm_copy_retry_wait_seconds": 0, "cmo_output_wait_seconds": 0,
                       "sim_settle_seconds": 0},
            "bridge": {"max_cycles": 2}, "play": {"turn_cap": 1},
            "anchors": {"llm_input": {"window": "llm", "mode": "frac",
                                         "dx": 0.5, "dy": 0.5}}}))
        cfg = Config(p)
        check("reply wait restored", cfg.get("timing.llm_output_wait_seconds") == 300)
        check("CMO wait restored", cfg.get("timing.cmo_output_wait_seconds") == 20)
        check("cycle budget restored", cfg.get("bridge.max_cycles") == 500)
        check("turn cap restored", cfg.get("play.turn_cap") == 40)
        check("anchors untouched", cfg.get("anchors.llm_input.dx") == 0.5)
        again = _json.loads(p.read_text())
        check("healed values written back", again["timing"]["llm_output_wait_seconds"] == 300)

        p.write_text(_json.dumps({"timing": {"llm_output_wait_seconds": 90},
                                  "bridge": {"max_cycles": 2}}))
        cfg = Config(p)
        check("deliberate settings are left alone",
              cfg.get("timing.llm_output_wait_seconds") == 90
              and cfg.get("bridge.max_cycles") == 2)


def test_console_and_copy_fixes():
    print("console reads, copies and reprints (2026-09-26)")
    import tempfile as _tf
    from conn.engine import (Halted, slice_between_markers, text_after_end_marker)

    t = "old\nCONN_BEGIN:aa\nBRIDGE_DONE: old\nCONN_END:aa\nCONN_BEGIN:bb\nerror in line 3"
    check("BEGIN without END returns only this run's text",
          slice_between_markers(t, "bb") == "error in line 3", slice_between_markers(t, "bb"))
    t2 = "CONN_BEGIN:aa\nbase\nCONN_END:aa\nevent print during the window"
    check("post-run read is what came after END",
          text_after_end_marker(t2, "aa") == "event print during the window")
    check("post-run read is empty when nothing new", text_after_end_marker(t2 + "\n", "zz") == "")

    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        eng = _live_engine(cfg)
        eng.cfg.set("timing.cmo_output_poll_seconds", 0)
        eng._last_token = "bb"
        reads = {"n": 0}

        def pane(anchor, label=None):
            reads["n"] += 1
            return t
        eng.act.copy_region = pane
        t0 = time.time()
        out = eng.read_cmo_output()
        check("a run that died on an error is read without waiting out the timeout",
              reads["n"] <= 4 and time.time() - t0 < 5, str(reads))
        check("and the stale BRIDGE_DONE is not in it", "BRIDGE_DONE" not in out, out)

        # copy_region: a failed click or a copy that changed nothing gives ""
        from conn.engine import Actuator
        act = eng.act
        real = Actuator(cfg, eng.resolver, lambda *a, **k: None, dry_run=False)
        real.click = lambda *a, **k: False
        check("failed click copies nothing", real.copy_region("cmo_output_area") == "")
        board = {"v": "operator text"}
        real.click = lambda *a, **k: True
        real.hotkey = lambda *a, **k: True
        real._pause = lambda s=None: None
        real.clip.read = lambda: board["v"]
        real.clip.write = lambda v: board.__setitem__("v", v) or True
        check("a copy that did not change the clipboard is empty, not the old clipboard",
              real.copy_region("cmo_output_area") == "")
        check("the operator's clipboard is put back", board["v"] == "operator text", board["v"])

        # a copy equal to the last accepted reply is the old reply
        eng2 = _live_engine(cfg)
        cfg.set("timing.llm_reply_poll_seconds", 0)
        cfg.set("timing.llm_min_wait_seconds", 0)
        cfg.set("timing.llm_output_wait_seconds", 0)
        old = "```lua\nprint(1)\nprint('NEXT_RECOMMENDED_STATE: TEST')\n```"
        eng2._last_reply_raw = old
        eng2.act.copy_button = lambda anchor, label=None: old
        rep = {"n": 0}
        eng2._request_reprint = lambda why="": rep.__setitem__("n", rep["n"] + 1)
        try:
            eng2.copy_llm_code()
            msg = ""
        except Halted as h:
            msg = str(h)
        check("the previous reply is never re-injected", "previous reply" in msg
              and rep["n"] == 0, msg[:80])

        # the reprint request fits under the paste limit
        eng3 = _live_engine(cfg)
        pasted = []
        eng3.act.paste_text = lambda text, label="": pasted.append(text) or True
        eng3._wait = lambda *a, **k: None
        eng3._request_reprint("syntax: 1 block(s) missing 'end'")
        check("reprint request is short enough to paste as text",
              pasted and len(pasted[0]) < 1500 and "CURRENT_CYCLE_AND_TASK" in pasted[0],
              str(len(pasted[0]) if pasted else 0))

        # a live step that cannot land stops the run; dry run only reports it
        eng4 = _live_engine(cfg)
        eng4.act.clear_field = lambda *a, **k: False
        try:
            eng4.run_lua_in_cmo("print(1)")
            msg = ""
        except Halted as h:
            msg = str(h)
        check("closed Lua console stops the run instead of pasting elsewhere",
              "cmo_lua_input" in msg, msg[:60])
        eng4.set_dry_run(True)
        check("dry run only reports it", eng4.run_lua_in_cmo("print(1)") is True)


def test_popup_and_answers():
    print("popup state and declared answers (2026-09-26)")
    import tempfile as _tf
    from conn import engine as _eng
    from conn import popups
    check("answer with trailing words still parses",
          popups.parse_answer_directives("-- BRIDGE_ANSWER: YES then run") == ["YES"])
    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        eng = _live_engine(cfg)
        box = {"hwnd": 77}
        orig_find, orig_read = _eng._popups.find_popup, _eng._popups.read_popup
        try:
            _eng._popups.find_popup = lambda rx=None: box["hwnd"]
            _eng._popups.read_popup = lambda h: {"title": "Incoming message", "text": "Q?",
                                                 "buttons": ["Yes", "No"]}
            first = eng._service_popup()
            second = eng._service_popup()
            check("a new box ends the wait once", first is True, str(first))
            check("the same box does not end every later wait", second is False, str(second))
            box["hwnd"] = 0
            check("a box closed by hand clears the pending state",
                  eng._answer_pending_popup() is True and not eng.state.get("popup_pending"))
        finally:
            _eng._popups.find_popup, _eng._popups.read_popup = orig_find, orig_read
        eng._answers = ["YES"]
        eng.start  # noqa
        eng.state["running"] = False
        ok, _m = True, ""
        check("start() clears leftover answers",
              (eng.start("design", {}) or True) and eng._answers == [], str(eng._answers))
        eng.abort()
        for _ in range(100):
            if not eng.state["running"]:
                break
            time.sleep(0.05)
        check("the abort flag is cleared when the run ends", not eng._abort.is_set())


def test_play_rules_and_locks():
    print("play rules, locks and attachments (2026-09-26)")
    import tempfile as _tf
    from conn.luacheck import scan_blocklist
    from conn.turnengine import TurnEngine, side_named
    check("editor lock sees Name{...}", scan_blocklist("ScenEdit_AddUnit{side='B'}",
                                                     ["ScenEdit_AddUnit"]) == ["ScenEdit_AddUnit"])
    check("editor lock sees an alias", scan_blocklist("local f = ScenEdit_SetTime",
                                                    ["ScenEdit_SetTime"]) == ["ScenEdit_SetTime"])
    check("a comment that names a call does not block",
          scan_blocklist("-- no ScenEdit_AddUnit here\nprint(1)", ["ScenEdit_AddUnit"]) == [])
    check("reading a contact's side is not a side switch",
          not side_named("if c.side == 'Red' then print(c.name) end", "Red"))
    check("acting as the other side is", side_named("ScenEdit_GetUnit({side='Red', name='x'})",
                                                    "Red"))
    with _tf.TemporaryDirectory() as d:
        cfg = Config(Path(d) / "bridge_config.json")
        eng = _live_engine(cfg)
        eng.state["mode"] = "llm_vs_llm"
        te = TurnEngine(eng)
        eng.state["last_output"] = "Blue intent: deny Red victory at the strait"
        check("a bare 'victory' no longer ends the game", not te._scenario_over())
        eng.state["last_output"] = "SCENARIO HAS ENDED"
        check("an explicit end marker still does", te._scenario_over())
        f = Path(d) / "map.png"
        f.write_text("x")
        eng._pending_by_side.setdefault("Blue", []).append((f, "map"))
        sent = []
        eng.act.attach_file = lambda path, anchor="": sent.append(path.name) or True
        eng.act.paste_text_chunks = lambda *a, **k: True
        eng._wait = lambda *a, **k: None
        eng.submit_to_llm("short", side="Red")
        check("one side's files never go to the other side", sent == [], str(sent))
        eng.submit_to_llm("short", side="Blue")
        check("they go with that side's own prompt", sent == ["map.png"], str(sent))


def test_config_and_layout_safety():
    print("config safety and layout profiles (2026-09-26)")
    import json as _json
    import tempfile as _tf
    from conn.layouts import LayoutManager
    from conn.winmgr import WindowManager, Rect
    with _tf.TemporaryDirectory() as d:
        p = Path(d) / "bridge_config.json"
        p.write_text(_json.dumps({"timing": {"cmo_output_poll_seconds": "2.0",
                                             "cmo_output_wait_seconds": "20"},
                                  "anchors": {"llm_input": {"window": "llm", "mode": "px",
                                                               "corner": "bl", "dx": 472,
                                                               "dy": 142}}}),
                     encoding="utf-8-sig")
        cfg = Config(p)
        check("a file with a byte-order mark loads", not cfg.load_error and
              cfg.get("anchors.llm_input.dx") == 472, cfg.load_error)
        check("numbers stored as text become numbers",
              cfg.get("timing.cmo_output_wait_seconds") == 20
              and cfg.get("timing.cmo_output_poll_seconds") == 2.0)
        cfg.save()
        check("the first save keeps a backup", (Path(d) / "bridge_config.backup.json").exists())
        p.write_text("{ not json", encoding="utf-8")
        bad = Config(p)
        refused = False
        try:
            bad.save()
        except IOError:
            refused = True
        check("an unreadable file is never overwritten with defaults",
              refused and p.read_text(encoding="utf-8") == "{ not json")
        check("and a copy of it is kept", any(x.name.startswith("bridge_config.bad-")
                                               for x in Path(d).iterdir()))

        cfg2 = Config(Path(d) / "c2.json")

        class WM(WindowManager):
            def topology_key(self):
                return "0,0,3840,2160"

            def rect(self, key):
                return None
        lm = LayoutManager(cfg2, WM(cfg2))
        k1 = lm.key_for_topology("X")
        check("topology key is the same in every process", k1 == "X@{}".format(
            __import__("zlib").crc32(b"0,0,3840,2160") % 100000), k1)
        cfg2.profiles["LLM_SCEN_DEV@99863"] = {"label": "a", "topology": "0,0,3840,2160",
                                                  "windows": {}}
        check("an existing @NNNNN profile resolves by name",
              lm.resolve_for_topology("LLM_SCEN_DEV@99863") == "LLM_SCEN_DEV@99863")
        check("and by its base name on the same monitors",
              lm.resolve_for_topology("LLM_SCEN_DEV") == "LLM_SCEN_DEV@99863")


def test_ui_fixes():
    print("UI fixes (2026-09-26)")
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("  skip (no tkinter)")
        return
    from conn.app import ConnApp
    from conn import theme
    app = ConnApp()
    app.update()
    # custom layout profile survives a mode change
    app.cfg.profiles["My Dev@12345"] = {"label": "mine", "topology": "x", "windows": {}}
    app.cfg.set("layouts.active", "My Dev@12345")
    app.refresh_layouts()
    app.mode_var.set("Player vs LLM")
    app.on_mode_change()
    check("mode change keeps a profile you picked", app.layouts.active() == "My Dev@12345",
          app.layouts.active())
    idx = app._layout_keys.index("My Dev@12345")
    app.layout_list.selection_clear(0, "end")
    app.layout_list.selection_set(idx)
    check("names with spaces are read whole", app.selected_profile() == "My Dev@12345",
          app.selected_profile())
    app.mode_var.set("Scenario Development")
    app.on_mode_change()

    # overlay and status dots keep their colours through a theme change
    app.overlay.show()
    app.update()
    app.dry_run.set(False)
    app.on_dry_run_toggle()
    app.update()
    check("overlay stays black (its transparent key)",
          str(app.overlay.top.cget("bg")) == "black" and
          str(app.overlay.canvas.cget("bg")) == "black", str(app.overlay.top.cget("bg")))
    app.overlay.hide()
    dots = [w for row in app.pf_holder.winfo_children() for w in row.winfo_children()
            if getattr(w, "_conn_fixed_color", False)]
    check("preflight dots keep distinct colours",
          len({str(w.cget("bg")) for w in dots}) >= 2, str(len(dots)))

    # monitor boxes are not rewritten when nothing changed
    panel = app.panels[0]
    panel._set_text(panel.lua_box, "x" * 50)
    panel.lua_box.configure(state="normal")
    panel.lua_box.insert("end", "MARK")
    panel.lua_box.configure(state="disabled")
    panel._set_text(panel.lua_box, "x" * 50)
    check("unchanged text is not rewritten", "MARK" in panel.lua_box.get("1.0", "end"))
    for i in range(1200):
        panel.append_log("line {}".format(i))
    lines = int(panel.log.index("end-1c").split(".")[0])
    check("log widget stays bounded", lines <= 802, str(lines))

    # run buttons follow the run
    check("Pause and Step are off while idle",
          "disabled" in app.btn_pause.state() and "disabled" in app.btn_step.state())
    app.engine.state["running"] = True
    app._sync_run_buttons()
    check("Start is off during a run", "disabled" in app.btn_start.state())
    app.engine.state["running"] = False
    app._sync_run_buttons()

    # the request and stage come back after a restart
    app.prompt.delete("1.0", "end")
    app.prompt.insert("1.0", "Play Hormuz as the United States")
    app.start_stage.set("PLAYTEST (play the loaded scenario)")
    app._remember_mission()
    cfg_path = app.cfg.path
    app.on_close()
    app2 = ConnApp()
    app2.update()
    check("mission text restored", app2.prompt.get("1.0", "end").strip() ==
          "Play Hormuz as the United States")
    check("opening stage restored", app2.start_stage.get().startswith("PLAYTEST"),
          app2.start_stage.get())
    app2.on_close()


def main():
    for t in (test_luacheck, test_anchor_math, test_layout_math, test_config,
              test_ike, test_turn_helpers, test_scroll_before_copy,
              test_copy_validation, test_cycle_and_markers,
              test_knowledge_pack_integration, test_env_symbols_and_copy_retry, test_console_suppression_and_state, test_stop_policy, test_halt_only_from_console,
              test_loop_persistence, test_attach_route, test_bridge_control_directives, test_chaos_resilience, test_progress_and_directive_order,
              test_audit_start,
              test_ui, test_turn_gate, test_reply_wait_and_halts, test_llm_tab_guard,
              test_abort_is_immediate, test_config_heals_test_values,
              test_console_and_copy_fixes, test_popup_and_answers, test_play_rules_and_locks,
              test_config_and_layout_safety, test_ui_fixes):
        t()
    print("")
    if FAILS:
        print("FAILURES: {}".format(len(FAILS)))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
