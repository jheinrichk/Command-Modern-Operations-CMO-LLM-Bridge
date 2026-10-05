"""
conn.anchors  -  window-relative click targets.

An anchor is stored as a position inside a named window rather than as an
absolute screen point, so moving or resizing a window never invalidates
calibration and the same file works across monitors and DPI scales.

    {"window": "cmo_lua", "mode": "frac", "dx": 0.147, "dy": 0.630}
    {"window": "cmo",     "mode": "px", "corner": "tl", "dx": 246, "dy": 127}

"frac" scales with the window and suits fields and content areas.
"px" holds a fixed offset from a corner and suits toolbar and edge buttons.
Window "screen" pins to the virtual desktop for anything not inside a window.
"""

from .winmgr import Rect, rect_w, rect_h, rect_contains, rect_area

CORNERS = ("tl", "tr", "bl", "br")

# How close to an edge a point must be before migration prefers px mode.
EDGE_THRESHOLD_PX = 160


class AnchorResolver:
    def __init__(self, cfg, wm):
        self.cfg = cfg
        self.wm = wm

    # -- resolution -------------------------------------------------
    def window_rect(self, window):
        if window == "screen":
            return self.wm.virtual_screen()
        return self.wm.rect(window)

    def resolve(self, name):
        """Return (x, y) or None when the anchor is unset or its window
        is not on screen."""
        a = self.cfg.anchors.get(name)
        if not a:
            return None
        r = self.window_rect(a.get("window", "screen"))
        if not r:
            return None
        return anchor_to_point(a, r)

    def has(self, name):
        return self.resolve(name) is not None

    def status(self, name):
        a = self.cfg.anchors.get(name)
        if not a:
            return "unset"
        if not self.window_rect(a.get("window", "screen")):
            return "window missing"
        return "ok"

    # -- authoring --------------------------------------------------
    def set_from_point(self, name, x, y, prefer_window=None):
        """Store a screen point as an anchor, choosing the smallest window
        that contains it and the mode that will survive resizing."""
        rects = self.wm.all_rects()
        rects["screen"] = self.wm.virtual_screen()
        chosen, chosen_rect = None, None
        if prefer_window and prefer_window in rects:
            chosen, chosen_rect = prefer_window, rects[prefer_window]
        else:
            for key, r in rects.items():
                if key == "screen" or key == "conn":
                    continue
                if rect_contains(r, x, y):
                    if chosen_rect is None or rect_area(r) < rect_area(chosen_rect):
                        chosen, chosen_rect = key, r
        if chosen is None:
            chosen, chosen_rect = "screen", rects["screen"]
        anchor = point_to_anchor(chosen, chosen_rect, x, y)
        self.cfg.anchors[name] = anchor
        return anchor

    def rebind(self, name, window):
        """Move an existing anchor to a different window, keeping the
        current on-screen point."""
        pt = self.resolve(name)
        if not pt:
            return None
        return self.set_from_point(name, pt[0], pt[1], prefer_window=window)


def point_to_anchor(window, rect, x, y):
    w, h = rect_w(rect), rect_h(rect)
    dl, dt = x - rect.left, y - rect.top
    dr, db = rect.right - x, rect.bottom - y
    near_h = min(dl, dr) < EDGE_THRESHOLD_PX
    near_v = min(dt, db) < EDGE_THRESHOLD_PX
    if near_h or near_v:
        corner = ("t" if dt <= db else "b") + ("l" if dl <= dr else "r")
        corner = {"tl": "tl", "tr": "tr", "bl": "bl", "br": "br"}[corner[0] + corner[1]]
        ox = dl if corner.endswith("l") else dr
        oy = dt if corner.startswith("t") else db
        return {"window": window, "mode": "px", "corner": corner,
                "dx": int(ox), "dy": int(oy)}
    return {"window": window, "mode": "frac",
            "dx": round(dl / float(w), 4), "dy": round(dt / float(h), 4)}


def anchor_to_point(anchor, rect):
    mode = anchor.get("mode", "frac")
    dx = anchor.get("dx", 0)
    dy = anchor.get("dy", 0)
    if mode == "px":
        corner = anchor.get("corner", "tl")
        x = rect.left + dx if corner.endswith("l") else rect.right - dx
        y = rect.top + dy if corner.startswith("t") else rect.bottom - dy
        return int(x), int(y)
    return int(rect.left + dx * rect_w(rect)), int(rect.top + dy * rect_h(rect))


def migrate_absolute(coords, rects, screen_rect):
    """Convert a legacy 'coordinates' block into anchors using live rects.

    coords: {name: [x, y]}
    rects:  {window_key: Rect} for the windows as currently arranged
    Returns (anchors, notes).
    """
    anchors, notes = {}, []
    for name, xy in (coords or {}).items():
        if not xy or len(xy) != 2:
            continue
        x, y = int(xy[0]), int(xy[1])
        best_key, best_rect = None, None
        for key, r in rects.items():
            if key == "conn":
                continue
            if rect_contains(r, x, y):
                if best_rect is None or rect_area(r) < rect_area(best_rect):
                    best_key, best_rect = key, r
        if best_key is None:
            anchors[name] = point_to_anchor("screen", screen_rect, x, y)
            notes.append("{}: not inside any tracked window, pinned to screen".format(name))
        else:
            anchors[name] = point_to_anchor(best_key, best_rect, x, y)
            notes.append("{}: bound to {} ({})".format(
                name, best_key, anchors[name]["mode"]))
    return anchors, notes


def anchors_to_absolute(cfg, resolver):
    """Write resolved points back into the legacy 'coordinates' block so the
    old command-line bridge keeps working from the same file."""
    coords = cfg.data.setdefault("coordinates", {})
    written = 0
    for name in list(cfg.anchors.keys()):
        pt = resolver.resolve(name)
        if pt:
            coords[name] = [int(pt[0]), int(pt[1])]
            written += 1
    return written
