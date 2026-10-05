"""
conn.cmologs  -  read CMO's own log files for the model.

CMO writes an after-action log (AALog.txt), per-day exception logs
(ExceptionLog_YYYY_MM_DD.txt), per-day Lua console histories
(LuaHistory_YYYY-MM-DD.txt) and a dated message log per session, all into
one Logs folder:

    Steam   C:\\Program Files (x86)\\Steam\\steamapps\\common\\Command - Modern Operations\\Logs
    Matrix  C:\\Matrix Games\\Command Modern Operations\\Logs   (typical)

The folder is configurable (cmo.logs_folder) and auto-detected otherwise.

What the model gets:
  * an EXCERPT of the AALog: a digest header (counts of kills, hits,
    launches, contacts, events) followed by the tail, capped in lines and
    characters so it always fits the prompt file route
  * a DELTA: only the lines written since the last time a marker was taken,
    which is what a commander wants at the start of each turn
  * the latest exception log or Lua history when asked
"""

import json
import os
import re
import time
from pathlib import Path

STEAM_DEFAULT = r"C:\Program Files (x86)\Steam\steamapps\common\Command - Modern Operations\Logs"
MATRIX_DEFAULTS = [
    r"C:\Matrix Games\Command Modern Operations\Logs",
    r"C:\Matrix Games\Command - Modern Operations\Logs",
    r"C:\Program Files (x86)\Matrix Games\Command Modern Operations\Logs",
]

AALOG = "AALog.txt"

# one line per class of thing worth counting in a digest
DIGEST_PATTERNS = [
    ("destroyed", re.compile(r"\b(destroyed|has been sunk|is sinking|has been destroyed)\b", re.I)),
    ("hits", re.compile(r"\bHIT\b|\bhas impacted\b|\bimpact\b", re.I)),
    ("misses", re.compile(r"\bMISS\b|\bself-destructing\b", re.I)),
    ("launches", re.compile(r"\b(fired|launched|has launched|is attacking)\b", re.I)),
    ("new_contacts", re.compile(r"\bNew contact\b|\bhas been detected\b", re.I)),
    ("contacts_lost", re.compile(r"\bhas been lost\b", re.I)),
    ("events", re.compile(r"\bEvent: '", re.I)),
    ("damage", re.compile(r"\bdamage\b", re.I)),
    ("side_switches", re.compile(r"\bSwitched side to\b", re.I)),
]


def candidate_folders(cfg=None):
    """Ordered list of folders to try: the configured one first, then the
    Steam default, then Matrix defaults, then Steam libraries on other
    drives."""
    out = []
    configured = ""
    if cfg is not None:
        try:
            configured = str(cfg.get("cmo.logs_folder", "") or "").strip()
        except Exception:
            configured = ""
    if configured:
        out.append(configured)
    out.append(STEAM_DEFAULT)
    out.extend(MATRIX_DEFAULTS)
    for drive in "DEFGH":
        out.append(r"{}:\SteamLibrary\steamapps\common\Command - Modern Operations\Logs".format(drive))
        out.append(r"{}:\Steam\steamapps\common\Command - Modern Operations\Logs".format(drive))
    return out


def find_folder(cfg=None):
    """First candidate folder that exists and holds an AALog.txt, else the
    first that merely exists, else None."""
    cands = candidate_folders(cfg)
    for c in cands:
        p = Path(c)
        if p.is_dir() and (p / AALOG).exists():
            return p
    for c in cands:
        if Path(c).is_dir():
            return Path(c)
    return None


class CmoLogs:
    def __init__(self, cfg, state_dir=None, log=None):
        self.cfg = cfg
        self.log = log or (lambda m: None)
        self.folder = find_folder(cfg)
        self.state_dir = Path(state_dir) if state_dir else None
        self._marks = {}
        self._load_marks()

    # -- discovery ----------------------------------------------------
    def available(self):
        return self.folder is not None and (self.folder / AALOG).exists()

    def aalog_path(self):
        return (self.folder / AALOG) if self.folder else None

    def describe(self):
        if not self.folder:
            return "CMO Logs folder not found; set cmo.logs_folder in Settings"
        p = self.aalog_path()
        if p and p.exists():
            return "{} ({} bytes)".format(p, p.stat().st_size)
        return "{} (no {} yet)".format(self.folder, AALOG)

    def latest(self, prefix):
        """Newest file whose name starts with prefix, e.g. 'ExceptionLog_'
        or 'LuaHistory_'. Dated session logs use a YYYY-MM-DD_ prefix."""
        if not self.folder:
            return None
        files = [p for p in self.folder.glob(prefix + "*") if p.is_file()]
        if not files:
            return None
        return max(files, key=lambda p: p.stat().st_mtime)

    # -- reading ------------------------------------------------------
    @staticmethod
    def _read(path, max_bytes=8_000_000):
        try:
            size = path.stat().st_size
            with open(str(path), "rb") as f:
                if size > max_bytes:
                    f.seek(size - max_bytes)
                data = f.read()
            return data.decode("utf-8", errors="replace").replace("\r\r\n", "\n").replace("\r\n", "\n")
        except Exception as ex:
            return ""

    def tail(self, lines=400, max_chars=24000):
        p = self.aalog_path()
        if not p or not p.exists():
            return ""
        text = self._read(p)
        rows = text.splitlines()
        cut = "\n".join(rows[-int(lines):])
        if len(cut) > max_chars:
            cut = cut[-max_chars:]
            cut = cut[cut.find("\n") + 1:]     # start on a whole line
        return cut

    def delta(self, marker, take_marker=True, max_chars=24000):
        """Lines written since the marker was last taken. The first call
        for a marker returns the tail and sets the marker at end of file."""
        p = self.aalog_path()
        if not p or not p.exists():
            return ""
        size = p.stat().st_size
        start = int(self._marks.get(marker, -1))
        if start < 0 or start > size:
            text = self.tail(lines=200, max_chars=max_chars)
        else:
            try:
                with open(str(p), "rb") as f:
                    f.seek(start)
                    data = f.read()
                text = data.decode("utf-8", errors="replace").replace("\r\r\n", "\n").replace("\r\n", "\n")
            except Exception:
                text = ""
            if len(text) > max_chars:
                text = text[-max_chars:]
                text = text[text.find("\n") + 1:]
        if take_marker:
            self._marks[marker] = size
            self._save_marks()
        return text

    def reset_marker(self, marker):
        self._marks.pop(marker, None)
        self._save_marks()

    # -- digest -------------------------------------------------------
    @staticmethod
    def digest(text):
        """Counts of the things a commander or a scenario author cares
        about, so the model reads the summary before the lines."""
        rows = text.splitlines()
        counts = {name: 0 for name, _ in DIGEST_PATTERNS}
        for row in rows:
            for name, pat in DIGEST_PATTERNS:
                if pat.search(row):
                    counts[name] += 1
        first = rows[0][:19] if rows else ""
        last = rows[-1][:19] if rows else ""
        parts = ["AALOG DIGEST: {} lines".format(len(rows))]
        if first or last:
            parts.append("span {} .. {}".format(first, last))
        parts.append(", ".join("{}={}".format(k, v) for k, v in counts.items() if v))
        return " | ".join(p for p in parts if p)

    # -- losses, kills and score from the message log -----------------
    _SIDE_RE = re.compile(r"^\S+ \S+ \S+ - \[([^\]]+)\]\s*(.*)$")
    _UNIT_LOST_RE = re.compile(r"^(.+?) \(([^)]+)\) has been destroyed!?$|^(.+?) is sinking!+$", re.I)
    _COMPONENT_RE = re.compile(r"damage report:", re.I)
    _SCORE_RE = re.compile(r"Score changed from (-?\d+) to (-?\d+)\. Reason: (.*)$", re.I)
    _KILL_RE = re.compile(r"reports BDA status change on contact: (.+?) - Destroyed", re.I)

    @classmethod
    def side_of(cls, row):
        m = cls._SIDE_RE.match(row.strip())
        return m.group(1) if m else None

    @classmethod
    def filter_side(cls, text, for_side):
        """Only the lines that side's own message log would show: its own
        [Side] lines and lines with no side prefix. The AALog is CMO's
        global log, so this is what keeps two LLM commanders honest."""
        if not for_side:
            return text
        keep = []
        for row in (text or "").splitlines():
            side = cls.side_of(row)
            if side is None or side == for_side:
                keep.append(row)
        return "\n".join(keep)

    @classmethod
    def tally(cls, text):
        """Per-side unit losses, kills (from that side's BDA reports) and
        score changes found in message-log text. A 'damage report: ... has
        been destroyed' line is a component, not a unit, and is skipped."""
        losses, kills, score = {}, {}, []
        for row in (text or "").splitlines():
            m = cls._SIDE_RE.match(row.strip())
            if not m:
                continue
            side, body = m.group(1), m.group(2)
            if cls._COMPONENT_RE.search(body):
                continue
            u = cls._UNIT_LOST_RE.match(body)
            if u:
                name = u.group(1) or u.group(3)
                cls_ = u.group(2) or ""
                losses.setdefault(side, []).append((name.strip(), cls_.strip()))
                continue
            k = cls._KILL_RE.search(body)
            if k:
                kills.setdefault(side, []).append(k.group(1).strip())
                continue
            sc = cls._SCORE_RE.search(body)
            if sc:
                score.append((side, int(sc.group(1)), int(sc.group(2)), sc.group(3).strip()))
        return {"losses": losses, "kills": kills, "score": score}

    @classmethod
    def tally_text(cls, text, for_side=None):
        """A short block: losses and kills by side and score changes. With
        for_side, only that side's lines are consulted."""
        t = cls.tally(cls.filter_side(text, for_side))
        out = []
        for side, items in sorted(t["losses"].items()):
            out.append("LOSSES {}: {}".format(side, ", ".join(
                "{} ({})".format(n, c) if c else n for n, c in items[:30])))
        for side, items in sorted(t["kills"].items()):
            seen, uniq = set(), []
            for x in items:
                if x not in seen:
                    seen.add(x)
                    uniq.append(x)
            out.append("KILLS by {}: {}".format(side, ", ".join(uniq[:30])))
        for side, a, b, reason in t["score"]:
            out.append("SCORE {}: {} -> {}  {}".format(side, a, b, reason))
        return "\n".join(out)

    def excerpt(self, mode="tail", marker=None, lines=400, max_chars=24000, for_side=None):
        """A prompt-ready block: digest header then the lines."""
        if mode == "delta" and marker:
            body = self.delta(marker, max_chars=max_chars)
            head = "AALOG since marker '{}'".format(marker)
        else:
            body = self.tail(lines=lines, max_chars=max_chars)
            head = "AALOG tail ({} lines requested)".format(lines)
        body = self.filter_side(body, for_side)
        if not body.strip():
            return "{}: (empty or unavailable: {})".format(head, self.describe())
        tally = self.tally_text(body, for_side=for_side)
        return "{}\n{}\n{}\n{}".format(head, self.digest(body), tally, body) if tally \
            else "{}\n{}\n{}".format(head, self.digest(body), body)

    # -- files for attaching ------------------------------------------
    def write_excerpt(self, dest_dir, label="aalog", **kw):
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / "{}_{}.txt".format(label, time.strftime("%Y%m%d_%H%M%S"))
        path.write_text(self.excerpt(**kw), encoding="utf-8")
        return path

    def copy_latest(self, prefix, dest_dir, label=None):
        src = self.latest(prefix)
        if not src:
            return None
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        text = self._read(src, max_bytes=2_000_000)
        if len(text) > 60000:
            text = text[-60000:]
        path = dest / "{}_{}.txt".format(label or prefix.rstrip("_").lower(),
                                         time.strftime("%Y%m%d_%H%M%S"))
        path.write_text("SOURCE: {}\n\n{}".format(src, text), encoding="utf-8")
        return path

    # -- marker persistence -------------------------------------------
    def _marks_path(self):
        if not self.state_dir:
            return None
        return self.state_dir / "aalog_marks.json"

    def _load_marks(self):
        p = self._marks_path()
        if p and p.exists():
            try:
                self._marks = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                self._marks = {}

    def _save_marks(self):
        p = self._marks_path()
        if not p:
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self._marks), encoding="utf-8")
        except Exception:
            pass


# -- directives from the model ----------------------------------------
# option values are plain tokens so a directive printed from Lua, e.g.
# print('BRIDGE_ATTACH: AALOG tail=800'), does not swallow the closing quote
_ATTACH_RE = re.compile(
    r"BRIDGE_ATTACH\s*:\s*([A-Z_]+)((?:\s+[a-z_]+=[A-Za-z0-9_.\-]+)*)", re.IGNORECASE)


def parse_attach_directives(text):
    """Return a list of (kind, {option: value}) from a reply or console
    output. Kinds: AALOG, MAPSHOT, EXCEPTIONLOG, LUAHISTORY, SESSIONLOG.
    Options: tail=N for AALOG."""
    out = []
    for m in _ATTACH_RE.finditer(text or ""):
        kind = m.group(1).upper()
        opts = {}
        for kv in (m.group(2) or "").split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                opts[k.lower()] = v
        out.append((kind, opts))
    return out
