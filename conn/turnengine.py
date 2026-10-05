"""
conn.turnengine  -  one turn loop, four participant arrangements.

    normal          human plays, CONN monitors only and never injects
    player_vs_llm   human holds one side, a commander agent holds the other
    llm_vs_llm      two commander agents alternate, with an arbiter and a cap
    pbem_h2h        turns arrive and leave as IKE .save files in a watch folder

All four share the same turn state machine, so the only thing that changes is
who produces the orders for the side that is on the clock:

    AWAIT_TURN -> SITREP -> ORDERS -> ARBITER -> INJECT -> END_TURN -> HANDOFF

Side lock refuses to inject orders that name a side other than the one on the
clock. The arbiter refuses editor calls and unbalanced Lua.
"""

import re
import time
from pathlib import Path

from . import luacheck


class TurnEngine:
    def __init__(self, engine, params=None):
        self.e = engine
        self.cfg = engine.cfg
        self.p = params or {}
        self.mode = engine.state["mode"]
        self.my_side = self.cfg.get("play.my_side", "Blue")
        self.op_side = self.cfg.get("play.opponent_side", "Red")
        self.commanders = engine.commanders()
        self.turn = 0
        self.intents = {self.my_side: [], self.op_side: []}
        self.exchange = self.cfg.folder("save_exchange_folder") or Path(
            self.cfg.get("ike.save_exchange_folder", "."))
        self.seen_saves = set()

    # -- helpers ----------------------------------------------------
    def emit(self, kind, **f):
        self.e.emit(kind, **f)

    def phase(self, name, side=None):
        self.e.state["phase"] = name
        self.e.state["side"] = side or ""
        self.emit("turn", turn=self.turn, phase=name, side=side or "")

    def llm_sides(self):
        if self.mode == "player_vs_llm":
            return [self.op_side]
        if self.mode == "llm_vs_llm":
            return [self.my_side, self.op_side]
        return []

    # -- run --------------------------------------------------------
    def run(self):
        if self.mode == "normal":
            return self._run_normal()
        cap = int(self.cfg.get("play.turn_cap", 40))
        order = [self.my_side, self.op_side]
        while self.turn < cap:
            self.e._checkpoint()
            self.turn += 1
            self.e.state["turn"] = self.turn
            for side in order:
                self.e._checkpoint()
                if self.mode == "pbem_h2h" and side == self.op_side:
                    if not self._await_opponent_save():
                        return
                    continue
                if side in self.llm_sides():
                    self._llm_turn(side)
                else:
                    self._human_turn(side)
            if self._scenario_over():
                self.emit("log", text="Scenario end detected, stopping the turn loop.")
                break
        self.emit("log", text="Turn loop finished after {} turns.".format(self.turn))
        if self.e.session:
            self.emit("log", text=self.e.session.export(
                extra_notes=self._intent_notes()))

    def _run_normal(self):
        """Monitor only. No synthetic input at all, whatever the dry-run state.
        No RAG either: nothing is retrieved, validated or harvested while a
        human plays unassisted."""
        self.emit("log", text="Normal play. CONN is monitoring and will not inject.")
        self.phase("MONITOR")           # once; it used to log every 2 seconds
        while True:
            self.e._checkpoint()
            time.sleep(0.5)

    # -- turns ------------------------------------------------------
    def _human_turn(self, side):
        # A human turn touches no RAG. Nothing is retrieved for the human,
        # nothing the human does is harvested, and the index is never built
        # or rebuilt here, so the simulation runs undisturbed.
        self.phase("AWAIT_HUMAN", side)
        deadline = int(self.cfg.get("play.order_deadline_minutes", 20)) * 60
        self.emit("log", text="Turn {}: your orders for {}. Press Step when the "
                             "turn is given.".format(self.turn, side))
        self.e.await_step("Order deadline {}".format(side), cap=deadline)
        self.phase("HUMAN_DONE", side)

    def _llm_turn(self, side):
        cmd = self.commanders.get(side)
        if not cmd:
            self.emit("error", text="no commander profile for side {}".format(side))
            return

        self.phase("SITREP", side)
        self.e.run_lua_in_cmo(cmd.sitrep_lua(), label="sitrep")
        self.e._wait(int(self.cfg.get("timing.cmo_output_wait_seconds", 5)), "SITREP read")
        sitrep = self.e.read_cmo_output()

        # What CMO itself recorded since this side's last turn. The marker
        # is per side, so each commander sees exactly the interval it was
        # away for, and nothing of the other's turn is carried in prose.
        if self.cfg.get("play.attach_aalog_each_turn", True):
            logs = self.e._ensure_logs()
            if logs and logs.available():
                try:
                    block = logs.excerpt(mode="delta", marker="turn:" + side,
                                         max_chars=int(self.cfg.get("play.aalog_max_chars", 12000)),
                                         for_side=side)
                    sitrep = (sitrep or "") + "\n\nAFTER_ACTION_LOG_SINCE_YOUR_LAST_TURN:\n" + block
                except Exception as ex:
                    self.emit("log", text="AALog delta skipped: {}".format(ex), level="warn")
        if self.cfg.get("play.attach_mapshot_each_turn", False):
            self.e.prepare_attachments([("MAPSHOT", {})], side=side)

        self.phase("ORDERS", side)
        # RAG for the commander happens here, during the order phase, when
        # IKE or the turn engine already has the clock stopped. It retrieves
        # on the actual tactical situation (the SITREP tail and the last
        # intents), uses the commander profile (orders rules, not build
        # rules), and only sees lessons harvested for THIS side.
        rag = ""
        if self.cfg.get("play.rag_enabled", True) and self.e._ensure_rag():
            try:
                q = "{} orders. {}\n{}".format(
                    side, (sitrep or "")[-1200:],
                    "\n".join(self.intents.get(side, [])[-3:]))
                rag = self.e.rag.retrieve_context(
                    q,
                    k_recipes=int(self.cfg.get("bridge.rag_recipes", 5)),
                    k_docs=int(self.cfg.get("play.rag_docs", 2)),
                    k_lessons=int(self.cfg.get("play.rag_lessons", 3)),
                    max_chars=int(self.cfg.get("play.rag_max_chars", 4500)),
                    profile="commander", side=side)
            except Exception as ex:
                self.emit("log", text="commander RAG skipped: {}".format(ex), level="warn")
                rag = ""
        prompt = cmd.order_prompt(self.turn, sitrep, rag,
                                  "\n".join(self.intents.get(side, [])[-4:]))
        self.e.submit_to_llm(prompt, wait_label="{} orders".format(side), side=side)
        code, raw = self.e.copy_llm_code()
        if not code.strip():
            self.emit("error", text="no orders returned for {}".format(side))
            return
        # a commander may ask for evidence too; it arrives with its next prompt
        try:
            from .cmologs import parse_attach_directives
            wants = parse_attach_directives(raw)
            if wants:
                # this side's next prompt only; the AALOG comes as a tail
                # filtered to what this side can see (the delta marker was
                # already spent on the SITREP)
                self.e.prepare_attachments(wants, side=side)
        except Exception as ex:
            self.emit("log", text="attachment request skipped: {}".format(ex), level="warn")

        self.phase("ARBITER", side)
        ok, why = self.arbiter(code, side)
        if not ok:
            self.emit("error", text="orders rejected for {}: {}".format(side, why))
            self.e.state["errors"] += 1
            # tell the commander next turn; otherwise it repeats the same
            # rejected orders every turn without knowing
            self.intents.setdefault(side, []).append(
                "T{}: YOUR ORDERS WERE REJECTED BY THE ARBITER AND NOT RUN: {}. Fix this "
                "first.".format(self.turn, why[:200]))
            return

        self.phase("INJECT", side)
        if self.e.run_lua_in_cmo(code, label="orders"):
            self.e._wait(int(self.cfg.get("timing.cmo_output_wait_seconds", 5)),
                         "orders execution")
            out = self.e.read_cmo_output()
            intent = extract_intent(raw) or extract_intent(out)
            if intent:
                self.intents.setdefault(side, []).append(
                    "T{}: {}".format(self.turn, intent))
                self.emit("log", text="{} intent: {}".format(side, intent))
            # Learning during play is OFF by default. In llm_vs_llm a note one
            # commander prints could describe the other's positions, and an
            # unscoped lesson store would hand it across. When enabled, every
            # lesson is tagged play:<side> and only that side's commander can
            # retrieve it. This runs now, while the clock is still stopped,
            # so the index rebuild never overlaps the simulation.
            if self.cfg.get("play.rag_learn_in_play", False) and self.e.rag \
                    and hasattr(self.e.rag, "harvest_lessons"):
                try:
                    pairs = [("play:{}:{}".format(side, t), x)
                             for t, x in self.e.rag.harvest_lessons(code, out)]
                    n = self.e.rag.ingest_many(pairs) if pairs else 0
                    if n:
                        self.emit("log", text="RAG learned {} lesson(s) for {}".format(n, side))
                except Exception as ex:
                    self.emit("log", text="play harvest skipped: {}".format(ex), level="warn")
            # IKE hotseat: the orders are in, now the LLM side's turn has to
            # RUN. IKE stops the clock itself when the turn length elapses
            # and raises the hand-off popup, so CONN presses play, waits the
            # turn out on the wall clock, and does NOT press pause. Compression
            # is whatever the operator set by hand.
            if self.cfg.get("play.ike_hotseat", False) and self.e.sim and not self.e.dry_run:
                self.phase("RUN_TURN", side)
                mins = int(self.cfg.get("play.turn_length_minutes", 30))
                comp = int(self.cfg.get("bridge.manual_compression", 5))
                wall = int(mins * 60 / max(1, comp)) + 10
                self.emit("log", text="Running {}'s turn: {} min of sim at x{} "
                                      "(about {}s wall). IKE stops it at the "
                                      "turn boundary.".format(side, mins, comp, wall))
                self.e.sim.play()
                self.e._wait(wall, "IKE turn {} ({})".format(self.turn, side))
                self.emit("log", text="IKE should now show the end-of-turn notice for "
                                      "{}. Save the turn, then enter the next side's "
                                      "password and press Step.".format(side))
                self.e.await_step("IKE hand-off after {}".format(side))
        self.phase("END_TURN", side)

    # -- arbiter and locks ------------------------------------------
    def arbiter(self, code, side):
        if not self.cfg.get("play.arbiter_enabled", True):
            return True, ""
        ok, problems, _ = luacheck.check(code)
        if not ok:
            return False, "; ".join(problems)
        blocked = luacheck.scan_blocklist(code, self.cfg.get("safety.blocked_in_play", []))
        if blocked:
            return False, "editor calls: " + ", ".join(blocked)
        if self.cfg.get("play.side_lock", True):
            other = self.op_side if side == self.my_side else self.my_side
            if side_named(code, other):
                return False, "side lock: orders reference {}".format(other)
        budget = int(self.cfg.get("play.order_budget_per_turn", 12))
        calls = len(re.findall(r"ScenEdit_\w+\s*\(", code))
        if calls > budget * 3:
            return False, "order budget exceeded ({} calls)".format(calls)
        return True, ""

    # -- PBEM exchange ----------------------------------------------
    def _await_opponent_save(self):
        folder = Path(self.exchange)
        self.phase("AWAIT_SAVE", self.op_side)
        if not folder.exists():
            self.emit("error", text="exchange folder missing: {}".format(folder))
            return False
        self.emit("log", text="Waiting for the opponent .save in {}".format(folder))
        poll = float(self.cfg.get("play.watch_poll_seconds", 3))
        known = {p.name for p in folder.glob("*.save")}
        self.seen_saves |= known
        while True:
            self.e._checkpoint()
            for p in sorted(folder.glob("*.save"), key=lambda q: q.stat().st_mtime):
                if p.name not in self.seen_saves:
                    self.seen_saves.add(p.name)
                    self.emit("log", text="Incoming turn file: {}".format(p.name))
                    self.phase("LOAD_SAVE", self.op_side)
                    self.emit("log", text="Load it in CMO, enter your password, then "
                                         "press Step to continue.")
                    self.e.await_step("Load incoming save")
                    return True
            time.sleep(poll)

    def _scenario_over(self):
        text = (self.e.state.get("last_output") or "").upper()
        # explicit end markers only; a bare "VICTORY" also matched intent
        # lines such as "deny Red victory" and ended the game after turn 1
        for marker in ("SCENARIO COMPLETE", "SCENARIO HAS ENDED", "SCEN_ENDED: TRUE"):
            if marker in text:
                return True
        return False

    def _intent_notes(self):
        lines = []
        for side, items in self.intents.items():
            if items:
                lines.append("### {}".format(side))
                lines.extend("- " + i for i in items)
        return "\n".join(lines)


def extract_intent(text):
    m = re.search(r"TURN_INTENT[:\s]*(.+)", text or "", re.IGNORECASE)
    return m.group(1).strip()[:200] if m else ""


def side_named(code, side_name):
    """True when the code acts AS the named side: side = 'X' in a call's
    table or an assignment, or 'X' as the first argument of a ScenEdit call.

    Comparing a contact's side (c.side == 'X') is a read, not a side switch,
    and used to get whole turns of orders rejected without the commander
    ever being told why."""
    if not side_name:
        return False
    q = r"['\"]\s*" + re.escape(side_name) + r"\s*['\"]"
    if re.search(r"\bside\s*=(?!=)\s*" + q, code, re.IGNORECASE):
        return True
    if re.search(r"\bScenEdit_\w+\s*\(\s*" + q, code, re.IGNORECASE):
        return True
    return False
