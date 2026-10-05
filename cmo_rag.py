"""
cmo_rag.py  —  CMO CommandLua Retrieval (Silent Night style)
============================================================
Zero-dependency, stdlib-only lexical RAG over the CMO Lua Unified library.
Mirrors the Silent Night RAG contract: TF-IDF over internal standards, with
a feedback-ingestion channel so retrieval improves as the bridge runs. No
embeddings, no network, no third-party packages — safe on a locked office
machine.

Two retrieval subsystems:

  1. DOC RETRIEVAL  (lexical TF-IDF, cosine)
       corpus = master-library section chunks
              + auto-extracted recipe blocks (snippets/recipe_manifest.json)
              + the authoritative sim-control snippet
              + any ingested feedback notes
       -> query(text, k) returns ranked chunks to inject into the prompt.

  2. PLATFORM LOOKUP  (exact + normalized-key, like the Lua modules)
       source = lua_unified/cmo_lookup_library_clean_v2.csv (18,744 records)
       -> lookup(name), lookup_key(key), get_type(type), suggest(substr).

Build once:   python cmo_rag.py --build
Query:        python cmo_rag.py --query "spawn a CAP box and patrol mission"
Lookup:       python cmo_rag.py --lookup "F-15C Eagle"
Feedback:     python cmo_rag.py --feedback "prefer GUIDs for missions" --tag missions

The bridge imports CmoRag and calls .retrieve_context(task) each cycle.
"""

import argparse
import csv
import json
import math
import re
import io
import zipfile
from contextlib import contextmanager
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE / "lua_unified"
IDX = HERE / "rag_index"
IDX.mkdir(exist_ok=True)

MD_PATH = LIB / "cmo_comprehensive_unified_library_v3.md"
MANIFEST = LIB / "snippets" / "recipe_manifest.json"
SIMCTL = LIB / "snippets" / "_sim_control_authoritative.lua"
CSV_PATH = LIB / "cmo_lookup_library_clean_v2.csv"

# Knowledge pack v4: preferred when present. The v4 master reference carries
# the environment facts (callable-userdata API, wrapper shapes, error globals)
# that v3 lacked, and its CSV supersedes the v2 lookup layer.
KP = HERE / "knowledge_pack"
KP_MD = KP / "cmo_bridge_master_reference_v4.md"
KP_CSV = KP / "cmo_lookup_library_clean.csv"
KP_SYSPROMPT = KP / "CMO_BRIDGE_SYSTEM_PROMPT.txt"
KP_PROTOCOL = KP / "CMO_BRIDGE_TERMINAL_PROTOCOL.md"

DOC_INDEX = IDX / "doc_index.json"
LOOKUP_INDEX = IDX / "lookup_index.json"
FEEDBACK = IDX / "feedback.jsonl"

# Session knowledge: what the bridge learned by RUNNING scenarios. These are
# first-class retrievable documents and a small pinned subset is injected
# into every cycle regardless of lexical match.
KP_LESSONS = KP / "CMO_LUA_SESSION_RAG.md"
KP_PINNED = KP / "CMO_PINNED_RULES.txt"
KP_PINNED_COMMANDER = KP / "CMO_PINNED_RULES_COMMANDER.txt"

# lesson section tags that matter to a commander giving orders; build,
# playtest pacing, database and event-plumbing lessons stay out of the
# orders prompt
COMMANDER_LESSON_TAGS = ("doctrine", "posture", "missions", "units and movement",
                         "special actions", "process")
LESSONS = IDX / "lessons.jsonl"          # auto-harvested from Lua output

# DB3000 v515 corrected catalog: type-namespaced DBIDs with operator country
# and service, plus the aircraft -> loadout relation. This is what caught
# nine wrong-nation aircraft that a name search had passed.
DB515 = KP / "db515"
DB515_PLATFORMS = DB515 / "cmo_platform_lookup_corrected.csv"
DB515_LOADOUTS = DB515 / "cmo_aircraft_loadouts.csv"
DB515_ARCHIVE = HERE / "data" / "CMO_DB515_FINAL_LOOKUP_LIBRARY.zip"
DB515_INDEX = IDX / "db515_index.json"


@contextmanager
def open_db515_loadouts():
    """Read the local CSV or its identical copy in the complete data archive."""
    if DB515_LOADOUTS.exists():
        with DB515_LOADOUTS.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
            yield stream
    else:
        with zipfile.ZipFile(DB515_ARCHIVE) as archive:
            with archive.open("CMO_DB515_FINAL_LOOKUP_LIBRARY/cmo_aircraft_loadouts.csv") as raw:
                with io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="") as stream:
                    yield stream

_TOKEN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")


def normalize_key(text):
    if text is None:
        return None
    out = str(text).lower()
    out = re.sub(r"[^0-9a-z]+", "_", out)
    out = re.sub(r"_+", "_", out).strip("_")
    return out or None


_SUBWORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|[0-9]+")


def tokenize(text):
    """Emit whole CMO identifiers (ScenEdit_AddUnit) AND their subword pieces
    (scenedit, add, unit) so plain-language queries like 'pause the sim' match
    VP_PauseSimulation. Subwords come from camelCase and underscore splits."""
    out = []
    for t in _TOKEN.findall(text or ""):
        low = t.lower()
        out.append(low)
        parts = _SUBWORD.findall(t)
        if len(parts) > 1:
            out.extend(p.lower() for p in parts if len(p) >= 2)
    return out


# --------------------------------------------------------------------------
# Corpus construction
# --------------------------------------------------------------------------
def _chunk_markdown(md_text):
    """Split the master library into heading-scoped chunks."""
    chunks = []
    cur_head = "Preamble"
    buf = []
    for line in md_text.splitlines():
        if line.startswith("#"):
            if buf and any(x.strip() for x in buf):
                chunks.append((cur_head, "\n".join(buf).strip()))
            cur_head = line.lstrip("#").strip()
            buf = []
        else:
            buf.append(line)
    if buf and any(x.strip() for x in buf):
        chunks.append((cur_head, "\n".join(buf).strip()))
    # drop trivially short chunks
    return [(h, b) for h, b in chunks if len(b) >= 40]


def build_corpus():
    docs = []  # each: {id, kind, tag, title, text}

    if KP_MD.exists():
        for i, (head, body) in enumerate(_chunk_markdown(KP_MD.read_text(
                encoding="utf-8", errors="replace"))):
            docs.append({
                "id": "v4:{}".format(i),
                "kind": "doc",
                "tag": "reference_v4",
                "title": head,
                "text": head + "\n" + body,
            })
    for extra, tag in ((KP_SYSPROMPT, "operating_rules"), (KP_PROTOCOL, "protocol")):
        if extra.exists():
            docs.append({
                "id": "kp:{}".format(extra.stem),
                "kind": "doc",
                "tag": tag,
                "title": extra.stem.replace("_", " "),
                "text": extra.read_text(encoding="utf-8", errors="replace"),
            })

    if MD_PATH.exists():
        for i, (head, body) in enumerate(_chunk_markdown(MD_PATH.read_text(
                encoding="utf-8", errors="replace"))):
            docs.append({
                "id": "doc:{}".format(i),
                "kind": "doc",
                "tag": "reference",
                "title": head,
                "text": head + "\n" + body,
            })

    if MANIFEST.exists():
        for i, b in enumerate(json.loads(MANIFEST.read_text(encoding="utf-8"))):
            docs.append({
                "id": "recipe:{}".format(i),
                "kind": "recipe",
                "tag": b.get("topic", "misc"),
                "title": b.get("heading", "recipe"),
                "text": "{}\n{}".format(b.get("heading", ""), b.get("code", "")),
            })

    if SIMCTL.exists():
        docs.append({
            "id": "simctl:0",
            "kind": "recipe",
            "tag": "sim_control",
            "title": "Authoritative simulation control (play/pause/time-compression/lifecycle)",
            "text": SIMCTL.read_text(encoding="utf-8", errors="replace"),
        })

    # session lessons: the hand-written knowledge file, one doc per bullet
    if KP_LESSONS.exists():
        for i, (head, body) in enumerate(_chunk_markdown(KP_LESSONS.read_text(
                encoding="utf-8", errors="replace"))):
            # split each section into its bold-led paragraphs so a single
            # lesson retrieves on its own rather than dragging the section
            raw = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
            # a paragraph that is itself a code block is the example for the
            # lesson before it; merge them so the fence never becomes a title
            paras = []
            for p in raw:
                if p.startswith("```") and paras:
                    paras[-1] = paras[-1] + "\n\n" + p
                else:
                    paras.append(p)
            # separators and short lead-ins are not lessons
            paras = [p for p in paras
                     if not p.startswith(("---", "```", "Each entry", "Paste the"))
                     and len(p) >= 60]
            for j, p in enumerate(paras):
                first = p.split("\n")[0]
                title = re.sub(r"[`*_]+", "", first).strip()[:70] or "lesson"
                docs.append({
                    "id": "lesson:{}:{}".format(i, j),
                    "kind": "lesson",
                    "tag": head.strip("# ").lower(),
                    "title": head.strip("# ") + " / " + title,
                    "text": p,
                })

    # lessons harvested automatically from Lua output during runs
    if LESSONS.exists():
        for i, line in enumerate(LESSONS.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            docs.append({
                "id": "harvest:{}".format(i),
                "kind": "lesson",
                "tag": rec.get("tag", "harvest"),
                "title": "Harvested: " + rec.get("tag", "note"),
                "text": rec.get("text", ""),
            })

    # ingested feedback becomes first-class retrievable docs
    if FEEDBACK.exists():
        for i, line in enumerate(FEEDBACK.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            docs.append({
                "id": "fb:{}".format(i),
                "kind": "feedback",
                "tag": rec.get("tag", "feedback"),
                "title": "Feedback: " + rec.get("tag", "note"),
                "text": rec.get("text", ""),
            })
    return docs


# --------------------------------------------------------------------------
# TF-IDF index
# --------------------------------------------------------------------------
def build_doc_index():
    docs = build_corpus()
    df = Counter()
    doc_tokens = []
    for d in docs:
        toks = tokenize(d["text"])
        tf = Counter(toks)
        doc_tokens.append(tf)
        for term in tf:
            df[term] += 1
    N = max(1, len(docs))
    idf = {t: math.log((N + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    vectors = []
    for tf in doc_tokens:
        vec = {}
        for term, c in tf.items():
            vec[term] = (1 + math.log(c)) * idf.get(term, 0.0)
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: v / norm for t, v in vec.items()})

    payload = {
        "meta": {"docs": N, "terms": len(idf)},
        "idf": idf,
        "docs": [{k: d[k] for k in ("id", "kind", "tag", "title", "text")} for d in docs],
        "vectors": vectors,
    }
    DOC_INDEX.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def build_lookup_index():
    by_name, by_key, by_type = {}, {}, defaultdict(list)
    records = []
    src = KP_CSV if KP_CSV.exists() else CSV_PATH
    if src.exists():
        with src.open(encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("Name") or "").strip()
                typ = (row.get("Type") or "").strip()
                cost = (row.get("Cost") or "").strip()
                key = (row.get("Key") or "").strip() or normalize_key(name)
                idx = len(records)
                records.append({"name": name, "type": typ, "cost": cost, "key": key})
                by_name.setdefault(name, idx)
                if key:
                    by_key.setdefault(key, idx)
                if typ:
                    by_type[typ].append(idx)
    payload = {
        "records": records,
        "by_name": by_name,
        "by_key": by_key,
        "by_type": {k: v for k, v in by_type.items()},
        "count": len(records),
    }
    LOOKUP_INDEX.write_text(json.dumps(payload), encoding="utf-8")
    return payload


# --------------------------------------------------------------------------
# Runtime engine
# --------------------------------------------------------------------------
def build_db515_index():
    """Type-namespaced platform catalog + aircraft->loadout relation from the
    DB3000 v515 extraction. Country codes in the platform CSV are numeric;
    the loadout CSV carries the resolved names, so a code map is built from
    it and applied to every platform row."""
    if not DB515_PLATFORMS.exists():
        return None
    code_country, code_service = {}, {}
    loadouts = {}          # aircraft_dbid -> {loadout_id: name}
    if DB515_LOADOUTS.exists() or DB515_ARCHIVE.exists():
        with open_db515_loadouts() as f:
            for r in csv.DictReader(f):
                try:
                    ac, lo = int(r["aircraft_dbid"]), int(r["loadout_dbid"])
                except (KeyError, ValueError):
                    continue
                loadouts.setdefault(str(ac), {})[str(lo)] = (r.get("loadout_name") or "")[:80]
                cc, cs = r.get("aircraft_operatorcountry"), r.get("aircraft_operatorservice")
                if cc and r.get("operator_country"):
                    code_country[cc] = r["operator_country"]
                if cs and r.get("operator_service"):
                    code_service[cs] = r["operator_service"]
    plats = {}             # "type:dbid" -> record
    by_name = {}           # normalized name -> ["type:dbid", ...]
    with DB515_PLATFORMS.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t, d = r["platform_type"].strip(), int(r["dbid"])
            except (KeyError, ValueError):
                continue
            key = "{}:{}".format(t, d)
            rec = {
                "type": t, "dbid": d, "name": r.get("name", ""),
                "country": code_country.get(r.get("operatorcountry", ""), r.get("operatorcountry", "")),
                "service": code_service.get(r.get("operatorservice", ""), r.get("operatorservice", "")),
                "year": r.get("yearcommissioned", ""),
                "hypothetical": (r.get("hypothetical", "0") or "0") not in ("0", ""),
                "deprecated": (r.get("deprecated", "0") or "0") not in ("0", ""),
            }
            plats[key] = rec
            by_name.setdefault(normalize_key(rec["name"]), []).append(key)
    idx = {"meta": {"platforms": len(plats), "aircraft_with_loadouts": len(loadouts)},
           "platforms": plats, "by_name": by_name, "loadouts": loadouts}
    DB515_INDEX.write_text(json.dumps(idx), encoding="utf-8")
    return idx


# rows in the build files look like:  { side="X", type="Ship", name="Y", ... dbid=123, loadoutid=456 ... }
_UNIT_ROW = re.compile(
    r'side\s*=\s*"(?P<side>[^"]+)"\s*,\s*type\s*=\s*"(?P<ptype>[^"]+)"\s*,\s*name\s*=\s*"(?P<name>[^"]+)"'
    r'(?P<rest>[^}]*?)dbid\s*=\s*(?P<dbid>\d+)(?P<tail>[^}]*)')
_LOADOUT = re.compile(r'loadoutid\s*=\s*(\d+)')


class CmoRag:
    def __init__(self, autobuild=True):
        if autobuild and not DOC_INDEX.exists():
            build_doc_index()
        if autobuild and not LOOKUP_INDEX.exists():
            build_lookup_index()
        self.doc = json.loads(DOC_INDEX.read_text(encoding="utf-8")) if DOC_INDEX.exists() else None
        self.lk = json.loads(LOOKUP_INDEX.read_text(encoding="utf-8")) if LOOKUP_INDEX.exists() else None
        if autobuild and not DB515_INDEX.exists():
            try:
                build_db515_index()
            except Exception:
                pass
        self.db = json.loads(DB515_INDEX.read_text(encoding="utf-8")) if DB515_INDEX.exists() else None

    # ---- DB3000 v515 catalog: type-aware, with nationality ----
    def platform(self, ptype, dbid):
        """Exact record for a (type, dbid) pair, or None. Types are namespaced:
        Ship 3226 and Aircraft 3226 are different entries."""
        if not self.db:
            return None
        return self.db["platforms"].get("{}:{}".format(ptype, int(dbid)))

    def find_platform(self, name, ptype=None, country=None):
        """All catalog entries matching a name, optionally narrowed by type
        and operator country. Use this instead of a bare name search: nine
        of nine aircraft were once the wrong nation by name alone."""
        if not self.db:
            return []
        keys = self.db["by_name"].get(normalize_key(name), [])
        out = [self.db["platforms"][k] for k in keys]
        if ptype:
            out = [r for r in out if r["type"].lower() == ptype.lower()]
        if country:
            out = [r for r in out if country.lower() in (r["country"] or "").lower()]
        return out

    def loadouts_for(self, aircraft_dbid):
        if not self.db:
            return {}
        return self.db["loadouts"].get(str(int(aircraft_dbid)), {})

    def validate_pairing(self, aircraft_dbid, loadout_id):
        """True if the loadout belongs to the airframe in v515."""
        return str(int(loadout_id)) in self.loadouts_for(aircraft_dbid)

    def validate_lua_units(self, code):
        """Scan a build script's unit rows and return a list of warnings.
        Non-blocking by design: the author decides. Catches the classes of
        error that cost the Hormuz project the most: unknown dbid for the
        type, wrong-nation variants, hypothetical/deprecated entries, and
        loadouts that do not belong to the airframe."""
        warns = []
        if not self.db or not code:
            return warns
        for m in _UNIT_ROW.finditer(code):
            side, ptype, name, dbid = m.group("side"), m.group("ptype"), m.group("name"), int(m.group("dbid"))
            rec = self.platform(ptype, dbid)
            if rec is None:
                warns.append("UNKNOWN DBID {}:{} for '{}' ({})".format(ptype, dbid, name, side))
                continue
            if rec["hypothetical"]:
                warns.append("HYPOTHETICAL entry {}:{} '{}' used for '{}'".format(
                    ptype, dbid, rec["name"], name))
            if rec["deprecated"]:
                warns.append("DEPRECATED entry {}:{} '{}' used for '{}'".format(
                    ptype, dbid, rec["name"], name))
            # nationality check for the two combatant sides. Generic and
            # Commercial entries (airfields, ports, structures, merchant
            # hulls) have no nation and are exempt.
            c = (rec["country"] or "").lower()
            generic = c in ("", "generic", "commercial", "civilian", "n/a", "none")
            if generic:
                c = ""
            if side == "United States" and c and "united states" not in c:
                warns.append("WRONG NATION {}:{} '{}' is {} / {} but assigned to United States as '{}'".format(
                    ptype, dbid, rec["name"], rec["country"], rec["service"], name))
            if side == "Iran" and c and "iran" not in c:
                warns.append("WRONG NATION {}:{} '{}' is {} / {} but assigned to Iran as '{}'".format(
                    ptype, dbid, rec["name"], rec["country"], rec["service"], name))
            if ptype == "Aircraft":
                lm = _LOADOUT.search(m.group("tail") or "") or _LOADOUT.search(m.group("rest") or "")
                if lm:
                    lo = int(lm.group(1))
                    if not self.validate_pairing(dbid, lo):
                        warns.append("LOADOUT {} is not valid for airframe {}:{} '{}' ('{}')".format(
                            lo, ptype, dbid, rec["name"], name))
                    elif lo in (3, 4) and side in ("United States", "Iran"):
                        # civil traffic on neutral sides is unarmed by design
                        warns.append("UNARMED loadout {} (Reserve/Maintenance) on '{}'; an AI-flown aircraft with this will not sortie".format(
                            lo, name))
        return warns

    # ---- doc retrieval ----
    def query(self, text, k=6, kinds=None):
        if not self.doc:
            return []
        idf = self.doc["idf"]
        tf = Counter(tokenize(text))
        qv = {t: (1 + math.log(c)) * idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        qv = {t: v / norm for t, v in qv.items()}
        scored = []
        for d, vec in zip(self.doc["docs"], self.doc["vectors"]):
            if kinds and d["kind"] not in kinds:
                continue
            s = sum(qv.get(t, 0.0) * w for t, w in vec.items())
            if s > 0:
                scored.append((s, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": round(s, 4), **d} for s, d in scored[:k]]

    @staticmethod
    def _clip(text, n):
        """Slice a doc excerpt without leaving a code fence open. The
        reference chunks carry fences inside them; a raw slice can end in
        the middle of one and every later fence in the prompt then inverts."""
        t = text[:n]
        if t.count("```") % 2:
            t += "\n```"
        return t

    def pinned_rules(self, profile="design"):
        """The always-on rules. Short, and injected verbatim every cycle.
        The commander profile gets a different, shorter set: rules about
        giving orders inside a running turn, not about building scenarios."""
        path = KP_PINNED_COMMANDER if profile == "commander" else KP_PINNED
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace").strip()
        return ""

    @staticmethod
    def _lesson_visible(doc, profile, side):
        """Play-harvested lessons are tagged play:<side>:... and are visible
        only to that side's commander, so one LLM commander never learns
        from what the other printed. Design sees everything."""
        tag = doc.get("tag", "") or ""
        if tag.startswith("play:"):
            if profile != "commander":
                return True
            owner = tag.split(":")[1] if ":" in tag else ""
            return bool(side) and owner == side
        if profile == "commander":
            return any(t in tag for t in COMMANDER_LESSON_TAGS)
        return True

    def retrieve_context(self, task, k_recipes=5, k_docs=3, max_chars=6000,
                         k_lessons=4, profile="design", side=None):
        """Assemble a compact grounding block for the LLM prompt.

        Order matters: pinned rules first (always), then the lessons that
        match this task, then recipes, then reference notes. Lessons are
        what the bridge learned by running scenarios; they outrank the
        reference because they were observed on THIS build.
        """
        recipes = self.query(task, k=k_recipes, kinds={"recipe"})
        # over-fetch lessons, then filter by visibility for this profile/side
        lessons = [d for d in self.query(task, k=k_lessons * 4, kinds={"lesson", "feedback"})
                   if self._lesson_visible(d, profile, side)][:k_lessons]
        docs = self.query(task, k=k_docs, kinds={"doc"})
        if profile == "commander":
            # sim-control and build recipes are not orders
            recipes = [r for r in recipes
                       if r.get("tag") not in ("sim_control", "scenario_state", "events")]
        parts = ["## RETRIEVED CMO CONTEXT (from local unified library — do NOT search online)"]
        pinned = self.pinned_rules(profile)
        if pinned:
            parts.append("\n### PINNED RULES (apply every {})\n".format(
                "turn" if profile == "commander" else "cycle") + pinned)
        for d in lessons:
            parts.append("\n### LESSON [{}] {}\n{}".format(d["tag"], d["title"], self._clip(d["text"], 600)))
        for d in recipes:
            parts.append("\n### RECIPE [{}] {}\n```lua\n{}\n```".format(
                d["tag"], d["title"], _codeonly(d["text"])))
        for d in docs:
            parts.append("\n### NOTE [{}] {}\n{}".format(d["kind"], d["title"], self._clip(d["text"], 1200)))
        # assemble within budget at PART boundaries so a recipe's code fence
        # is never cut in half. Pinned rules always fit. Lessons may take at
        # most half of what remains, so a DESIGN cycle still gets its code
        # examples and a PLAYTEST cycle still gets its lessons.
        head = parts[0] + ("\n" + parts[1] if pinned else "")
        rest = parts[2:] if pinned else parts[1:]
        budget = max(1500, max_chars - len(head))
        lesson_cap = budget // 2
        block, used, lused = [head], 0, 0
        for p in rest:
            is_lesson = p.startswith("\n### LESSON")
            if is_lesson and lused + len(p) > lesson_cap:
                continue
            if used + len(p) + 1 > budget:
                continue
            block.append(p)
            used += len(p) + 1
            if is_lesson:
                lused += len(p)
        return "\n".join(block)

    # ---- lesson harvesting (the bridge learns from its own runs) ----
    _HARVEST_PATTERNS = [
        # explicit note lines the model prints in its Lua output
        re.compile(r"^\s*(?:RAG_NOTE|LESSON)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        # the same note still inside the CODE, so it is learned even when the
        # console capture comes back empty:  print("RAG_NOTE: ...")
        re.compile(r"print\s*\(\s*(.+?RAG_NOTE\s*:.+?)\)\s*(?:\n|$)", re.IGNORECASE),
        # the keystore pattern used throughout the Hormuz playtests, in both
        # the direct form and the pcall form:
        #   ScenEdit_SetKeyValue("rag_x", "...")
        #   pcall(ScenEdit_SetKeyValue, "rag_x", "..." .. "...")
        re.compile(r"ScenEdit_SetKeyValue\s*,?\s*\(?\s*['\"](rag_[A-Za-z0-9_]+)['\"]\s*,\s*(.+?)\)\s*(?:\n|$)",
                   re.DOTALL),
    ]

    _LUA_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'')

    @staticmethod
    def _flatten_lua_string(expr):
        """Turn a Lua string expression like  "a" .. x .. "b"  into prose:
        keep the literals in order, drop the dynamic pieces. Double- and
        single-quoted literals are matched separately so an apostrophe
        inside a double-quoted string is text, not a delimiter."""
        parts = []
        for m in CmoRag._LUA_LITERAL.finditer(expr):
            lit = m.group(1) if m.group(1) is not None else m.group(2)
            lit = lit.replace("\\'", "'").replace('\\"', '"')
            if lit.strip():
                parts.append(lit.strip())
        text = re.sub(r"\s+", " ", " ".join(parts))
        return text.strip()

    @staticmethod
    def _is_telemetry(text):
        """A readout such as 'pass=8 fail=2 iran_air=2' is state, not a
        lesson. Reject when key=value tokens dominate the prose."""
        toks = text.split()
        if not toks:
            return True
        kv = sum(1 for t in toks if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=[^\s]*", t))
        words = sum(1 for t in toks if re.fullmatch(r"[A-Za-z][A-Za-z'\-]+", t))
        return (kv >= 2 and words < 12) or words < 5

    def harvest_lessons(self, *texts):
        """Pull lesson candidates out of Lua code and console output.
        Returns a list of (tag, text). Dedupe happens in ingest_lesson."""
        out = []
        seen = set()
        def push(tag, t):
            t = t.strip()
            if len(t) <= 20 or self._is_telemetry(t):
                return
            k = normalize_key(t)[:120]
            if k in seen:
                return
            seen.add(k)
            out.append((tag, t[:800]))
        for text in texts:
            if not text:
                continue
            # output form: a bare RAG_NOTE line
            for m in self._HARVEST_PATTERNS[0].finditer(text):
                line = m.group(1).strip()
                # if this "line" is actually inside a print(...) in code, the
                # code pattern below handles it; skip the raw form there
                if not line.startswith(('"', "'")):
                    push("harvest", line)
            # code form: print("RAG_NOTE: ...")
            for m in self._HARVEST_PATTERNS[1].finditer(text):
                t = self._flatten_lua_string(m.group(1))
                t = re.sub(r"^\s*RAG_NOTE\s*:\s*", "", t, flags=re.IGNORECASE)
                push("harvest", t)
            # keystore form, direct or pcall, single or multi-line
            for m in self._HARVEST_PATTERNS[2].finditer(text):
                tag, expr = m.group(1), m.group(2)
                push(tag, self._flatten_lua_string(expr))
        return out

    def ingest_lesson(self, text, tag="harvest", rebuild=False):
        """Append a lesson if it is not already known. Returns True if new."""
        key = normalize_key(text)[:160]
        known = set()
        if LESSONS.exists():
            for line in LESSONS.read_text(encoding="utf-8").splitlines():
                try:
                    known.add(normalize_key(json.loads(line).get("text", ""))[:160])
                except Exception:
                    pass
        if key in known:
            return False
        with LESSONS.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"text": text.strip(), "tag": tag}, ensure_ascii=False) + "\n")
        if rebuild:
            build_doc_index()
            self.doc = json.loads(DOC_INDEX.read_text(encoding="utf-8"))
        return True

    def forget_lesson(self, substring):
        """Remove every harvested lesson containing the substring (case-
        insensitive) and rebuild. The safety valve for a hypothesis that
        was later disproven: a store holding both the claim and the
        retraction can surface either."""
        if not LESSONS.exists():
            return 0
        keep, dropped = [], 0
        needle = substring.lower()
        for line in LESSONS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if needle in (rec.get("text", "") + " " + rec.get("tag", "")).lower():
                dropped += 1
            else:
                keep.append(line)
        LESSONS.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
        build_doc_index()
        self.doc = json.loads(DOC_INDEX.read_text(encoding="utf-8"))
        return dropped

    def ingest_many(self, pairs):
        """Ingest a batch of (tag, text); rebuild the index once at the end."""
        new = 0
        for tag, text in pairs:
            if self.ingest_lesson(text, tag=tag, rebuild=False):
                new += 1
        if new:
            build_doc_index()
            self.doc = json.loads(DOC_INDEX.read_text(encoding="utf-8"))
        return new

    # ---- platform lookup ----
    def lookup(self, name):
        if not self.lk:
            return None
        i = self.lk["by_name"].get(name)
        if i is None:
            i = self.lk["by_key"].get(normalize_key(name))
        return self.lk["records"][i] if i is not None else None

    def lookup_key(self, key):
        if not self.lk:
            return None
        i = self.lk["by_key"].get(key)
        return self.lk["records"][i] if i is not None else None

    def get_type(self, typ):
        if not self.lk:
            return []
        return [self.lk["records"][i] for i in self.lk["by_type"].get(typ, [])]

    def suggest(self, substr, limit=15):
        if not self.lk:
            return []
        s = substr.lower()
        out = []
        for r in self.lk["records"]:
            if s in r["name"].lower():
                out.append(r)
                if len(out) >= limit:
                    break
        return out

    # ---- feedback ingestion (Silent Night style) ----
    def ingest_feedback(self, text, tag="feedback", rebuild=True):
        rec = {"text": text.strip(), "tag": tag}
        with FEEDBACK.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if rebuild:
            build_doc_index()
            self.doc = json.loads(DOC_INDEX.read_text(encoding="utf-8"))
        return rec


def _codeonly(text):
    # recipe docs are "heading\n<code>"; strip the leading heading line
    lines = text.splitlines()
    return "\n".join(lines[1:]) if len(lines) > 1 else text


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="CMO CommandLua RAG (stdlib only)")
    ap.add_argument("--build", action="store_true", help="build both indexes")
    ap.add_argument("--query", help="retrieve docs/recipes for a task")
    ap.add_argument("--lesson", help="ingest a session lesson (what the bridge learned)")
    ap.add_argument("--harvest", help="path to a Lua or console file to harvest lessons from")
    ap.add_argument("--forget", help="remove harvested lessons containing this text (a disproven hypothesis)")
    ap.add_argument("--lessons", action="store_true", help="list the harvested lessons")
    ap.add_argument("--platform", help="find v515 platform entries by name, e.g. 'P-8A Poseidon'")
    ap.add_argument("--ptype", help="narrow --platform by type: Aircraft/Ship/Submarine/Facility")
    ap.add_argument("--validate", help="path to a Lua build file; validate its unit rows against v515")
    ap.add_argument("--lookup", help="exact/normalized platform lookup")
    ap.add_argument("--suggest", help="substring platform search")
    ap.add_argument("--type", help="list records of a type (Ship, Aircraft, ...)")
    ap.add_argument("--feedback", help="ingest a feedback note")
    ap.add_argument("--tag", default="feedback", help="tag for the feedback note")
    ap.add_argument("-k", type=int, default=6)
    args = ap.parse_args()

    if args.build:
        d = build_doc_index()
        l = build_lookup_index()
        print("doc_index: {} docs / {} terms".format(d["meta"]["docs"], d["meta"]["terms"]))
        print("lookup_index: {} records".format(l["count"]))
        b = build_db515_index()
        if b:
            print("db515_index: {} platforms, {} aircraft with loadouts".format(
                b["meta"]["platforms"], b["meta"]["aircraft_with_loadouts"]))
        return

    rag = CmoRag()

    if args.lesson:
        print("new lesson" if rag.ingest_lesson(args.lesson, tag=args.tag, rebuild=True)
              else "already known")
        return
    if args.forget:
        print("forgot {} lesson(s)".format(rag.forget_lesson(args.forget)))
        return
    if args.lessons:
        if LESSONS.exists():
            for i, line in enumerate(LESSONS.read_text(encoding="utf-8").splitlines(), 1):
                try:
                    rec = json.loads(line)
                    print("{:3d} [{}] {}".format(i, rec.get("tag", ""), rec.get("text", "")[:110]))
                except Exception:
                    pass
        else:
            print("no harvested lessons yet")
        return
    if args.harvest:
        text = Path(args.harvest).read_text(encoding="utf-8", errors="replace")
        pairs = rag.harvest_lessons(text)
        n = rag.ingest_many(pairs)
        print("harvested {} candidate(s), {} new".format(len(pairs), n))
        return
    if args.platform:
        rows = rag.find_platform(args.platform, ptype=args.ptype)
        if not rows:
            print("no exact v515 match; try --suggest for substrings")
        for r in rows:
            print("{:10s} dbid={:<6d} {:34s} {:18s} {:14s} {}{}{}".format(
                r["type"], r["dbid"], r["name"][:34], r["country"][:18], r["service"][:14],
                r["year"], "  HYPOTHETICAL" if r["hypothetical"] else "",
                "  DEPRECATED" if r["deprecated"] else ""))
        return
    if args.validate:
        code = Path(args.validate).read_text(encoding="utf-8", errors="replace")
        w = rag.validate_lua_units(code)
        print("{} warning(s)".format(len(w)))
        for x in w:
            print("  ", x)
        return
    if args.feedback:
        rec = rag.ingest_feedback(args.feedback, tag=args.tag)
        print("ingested:", rec)
        return
    if args.query:
        for d in rag.query(args.query, k=args.k):
            print("[{:.3f}] {:8s} {:16s} {}".format(d["score"], d["kind"], d["tag"], d["title"]))
        return
    if args.lookup:
        print(json.dumps(rag.lookup(args.lookup), indent=2))
        return
    if args.suggest:
        for r in rag.suggest(args.suggest):
            print("{:10s} {:>12s}  {}".format(r["type"], r["cost"], r["name"]))
        return
    if args.type:
        rows = rag.get_type(args.type)
        print("{} records of type {}".format(len(rows), args.type))
        for r in rows[:20]:
            print("  ", r["name"])
        return
    ap.print_help()


if __name__ == "__main__":
    main()
