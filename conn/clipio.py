"""
conn.clipio  -  clipboard handling.

Two jobs:
  1. Guard the user's clipboard. Every copy or paste the bridge performs
     saves the prior contents and restores them afterwards.
  2. Route oversized prompts. Pastes over the configured limit arrive empty
     in the browser, so the text is written to a file in the IN folder and
     attached to the conversation instead, with a short pointer pasted.

Payload files are pruned automatically after every write so the folder does
not fill up: keep the newest io.payload_keep_recent (default 40), keep
anything younger than io.payload_max_age_hours (default 72) and enforce a
hard io.payload_max_files cap (default 400). Only files this module wrote
(matching "<label>_*.txt", normally "prompt_*.txt") are ever deleted, so
manually saved files in the same folder are never touched.
"""

import time
from pathlib import Path

try:
    import pyperclip
except Exception:  # pragma: no cover - absent off Windows
    pyperclip = None


class Clipboard:
    def __init__(self, cfg, log=None, dry_run=False):
        self.cfg = cfg
        self.log = log or (lambda m: None)
        self.dry_run = dry_run
        self._saved = None

    def available(self):
        return pyperclip is not None

    def read(self):
        if not pyperclip:
            return ""
        try:
            return pyperclip.paste() or ""
        except Exception as ex:
            self.log("clipboard read failed: {}".format(ex))
            return ""

    def write(self, text):
        if self.dry_run:
            self.log("DRY RUN: would set clipboard ({} chars)".format(len(text or "")))
            return True
        if not pyperclip:
            return False
        try:
            pyperclip.copy(text)
            return True
        except Exception as ex:
            self.log("clipboard write failed: {}".format(ex))
            return False

    # -- guard ------------------------------------------------------
    def save(self):
        if self.cfg.get("io.guard_clipboard", True):
            self._saved = self.read()

    def restore(self):
        if self._saved is not None and self.cfg.get("io.guard_clipboard", True):
            if not self.dry_run and pyperclip:
                try:
                    pyperclip.copy(self._saved)
                except Exception:
                    pass
            self._saved = None

    # -- payload files -----------------------------------------------
    def write_payload_file(self, text, label="prompt"):
        """Write oversized text to the IN folder and return the path.

        The path is attached to the browser conversation as a file. It is
        never pasted as a bare pointer: the browser model has no access to
        this machine's disk, so a pointer alone is unreadable.
        """
        folder = self.cfg.folder("in_folder")
        if not folder:
            return None
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = folder / "{}_{}.txt".format(label, stamp)
        if self.dry_run:
            self.log("DRY RUN: would write {} chars to {}".format(len(text or ""), path))
            return path
        try:
            path.write_text(text or "", encoding="utf-8")
        except Exception as ex:
            self.log("payload file write failed: {}".format(ex))
            return None
        self._prune_payloads(folder, label)
        return path

    def _prune_payloads(self, folder, label):
        """Delete old payload files so the folder does not accumulate.

        Scope is strictly the files this module writes: "<label>_*.txt".
        Anything else in the folder (for example manually saved console
        dumps) is left alone. Policy: always keep the newest
        io.payload_keep_recent, additionally keep files younger than
        io.payload_max_age_hours, and enforce io.payload_max_files as a
        hard cap regardless of age. Failures are logged and never raised.
        """
        try:
            keep_recent = int(self.cfg.get("io.payload_keep_recent", 40))
            max_age_h = float(self.cfg.get("io.payload_max_age_hours", 72))
            max_files = int(self.cfg.get("io.payload_max_files", 400))
        except Exception:
            keep_recent, max_age_h, max_files = 40, 72.0, 400
        try:
            files = [p for p in Path(folder).glob(str(label) + "_*.txt")
                     if p.is_file()]
        except Exception as ex:
            self.log("payload prune scan failed: {}".format(ex))
            return 0
        if len(files) <= keep_recent:
            return 0
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        cutoff = time.time() - max_age_h * 3600.0
        removed = 0
        for idx, p in enumerate(files):
            keep = idx < keep_recent or p.stat().st_mtime >= cutoff
            if idx >= max_files:
                keep = False
            if keep:
                continue
            if self.dry_run:
                self.log("DRY RUN: would prune payload {}".format(p.name))
                continue
            try:
                p.unlink()
                removed += 1
            except Exception as ex:
                self.log("payload prune failed for {}: {}".format(p.name, ex))
        if removed:
            self.log("pruned {} old payload file(s) from {}".format(removed, folder))
        return removed
