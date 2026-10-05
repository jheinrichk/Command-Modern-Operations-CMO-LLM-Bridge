"""
conn.theme  -  two palettes and one switch.

Dry run is not a checkbox you have to hunt for. When it is on the whole
window changes colour, so there is never a doubt about whether CONN is
allowed to touch the screen.
"""

import tkinter as tk
from tkinter import ttk

LIVE = {
    "name": "live",
    "bg": "#11181f",
    "panel": "#1a2331",
    "raised": "#233043",
    "fg": "#dde5ee",
    "muted": "#8fa0b4",
    "entry": "#0c1218",
    "accent": "#4d9de0",
    "ok": "#3fbf7f",
    "warn": "#e0a33e",
    "fail": "#e0574d",
    "chip_off": "#2a3648",
    "banner": "#1f2c3d",
    "banner_fg": "#9fc7ea",
}

DRY = {
    "name": "dry",
    "bg": "#2b2410",
    "panel": "#39301a",
    "raised": "#4a3f22",
    "fg": "#f6ead0",
    "muted": "#cbb488",
    "entry": "#1e1a0b",
    "accent": "#e8b14a",
    "ok": "#8fbf6a",
    "warn": "#e8b14a",
    "fail": "#e0574d",
    "chip_off": "#544526",
    "banner": "#6b5417",
    "banner_fg": "#fff3d6",
}


def palette(dry_run):
    return DRY if dry_run else LIVE


def apply_theme(root, pal):
    """Recolour ttk styles and every existing tk widget."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(".", background=pal["bg"], foreground=pal["fg"],
                    fieldbackground=pal["entry"], bordercolor=pal["raised"])
    style.configure("TFrame", background=pal["bg"])
    style.configure("Panel.TFrame", background=pal["panel"])
    style.configure("TLabel", background=pal["bg"], foreground=pal["fg"])
    style.configure("Panel.TLabel", background=pal["panel"], foreground=pal["fg"])
    style.configure("Muted.TLabel", background=pal["bg"], foreground=pal["muted"])
    style.configure("Head.TLabel", background=pal["bg"], foreground=pal["accent"],
                    font=("Segoe UI", 11, "bold"))
    style.configure("Banner.TLabel", background=pal["banner"],
                    foreground=pal["banner_fg"], font=("Segoe UI", 10, "bold"))
    style.configure("TButton", background=pal["raised"], foreground=pal["fg"],
                    borderwidth=1, focusthickness=0, padding=4)
    style.map("TButton",
              background=[("active", pal["accent"]), ("disabled", pal["panel"])],
              foreground=[("active", pal["bg"]), ("disabled", pal["muted"])])
    style.configure("Accent.TButton", background=pal["accent"], foreground=pal["bg"])
    style.configure("Danger.TButton", background=pal["fail"], foreground="#ffffff")
    style.configure("TCheckbutton", background=pal["bg"], foreground=pal["fg"])
    style.configure("Dry.TCheckbutton", background=pal["banner"],
                    foreground=pal["banner_fg"], font=("Segoe UI", 10, "bold"))
    style.configure("TNotebook", background=pal["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=pal["panel"], foreground=pal["muted"],
                    padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", pal["raised"])],
              foreground=[("selected", pal["fg"])])
    style.configure("Treeview", background=pal["entry"], fieldbackground=pal["entry"],
                    foreground=pal["fg"], borderwidth=0, rowheight=22)
    style.configure("Treeview.Heading", background=pal["raised"], foreground=pal["fg"])
    style.map("Treeview", background=[("selected", pal["accent"])],
              foreground=[("selected", pal["bg"])])
    style.configure("TEntry", fieldbackground=pal["entry"], foreground=pal["fg"])
    style.configure("TCombobox", fieldbackground=pal["entry"], foreground=pal["fg"],
                    background=pal["raised"], arrowcolor=pal["fg"],
                    selectbackground=pal["entry"], selectforeground=pal["fg"])
    style.map("TCombobox",
              fieldbackground=[("readonly", pal["entry"]), ("disabled", pal["panel"])],
              foreground=[("readonly", pal["fg"])],
              selectbackground=[("readonly", pal["entry"])],
              selectforeground=[("readonly", pal["fg"])])
    root.option_add("*TCombobox*Listbox.background", pal["entry"])
    root.option_add("*TCombobox*Listbox.foreground", pal["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", pal["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", pal["bg"])
    style.configure("Horizontal.TProgressbar", background=pal["accent"],
                    troughcolor=pal["entry"], borderwidth=0)
    style.configure("TLabelframe", background=pal["bg"], foreground=pal["accent"])
    style.configure("TLabelframe.Label", background=pal["bg"], foreground=pal["accent"])
    _recolor(root, pal)


def _recolor(widget, pal):
    # Widgets that must keep their own colours: the calibration overlay
    # (black is its transparent key; repainting it made a full-screen,
    # always-on-top sheet) and the preflight status dots.
    if getattr(widget, "_conn_fixed_color", False):
        return
    try:
        cls = widget.winfo_class()
    except Exception:
        return
    try:
        if cls in ("Tk", "Toplevel", "Frame", "Labelframe", "Canvas"):
            widget.configure(bg=pal["bg"])
        elif cls == "Text":
            widget.configure(bg=pal["entry"], fg=pal["fg"],
                             insertbackground=pal["fg"],
                             selectbackground=pal["accent"],
                             highlightbackground=pal["raised"])
        elif cls == "Listbox":
            widget.configure(bg=pal["entry"], fg=pal["fg"],
                             selectbackground=pal["accent"])
        elif cls == "Label":
            widget.configure(bg=pal["bg"], fg=pal["fg"])
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _recolor(child, pal)
