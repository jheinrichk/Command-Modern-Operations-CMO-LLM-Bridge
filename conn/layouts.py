"""
conn.layouts  -  named window-arrangement profiles.

A profile stores each window as fractions of the virtual desktop, so the
reference arrangement reproduces on any resolution. Profiles are keyed by
display topology, so a docked setup and a laptop-only setup do not overwrite
each other.
"""

import time
import zlib

from .winmgr import Rect, rect_w, rect_h


def frac_to_rect(frac, screen):
    sw, sh = rect_w(screen), rect_h(screen)
    l = int(screen.left + frac[0] * sw)
    t = int(screen.top + frac[1] * sh)
    r = int(screen.left + frac[2] * sw)
    b = int(screen.top + frac[3] * sh)
    return Rect(l, t, max(l + 200, r), max(t + 150, b))


def rect_to_frac(rect, screen):
    sw, sh = float(rect_w(screen)), float(rect_h(screen))
    return [round((rect.left - screen.left) / sw, 4),
            round((rect.top - screen.top) / sh, 4),
            round((rect.right - screen.left) / sw, 4),
            round((rect.bottom - screen.top) / sh, 4)]


class LayoutManager:
    def __init__(self, cfg, wm, log=None):
        self.cfg = cfg
        self.wm = wm
        self.log = log or (lambda m: None)

    def profile_names(self):
        return sorted(self.cfg.profiles.keys())

    def get(self, name):
        return self.cfg.profiles.get(name)

    def active(self):
        return self.cfg.get("layouts.active", "scenario_dev")

    def key_for_topology(self, name):
        """Profiles saved for a specific topology get a suffixed key.

        crc32, not hash(): Python salts string hashes per process, so the
        old suffix changed on every launch and a saved variant was never
        found again. Existing @NNNNN profiles keep their names."""
        topo = self.wm.topology_key() or ""
        return "{}@{}".format(name, zlib.crc32(topo.encode("utf-8")) % 100000)

    def resolve_for_topology(self, name):
        """Prefer a topology-specific variant when one exists: the stable
        key first, then any name@... profile saved on this same topology."""
        if "@" in name and name in self.cfg.profiles:
            return name
        specific = self.key_for_topology(name)
        if specific in self.cfg.profiles:
            return specific
        topo = self.wm.topology_key()
        for key, prof in self.cfg.profiles.items():
            if key.split("@")[0] == name and "@" in key and prof.get("topology") == topo:
                return key
        return name

    # -- apply ------------------------------------------------------
    def apply(self, name, include_conn=True, conn_setter=None):
        """Position every window in the profile. conn_setter(rect) is called
        for the CONN window itself since Tk owns that geometry."""
        key = self.resolve_for_topology(name)
        prof = self.get(key) or self.get(name)
        if not prof:
            return False, "profile not found: {}".format(name)
        self.wm.refresh()
        screen = self.wm.virtual_screen()
        wins = prof.get("windows", {})
        missing, placed = [], []
        ordered = sorted(wins.items(), key=lambda kv: kv[1].get("z", 0))
        for wkey, spec in ordered:
            rect = frac_to_rect(spec.get("rect", [0, 0, 0.5, 0.5]), screen)
            if wkey == "conn":
                if include_conn and conn_setter:
                    conn_setter(rect, bool(spec.get("topmost", True)))
                    placed.append(wkey)
                continue
            if not self.wm.info(wkey):
                missing.append(wkey)
                continue
            ok = self.wm.set_rect(wkey, rect, topmost=spec.get("topmost"))
            (placed if ok else missing).append(wkey)
            time.sleep(0.06)
        # raise in z order, lowest first
        self.wm.apply_z([k for k, s in ordered if k != "conn" and k in placed])
        self.cfg.set("layouts.active", name)
        msg = "applied {} ({} placed)".format(name, len(placed))
        if missing:
            msg += ", missing: " + ", ".join(missing)
        self.log(msg)
        return True, msg

    # -- capture ----------------------------------------------------
    def capture(self, name, label=None, conn_rect=None, topology_specific=True):
        """Save the current arrangement as a profile."""
        self.wm.refresh()
        screen = self.wm.virtual_screen()
        wins = {}
        # z from the real stacking order, bottom = 1. Taking it from the
        # order of the config keys meant a profile captured with LLM on
        # top of CMO restored with CMO on top, and llm_input clicks hit CMO.
        try:
            top_down = [k for k in self.wm.z_order() if k != "conn"]
        except Exception:
            top_down = []
        order = list(reversed(top_down)) + [k for k in self.cfg.windows.keys()
                                            if k != "conn" and k not in top_down]
        z = 1
        for wkey in order:
            r = self.wm.rect(wkey)
            if r:
                wins[wkey] = {"rect": rect_to_frac(r, screen), "z": z}
                z += 1
        if conn_rect:
            wins["conn"] = {"rect": rect_to_frac(conn_rect, screen),
                            "z": 99, "topmost": True}
        key = self.key_for_topology(name) if topology_specific else name
        self.cfg.profiles[key] = {
            "label": label or name,
            "topology": self.wm.topology_key() if topology_specific else "any",
            "windows": wins,
        }
        self._save()
        return key

    def _save(self):
        try:
            self.cfg.save()
            return True
        except Exception as ex:
            self.log("layout not saved: {}".format(ex))
            return False

    def delete(self, name):
        if name in self.cfg.profiles:
            del self.cfg.profiles[name]
            self._save()
            return True
        return False

    # -- strip reservation ------------------------------------------
    def reserve_strip(self, profile_name, side="right", width=320):
        """Shrink every window in a profile away from one screen edge and put
        CONN in the reserved band."""
        prof = self.get(profile_name)
        if not prof:
            return False
        screen = self.wm.virtual_screen()
        f = width / float(rect_w(screen))
        for wkey, spec in prof.get("windows", {}).items():
            if wkey == "conn":
                continue
            r = spec.get("rect")
            if side == "right":
                r[2] = min(r[2], 1.0 - f)
            elif side == "left":
                r[0] = max(r[0], f)
            spec["rect"] = r
        band = [1.0 - f, 0.0, 1.0, 1.0] if side == "right" else [0.0, 0.0, f, 1.0]
        prof.setdefault("windows", {})["conn"] = {"rect": band, "z": 99, "topmost": True}
        self._save()
        return True
