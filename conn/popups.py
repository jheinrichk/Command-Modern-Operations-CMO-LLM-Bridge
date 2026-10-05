"""
conn.popups  -  CMO's modal message boxes.

A scenario's ScenEdit_MsgBox stops the clock and blocks the CMO window,
including the Lua console, until someone answers it. This module lets the
bridge do that:

  find_popup(title_regex)   the box, if one is open
  read_popup(hwnd)          its title, message text and button labels
  answer_popup(hwnd, ...)   activate it, Tab to the wanted button, Enter

The Tab method is the operator's stated preference. Because the bridge
cannot see keyboard focus, it verifies the box closed afterwards; if it is
still there it clicks the button's live on-screen rectangle (read from the
box itself, so no calibration is involved), and finally tries the button's
accelerator letter. Every route is guarded; nothing here raises into the
run loop.
"""

import ctypes
import re
import time

from .winmgr import IS_WINDOWS, Rect

if IS_WINDOWS:
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

CHOICES = ("YES", "NO", "CANCEL", "OK", "RETRY", "ABORT", "IGNORE")


def _text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return Rect(r.left, r.top, r.right, r.bottom)


def find_popup(title_regex=r"^Incoming message$|^Command: Modern Operations$"):
    """The first visible top-level window whose title matches and whose
    class is a dialog (#32770). Returns hwnd or None."""
    if not IS_WINDOWS:
        return None
    pat = re.compile(title_regex, re.I)
    found = []

    def cb(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            t = _text(hwnd)
            if t and pat.search(t) and _class(hwnd) == "#32770":
                found.append(hwnd)
        except Exception:
            pass
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found[0] if found else None


def read_popup(hwnd):
    """title, message text and the button labels in tab order."""
    if not IS_WINDOWS or not hwnd:
        return None
    statics, buttons = [], []

    def cb(child, _):
        try:
            cls = _class(child)
            t = _text(child)
            if cls == "Static" and t.strip():
                statics.append(t.strip())
            elif cls == "Button" and t.strip():
                buttons.append((child, t.strip().replace("&", "")))
        except Exception:
            pass
        return True

    user32.EnumChildWindows(hwnd, WNDENUMPROC(cb), 0)
    return {"hwnd": hwnd, "title": _text(hwnd), "text": "\n".join(statics),
            "buttons": [b for _, b in buttons], "button_hwnds": [h for h, _ in buttons]}


def _button_index(labels, choice):
    want = (choice or "").strip().upper()
    for i, lab in enumerate(labels):
        if lab.upper() == want:
            return i
    for i, lab in enumerate(labels):
        if lab.upper().startswith(want[:1]) and want:
            return i
    return None


def answer_popup(hwnd, choice, cfg=None, log=None, key=None, click=None):
    """Answer an open box. choice: YES / NO / CANCEL / OK.
    key(name) and click(x, y) are the bridge's input primitives.
    Returns the route that worked, or None."""
    log = log or (lambda m: None)
    if not IS_WINDOWS or not hwnd:
        return None
    info = read_popup(hwnd)
    if not info or not info["buttons"]:
        log("popup: could not read its buttons")
        return None
    labels = info["buttons"]
    idx = _button_index(labels, choice)
    if idx is None:
        log("popup: no button matches {!r}; buttons are {}".format(choice, labels))
        return None
    get = (lambda k, d: cfg.get(k, d)) if cfg is not None else (lambda k, d: d)
    method = str(get("popup.method", "tab")).lower()
    initial = int(get("popup.initial_focus_index", 0))
    settle = float(get("popup.settle_seconds", 0.3))

    def gone():
        return not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd)

    def activate():
        try:
            user32.ShowWindow(hwnd, 5)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(settle)

    routes = {"tab": None, "click": None, "accelerator": None}
    order = [method] + [r for r in ("tab", "click", "accelerator") if r != method]
    for route in order:
        try:
            if route == "tab" and key:
                activate()
                tabs = (idx - initial) % max(1, len(labels))
                for _ in range(tabs):
                    key("tab")
                    time.sleep(0.12)
                key("enter")
            elif route == "click" and click:
                activate()
                r = _rect(info["button_hwnds"][idx])
                click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
            elif route == "accelerator" and key:
                activate()
                if labels[idx].upper() == "CANCEL":
                    key("escape")
                else:
                    key(labels[idx][0].lower())
            else:
                continue
            time.sleep(settle + 0.4)
            if gone():
                log("popup answered {} via {} ({})".format(labels[idx], route, info["text"][:80]))
                return route
            log("popup still open after {}".format(route))
        except Exception as ex:
            log("popup {} route failed: {}".format(route, ex))
    return None


def parse_answer_directives(text):
    """BRIDGE_ANSWER: YES   or   BRIDGE_ANSWER: NO; YES   for a sequence.
    Returns a list of choices, in order."""
    out = []
    for m in re.finditer(r"BRIDGE_ANSWER\s*:\s*([A-Za-z ,;/]+)", text or ""):
        for tok in re.split(r"[;,/]", m.group(1)):
            words = tok.strip().upper().split()
            # "YES then click Start" still means YES
            if words and words[0] in CHOICES:
                out.append(words[0])
    return out
