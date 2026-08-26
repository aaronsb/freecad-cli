#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Drive each command's example against a running FreeCAD, record the result.

ADR-501. Reads `fccli/dictionary.json` for commands that carry an `example`,
runs each over the socket the way a person would, and stamps a per-command
entry in `fccli/verified.json`: the date, the FreeCAD version, the example,
and the result.

Nothing here imports FreeCAD. It speaks to `bin/fccli`, which speaks the
socket, so a command is verified through the same door a person uses.

The result is what running the example did:

    ok         ran to completion, engine idle, and every object in the
               active document is valid
    invalid    ran to completion but left an invalid object -- FreeCAD
               computed it and rejected the result (ADR-302, GH #51)
    panel      a task panel is open -- the command is not positional and
               belongs to the panel tier
    incomplete the command is still collecting -- the example did not drive
               it to the end, so the example needs fixing
    busy       the floor was held by someone else (EX_TEMPFAIL)
    broken     the example was rejected outright -- a fault, reason in `detail`
    hazard     the command took the instance down or wedged it -- skipped
               by later sweeps unless --force

A sweep survives its own targets: a command that kills FreeCAD is recorded
as `hazard`, a fresh headless instance is started, and the sweep continues.
The ledger is written after every command, so a stopped sweep loses at most
the command it was on.

`--modemap` drives the drafted examples in `fccli/modemap.json` (positional
commands only) instead of the dictionary's authored ones, and records the
outcomes in `modemap_sweep.json` at the repo root. The tree is untouched: a
draft earns its `example:` field only after it passes here. A draft already
in the report is skipped, so the sweep resumes where it stopped.

A run updates only the commands it drove; every other entry is left as it
was, so a sweep of one workbench does not erase the rest of the ledger.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(ROOT, "bin", "fccli")
DICT = os.path.join(ROOT, "fccli", "dictionary.json")
LEDGER = os.path.join(ROOT, "fccli", "verified.json")
MODEMAP = os.path.join(ROOT, "fccli", "modemap.json")
SWEEP_REPORT = os.path.join(ROOT, "modemap_sweep.json")

# Commands no headless sweep may run. Each has taken an instance down or
# poisoned it, live. GH #61 is the SIGSEGV. The stereo modes switch the
# Coin viewer into a GL mode Xvfb's software renderer does not have, and
# every repaint from then on prints "Unsupported format/type:
# GL_NONE/GL_NONE" -- the spam that once wrote 51GB into /tmp before the
# quota stopped it (GH #62).
_STEREO = "switches the viewer to a stereo GL mode headless GL lacks (GH #62)"
KNOWN_HAZARDS = {
    "Std_ToggleToolBarLock":
        "SIGSEGV: checkable command with no live QAction (GH #61)",
    "Std_TestProgress":
        "modal progress dialog that outlives the client (GH #60)",
    "Std_ViewIvStereoQuadBuff": _STEREO,
    "Std_ViewIvStereoInterleavedColumns": _STEREO,
    "Std_ViewIvStereoInterleavedRows": _STEREO,
    "Std_ViewIvStereoRedGreen": _STEREO,
}


def fccli(*args, **kw):
    kw.setdefault("stdin", subprocess.DEVNULL)
    kw.setdefault("timeout", 60)
    proc = subprocess.run([sys.executable, CLIENT, *args],
                          capture_output=True, text=True, **kw)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def running():
    return fccli("ls")[0] == 0


def start_headless():
    """Start a fresh headless instance, output to the void.

    DEVNULL, not a log file: a poisoned instance can write tens of
    megabytes of repaint errors a second, and a sweep must survive its
    own targets without filling a disk.
    """
    code, _out, _err = fccli("start", "--headless", "--timeout", "90",
                             timeout=120)
    time.sleep(1)
    return code == 0 and running()


def _snapshot():
    """The session's state, as the JSON the server sent.

    The server's own facts, not a scrape of their human rendering
    (ADR-302).
    """
    _, out, _ = fccli("--json", "state")
    try:
        return json.loads(out)
    except ValueError:
        return {}


def classify(code, engine, panel, invalid):
    """The result, from the exec exit code and the state after it.

    ``panel`` is the server's word that a task panel is open. ``invalid``
    is what the run left invalid. A 75 exit means the command never ran
    at all -- the floor or a dialog belongs to someone else -- and an
    open panel may be that very dialog, so busy outranks panel. A panel
    outranks the engine reading: a panel driven from the command line
    keeps the engine collecting, and that is the panel tier, not a short
    example. `ok` requires a clean exit AND nothing left invalid -- a
    command that computes an object FreeCAD rejects has not verified,
    however cleanly it returned.
    """
    if code == 75:
        return "busy"
    if panel:
        return "panel"
    if engine != "idle":
        return "incomplete"
    if code != 0:
        return "broken"
    if invalid:
        return "invalid"
    return "ok"


def _invalid(snap):
    active = next((d for d in snap.get("documents") or []
                   if d.get("active")), {})
    return active.get("invalid") or []


def verify_one(example):
    """Run one example, classify what happened. Leaves the engine idle.

    Invalidity is judged on the delta: what this run made invalid, not
    what it found already broken. An invalid run is undone, so one bad
    example cannot mark every example after it.
    """
    fccli("cancel")                       # clear whatever the last one left
    before = _invalid(_snapshot())
    code, _out, err = fccli("exec", example)
    snap = _snapshot()
    fresh = [n for n in _invalid(snap) if n not in before]
    result = classify(code, snap.get("engine") or "",
                      snap.get("panel"), fresh)
    if result in ("incomplete", "panel"):
        fccli("cancel")
    if result == "invalid":
        fccli("exec", "undo")
        return result, ", ".join(fresh)
    return result, (err if result in ("incomplete", "broken") else "")


def plan(targets, prior, force=False, start_at=None):
    """Split targets into what this sweep runs and what it skips.

    ``prior`` is the record of earlier sweeps, {cid: entry}. A command in
    KNOWN_HAZARDS or recorded `hazard` is skipped; --force runs it anyway.
    """
    run, skipped = {}, {}
    for cid, example in sorted(targets.items()):
        if start_at and cid < start_at:
            continue
        reason = KNOWN_HAZARDS.get(cid)
        if reason is None and prior.get(cid, {}).get("result") == "hazard":
            reason = prior[cid].get("detail", "recorded hazard")
        if reason and not force:
            skipped[cid] = reason
            continue
        run[cid] = example
    return run, skipped


def sweep(targets, record):
    """Run every target, restart a dead instance, checkpoint each result.

    ``record(cid, example, result, detail)`` is called after every
    command -- it owns persistence, so a stopped sweep keeps everything
    already run. Returns (tally, finished).
    """
    tally = {}
    total = len(targets)
    for i, (cid, example) in enumerate(sorted(targets.items()), 1):
        try:
            result, detail = verify_one(example)
        except subprocess.TimeoutExpired:
            result, detail = "hazard", "client timed out; instance wedged"
            try:
                fccli("cancel", timeout=15)
            except subprocess.TimeoutExpired:
                pass
        if not running():
            result, detail = "hazard", "killed the FreeCAD instance"
            print(f"[{i}/{total}] {'hazard':10} {cid} -- restarting FreeCAD",
                  flush=True)
            record(cid, example, result, detail)
            tally[result] = tally.get(result, 0) + 1
            if not start_headless():
                print("verify: restart failed, stopping", file=sys.stderr)
                return tally, False
            fccli("exec", "new verify")
            continue
        record(cid, example, result, detail)
        tally[result] = tally.get(result, 0) + 1
        print(f"[{i}/{total}] {result:10} {cid}  ({example})", flush=True)
    return tally, True


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Verify command examples (ADR-501).")
    ap.add_argument("--only", help="verify one command id, e.g. Part_Box")
    ap.add_argument("--modemap", action="store_true",
                    help="drive the mode map's positional drafts instead, "
                         "recording to modemap_sweep.json; the tree and the "
                         "ledger are untouched")
    ap.add_argument("--start-at", metavar="COMMAND",
                    help="skip every command id before this one")
    ap.add_argument("--force", action="store_true",
                    help="run commands recorded as hazards")
    args = ap.parse_args(argv)

    version = json.load(open(DICT)).get("freecad")
    if args.modemap:
        modemap = json.load(open(MODEMAP))
        targets = {cid: e["example"]
                   for cid, e in modemap["commands"].items()
                   if e.get("mode") == "positional" and e.get("example")}
        store_path = SWEEP_REPORT
        store = {}
        if os.path.exists(store_path):
            store = json.load(open(store_path))
        entries = store
        # Resumable: a draft already recorded is not run again.
        prior = dict(entries)
        if not args.force:
            targets = {c: e for c, e in targets.items() if c not in entries
                       or entries[c].get("example") != e}
    else:
        data = json.load(open(DICT))
        targets = {cid: e["example"] for cid, e in data["commands"].items()
                   if e.get("example")}
        store_path = LEDGER
        store = {}
        if os.path.exists(store_path):
            store = json.load(open(store_path))
        entries = store.setdefault("commands", {})
        prior = entries

    if args.only:
        targets = {k: v for k, v in targets.items() if k == args.only}
    if not targets:
        print("nothing to verify -- no examples, or all already recorded")
        return 0

    run, skipped = plan(targets, prior, force=args.force,
                        start_at=args.start_at)
    for cid, reason in sorted(skipped.items()):
        print(f"  {'skipped':10} {cid}  ({reason})")

    started = False
    if not running():
        print("starting a headless FreeCAD ...")
        if not start_headless():
            print("could not start FreeCAD", file=sys.stderr)
            return 3
        started = True

    if "panel" not in _snapshot():
        print("this FreeCAD predates ADR-302 and cannot report panel or "
              "validity facts -- restart it with the current addon",
              file=sys.stderr)
        return 3

    today = datetime.date.today().isoformat()

    def record(cid, example, result, detail):
        entry = {"example": example, "result": result}
        if not args.modemap:
            entry["date"] = today
            entry["freecad"] = version
        if detail:
            entry["detail"] = detail[:200]
        entries[cid] = entry
        if not args.modemap:
            store["date"] = today
            store["freecad"] = version
        with open(store_path, "w", encoding="utf-8") as fh:
            json.dump(store, fh, indent=1, sort_keys=True)
            fh.write("\n")

    # Skips are recorded too, so the report says why a command was not run.
    for cid, reason in skipped.items():
        record(cid, targets[cid], "hazard", reason)

    fccli("exec", "new verify")
    try:
        tally, finished = sweep(run, record)
    finally:
        if started and running():
            fccli("cancel")
            fccli("exec", "quit!")

    summary = ", ".join(f"{n} {k}" for k, n in sorted(tally.items()))
    print(f"\n{len(run)} run, {len(skipped)} skipped ({summary}). "
          f"{os.path.relpath(store_path, ROOT)}")
    return 0 if finished else 3


if __name__ == "__main__":
    sys.exit(main())
