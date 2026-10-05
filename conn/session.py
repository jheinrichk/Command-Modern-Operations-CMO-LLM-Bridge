"""
conn.session  -  event log, transcript, script diff, export.

Every run creates a session folder:

    SESSIONS/2026-08-22_141233_scenario_dev/
        events.jsonl     machine-readable event stream
        transcript.md    prompts, replies and console output in order
        scripts/         each deployed Lua block, numbered
        diff.md          unified diff between successive deployed scripts
        report.md        exported summary

Events are also pushed to the UI queue by the engine, so this module only
persists them.
"""

import difflib
import json
import time
from pathlib import Path


def _quiet(fn):
    """Session recording is a convenience. It never interrupts a run."""
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception:
            return None
    wrapper.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapper


class Session:
    def __init__(self, cfg, mode="design", log=None):
        self.cfg = cfg
        self.mode = mode
        self.log = log or (lambda m: None)
        self.started = time.time()
        base = cfg.folder("sessions_folder") or Path.cwd() / "SESSIONS"
        name = time.strftime("%Y-%m-%d_%H%M%S") + "_" + mode
        self.dir = Path(base) / name
        self.scripts_dir = self.dir / "scripts"
        self.enabled = True
        try:
            self.scripts_dir.mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            self.enabled = False
            self.log("session folder unavailable ({}), logging to memory only".format(ex))
        self.events = []
        self.scripts = []
        self.transcript = []

    # -- writing ----------------------------------------------------
    def event(self, kind, **fields):
        rec = {"t": round(time.time() - self.started, 2), "kind": kind}
        rec.update(fields)
        self.events.append(rec)
        if self.enabled:
            try:
                with open(self.dir / "events.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, default=str) + "\n")
            except Exception:
                pass
        return rec

    @_quiet
    def add_transcript(self, role, text):
        block = "\n### {}  ({})\n\n```\n{}\n```\n".format(
            role, time.strftime("%H:%M:%S"), (text or "").strip())
        self.transcript.append(block)
        if self.enabled:
            try:
                with open(self.dir / "transcript.md", "a", encoding="utf-8") as f:
                    f.write(block)
            except Exception:
                pass

    @_quiet
    def add_script(self, stage, code):
        idx = len(self.scripts) + 1
        self.scripts.append({"index": idx, "stage": stage, "code": code})
        if self.enabled:
            try:
                (self.scripts_dir / "{:03d}_{}.lua".format(idx, stage.lower())).write_text(
                    code, encoding="utf-8")
            except Exception:
                pass
        return idx

    # -- derived ----------------------------------------------------
    def diff_text(self):
        out = []
        for a, b in zip(self.scripts, self.scripts[1:]):
            d = difflib.unified_diff(
                a["code"].splitlines(), b["code"].splitlines(),
                fromfile="{:03d}_{}".format(a["index"], a["stage"]),
                tofile="{:03d}_{}".format(b["index"], b["stage"]),
                lineterm="", n=2)
            body = "\n".join(d)
            if body.strip():
                out.append("## {} -> {}\n\n```diff\n{}\n```\n".format(
                    a["stage"], b["stage"], body))
        return "\n".join(out) or "No successive scripts to compare.\n"

    def summary(self):
        kinds = {}
        for e in self.events:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        return {
            "mode": self.mode,
            "duration_s": round(time.time() - self.started, 1),
            "events": len(self.events),
            "scripts": len(self.scripts),
            "by_kind": kinds,
        }

    @_quiet
    def export(self, extra_notes=""):
        s = self.summary()
        lines = [
            "# CONN session report",
            "",
            "- Mode: {}".format(s["mode"]),
            "- Started: {}".format(time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime(self.started))),
            "- Duration: {} s".format(s["duration_s"]),
            "- Scripts deployed: {}".format(s["scripts"]),
            "- Events: {}".format(s["events"]),
            "",
            "## Event counts",
            "",
        ]
        for k, v in sorted(s["by_kind"].items()):
            lines.append("- {}: {}".format(k, v))
        if extra_notes:
            lines += ["", "## Notes", "", extra_notes]
        lines += ["", "## Stage sequence", ""]
        for sc in self.scripts:
            lines.append("{:03d}. {} ({} chars)".format(
                sc["index"], sc["stage"], len(sc["code"])))
        text = "\n".join(lines) + "\n"
        if self.enabled:
            try:
                (self.dir / "report.md").write_text(text, encoding="utf-8")
                (self.dir / "diff.md").write_text(self.diff_text(), encoding="utf-8")
            except Exception:
                pass
        return text
