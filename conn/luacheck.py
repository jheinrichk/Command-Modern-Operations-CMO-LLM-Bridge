"""
conn.luacheck  -  cheap pre-injection validation of generated Lua.

Not a full parser. It tokenizes enough to skip comments, quoted strings and
long brackets, then checks bracket balance and block keyword balance. This
catches the truncated or fenced pastes that used to burn a whole cycle.

Also provides the editor lock used in play modes: a call blocklist that stops
scenario-editor functions from being run while a game is in progress.
"""

import re

BLOCK_OPEN = {"function", "if", "for", "while", "do"}
LONG_OPEN = re.compile(r"\[(=*)\[")


def strip_fences(code):
    c = (code or "").strip()
    if c.startswith("```"):
        c = re.sub(r"^```[a-zA-Z]*\s*", "", c)
        c = re.sub(r"```\s*$", "", c)
    return c.strip()


def _tokens(code):
    """Yield (kind, text, line) for code, skipping comments and strings."""
    i, line, n = 0, 1, len(code)
    while i < n:
        ch = code[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        # long comment or long string
        if code.startswith("--", i):
            m = LONG_OPEN.match(code, i + 2)
            if m:
                close = "]" + m.group(1) + "]"
                end = code.find(close, m.end())
                if end < 0:
                    yield ("error", "unterminated long comment", line)
                    return
                line += code.count("\n", i, end)
                i = end + len(close)
                continue
            end = code.find("\n", i)
            i = n if end < 0 else end
            continue
        m = LONG_OPEN.match(code, i)
        if m:
            close = "]" + m.group(1) + "]"
            end = code.find(close, m.end())
            if end < 0:
                yield ("error", "unterminated long string", line)
                return
            line += code.count("\n", i, end)
            i = end + len(close)
            continue
        if ch in "\"'":
            j, esc = i + 1, False
            while j < n:
                c2 = code[j]
                if esc:
                    esc = False
                elif c2 == "\\":
                    esc = True
                elif c2 == ch:
                    break
                elif c2 == "\n":
                    yield ("error", "unterminated string", line)
                    return
                j += 1
            if j >= n:
                yield ("error", "unterminated string", line)
                return
            i = j + 1
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (code[j].isalnum() or code[j] == "_"):
                j += 1
            yield ("word", code[i:j], line)
            i = j
            continue
        if ch in "()[]{}":
            yield ("punct", ch, line)
            i += 1
            continue
        i += 1


def check(code):
    """Return (ok, problems, stats)."""
    code = strip_fences(code)
    problems = []
    if not code:
        return False, ["empty code block"], {}
    depth = {"(": 0, "[": 0, "{": 0}
    pair = {")": "(", "]": "[", "}": "{"}
    blocks, then_seen, repeats, funcs = 0, 0, 0, 0
    awaiting_do = 0
    prev = ""
    for kind, text, line in _tokens(code):
        if kind == "error":
            problems.append("line {}: {}".format(line, text))
            continue
        if kind == "punct":
            if text in depth:
                depth[text] += 1
            else:
                o = pair[text]
                depth[o] -= 1
                if depth[o] < 0:
                    problems.append("line {}: unmatched '{}'".format(line, text))
                    depth[o] = 0
            continue
        w = text.lower()
        if w == "function":
            blocks += 1
            funcs += 1
        elif w == "if":
            blocks += 1
        elif w in ("for", "while"):
            # the block opens here; the 'do' that closes the header is not
            # a second block
            blocks += 1
            awaiting_do += 1
        elif w == "do":
            if awaiting_do > 0:
                awaiting_do -= 1
            else:
                blocks += 1
        elif w == "then":
            then_seen += 1
        elif w == "repeat":
            repeats += 1
        elif w == "until":
            repeats -= 1
        elif w == "end":
            blocks -= 1
            if blocks < 0:
                problems.append("line {}: 'end' without a matching block".format(line))
                blocks = 0
        prev = w
    for sym, d in depth.items():
        if d > 0:
            problems.append("{} unclosed '{}'".format(d, sym))
    if blocks > 0:
        problems.append("{} block(s) missing 'end'".format(blocks))
    if repeats > 0:
        problems.append("{} 'repeat' without 'until'".format(repeats))
    stats = {"chars": len(code), "lines": code.count("\n") + 1, "functions": funcs}
    return (not problems), problems, stats


def scan_blocklist(code, blocked):
    """Return the blocked calls present in code.

    Any use of the name counts, not only Name( : Lua also calls with
    Name{...} and Name"...", and local f = Name aliases it. Comments are
    removed first so a note that mentions a name does not block."""
    code = strip_fences(code)
    code = re.sub(r"--\[(=*)\[.*?\]\1\]", " ", code, flags=re.S)   # block comments
    code = re.sub(r"--[^\n]*", " ", code)                              # line comments
    hits = []
    for name in blocked or []:
        if re.search(r"\b" + re.escape(name) + r"\b", code):
            hits.append(name)
    return hits


def has_print_contract(code):
    return "NEXT_RECOMMENDED_STATE" in (code or "").upper()
