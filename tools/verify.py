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

A run updates only the commands it drove; every other entry is left as it
was, so a sweep of one workbench does not erase the rest of the ledger.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(ROOT, "bin", "fccli")
DICT = os.path.join(ROOT, "fccli", "dictionary.json")
LEDGER = os.path.join(ROOT, "fccli", "verified.json")


def fccli(*args, **kw):
    kw.setdefault("stdin", subprocess.DEVNULL)
    kw.setdefault("timeout", 60)
    proc = subprocess.run([sys.executable, CLIENT, *args],
                          capture_output=True, text=True, **kw)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def running():
    return fccli("ls")[0] == 0


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
    is the active document's invalid objects. A panel outranks the engine
    reading: a panel being driven from the command line keeps the engine
    collecting, and that is the panel tier, not a short example. `ok`
    requires a clean exit AND a document with nothing invalid in it -- a
    command that computes an object FreeCAD rejects has not verified,
    however cleanly it returned.
    """
    if panel:
        return "panel"
    if engine != "idle":
        return "incomplete"
    if code == 75:
        return "busy"
    if code != 0:
        return "broken"
    if invalid:
        return "invalid"
    return "ok"


def verify_one(example):
    """Run one example, classify what happened. Leaves the engine idle."""
    fccli("cancel")                       # clear whatever the last one left
    code, _out, err = fccli("exec", example)
    snap = _snapshot()
    active = next((d for d in snap.get("documents") or []
                   if d.get("active")), {})
    invalid = active.get("invalid") or []
    result = classify(code, snap.get("engine") or "",
                      snap.get("panel"), invalid)
    if result in ("incomplete", "panel"):
        fccli("cancel")
    if result == "invalid":
        return result, ", ".join(invalid)
    return result, (err if result in ("incomplete", "broken") else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify command examples (ADR-501).")
    ap.add_argument("--only", help="verify one command id, e.g. Part_Box")
    args = ap.parse_args(argv)

    data = json.load(open(DICT))
    version = data.get("freecad")
    targets = {cid: e["example"] for cid, e in data["commands"].items()
               if e.get("example")}
    if args.only:
        targets = {k: v for k, v in targets.items() if k == args.only}
    if not targets:
        print("no commands carry an example yet -- author one and recompile")
        return 0

    started = False
    if not running():
        print("starting a headless FreeCAD ...")
        code, _out, err = fccli("start", "--headless", "--timeout", "90")
        if code != 0:
            print(f"could not start FreeCAD: {err}", file=sys.stderr)
            return 3
        started = True

    ledger = {}
    if os.path.exists(LEDGER):
        ledger = json.load(open(LEDGER))
    entries = ledger.setdefault("commands", {})
    today = datetime.date.today().isoformat()

    fccli("exec", "new verify")
    tally = {}
    try:
        for cid, example in sorted(targets.items()):
            result, detail = verify_one(example)
            entry = {"date": today, "freecad": version,
                     "example": example, "result": result}
            if detail:
                entry["detail"] = detail[:200]
            entries[cid] = entry
            tally[result] = tally.get(result, 0) + 1
            print(f"  {result:7} {cid}  ({example})")
    finally:
        if started:
            fccli("cancel")
            fccli("exec", "quit!")

    ledger["date"] = today
    ledger["freecad"] = version
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1, sort_keys=True)
        fh.write("\n")

    summary = ", ".join(f"{n} {k}" for k, n in sorted(tally.items()))
    print(f"\n{len(targets)} verified ({summary}). "
          f"ledger: {os.path.relpath(LEDGER, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
