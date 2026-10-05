"""
conn.ike  -  IKE PBEM finalization.

IKE conversion is one-way: once the conversion Lua is injected the .scen is
turn-based and cannot be reverted. The rules here exist so the master file
survives that:

  1. Copy the master to SNAPSHOTS as name_vNN_preIKE.scen before anything runs.
  2. Set the master read-only for the duration of the conversion.
  3. Convert the working copy only, never the master.
  4. Write a sidecar .json recording source, time, sides and turn length.
  5. Verify the output exists and is non-empty before reporting success.

IKE itself is musurca's project and is not bundled. Point
ike.ike_conversion_lua_path at the conversion Lua from the Scenario Author Pack.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import time
from pathlib import Path


def file_sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            if limit and f.tell() > limit:
                break
    return h.hexdigest()


def next_version(folder, stem, suffix="_preIKE"):
    folder = Path(folder)
    rx = re.compile(re.escape(stem) + r"_v(\d+)" + re.escape(suffix) + r"\.scen$",
                    re.IGNORECASE)
    highest = 0
    if folder.exists():
        for p in folder.iterdir():
            m = rx.match(p.name)
            if m:
                highest = max(highest, int(m.group(1)))
    return highest + 1


def set_readonly(path, on=True):
    try:
        p = Path(path)
        mode = p.stat().st_mode
        if on:
            os.chmod(str(p), mode & ~stat.S_IWRITE)
        else:
            os.chmod(str(p), mode | stat.S_IWRITE)
        return True
    except Exception:
        return False


class IkeFinalizer:
    """Sequenced conversion. run_lua and wait are supplied by the engine so
    this module stays free of UI automation."""

    def __init__(self, cfg, run_lua, wait, log, dry_run=False):
        self.cfg = cfg
        self.run_lua = run_lua
        self.wait = wait
        self.log = log
        self.dry_run = dry_run

    # -- step 1: snapshot -------------------------------------------
    def snapshot(self, master_path):
        master = Path(master_path)
        if not master.exists():
            return None, "master scenario not found: {}".format(master)
        folder = self.cfg.folder("snapshots_folder") or master.parent
        Path(folder).mkdir(parents=True, exist_ok=True)
        suffix = self.cfg.get("ike.snapshot_suffix", "_preIKE")
        v = next_version(folder, master.stem, suffix)
        dest = Path(folder) / "{}_v{:02d}{}.scen".format(master.stem, v, suffix)
        if self.dry_run:
            self.log("DRY RUN: would copy {} to {}".format(master, dest))
            return dest, None
        shutil.copy2(str(master), str(dest))
        if not dest.exists() or dest.stat().st_size == 0:
            return None, "snapshot copy failed or empty"
        self.log("Snapshot written: {} ({} bytes)".format(dest, dest.stat().st_size))
        return dest, None

    # -- step 2: working copy ---------------------------------------
    def working_copy(self, master_path, tag="PBEM"):
        master = Path(master_path)
        dest = master.with_name("{}_{}.scen".format(master.stem, tag))
        if self.dry_run:
            self.log("DRY RUN: would create working copy {}".format(dest))
            return dest, None
        if dest.exists():
            # an earlier converted file is kept, never silently overwritten
            keep = dest.with_name("{}_prev_{}.scen".format(dest.stem, time.strftime("%Y%m%d_%H%M%S")))
            shutil.copy2(str(dest), str(keep))
            self.log("Kept the previous {} as {}".format(dest.name, keep.name))
        shutil.copy2(str(master), str(dest))
        return dest, None

    # -- step 3: conversion -----------------------------------------
    def conversion_lua(self):
        path = self.cfg.get("ike.ike_conversion_lua_path", "")
        p = Path(path) if path else None
        if not p or not p.exists():
            return None, ("IKE conversion Lua not found at '{}'. Download the "
                          "Scenario Author Pack from {} and set "
                          "ike.ike_conversion_lua_path.".format(
                              path, self.cfg.get("ike.ike_release", "")))
        return p.read_text(encoding="utf-8", errors="replace"), None

    def finalize(self, master_path, sides=None, turn_minutes=None, on_step=None):
        """Full sequence. Returns (result_dict, error_string)."""
        step = on_step or (lambda s, d="": None)
        result = {"master": str(master_path), "started": time.time()}

        step("snapshot", "copying master")
        snap, err = self.snapshot(master_path)
        if err:
            return result, err
        result["snapshot"] = str(snap)

        step("working_copy", "creating PBEM copy")
        work, err = self.working_copy(master_path)
        if err:
            return result, err
        result["working_copy"] = str(work)
        if not self.dry_run:
            try:
                # verify compares against this: an unconverted copy must fail
                result["copy_sha256"] = file_sha256(work)
            except Exception:
                pass

        if self.cfg.get("safety.lock_master_scen_readonly", True) and not self.dry_run:
            set_readonly(master_path, True)
            result["master_locked"] = True

        try:
            step("load", "load the PBEM copy in CMO")
            lua, err = self.conversion_lua()
            if err:
                return result, err

            step("convert", "injecting IKE conversion Lua")
            if self.dry_run:
                self.log("DRY RUN: would inject {} chars of IKE conversion Lua".format(len(lua)))
            else:
                self.run_lua(lua)
                self.wait(int(self.cfg.get("timing.cmo_output_wait_seconds", 5)))

            step("popups", "answer IKE questions in CMO: sides, turn order, "
                           "turn length, setup phase, passwords")
            result["awaiting_user_popups"] = True

            step("save_as", "save the converted scenario with SAVE AS, not SAVE")
            result["expected_output"] = str(work)
        finally:
            if result.get("master_locked") and not self.dry_run:
                set_readonly(master_path, False)
                result["master_locked"] = False

        return result, None

    # -- step 5: verify and record ----------------------------------
    def verify_and_record(self, result, sides=None, turn_minutes=None):
        out = Path(result.get("expected_output", ""))
        if self.dry_run:
            result["verified"] = "dry_run"
            return result, None
        if not out.exists():
            return result, "converted file not found: {}".format(out)
        if out.stat().st_size == 0:
            return result, "converted file is empty: {}".format(out)
        before = result.get("copy_sha256")
        if before and file_sha256(out) == before:
            return result, ("{} is unchanged since CONN copied the master. Run the IKE "
                            "conversion in CMO and SAVE AS over this file, then verify "
                            "again.".format(out.name))
        sidecar = out.with_suffix(".ike.json")
        meta = {
            "source_master": result.get("master"),
            "pre_ike_snapshot": result.get("snapshot"),
            "converted_file": str(out),
            "converted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sides": sides or [self.cfg.get("play.my_side", "Blue"),
                               self.cfg.get("play.opponent_side", "Red")],
            "turn_length_minutes": turn_minutes or self.cfg.get("play.turn_length_minutes", 30),
            "ike_release": self.cfg.get("ike.ike_release", ""),
            "size_bytes": out.stat().st_size,
            "sha256_head": file_sha256(out, limit=4 << 20),
        }
        sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        result["sidecar"] = str(sidecar)
        result["verified"] = True
        return result, None
