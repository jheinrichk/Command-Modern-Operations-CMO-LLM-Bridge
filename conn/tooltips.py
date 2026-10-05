"""
conn.tooltips  -  hover help for the CONN interface.

tip(widget, text) attaches a delayed hover tooltip. It works on ttk and tk
widgets alike, follows the pointer into the widget, wraps long text, and
never steals focus. One shared window per application keeps it cheap.
"""

import tkinter as tk

_DELAY_MS = 450
_WRAP_PX = 380


class _TipWindow:
    """One floating label reused for every widget in the application."""

    def __init__(self, root):
        self.root = root
        self.win = None
        self.label = None
        self.after_id = None
        self.pal = {"bg": "#2b2f36", "fg": "#f3f4f6", "border": "#5b6470"}

    def set_palette(self, pal):
        if not pal:
            return
        self.pal = {"bg": pal.get("panel", pal.get("bg", "#2b2f36")),
                    "fg": pal.get("fg", "#f3f4f6"),
                    "border": pal.get("accent", "#5b6470")}
        if self.label is not None:
            try:
                self.win.configure(bg=self.pal["border"])
                self.label.configure(bg=self.pal["bg"], fg=self.pal["fg"])
            except tk.TclError:
                pass

    def schedule(self, widget, text):
        self.cancel()
        self.after_id = self.root.after(_DELAY_MS, lambda: self.show(widget, text))

    def cancel(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        self.hide()

    def show(self, widget, text):
        self.after_id = None
        if not text:
            return
        try:
            if not self.root.winfo_exists() or not widget.winfo_exists():
                return
            x = widget.winfo_rootx() + 14
            y = widget.winfo_rooty() + widget.winfo_height() + 8
        except tk.TclError:
            return
        # a window that was destroyed with a previous root is recreated
        if self.win is not None:
            try:
                if not self.win.winfo_exists():
                    self.win = None
                    self.label = None
            except tk.TclError:
                self.win = None
                self.label = None
        if self.win is None:
            self.win = tk.Toplevel(self.root)
            self.win.wm_overrideredirect(True)
            try:
                self.win.attributes("-topmost", True)
            except tk.TclError:
                pass
            self.win.configure(bg=self.pal["border"])
            self.label = tk.Label(self.win, text=text, justify="left",
                                  wraplength=_WRAP_PX, bg=self.pal["bg"],
                                  fg=self.pal["fg"], font=("Segoe UI", 9),
                                  padx=8, pady=5)
            self.label.pack(padx=1, pady=1)
        else:
            self.label.configure(text=text)
        # keep the tip on screen
        self.win.update_idletasks()
        w = self.win.winfo_reqwidth()
        h = self.win.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if x + w > sw - 8:
            x = max(8, sw - w - 8)
        if y + h > sh - 8:
            y = max(8, widget.winfo_rooty() - h - 8)
        self.win.geometry("+{}+{}".format(int(x), int(y)))
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        if self.win is not None:
            try:
                self.win.withdraw()
            except tk.TclError:
                pass


_SHARED = {}


def _shared(widget):
    root = widget.winfo_toplevel()
    # one tip window per Tk interpreter, not per toplevel, so it survives
    # the monitor strip being undocked; keyed by the interpreter object
    # because every Tk root is named "." and a new root must not inherit a
    # window that died with the old one
    app = root.nametowidget(".") if root.winfo_name() != "." else root
    key = id(app.tk)
    entry = _SHARED.get(key)
    if entry is None or entry.root is not app:
        entry = _TipWindow(app)
        _SHARED[key] = entry
    return entry


def tip(widget, text):
    """Attach hover help to a widget. Returns the widget so it can be used
    inline:  tip(ttk.Button(...), "what it does").pack(...)"""
    if widget is None or not text:
        return widget
    shared = _shared(widget)
    widget._conn_tip = text

    def on_enter(_e=None):
        shared.schedule(widget, widget._conn_tip)

    def on_leave(_e=None):
        shared.cancel()

    widget.bind("<Enter>", on_enter, add="+")
    widget.bind("<Leave>", on_leave, add="+")
    widget.bind("<ButtonPress>", on_leave, add="+")
    widget.bind("<Destroy>", on_leave, add="+")
    return widget


def set_palette(root, pal):
    """Colour the shared tip window from the application palette."""
    try:
        _shared(root).set_palette(pal)
    except Exception:
        pass


def has_tip(widget):
    return bool(getattr(widget, "_conn_tip", ""))
