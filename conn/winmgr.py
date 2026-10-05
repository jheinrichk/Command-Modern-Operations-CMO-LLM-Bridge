"""
conn.winmgr  -  window discovery, geometry and live change notification.

Windows only for the real work. On any other platform every call degrades to
a safe no-op so the UI still starts and can be inspected.

Public surface:
    WindowManager.refresh()             rescan and match configured windows
    WindowManager.rect(key)             Rect or None for a configured window
    WindowManager.set_rect(key, rect)   move / resize
    WindowManager.apply_z(order)        raise windows in the given order
    WindowManager.start_watch(cb)       fire cb() when any tracked rect moves
    WindowManager.stop_watch()
    WindowManager.virtual_screen()      Rect of the whole desktop
    WindowManager.monitors()            list of Rect, one per display
"""

import os
import re
import sys
import threading
import time
from collections import namedtuple

IS_WINDOWS = sys.platform.startswith("win")

Rect = namedtuple("Rect", "left top right bottom")


def rect_w(r):
    return max(1, r.right - r.left)


def rect_h(r):
    return max(1, r.bottom - r.top)


def rect_contains(r, x, y):
    return r.left <= x <= r.right and r.top <= y <= r.bottom


def rect_area(r):
    return rect_w(r) * rect_h(r)


# ----------------------------------------------------------------------
# Win32 bindings
# ----------------------------------------------------------------------
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    SW_SHOWNOACTIVATE = 4
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    WINEVENTPROC = ctypes.WINFUNCTYPE(
        None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
        wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD)

    SW_RESTORE = 9
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    HWND_TOP = 0
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    EVENT_OBJECT_LOCATIONCHANGE = 0x800B
    WINEVENT_OUTOFCONTEXT = 0x0000
    WINEVENT_SKIPOWNPROCESS = 0x0002
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    WM_QUIT = 0x0012

    def set_dpi_aware():
        """Per-monitor v2 first, then the older shcore and user32 calls."""
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return "per_monitor_v2"
        except Exception:
            pass
        try:
            ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
            return "per_monitor"
        except Exception:
            pass
        try:
            user32.SetProcessDPIAware()
            return "system"
        except Exception:
            return "none"
else:
    def set_dpi_aware():
        return "not_windows"


WindowInfo = namedtuple("WindowInfo", "hwnd title cls exe rect")


def _enum_windows():
    """All visible top-level windows with a non-empty title."""
    if not IS_WINDOWS:
        return []
    import ctypes
    from ctypes import wintypes
    out = []

    def cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            n = user32.GetWindowTextLengthW(hwnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            title = buf.value
            cbuf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cbuf, 256)
            r = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
                return True
            out.append(WindowInfo(hwnd, title, cbuf.value, _exe_for(hwnd),
                                  Rect(r.left, r.top, r.right, r.bottom)))
        except Exception:
            pass
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def _root_at(x, y):
    """Top-level window under a screen point, or 0."""
    import ctypes
    from ctypes import wintypes
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
    if not hwnd:
        return 0
    return user32.GetAncestor(hwnd, 2) or hwnd       # GA_ROOT


def window_pid(hwnd):
    """Process id that owns a window, or 0."""
    if not IS_WINDOWS or not hwnd:
        return 0
    import ctypes
    from ctypes import wintypes
    pid = wintypes.DWORD()
    try:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    except Exception:
        return 0
    return int(pid.value)


def point_is_own_window(x, y):
    """True when a click at (x, y) would land on one of CONN's own windows
    (the main window or the monitor strip). The calibration overlay is
    click-through, so hit testing passes it and it never counts."""
    if not IS_WINDOWS:
        return False
    try:
        root = _root_at(x, y)
        if not root or window_pid(root) != os.getpid():
            return False
        # the calibration overlay is WS_EX_TRANSPARENT: a real click goes
        # through it, so it never blocks one
        ex = user32.GetWindowLongW(root, -20)            # GWL_EXSTYLE
        return not (ex & 0x00000020)                      # WS_EX_TRANSPARENT
    except Exception:
        return False


def foreground_class():
    """Window class of the foreground window ('#32770' for a file dialog)."""
    if not IS_WINDOWS:
        return ""
    import ctypes
    from ctypes import wintypes
    try:
        user32.GetForegroundWindow.restype = wintypes.HWND
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


def window_title_at(x, y):
    """Title of the top-level window under a screen point: the window a
    click or paste at that point actually reaches. Empty off Windows."""
    if not IS_WINDOWS:
        return ""
    import ctypes
    from ctypes import wintypes
    try:
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        if not hwnd:
            return ""
        root = user32.GetAncestor(hwnd, 2) or hwnd       # GA_ROOT
        n = user32.GetWindowTextLengthW(root)
        if n <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(root, buf, n + 1)
        return buf.value
    except Exception:
        return ""


def _exe_for(hwnd):
    if not IS_WINDOWS:
        return ""
    import ctypes
    from ctypes import wintypes
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        size = wintypes.DWORD(512)
        buf = ctypes.create_unicode_buffer(512)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value.rsplit("\\", 1)[-1]
    finally:
        kernel32.CloseHandle(h)
    return ""


def _match(spec, info):
    for field, key in (("title_regex", info.title), ("class_regex", info.cls),
                       ("exe_regex", info.exe)):
        pat = spec.get(field)
        if pat:
            try:
                if not re.search(pat, key or "", re.IGNORECASE):
                    return False
            except re.error:
                return False
    return True


class WindowManager:
    def __init__(self, cfg, log=None):
        self.cfg = cfg
        self.log = log or (lambda m: None)
        self.dpi_mode = set_dpi_aware()
        self.tracked = {}        # key -> WindowInfo
        self._watch_thread = None
        self._watch_stop = threading.Event()
        self._hook_thread_id = None
        self._callback = None
        self._lock = threading.Lock()

    # -- discovery --------------------------------------------------
    def refresh(self):
        found = {}
        if IS_WINDOWS:
            wins = _enum_windows()
            # A browser tab titled "CMO Lua Console notes - LLM" matches the
            # cmo_lua title rule, and the largest match wins, so Lua would be
            # pasted into the browser. Windows owned by the browser (the llm
            # exe rule) and by CONN itself only ever match their own keys.
            browser_rx = (self.cfg.windows.get("llm") or {}).get("exe_regex") or ""
            own_pid = os.getpid()
            for key, spec in self.cfg.windows.items():
                best = None
                for info in wins:
                    if key not in ("llm", "conn"):
                        try:
                            if browser_rx and re.search(browser_rx, info.exe or "", re.I):
                                continue
                        except re.error:
                            pass
                        if window_pid(info.hwnd) == own_pid:
                            continue
                    if _match(spec, info):
                        if best is None or rect_area(info.rect) > rect_area(best.rect):
                            best = info
                if best:
                    found[key] = best
        with self._lock:
            self.tracked = found
        return found

    def info(self, key):
        with self._lock:
            return self.tracked.get(key)

    def rect(self, key):
        """Live rectangle of a tracked window.

        A window that was closed (and maybe reopened elsewhere) is looked up
        again instead of returning where it used to be. A minimized window
        returns None: its rectangle is the off-screen -32000 placeholder, and
        clicking there drives the pointer into a corner and trips
        pyautogui's fail-safe."""
        info = self.info(key)
        if not info:
            return None
        if IS_WINDOWS:
            import ctypes
            from ctypes import wintypes
            if not user32.IsWindow(info.hwnd):
                self.refresh()
                info = self.info(key)
                if not info:
                    return None
            if user32.IsIconic(info.hwnd):
                return None
            r = wintypes.RECT()
            if user32.GetWindowRect(info.hwnd, ctypes.byref(r)):
                return Rect(r.left, r.top, r.right, r.bottom)
            return None
        return info.rect

    def is_minimized(self, key):
        info = self.info(key)
        if not info or not IS_WINDOWS:
            return False
        try:
            return bool(user32.IsIconic(info.hwnd))
        except Exception:
            return False

    def restore_if_minimized(self, key):
        """Bring a minimized window back without giving it focus. Returns
        True when it was minimized and has been restored."""
        if not self.is_minimized(key):
            return False
        info = self.info(key)
        try:
            user32.ShowWindow(info.hwnd, SW_SHOWNOACTIVATE)
            time.sleep(0.3)
            self.log("{} was minimized; restored it without focus".format(key))
            return True
        except Exception:
            return False

    def z_order(self):
        """Tracked keys from the top of the stacking order down."""
        if not IS_WINDOWS:
            return list(self.tracked.keys())
        rank = {}
        for i, w in enumerate(_enum_windows()):     # EnumWindows lists topmost first
            rank.setdefault(w.hwnd, i)
        with self._lock:
            items = list(self.tracked.items())
        return [k for k, _inf in sorted(items, key=lambda kv: rank.get(kv[1].hwnd, 1 << 30))]

    def all_rects(self):
        out = {}
        for key in list(self.tracked.keys()):
            r = self.rect(key)
            if r:
                out[key] = r
        return out

    # -- geometry ---------------------------------------------------
    def set_rect(self, key, rect, topmost=None, activate=False):
        info = self.info(key)
        if not info or not IS_WINDOWS:
            return False
        flags = SWP_SHOWWINDOW | (0 if activate else SWP_NOACTIVATE)
        insert = HWND_TOP
        if topmost is True:
            insert = HWND_TOPMOST
        elif topmost is False:
            insert = HWND_NOTOPMOST
        else:
            flags |= SWP_NOZORDER
        try:
            user32.ShowWindow(info.hwnd, SW_RESTORE)
            return bool(user32.SetWindowPos(
                info.hwnd, insert, int(rect.left), int(rect.top),
                int(rect_w(rect)), int(rect_h(rect)), flags))
        except Exception as ex:
            self.log("set_rect failed for {}: {}".format(key, ex))
            return False

    def raise_window(self, key):
        info = self.info(key)
        if info and IS_WINDOWS:
            try:
                user32.SetWindowPos(info.hwnd, HWND_TOP, 0, 0, 0, 0,
                                    0x0001 | 0x0002 | SWP_NOACTIVATE)
                return True
            except Exception:
                return False
        return False

    def focus(self, key):
        info = self.info(key)
        if info and IS_WINDOWS:
            try:
                user32.ShowWindow(info.hwnd, SW_RESTORE)
                user32.SetForegroundWindow(info.hwnd)
                return True
            except Exception:
                return False
        return False

    def apply_z(self, order):
        """order is a list of keys, lowest first."""
        for key in order:
            self.raise_window(key)
            time.sleep(0.03)

    # -- displays ---------------------------------------------------
    def virtual_screen(self):
        if not IS_WINDOWS:
            return Rect(0, 0, 1920, 1080)
        SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
        SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
        x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return Rect(x, y, x + w, y + h)

    def monitors(self):
        if not IS_WINDOWS:
            return [self.virtual_screen()]
        import ctypes
        out = []

        def cb(_hmon, _hdc, lprect, _lparam):
            r = lprect.contents
            out.append(Rect(r.left, r.top, r.right, r.bottom))
            return True

        user32.EnumDisplayMonitors(0, None, MONITORENUMPROC(cb), 0)
        return out or [self.virtual_screen()]

    def topology_key(self):
        return "|".join("{},{},{},{}".format(*m) for m in self.monitors())

    # -- live change notification -----------------------------------
    def start_watch(self, callback, rate_ms=250):
        """Fire callback() whenever a tracked window moves or resizes.

        Uses SetWinEventHook when available so an arrangement change is
        reflected immediately, and falls back to polling otherwise.
        """
        self.stop_watch()
        self._callback = callback
        self._watch_stop.clear()
        use_hook = bool(self.cfg.get("ui.use_winevent_hook", True)) and IS_WINDOWS
        target = self._hook_loop if use_hook else self._poll_loop
        self._watch_thread = threading.Thread(
            target=target, args=(rate_ms,), name="conn-winwatch", daemon=True)
        self._watch_thread.start()
        return "hook" if use_hook else "poll"

    def stop_watch(self):
        self._watch_stop.set()
        if IS_WINDOWS and self._hook_thread_id:
            try:
                user32.PostThreadMessageW(self._hook_thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        self._hook_thread_id = None
        self._watch_thread = None

    def _fire(self):
        try:
            if self._callback:
                self._callback()
        except Exception as ex:
            self.log("watch callback error: {}".format(ex))

    def _poll_loop(self, rate_ms):
        last = {}
        while not self._watch_stop.is_set():
            cur = self.all_rects()
            if cur != last:
                last = cur
                self._fire()
            time.sleep(max(0.05, rate_ms / 1000.0))

    def _hook_loop(self, rate_ms):
        import ctypes
        from ctypes import wintypes
        self._hook_thread_id = kernel32.GetCurrentThreadId()
        state = {"last": 0.0, "pending": False}

        def on_event(_hook, _event, hwnd, idobj, idchild, _thread, _time):
            if idobj != 0 or idchild != 0:
                return
            with self._lock:
                hwnds = [i.hwnd for i in self.tracked.values()]
            if hwnd not in hwnds:
                return
            now = time.time()
            if now - state["last"] < 0.08:
                state["pending"] = True
                return
            state["last"] = now
            state["pending"] = False
            self._fire()

        proc = WINEVENTPROC(on_event)
        hook = user32.SetWinEventHook(
            EVENT_OBJECT_LOCATIONCHANGE, EVENT_OBJECT_LOCATIONCHANGE, 0,
            proc, 0, 0, WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS)
        if not hook:
            self.log("SetWinEventHook failed, falling back to polling.")
            self._poll_loop(rate_ms)
            return
        msg = wintypes.MSG()
        try:
            while not self._watch_stop.is_set():
                res = user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)
                if res:
                    if msg.message == WM_QUIT:
                        break
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    if state["pending"] and time.time() - state["last"] > 0.15:
                        state["last"] = time.time()
                        state["pending"] = False
                        self._fire()
                    time.sleep(0.02)
        finally:
            try:
                user32.UnhookWinEvent(hook)
            except Exception:
                pass
