"""
conn.overlay  -  see the calibration instead of guessing at it.

Two tools:

  AnchorOverlay   a transparent, click-through, always-on-top window that
                  draws a crosshair and label at every resolved anchor and at
                  the outline of every tracked window. It follows live window
                  moves, so you can drag CMO around and watch the targets
                  track with it.

  capture_point   the proven countdown capture from the original calibration
                  UI: hide, count down, read the pointer position.
"""

import time
import tkinter as tk

from .winmgr import IS_WINDOWS, rect_w, rect_h

try:
    import pyautogui
except Exception:
    pyautogui = None


def capture_point(root, seconds=5, hide=True, on_tick=None):
    """Blocking countdown capture. Returns (x, y) or None."""
    if not pyautogui:
        return None
    if hide:
        try:
            root.withdraw()
        except Exception:
            pass
    try:
        for r in range(int(seconds), 0, -1):
            if on_tick:
                on_tick(r)
            try:
                root.update()
            except Exception:
                pass
            time.sleep(1.0)
        x, y = pyautogui.position()
        return int(x), int(y)
    finally:
        if hide:
            try:
                root.deiconify()
            except Exception:
                pass


class AnchorOverlay:
    def __init__(self, master, cfg, wm, resolver):
        self.master = master
        self.cfg = cfg
        self.wm = wm
        self.resolver = resolver
        self.top = None
        self.canvas = None
        self.visible = False

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()
        return self.visible

    def show(self):
        if self.top is None:
            screen = self.wm.virtual_screen()
            self.top = tk.Toplevel(self.master)
            self.top.overrideredirect(True)
            self.top.attributes("-topmost", True)
            self.top.geometry("{}x{}+{}+{}".format(
                rect_w(screen), rect_h(screen), screen.left, screen.top))
            self.top.configure(bg="black")
            try:
                self.top.attributes("-transparentcolor", "black")
                self.top.attributes("-alpha", 0.95)
            except Exception:
                self.top.attributes("-alpha", 0.35)
            self.top._conn_fixed_color = True     # theme must never repaint it
            self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0,
                                    bd=0)
            self.canvas.pack(fill="both", expand=True)
            self._make_click_through()
        self.top.deiconify()
        self.visible = True
        self.redraw()

    def hide(self):
        if self.top is not None:
            self.top.withdraw()
        self.visible = False

    def destroy(self):
        if self.top is not None:
            self.top.destroy()
            self.top = None
        self.visible = False

    def _make_click_through(self):
        """WS_EX_TRANSPARENT so clicks pass to the app underneath."""
        if not IS_WINDOWS:
            return
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080
            self.top.update_idletasks()
            hwnd = int(self.top.winfo_id())
            parent = user32.GetParent(hwnd)
            hwnd = parent or hwnd
            cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                  cur | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
        except Exception:
            pass

    def redraw(self):
        if not self.visible or self.canvas is None:
            return
        screen = self.wm.virtual_screen()
        c = self.canvas
        c.delete("all")
        colors = {"llm": "#4d9de0", "cmo": "#e0a33e", "cmo_lua": "#3fbf7f",
                  "screen": "#a0a0a0", "conn": "#e0574d"}
        # window outlines
        for key in list(self.cfg.windows.keys()):
            r = self.wm.rect(key)
            if not r:
                continue
            col = colors.get(key, "#ffffff")
            c.create_rectangle(r.left - screen.left, r.top - screen.top,
                               r.right - screen.left, r.bottom - screen.top,
                               outline=col, width=2)
            c.create_text(r.left - screen.left + 8, r.top - screen.top + 12,
                          text=key, anchor="w", fill=col,
                          font=("Consolas", 11, "bold"))
        # anchors
        for name in sorted(self.cfg.anchors.keys()):
            pt = self.resolver.resolve(name)
            if not pt:
                continue
            a = self.cfg.anchors.get(name) or {}
            col = colors.get(a.get("window", "screen"), "#ffffff")
            x, y = pt[0] - screen.left, pt[1] - screen.top
            c.create_line(x - 14, y, x + 14, y, fill=col, width=2)
            c.create_line(x, y - 14, x, y + 14, fill=col, width=2)
            c.create_oval(x - 5, y - 5, x + 5, y + 5, outline=col, width=2)
            c.create_text(x + 18, y, text="{} [{}]".format(name, a.get("mode", "frac")),
                          anchor="w", fill=col, font=("Consolas", 10))
