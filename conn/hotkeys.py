"""
conn.hotkeys  -  one global hotkey, registered for abort.

The abort must work while CMO or the browser has focus, so it cannot be a Tk
binding. RegisterHotKey needs a thread with a message loop, which is what this
module owns. No-op off Windows.
"""

import threading

from .winmgr import IS_WINDOWS

MOD = {"alt": 0x0001, "ctrl": 0x0002, "shift": 0x0004, "win": 0x0008}
VK = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "esc": 0x1B, "space": 0x20, "pause": 0x13,
}


def parse(spec):
    """'ctrl+alt+x' -> (mods, vk) or None."""
    mods, vk = 0, None
    for part in (spec or "").lower().split("+"):
        part = part.strip()
        if not part:
            continue
        if part in MOD:
            mods |= MOD[part]
        elif part in VK:
            vk = VK[part]
        elif len(part) == 1:
            vk = ord(part.upper())
        else:
            # a typo such as "crtl+alt+x" used to register Alt+X for the
            # whole system; refuse the spec instead
            return None
    return (mods, vk) if vk else None


class GlobalHotkey:
    def __init__(self, spec, callback, log=None):
        self.spec = spec
        self.callback = callback
        self.log = log or (lambda m: None)
        self.thread = None
        self._stop = threading.Event()
        self.active = False

    def start(self):
        combo = parse(self.spec)
        if not combo or not IS_WINDOWS:
            self.log("global hotkey unavailable ({})".format(self.spec))
            return False
        self._stop.clear()
        self.thread = threading.Thread(target=self._loop, args=combo,
                                       name="conn-hotkey", daemon=True)
        self.thread.start()
        return True

    def stop(self, wait=1.0):
        """Stop and wait for the thread to unregister the key, so a new
        hotkey for the same combination can be registered straight away."""
        self._stop.set()
        t = self.thread
        if t is not None and t.is_alive():
            t.join(wait)

    def _loop(self, mods, vk):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        HOTKEY_ID = 0xC0DE
        MOD_NOREPEAT = 0x4000
        if not user32.RegisterHotKey(None, HOTKEY_ID, mods | MOD_NOREPEAT, vk):
            self.log("RegisterHotKey failed for {}".format(self.spec))
            return
        self.active = True
        self.log("global abort hotkey armed: {}".format(self.spec))
        msg = wintypes.MSG()
        try:
            while not self._stop.is_set():
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312:  # WM_HOTKEY
                        try:
                            self.callback()
                        except Exception as ex:
                            self.log("hotkey callback error: {}".format(ex))
                else:
                    import time
                    time.sleep(0.03)
        finally:
            try:
                user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass
            self.active = False
