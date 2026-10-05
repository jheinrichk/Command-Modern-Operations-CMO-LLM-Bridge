"""
conn.mapshot  -  a picture of the CMO map for the model.

The map window may be minimized, tiny, or buried under LLM and CONN.
So the capture:

  1. records the window's placement (rect, minimized or not, z-order),
  2. if it is minimized or smaller than mapshot.min_width x min_height,
     restores and resizes it to mapshot.rect (a fraction of the desktop)
     WITHOUT activating it, so the operator's focus is not stolen,
  3. waits mapshot.settle_seconds for CMO to redraw,
  4. captures with PrintWindow(PW_RENDERFULLCONTENT), which renders the
     window's own content even when other windows cover it; if that
     comes back blank, it raises the window without focus and grabs the
     screen region instead,
  5. puts the window back exactly as it was,
  6. downscales to mapshot.max_width and writes a PNG.

Everything is wrapped so a failure returns None and a log line; it never
raises into the turn loop.
"""

import ctypes
import time
from pathlib import Path

from .winmgr import IS_WINDOWS, Rect, rect_w, rect_h

try:
    from PIL import Image
except Exception:  # pillow is optional; the capture then needs pyautogui
    Image = None

SW_RESTORE = 9
SW_MINIMIZE = 6
SW_SHOWNOACTIVATE = 4
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004
HWND_TOP = 0
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020


def _u32():
    return ctypes.windll.user32


def _placement(hwnd):
    """(rect, minimized) for a window."""
    from ctypes import wintypes
    r = wintypes.RECT()
    _u32().GetWindowRect(hwnd, ctypes.byref(r))
    return Rect(r.left, r.top, r.right, r.bottom), bool(_u32().IsIconic(hwnd))


def _print_window(hwnd, w, h):
    """Render the window into a bitmap via PrintWindow. Returns a PIL
    image or None."""
    if Image is None or w <= 0 or h <= 0:
        return None
    gdi = ctypes.windll.gdi32
    u32 = _u32()
    hdc_win = u32.GetWindowDC(hwnd)
    if not hdc_win:
        return None
    hdc_mem = gdi.CreateCompatibleDC(hdc_win)
    bmp = gdi.CreateCompatibleBitmap(hdc_win, w, h)
    img = None
    try:
        gdi.SelectObject(hdc_mem, bmp)
        ok = u32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
        if ok:
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                            ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                            ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                            ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                            ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                            ("biClrImportant", ctypes.c_uint32)]

            class BITMAPINFO(ctypes.Structure):
                _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]

            bi = BITMAPINFO()
            bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bi.bmiHeader.biWidth = w
            bi.bmiHeader.biHeight = -h          # top-down
            bi.bmiHeader.biPlanes = 1
            bi.bmiHeader.biBitCount = 32
            bi.bmiHeader.biCompression = 0
            buf = ctypes.create_string_buffer(w * h * 4)
            got = gdi.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
            if got:
                img = Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1).copy()
    finally:
        gdi.DeleteObject(bmp)
        gdi.DeleteDC(hdc_mem)
        u32.ReleaseDC(hwnd, hdc_win)
    return img


def _looks_blank(img):
    """A PrintWindow of a window that did not draw is black or uniform."""
    if img is None:
        return True
    try:
        small = img.convert("L").resize((64, 40))
        lo, hi = small.getextrema()
        return (hi - lo) < 8
    except Exception:
        return True


def _grab_region(rect):
    try:
        if Image is not None:
            from PIL import ImageGrab
            return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True)
    except Exception:
        pass
    try:
        import pyautogui
        return pyautogui.screenshot(region=(rect.left, rect.top, rect_w(rect), rect_h(rect)))
    except Exception:
        return None


def capture_map(wm, cfg, out_path, log=None, window_key="cmo"):
    """Capture the CMO map window to out_path (PNG). Returns the path or
    None. Never raises."""
    log = log or (lambda m: None)
    if not IS_WINDOWS:
        log("map capture is Windows only")
        return None
    wm.refresh()
    info = wm.info(window_key)
    if not info:
        log("map capture: the CMO window was not found")
        return None
    hwnd = info.hwnd
    u32 = _u32()
    try:
        orig_rect, was_min = _placement(hwnd)
        screen = wm.virtual_screen()
        min_w = int(cfg.get("mapshot.min_width", 1400))
        min_h = int(cfg.get("mapshot.min_height", 900))
        moved = False
        if was_min or rect_w(orig_rect) < min_w or rect_h(orig_rect) < min_h:
            frac = cfg.get("mapshot.rect", [0.0, 0.0, 0.85, 0.95])
            target = Rect(int(screen.left + frac[0] * rect_w(screen)),
                          int(screen.top + frac[1] * rect_h(screen)),
                          int(screen.left + frac[2] * rect_w(screen)),
                          int(screen.top + frac[3] * rect_h(screen)))
            u32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
            u32.SetWindowPos(hwnd, HWND_TOP, target.left, target.top,
                             rect_w(target), rect_h(target),
                             SWP_NOACTIVATE | SWP_SHOWWINDOW)
            moved = True
            log("map capture: window restored to {}x{} for the shot".format(
                rect_w(target), rect_h(target)))
        time.sleep(float(cfg.get("mapshot.settle_seconds", 0.8)))
        rect, _ = _placement(hwnd)
        img = _print_window(hwnd, rect_w(rect), rect_h(rect))
        if _looks_blank(img):
            # raise without focus, grab the screen, then drop back
            u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                             SWP_NOACTIVATE | 0x0001 | 0x0002)
            time.sleep(0.3)
            img = _grab_region(rect)
            u32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                             SWP_NOACTIVATE | 0x0001 | 0x0002)
        # put it back
        if moved:
            u32.SetWindowPos(hwnd, HWND_TOP, orig_rect.left, orig_rect.top,
                             rect_w(orig_rect), rect_h(orig_rect),
                             SWP_NOACTIVATE | SWP_NOZORDER)
            if was_min:
                u32.ShowWindow(hwnd, SW_MINIMIZE)
        if img is None:
            log("map capture: nothing rendered")
            return None
        max_w = int(cfg.get("mapshot.max_width", 1600))
        if img.width > max_w:
            img = img.resize((max_w, int(img.height * max_w / img.width)))
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out), "PNG", optimize=True)
        log("map capture: {} ({}x{})".format(out, img.width, img.height))
        return out
    except Exception as ex:
        log("map capture failed: {}: {}".format(type(ex).__name__, ex))
        return None
