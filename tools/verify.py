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
import signal
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
    # Discovered live by the 2026-08-26 draft sweep: each killed the
    # instance. Recorded here so a fresh checkout does not rediscover
    # them by killing FreeCAD three more times.
    "Std_TestProgress2": "killed the FreeCAD instance (draft sweep)",
    "Std_TestProgress3": "killed the FreeCAD instance (draft sweep)",
    "Test_TestWork": "killed the FreeCAD instance (draft sweep)",
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


def _load(path):
    """The store, or a stop. A store that fails to parse ends the run:
    overwriting it would throw away every result it still holds."""
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path))
    except ValueError as exc:
        sys.exit(f"verify: {path} is unreadable ({exc}) -- "
                 f"repair or remove it")


def resumable(targets, entries):
    """Which targets a resumed sweep still runs.

    A result already recorded for the same example is an answer and
    stands -- except `busy`, the floor's state rather than the draft's,
    which is retried; and `hazard`, which stays in the targets so plan()
    reports the skip.
    """
    return {c: e for c, e in targets.items()
            if entries.get(c, {}).get("example") != e
            or entries[c].get("result") in ("hazard", "busy")}


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


def _healthy():
    """The instance answers with facts.

    ``fccli ls`` is not enough: it exits 0 for a live *process*, even one
    whose server no longer answers -- which is exactly the wedged case.
    """
    try:
        return bool(_snapshot())
    except subprocess.TimeoutExpired:
        return False


def _restart():
    """A working headless instance, whatever is there now.

    A wedged instance still holds its socket and would block the start,
    so a FreeCAD that no longer answers is killed first -- and only a
    FreeCAD: the pid comes from a socket filename, and a recycled pid
    must not take the signal. An instance that does answer is reused
    rather than doubled. Returns (ok, started_new): reuse is not
    ownership, and the caller must not quit an instance it only reused.
    """
    try:
        _, out, _ = fccli("--json", "ls", timeout=90)
        rows = json.loads(out)
    except (subprocess.TimeoutExpired, ValueError):
        rows = []
    killed = False
    for row in rows if isinstance(rows, list) else []:
        if row.get("reachable") or not row.get("pid"):
            continue
        try:
            with open(f"/proc/{int(row['pid'])}/comm") as fh:
                comm = fh.read().strip().lower()
        except (OSError, ValueError):
            continue
        if "freecad" not in comm:
            continue
        try:
            os.kill(int(row["pid"]), signal.SIGKILL)
            killed = True
        except OSError:
            pass
    if killed:
        # Killed is not gone: the corpse answers kill(pid, 0) and holds
        # its socket entry until its parent reaps it, so poll.
        for _ in range(20):
            if not running():
                break
            time.sleep(0.5)
    started_new = False
    if not running():
        if not start_headless():
            return False, False
        started_new = True
    if not _healthy():
        return False, started_new
    fccli("exec", "new verify")
    return True, started_new


def _restart_owned(owned):
    """The sweep's restart hook: ownership is a fact the restart updates.

    An instance this sweep started, first or mid-sweep, is quit at the
    end; one it merely reused belongs to whoever started it, and `quit!`
    against a reused instance discards their unsaved documents.
    """
    ok, started_new = _restart()
    if started_new:
        owned["it"] = True
    return ok


def sweep(targets, record, run_one=None, alive=None, healthy=None,
          restart=None):
    """Run every target, restart a dead or wedged instance, checkpoint
    each result.

    ``record(cid, example, result, detail)`` is called after every
    command, hazards included -- it owns persistence, so a stopped sweep
    keeps everything already run. The four hooks default to the real
    client; they exist so this loop is testable without a FreeCAD.
    Returns (tally, finished, restarts).
    """
    run_one = run_one or verify_one
    alive = alive or running
    healthy = healthy or _healthy
    restart = restart or _restart
    tally, restarts = {}, 0
    total = len(targets)
    for i, (cid, example) in enumerate(sorted(targets.items()), 1):
        try:
            result, detail = run_one(example)
        except subprocess.TimeoutExpired:
            result, detail = "hazard", "client timed out; instance wedged"
        if result != "hazard":
            try:
                if not healthy():
                    result = "hazard"
                    detail = ("left the instance unresponsive" if alive()
                              else "killed the FreeCAD instance")
            except subprocess.TimeoutExpired:
                result, detail = "hazard", "left the instance unresponsive"
        record(cid, example, result, detail)
        tally[result] = tally.get(result, 0) + 1
        if result == "hazard":
            print(f"[{i}/{total}] {'hazard':10} {cid} -- restarting FreeCAD",
                  flush=True)
            restarts += 1
            if not restart():
                print("verify: restart failed, stopping", file=sys.stderr)
                return tally, False, restarts
            continue
        print(f"[{i}/{total}] {result:10} {cid}  ({example})", flush=True)
    return tally, True, restarts


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
        store = _load(store_path)
        entries = store
        prior = dict(entries)
        if not args.force:
            targets = resumable(targets, entries)
    else:
        data = json.load(open(DICT))
        targets = {cid: e["example"] for cid, e in data["commands"].items()
                   if e.get("example")}
        store_path = LEDGER
        store = _load(store_path)
        entries = store.setdefault("commands", {})
        prior = dict(entries)

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
        # Written beside and swapped in whole: a checkpoint interrupted
        # mid-dump must not cost the results it was checkpointing.
        tmp = store_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(store, fh, indent=1, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, store_path)

    # Skips are recorded too, so the report says why a command was not run.
    for cid, reason in skipped.items():
        record(cid, targets[cid], "hazard", reason)

    owned = {"it": started}
    fccli("exec", "new verify")
    try:
        tally, finished, restarts = sweep(
            run, record, restart=lambda: _restart_owned(owned))
    finally:
        if owned["it"] and running():
            fccli("cancel")
            fccli("exec", "quit!")

    summary = ", ".join(f"{n} {k}" for k, n in sorted(tally.items()))
    note = (f", {restarts} restart" + ("s" if restarts > 1 else "")
            if restarts else "")
    print(f"\n{len(run)} run, {len(skipped)} skipped ({summary}{note}). "
          f"{os.path.relpath(store_path, ROOT)}")
    return 0 if finished else 3


if __name__ == "__main__":
    sys.exit(main())
