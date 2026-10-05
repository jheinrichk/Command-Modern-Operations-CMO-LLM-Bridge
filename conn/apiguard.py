"""
conn.apiguard  -  no invented CMO API names reach the console.

Backed by knowledge_pack/cmo_known_api_index.json (174 symbols extracted from
the comprehensive CommandLua library). Any CMO-looking identifier in a payload
that is not in the index blocks injection, which converts the "guessed a
function name, burned a cycle" failure into an instant local rejection.

Soft symbols (config safety.api_soft_symbols) warn instead of blocking. They
default to the Pro-only VP_ sim calls, which legitimate code references inside
guarded _try("...") fallbacks.

The user can extend the index without editing the pack through
safety.api_extra_symbols, for example after an environment dump shows symbols
present in their build that the pack predates.
"""

import json
import re
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PKG_ROOT / "knowledge_pack" / "cmo_known_api_index.json"
ENV_PATH = PKG_ROOT / "knowledge_pack" / "cmo_environment_symbols.json"

# Same pattern as the pack's cmo_lua_command_guard.py.
API_PATTERN = re.compile(
    r"\b(?:ScenEdit_[A-Za-z0-9_]+|VP_[A-Za-z0-9_]+|Tool_[A-Za-z0-9_]+|"
    r"UI_[A-Za-z0-9_]+|World_[A-Za-z0-9_]+|Command_[A-Za-z0-9_]+|"
    r"Exporter_[A-Za-z0-9_]+|GetScenarioTitle|SetScenarioTitle|GetBuildNumber)\b"
)

DEFAULT_SOFT = [
    # Professional Edition only. The library's own sim-control snippet calls
    # these through guarded lookups, so their presence is not an invention.
    "VP_RunSimulation", "VP_PauseSimulation",
    "VP_RunForTimeAndHalt", "VP_RunToTimeAndHalt",
]


class ApiGuard:
    def __init__(self, cfg=None, index_path=None):
        self.cfg = cfg
        self.index_path = Path(index_path) if index_path else INDEX_PATH
        self.known = set()
        self.loaded = False
        self.load()

    def load(self):
        self.known = set()
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            self.known = set(data.get("symbols", []))
            self.loaded = bool(self.known)
        except Exception:
            self.loaded = False
        # symbols confirmed present in the user's own build
        try:
            env = json.loads(ENV_PATH.read_text(encoding="utf-8"))
            self.known |= set(env.get("symbols", []))
        except Exception:
            pass
        if self.cfg:
            for s in self.cfg.get("safety.api_extra_symbols", []) or []:
                self.known.add(str(s))
        return self.loaded

    def learn_from_text(self, text):
        """Harvest API-pattern symbols from an environment dump and persist
        them to the environment symbol file. Returns the new symbols."""
        found = set(API_PATTERN.findall(text or ""))
        new = sorted(found - self.known)
        if not new:
            return []
        try:
            data = {"purpose": "environment-confirmed symbols", "symbols": []}
            if ENV_PATH.exists():
                data = json.loads(ENV_PATH.read_text(encoding="utf-8"))
            merged = sorted(set(data.get("symbols", [])) | found)
            data["symbols"] = merged
            data["count"] = len(merged)
            ENV_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        self.known |= found
        return new

    def soft(self):
        base = list(DEFAULT_SOFT)
        if self.cfg:
            base += [str(s) for s in
                     (self.cfg.get("safety.api_soft_symbols", []) or [])]
        return set(base)

    def scan(self, code):
        """Return (unknown_hard, unknown_soft, used)."""
        used = sorted(set(API_PATTERN.findall(code or "")))
        if not self.loaded:
            return [], [], used
        soft = self.soft()
        hard, warn = [], []
        for sym in used:
            if sym in self.known:
                continue
            (warn if sym in soft else hard).append(sym)
        return hard, warn, used

    def check(self, code):
        """Return (ok, reason, warns)."""
        hard, warn, used = self.scan(code)
        if hard:
            return False, "unknown CMO symbols (not in the local index): " + \
                ", ".join(hard), warn
        return True, "", warn
